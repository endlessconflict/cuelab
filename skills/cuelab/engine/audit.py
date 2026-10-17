"""Sync audit: measure when things actually happen in the picture, compare with when the cue sheet puts the sound.

One pass over the video (decoded at half resolution), per-frame signals in named regions of interest (ROIs, full-resolution coordinates):
  <colour>      pixels near a project colour (focus, data, ok, bad, white, ...)      cx_<colour>, cy_<colour>   their centroid
  lum           mean luminance                                                         diff   mean absolute change from the previous frame
The project's checks.py declares ROIS and a checks(S, A) function that uses the helpers below (A.first_above, A.last_move, A.steps_of,
A.report, A.stat ...). Tolerances are frames relative to the visual event:
  HARD (-1, +2)  the element snaps in: sound from 33 ms before to 67 ms after
  FADE (-1, +4)  the element fades in: sound may lag the first visible change by up to 4 frames
"""
from __future__ import annotations

import json
import os
import pickle
import subprocess

import numpy as np

import timeline as T

SCALE = 0.5
HARD = (-1.0, 2.0)
FADE = (-1.0, 4.0)
RESULTS: list[dict] = []


# ---------------------------------------------------------------------------------------------------- measurement
def video_pass(video, rois, colors, tol, w, h, scale=SCALE):
    sw, sh = int(w * scale), int(h * scale)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", f"scale={sw}:{sh}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    fsz = sw * sh * 3
    names = list(colors)
    tg = {k: np.array(v, dtype=np.int16) for k, v in colors.items()}
    S = {r: {**{k: [] for k in names}, **{"cx_" + k: [] for k in names}, **{"cy_" + k: [] for k in names}, "lum": [], "diff": []} for r in rois}
    prev = None
    n = 0
    while True:
        buf = p.stdout.read(fsz)
        if len(buf) < fsz:
            break
        fr = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3).astype(np.int16)
        cur = {}
        for r, (x, y, rw, rh) in rois.items():
            sx, sy, ww, hh = int(x * scale), int(y * scale), max(1, int(rw * scale)), max(1, int(rh * scale))
            a = fr[sy : sy + hh, sx : sx + ww]
            cur[r] = a
            d = S[r]
            d["lum"].append(float(a.mean()))
            d["diff"].append(float(np.abs(a - prev[r]).mean()) if prev is not None else 0.0)
            for k in names:
                m = np.all(np.abs(a - tg[k]) < tol, axis=2)
                d[k].append(int(m.sum()))
                if m.sum() > 4:
                    ys, xs = np.nonzero(m)
                    d["cx_" + k].append(float(xs.mean() / scale + x))
                    d["cy_" + k].append(float(ys.mean() / scale + y))
                else:
                    d["cx_" + k].append(float("nan"))
                    d["cy_" + k].append(float("nan"))
        prev = cur
        n += 1
    p.wait()
    return {r: {k: np.array(v) for k, v in d.items()} for r, d in S.items()}, n


def series(project, rois, force=False):
    cache = os.path.join(project.out, "series.pkl")
    if os.path.exists(cache) and not force and os.path.getmtime(cache) > os.path.getmtime(project.video):
        c = pickle.load(open(cache, "rb"))
        if set(c[0]) == set(rois):
            return c
    w, h = _size(project.video)
    S, n = video_pass(project.video, rois, project.cfg["colors"], project.cfg["color_tol"], w, h)
    pickle.dump((S, n), open(cache, "wb"))
    return S, n


def _size(video):
    o = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", video], capture_output=True, text=True).stdout)["streams"][0]
    return o["width"], o["height"]


# ---------------------------------------------------------------------------------------------------- helpers for checks.py
def onset(sig, lo, hi, frac=0.1, base=None):
    """first frame in [lo, hi) where sig rises above base + frac * (max - base)"""
    seg = sig[lo:hi]
    b = seg[0] if base is None else base
    m = seg.max()
    if m - b <= 1e-9:
        return None
    idx = np.nonzero(seg > b + frac * (m - b))[0]
    return lo + int(idx[0]) if len(idx) else None


def settle(sig, lo, hi, frac=0.9, base=None):
    seg = sig[lo:hi]
    b = seg[0] if base is None else base
    m = seg.max()
    idx = np.nonzero(seg >= b + frac * (m - b))[0]
    return lo + int(idx[0]) if len(idx) else None


def first_above(sig, lo, hi, thr):
    idx = np.nonzero(np.nan_to_num(np.asarray(sig[lo:hi])) > thr)[0]
    return lo + int(idx[0]) if len(idx) else None


def last_move(sig, lo, hi, thr):
    """last frame in [lo, hi) where the signal still moves more than thr per frame (a thing 'arrives' when this ends)"""
    seg = np.nan_to_num(np.asarray(sig[lo:hi]))
    mv = np.nonzero(np.abs(np.diff(seg)) > thr)[0]
    return lo + int(mv[-1]) + 1 if len(mv) else None


def steps_of(vals, lo, jump):
    """frames at which a (possibly NaN) series jumps by more than `jump` between consecutive frames"""
    return [lo + i + 1 for i in range(len(vals) - 1) if not np.isnan(vals[i]) and not np.isnan(vals[i + 1]) and abs(vals[i + 1] - vals[i]) > jump]


def edges(sig, lo, hi, thr, rising=True):
    """frames at which a count series steps up (rising) or down by more than thr; neighbouring steps are merged.
    A thing that stops being focus-coloured (a value locks) shows up as a falling edge of the colour count."""
    seg = np.nan_to_num(np.asarray(sig[lo : hi + 1], dtype=float))
    d = np.diff(seg)
    idx = np.nonzero(d > thr)[0] if rising else np.nonzero(d < -thr)[0]
    out = []
    for i in idx:
        if not out or lo + i + 1 - out[-1] > 1:
            out.append(lo + int(i) + 1)
    return out


def report(name, visual, cue, note="", tol=HARD):
    if visual is None or cue is None:
        RESULTS.append(dict(name=name, visual=None, cue=None, offset_f=None, ms=None, ok=False, note="not measurable " + note))
        print(f"  ?? {name:52s} not measurable {note}")
        return
    off = cue - visual
    ok = tol[0] <= off <= tol[1]
    RESULTS.append(dict(name=name, visual=float(visual), cue=float(cue), offset_f=float(off), ms=float(off / T.FPS * 1000), ok=bool(ok), note=note))
    print(f"  {'OK' if ok else 'XX'} {name:52s} visual f{visual:7.1f}  cue f{cue:7.1f}  offset {off:+5.1f} f = {off / T.FPS * 1000:+6.0f} ms  [{note}]")


def stat(name, errs, tol=HARD, note=""):
    errs = np.asarray(errs, dtype=float)
    if not len(errs):
        RESULTS.append(dict(name=name, visual=None, cue=None, offset_f=None, ms=None, ok=False, note="no data"))
        print(f"  ?? {name}: no data")
        return
    ok = bool(np.all((errs >= tol[0]) & (errs <= tol[1])))
    RESULTS.append(dict(name=name, visual=None, cue=None, offset_f=float(errs.mean()), ms=float(errs.mean() / T.FPS * 1000), ok=ok, note=f"n={len(errs)} range [{errs.min():+.2f}, {errs.max():+.2f}] f {note}"))
    print(f"  {'OK' if ok else 'XX'} {name:52s} mean {errs.mean():+.2f} f  range [{errs.min():+.2f}, {errs.max():+.2f}] f  n={len(errs)}")


def cue_frames(cues, typ, lo=0, hi=10**9):
    return sorted(c["f"] for c in cues if c["t"] == typ and lo <= c["f"] < hi)


class A:  # namespace handed to checks(S, A)
    pass


for _n in ("onset", "settle", "first_above", "last_move", "steps_of", "edges", "report", "stat", "cue_frames", "HARD", "FADE"):
    setattr(A, _n, staticmethod(globals()[_n]) if callable(globals()[_n]) else globals()[_n])


def run(project, force=False):
    cm = project.module("checks")
    if cm is None:
        raise SystemExit("project has no checks.py")
    cues = json.load(open(os.path.join(project.out, "cues.json"), encoding="utf-8"))
    A.cues = cues
    A.T = T
    S, n = series(project, cm.ROIS, force)
    if n != T.total_frames():
        print(f"WARNING decoded {n} frames, timeline says {T.total_frames()}")
    print(f"measuring {os.path.basename(project.video)}: {n} frames")
    RESULTS.clear()
    cm.checks(S, A)
    ok = sum(1 for r in RESULTS if r["ok"])
    print(f"\n{ok}/{len(RESULTS)} checks inside tolerance")
    json.dump(RESULTS, open(os.path.join(project.out, "sync_audit.json"), "w"), indent=1)
    return ok, len(RESULTS)
