"""Audio quality checks on the rendered stems and master. There are no ears in the loop, so everything measurable is measured:

  1 onset latency   cue time versus the detected onset of its own click in the effects stem
  2 focal vs bed    tier-1 sounds over the music at the same moment (do the important sounds read?)
  3 spectral balance per scene (fatigue above 6 kHz, bass present, mud)
  4 phone speaker   the master through a 230 Hz high-pass: how much loudness survives
  5 mono sum        loss when L and R are summed, and L/R correlation
  6 hygiene         first and last samples, DC offset, music level during a declared silence
  7 click detector  unexplained discontinuities in the master and the music stem (intended transients are excluded)
"""
from __future__ import annotations

import json
import os

import numpy as np
from scipy import signal
from scipy.io import wavfile

import mix as MX
import timeline as T
from dsp import SR


def _load(p):
    return wavfile.read(p)[1].astype(np.float64)


def dbfs(x):
    return 20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-12)


def run(project):
    cfg = project.cfg
    o = project.out
    rep = {}
    mix = _load(os.path.join(o, "mix.wav"))
    sfx = _load(os.path.join(o, "stems", "sfx.wav"))
    mus = _load(os.path.join(o, "stems", "music.wav"))
    t1 = np.load(os.path.join(o, "stems", "t1.npy")).astype(np.float64)
    cues = json.load(open(os.path.join(o, "cues.json"), encoding="utf-8"))
    FPS = T.FPS

    # 1 ---------------------------------------------------------------------------------------------- latency
    mono = sfx.mean(axis=1)
    e = np.abs(signal.sosfilt(signal.butter(2, 3000, "high", fs=SR, output="sos"), mono))
    e = signal.lfilter(*signal.butter(1, 800, fs=SR), e)
    de = np.gradient(e)
    kinds = set(cfg["latency_cue_types"])
    offs = []
    for c in cues:
        if c["t"] not in kinds or c["tier"] == 3:
            continue
        t0 = c["f"] / FPS
        a, b = int((t0 - 0.010) * SR), int((t0 + 0.030) * SR)
        if a < 0 or b >= len(de):
            continue
        if any(d is not c and abs(d["f"] - c["f"]) < 1.2 and d["t"] != "marker" for d in cues):
            continue  # crowded: another sound within 40 ms would pollute the measurement
        offs.append((a + int(np.argmax(de[a:b]))) / SR * 1000 - t0 * 1000)
    if offs:
        offs = np.array(offs)
        rep["onset_latency_ms"] = dict(n=int(len(offs)), mean=float(offs.mean()), p95=float(np.percentile(offs, 95)), max=float(offs.max()), min=float(offs.min()))
        print(f"1. onset latency: n={len(offs)} mean {offs.mean():+.1f} ms, p95 {np.percentile(offs, 95):+.1f} ms, range [{offs.min():+.1f}, {offs.max():+.1f}] ms")

    # 2 ----------------------------------------------------------------------------------------------- focal vs bed
    snr = []
    for c in cues:
        if c["tier"] != 1 or c["t"] in ("marker",):
            continue
        t0 = c["f"] / FPS
        a, b = int(t0 * SR), int((t0 + 0.25) * SR)
        if b >= len(sfx):
            continue
        snr.append((c["t"], c["f"], dbfs(t1[a:b]) - max(dbfs(mus[a:b]), -90)))
    if snr:
        arr = np.array([s[2] for s in snr])
        rep["tier1_over_music_db"] = dict(n=len(arr), median=float(np.median(arr)), p10=float(np.percentile(arr, 10)), p90=float(np.percentile(arr, 90)))
        print(f"2. focal events over the music bed (250 ms): median {np.median(arr):+.1f} dB, p10 {np.percentile(arr, 10):+.1f}, p90 {np.percentile(arr, 90):+.1f} (n={len(arr)})")

    # 3 ----------------------------------------------------------------------------------------------- balance
    bands = [(20, 60, "sub"), (60, 250, "bass"), (250, 500, "lowmid"), (500, 2000, "mid"), (2000, 5000, "presence"), (5000, 10000, "air"), (10000, 20000, "top")]
    print("3. spectral balance per scene (dB below total)")
    print("   scene      " + "".join(f"{b[2]:>9s}" for b in bands))
    rep["bands"] = {}
    names = [s for s, _ in T.SCENES]
    for i, n in enumerate(names):
        a = T.START[n] / FPS
        b = (T.START[names[i + 1]] if i + 1 < len(names) else T.total_frames()) / FPS
        seg = mix[int(a * SR) : int(b * SR)].mean(axis=1)
        f, p = signal.welch(seg, SR, nperseg=8192)
        row = [10 * np.log10(p[(f >= lo) & (f < hi)].sum() / p.sum() + 1e-12) for lo, hi, _ in bands]
        rep["bands"][n] = row
        print(f"   {n:10s} " + "".join(f"{v:9.1f}" for v in row))

    # 4 ----------------------------------------------------------------------------------------------- phone
    ph = signal.sosfilt(signal.butter(2, 9000, "low", fs=SR, output="sos"), signal.sosfilt(signal.butter(4, 230, "high", fs=SR, output="sos"), mix, axis=0), axis=0)
    lf, lp_ = MX.lufs_integrated(mix), MX.lufs_integrated(ph)
    rep["phone_lufs_drop_db"] = float(lf - lp_)
    print(f"4. phone-speaker simulation (HP 230 Hz): {lf:.1f} -> {lp_:.1f} LUFS (drop {lf - lp_:.1f} dB)")

    # 5 ----------------------------------------------------------------------------------------------- mono
    m = mix.mean(axis=1, keepdims=True)
    lm = MX.lufs_integrated(np.repeat(m, 2, axis=1))
    rep["mono_drop_db"] = float(lf - lm)
    rep["lr_correlation"] = float(np.corrcoef(mix[:, 0], mix[:, 1])[0, 1])
    print(f"5. mono sum {lm:.1f} LUFS vs stereo {lf:.1f} (loss {lf - lm:.2f} dB), L/R correlation {rep['lr_correlation']:.2f}")

    # 6 ----------------------------------------------------------------------------------------------- hygiene
    rep["last_10ms_dbfs"] = float(dbfs(mix[-480:]))
    rep["dc"] = [float(v) for v in mix.mean(axis=0)]
    print(f"6. last 10 ms {rep['last_10ms_dbfs']:.1f} dBFS, DC {rep['dc']}")
    for c in cues:
        if c["t"] == "marker" and c.get("silence"):
            a, b = int(c["f"] / FPS * SR), int(c["silence"] / FPS * SR)
            rep["music_during_silence_dbfs"] = float(dbfs(mus[a:b]))
            print(f"   music stem during the declared silence (frames {c['f']:.0f}-{c['silence']:.0f}): {rep['music_during_silence_dbfs']:.1f} dBFS")

    # 7 ----------------------------------------------------------------------------------------------- clicks
    grid = cfg["grid_frames"]
    known = np.array([c["f"] / FPS * SR for c in cues if c["tier"] < 3])

    def clicks(x, name):
        mono = x.mean(axis=1)
        d2 = np.abs(np.diff(mono, 2))
        loc = np.repeat(signal.medfilt(d2[::48], 41), 48)[: len(d2)]
        bad = np.nonzero(((d2 / (loc + 1e-9)) > 60) & (d2 > 0.01))[0]
        out, last = [], -10**9
        for i in bad:
            if i - last < 240:
                continue
            last = i
            fr = i / SR * FPS
            if len(known) and np.min(np.abs(known - i)) < 0.02 * SR:
                continue
            if min(fr % grid, grid - fr % grid) < 0.45:
                continue  # a drum hit on the music grid
            out.append(round(float(fr), 1))
        print(f"7. {name}: {len(out)} unexplained discontinuities {out[:12]}")
        return out

    rep["clicks_master"] = clicks(mix, "master")
    rep["clicks_music"] = clicks(mus, "music stem")
    json.dump(rep, open(os.path.join(o, "quality_report.json"), "w"), indent=1)
    return rep
