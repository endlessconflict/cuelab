"""Mixdown and master. Everything is driven by project.json; the only code a project adds is `post()` in music.py.

Chain: effects rig (+ room/hall reverb returns) | score stems (pad lowpassed, bass high-passed, arp lowpassed)
       -> project post() hook (mutes, bus filters) -> sum -> energy arc -> side-chain duck from tier-1 sounds
       -> + sfx + room tone -> top-end tilt -> master fade -> high-pass -> soft glue -> loudness to target -> look-ahead true-peak limiter
Loudness is measured with an ITU-R BS.1770-4 meter written here (K-weighting, gated blocks) and cross-checked against ffmpeg ebur128.
"""
from __future__ import annotations

import json
import sys
import os
import subprocess

import numpy as np
from scipy import signal
from scipy.io import wavfile

import cuelib
import synth as SY
import timeline as T
from dsp import SR, db, hp, lp, sweep_filter


# ------------------------------------------------------------------------------------------------ measurement (BS.1770-4)
def k_weight(x):
    y = signal.lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585], x, axis=0)
    return signal.lfilter([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], y, axis=0)


def lufs_integrated(x):
    k = k_weight(x)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([np.mean(k[s : s + blk] ** 2, axis=0).sum() for s in range(0, len(k) - blk + 1, hop)])
    loud = -0.691 + 10 * np.log10(ms + 1e-14)
    keep = ms[loud > -70]
    if not len(keep):
        return -70.0
    rel = -0.691 + 10 * np.log10(np.mean(keep)) - 10
    return -0.691 + 10 * np.log10(np.mean(ms[loud > rel]) + 1e-14)


def short_term(x, win=3.0, hop=1.0):
    k = k_weight(x)
    w, h = int(win * SR), int(hop * SR)
    return np.array([-0.691 + 10 * np.log10(np.mean(k[s : s + w] ** 2, axis=0).sum() + 1e-14) for s in range(0, len(k) - w + 1, h)])


def lra(x):
    """EBU R128 loudness range (LU): 95th minus 10th percentile of gated 3 s short-term values"""
    k = k_weight(x)
    w, h = int(3 * SR), int(0.5 * SR)
    st = np.array([-0.691 + 10 * np.log10(np.mean(k[s : s + w] ** 2, axis=0).sum() + 1e-14) for s in range(0, len(k) - w + 1, h)])
    st = st[st > -70]
    ref = -0.691 + 10 * np.log10(np.mean(10 ** ((st + 0.691) / 10))) - 20
    st = st[st > ref]
    return float(np.percentile(st, 95) - np.percentile(st, 10))


def true_peak_db(x):
    return 20 * np.log10(np.max(np.abs(signal.resample_poly(x, 4, 1, axis=0))) + 1e-12)


# ------------------------------------------------------------------------------------------------ helpers
def env_follow(x_mono, att=0.004, rel=0.22):
    a = np.abs(x_mono)
    fast = signal.lfilter([1 - np.exp(-1 / (att * SR))], [1, -np.exp(-1 / (att * SR))], a)
    slow = signal.lfilter([1 - np.exp(-1 / (rel * SR))], [1, -np.exp(-1 / (rel * SR))], a)
    return np.maximum(fast, slow)


def gain_curve(points, n):
    """points [(frame, dB)] -> per-sample linear gain; interpolation is linear in dB. Empty list = unity."""
    if not points:
        return np.ones(n)
    fr = np.array([p[0] for p in points], dtype=float)
    d = np.array([p[1] for p in points], dtype=float)
    return db(np.interp(np.arange(n) / SR * T.FPS, fr, d))


def tame(x, n):
    return x[:n] if len(x) >= n else np.pad(x, ((0, n - len(x)), (0, 0)))


def room_tone(n, level_dbfs):
    x = SY.room_tone(n / SR, seed=5, level=1.0)
    x = x / (np.sqrt(np.mean(x**2)) + 1e-9) * db(level_dbfs)
    return np.stack([x, np.roll(x, 211)], axis=1)


def bus_filter_sweep(arrays, frames, fc_from=12000.0, fc_to=260.0, warm=0.6, q=0.8):
    """close then reopen a low-pass lid over the listed stems between frames (a, b_close, c_open).
    The filter is warmed up on 0.6 s of signal and only the settled part is written back, so no state click."""
    a, b, c = (int(T.sec(f) * SR) for f in frames)
    w = int(warm * SR)
    for arr in arrays:
        seg = arr[a - w : c + w].copy()
        fc = np.concatenate([np.full(w, fc_from), np.exp(np.linspace(np.log(fc_from), np.log(fc_to), b - a)), np.exp(np.linspace(np.log(fc_to), np.log(fc_from), c - b)), np.full(w, fc_from)])
        for ch in (0, 1):
            seg[:, ch] = sweep_filter(seg[:, ch], fc, q=q, kind="lp")
        arr[a:c] = seg[w : w + (c - a)]


def mute(arrays, f0, f1, fade_in_frames=22):
    """silence the given stems from f0 to f1 (tiny fade into the silence, a short fade out of it)"""
    n = arrays[0].shape[0]
    pts = [(0, 0), (f0 - 2, 0), (f0 + 1, -80), (f1 - fade_in_frames, -80), (f1 - fade_in_frames * 0.1, -30), (f1, 0), (T.total_frames() + 100, 0)]
    c = gain_curve(pts, n)[:, None]
    for a in arrays:
        a *= c


def limiter(x, ceil_db=-1.8, look_ms=4.0, rel_ms=90.0):
    """look-ahead peak limiter on the 4x-oversampled peak. Gain reduction is the running minimum over the look-ahead, smoothed (no clicks),
    then released with a one-pole. No delay is introduced: the look-ahead only shapes the gain."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d

    c = db(ceil_db)
    pk = np.max(np.abs(signal.resample_poly(x, 4, 1, axis=0)), axis=1)
    need = np.minimum(1.0, c / np.maximum(pk, 1e-9))[::4]
    w = int(look_ms / 1000 * SR)
    need = uniform_filter1d(minimum_filter1d(need, size=2 * w + 1, mode="nearest"), size=w + 1, mode="nearest")
    r = np.exp(-1.0 / (rel_ms / 1000 * SR))
    gain = np.empty_like(need)
    acc = 1.0
    for i, v in enumerate(need):
        acc = v if v < acc else v + (acc - v) * r
        gain[i] = acc
    return x * np.minimum(gain, 1.0)[: len(x), None]


# ------------------------------------------------------------------------------------------------ the build
def build(project, write=True, verbose=True):
    cfg = project.cfg
    N = int(round(T.duration() * SR))
    cm = project.module("cues")
    mm = project.module("music")

    # effects
    C = cuelib.Cues()
    cm.build(C, T)
    rig = cuelib.render(C, extra=getattr(cm, "HANDLERS", None))
    room_ret, hall_ret = cuelib.apply_reverbs(rig)
    sfx = tame(rig.dry.buf, N) + tame(room_ret, N) * db(-4) + tame(hall_ret, N) * db(-3)
    t1 = tame(rig.t1.buf, N)

    # score
    st = mm.build(T)
    arr = {name: tame(tr.buf, N) for name, tr in st.dict().items()}
    arr["pad"] = lp(arr["pad"], 7000)
    arr["bass"] = hp(arr["bass"], 32)
    arr["arp"] = lp(arr["arp"], 9000)
    if hasattr(mm, "post"):
        mm.post(arr, dict(N=N, T=T, mix=sys.modules[__name__], cfg=cfg))
    music = sum(arr.values())
    music = music * gain_curve(cfg["arc"], N)[:, None]
    env = env_follow(t1.mean(axis=1), 0.004, cfg["duck_release"])
    music_d = music * db(-cfg["duck_db"] * np.clip(env / db(-27), 0, 1))[:, None]

    mix = music_d * db(cfg["music_trim"]) + sfx * db(cfg["sfx_trim"]) + room_tone(N, cfg["room_tone_dbfs"])
    mix = mix - cfg["tilt"] * hp(mix, 6500, order=2)
    outro = gain_curve(cfg["outro"], N)[:, None]
    mix = hp(mix * outro, cfg["hp_hz"], order=4)
    mix = np.tanh(mix * 0.9) / 0.9

    lu = lufs_integrated(mix)
    gain_db = cfg["target_lufs"] - lu
    out = mix * db(gain_db)
    pre_tp = true_peak_db(out)
    # where is the headroom going? the loudest moments before limiting (distinct by 0.5 s), so cues can be trimmed at the source
    pk = np.abs(out).max(axis=1)
    order = np.argsort(pk)[::-1]
    peaks, seen = [], []
    for i in order:
        fr = i / SR * T.FPS
        if all(abs(fr - s) > 15 for s in seen):
            seen.append(fr)
            peaks.append((round(float(fr), 1), round(float(20 * np.log10(pk[i] + 1e-12)), 1)))
        if len(peaks) >= 6:
            break
    out = limiter(out, ceil_db=cfg["ceiling_db"] - 0.25)
    for _ in range(3):
        tp = true_peak_db(out)
        if tp <= cfg["ceiling_db"]:
            break
        out = out * db(cfg["ceiling_db"] - tp - 0.05)
    lu2 = lufs_integrated(out)
    if lu2 < cfg["target_lufs"] - 0.3:  # the limiter ate loudness: raise the input once and limit again
        out = limiter(mix * db(gain_db + (cfg["target_lufs"] - lu2)), ceil_db=cfg["ceiling_db"] - 0.25)
        tp = true_peak_db(out)
        if tp > cfg["ceiling_db"]:
            out = out * db(cfg["ceiling_db"] - tp - 0.05)
    rep = {
        "lufs_integrated": float(lufs_integrated(out)),
        "lra_lu": lra(out),
        "true_peak_db": float(true_peak_db(out)),
        "pre_limiter_true_peak_db": float(pre_tp),
        "loudest_frames_pre_limiter": peaks,
        "lufs_sfx_only": float(lufs_integrated(sfx * db(cfg["sfx_trim"] + gain_db) * outro)),
        "lufs_music_only": float(lufs_integrated(music_d * db(cfg["music_trim"] + gain_db) * outro)),
        "cue_count": len(C),
    }
    if verbose:
        print(json.dumps(rep, indent=1))
    if write:
        o = project.out
        wavfile.write(os.path.join(o, "mix.wav"), SR, out.astype(np.float32))
        wavfile.write(os.path.join(o, "stems", "sfx.wav"), SR, (sfx * db(cfg["sfx_trim"] + gain_db) * outro).astype(np.float32))
        wavfile.write(os.path.join(o, "stems", "music.wav"), SR, (music_d * db(cfg["music_trim"] + gain_db) * outro).astype(np.float32))
        np.save(os.path.join(o, "stems", "t1.npy"), t1.astype(np.float32))
        json.dump(rep, open(os.path.join(o, "mix_report.json"), "w"), indent=1)
        json.dump(C.sorted(), open(os.path.join(o, "cues.json"), "w"), indent=0)
    return rep


def mux(project):
    """copy the video stream untouched, add the AAC track (the encoder delay is compensated by the container's edit list)"""
    cfg = project.cfg
    dst = os.path.join(project.out, os.path.splitext(os.path.basename(project.video))[0] + "-sound.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", project.video, "-i", os.path.join(project.out, "mix.wav"), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", cfg["audio_bitrate"], "-ar", "48000", "-ac", "2", "-movflags", "+faststart", dst]
    subprocess.run(cmd, check=True)
    return dst
