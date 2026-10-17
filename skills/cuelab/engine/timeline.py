"""The frame timeline of the picture, loaded from the same timeline.json the video project renders from.

    import timeline as T
    T.load("path/to/timeline.json")      # once, before anything else
    T.g("proof", 206)                     # global frame of scene-local frame 206
    T.prog(f, a, b, "inOut")              # exact port of the picture's easing
    T.inv_prog(0.25, a, b, "inOut")       # the (fractional) frame at which that easing reaches 25 percent
    T.landing(a, b, "out", dist_px)       # the frame at which a motion has visibly stopped

timeline.json:  { "fps": 30, "overlap": 10, "scenes": [{"name": "hook", "frames": 120}, ...],
                  "ease": {"out": [x1, y1, x2, y2], "inOut": [...], "soft": [...]} }
Scene i starts at start(i-1) + frames(i-1) - overlap (scene i is wiped in over `overlap` frames while scene i-1 keeps playing).
"""
from __future__ import annotations

import json
import os

SR = 48000
FPS = 30
OVL = 10
SCENES: list[tuple[str, int]] = []
START: dict[str, int] = {}
EASE: dict[str, tuple[float, float, float, float]] = {}
_EZ: dict = {}
_TOTAL = 0


def _bezier(p1x, p1y, p2x, p2y):
    """CSS cubic-bezier(x1,y1,x2,y2): bisection on x (60 steps is far below one audio sample of error)"""

    def cx(t):
        return 3 * p1x * t * (1 - t) ** 2 + 3 * p2x * t * t * (1 - t) + t**3

    def cy(t):
        return 3 * p1y * t * (1 - t) ** 2 + 3 * p2y * t * t * (1 - t) + t**3

    def f(x):
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if cx(mid) < x:
                lo = mid
            else:
                hi = mid
        return cy((lo + hi) / 2)

    return f


def load(path_or_dict):
    """(re)load the timeline. Mutates START/SCENES/EASE in place so earlier `from timeline import START` references stay valid."""
    global FPS, OVL, _TOTAL
    cfg = path_or_dict if isinstance(path_or_dict, dict) else json.load(open(path_or_dict, encoding="utf-8"))
    FPS = int(cfg.get("fps", 30))
    OVL = int(cfg.get("overlap", 10))
    SCENES[:] = [(s["name"], int(s["frames"])) for s in cfg["scenes"]]
    START.clear()
    t = 0
    for i, (n, d) in enumerate(SCENES):
        START[n] = t
        t = START[n] + d - OVL
    _TOTAL = START[SCENES[-1][0]] + SCENES[-1][1]
    EASE.clear()
    EASE.update({k: tuple(v) for k, v in cfg["ease"].items()})
    _EZ.clear()
    _EZ.update({k: _bezier(*v) for k, v in EASE.items()})
    return cfg


def total_frames() -> int:
    return _TOTAL


def duration() -> float:
    return _TOTAL / FPS


def prog(frame: float, a: float, b: float, ease: str = "out") -> float:
    """port of the picture's prog(): 0..1 between frames a and b, clamped, with a named easing"""
    if b == a:
        return 1.0 if frame >= b else 0.0
    x = min(1.0, max(0.0, (frame - a) / (b - a)))
    return _EZ[ease](x)


def inv_prog(y: float, a: float, b: float, ease: str = "out") -> float:
    """frame (fractional) at which prog() reaches y"""
    y = min(1.0, max(0.0, y))
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if _EZ[ease](mid) < y:
            lo = mid
        else:
            hi = mid
    return a + (b - a) * (lo + hi) / 2


def landing(a: float, b: float, ease: str, dist_px: float, thr_px: float = 0.5) -> float:
    """frame at which a thing travelling dist_px over frames a..b is moving slower than thr_px per frame for good:
    when the eye reads it as arrived"""
    f = b
    while f > a:
        if abs(prog(f, a, b, ease) - prog(f - 1, a, b, ease)) * dist_px > thr_px:
            return f
        f -= 0.25
    return a


def g(scene: str, local: float) -> float:
    """global frame of a scene-local frame"""
    return START[scene] + local


def sec(frame: float) -> float:
    return frame / FPS


def smp(frame: float) -> int:
    return int(round(frame / FPS * SR))


def scene_of(frame: float) -> str:
    cur = SCENES[0][0]
    for n, _ in SCENES:
        if frame >= START[n]:
            cur = n
    return cur


# ---- seeded randomness shared with the picture (port of anim.ts hash) -------------------------------------------------
def _imul(a: int, b: int) -> int:
    return ((a & 0xFFFFFFFF) * (b & 0xFFFFFFFF)) & 0xFFFFFFFF


def hash01(n: int) -> float:
    """Math.imul based hash used by the video templates; identical values in Python and TypeScript"""
    x = _imul((n ^ 0x9E3779B9) & 0xFFFFFFFF, 0x85EBCA6B)
    x ^= x >> 13
    x = _imul(x, 0xC2B2AE35)
    x ^= x >> 16
    return (x & 0xFFFFFFFF) / 4294967295
