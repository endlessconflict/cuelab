"""Cue sheet and the effect handlers that turn cues into sound.

A cue is a dict:  {f: global frame (float), t: type, tier: 1|2|3, gain: dB, pan: -1..1, ...type params}
tier 1 = focal (the lesson, the focus element), tier 2 = interface detail, tier 3 = ambience and captions.
Tier 1 sounds are what the music ducks under.

    from cuelib import Cues
    C = Cues()
    C.add(g("hook", 64), "ping", tier=1, midi=81, gain=-12, pan=-0.5)

Projects may register their own handlers with @handler("my_type") (see render()).

Rig output (stereo Tracks, same length as the video + 4 s tail):
  dry   the sounds   room  send to a short room reverb   hall  send to a long hall reverb   t1  tier-1 copy for ducking
"""
from __future__ import annotations

import numpy as np
from scipy import signal

import synth as S
import timeline as T
from dsp import SR, Track, db, fade, make_ir, midi, n_of, pan_curve, pan_stereo, sweep_filter

HANDLERS: dict = {}


def handler(name):
    """decorator: register fn(rig, cue, index) as the renderer of cue type `name`"""

    def deco(fn):
        HANDLERS[name] = fn
        return fn

    return deco


class Cues:
    def __init__(self):
        self.list: list[dict] = []

    def add(self, f, t, tier=2, **kw):
        self.list.append(dict(f=float(f), t=t, tier=tier, **kw))
        return self

    def sorted(self):
        return sorted(self.list, key=lambda c: (c["f"], c["tier"]))

    def __iter__(self):
        return iter(self.sorted())

    def __len__(self):
        return len(self.list)


class Rig:
    def __init__(self):
        L = T.duration() + 4
        self.dry = Track(L, "dry")
        self.room = Track(L, "room")
        self.hall = Track(L, "hall")
        self.t1 = Track(L, "t1")
        self.log = []

    def emit(self, sig, f, gain=0.0, pan=0.0, room=-99.0, hall=-99.0, tier=2, label=""):
        t = T.sec(f)
        st = pan_stereo(sig, pan) if sig.ndim == 1 else sig
        self.dry.add(st, t, gain, label=label)
        if room > -90:
            self.room.add(st, t, gain + room)
        if hall > -90:
            self.hall.add(st, t, gain + hall)
        if tier == 1:
            self.t1.add(st, t, gain)
        self.log.append((f, label, gain))


def eased(a, b, ease, f0, n):
    """eased progress (0..1) of a motion that runs over frames a..b, sampled at each of n samples of a sound that starts at global
    frame f0. This is how a sound follows a moving thing: pitch rides the position, loudness rides the speed."""
    idx = np.arange(0, n, 16)
    vals = np.array([T.prog(f0 + i / SR * T.FPS, a, b, ease) for i in idx])
    return np.interp(np.arange(n), idx, vals)


def _env(n, atk=0.01, rel=0.03):
    return np.minimum(1, np.arange(n) / (atk * SR)) * np.minimum(1, (n - np.arange(n)) / (rel * SR))


CHORDS = {  # midi voicings; extend from the project
    "Em9": [64, 67, 71, 74, 78],
    "Emaj9": [64, 68, 71, 75, 78],
    "Cmaj9": [60, 64, 67, 71, 74],
    "Am9": [57, 60, 64, 67, 71],
    "Dm9": [62, 65, 69, 72, 76],
    "Dmaj9": [62, 66, 69, 73, 76],
    "Fmaj9": [65, 69, 72, 76, 79],
    "Gadd9": [67, 71, 74, 79, 81],
}


# =============================================================================================================== handlers
@handler("wipe")
def _wipe(rig, c, i):
    rig.emit(S.whoosh(0.58, 350, 4300, q=1.1, seed=i, shape="swell", pan0=0.9, pan1=-0.9, air=0.35), c["f"], c.get("gain", -17), room=-12, hall=-16, label="wipe")


@handler("cap")
def _cap(rig, c, i):
    line = c.get("line", 0)
    rig.emit(S.tick(1900 - 350 * line, 0.05, i, tone=0.1), c["f"], c.get("gain", -32 - 1.5 * line), pan=-0.25 + 0.5 * line, room=-10, tier=3, label="cap")


@handler("title_rise")
def _title(rig, c, i):
    p = c.get("pan", 0.0)
    rig.emit(S.whoosh(0.4, 500, 3200, q=1.5, seed=i, shape="rise", pan0=p - 0.2, pan1=p + 0.2), c["f"], c.get("gain", -15), room=-10, hall=-12, label="title")


@handler("bell")
def _bell(rig, c, i):
    rig.emit(S.bell(float(midi(c["midi"])), c.get("dur", 3.2), tau=c.get("tau", 1.0)), c["f"], c["gain"], c.get("pan", 0), hall=-5, tier=c["tier"], label="bell")


@handler("ping")
def _ping(rig, c, i):
    """the focal leitmotif: a pure bright sine, reserved for the picture's focus element"""
    rig.emit(S.ping(float(midi(c["midi"])), c.get("dur", 0.7)), c["f"], c["gain"], c.get("pan", 0), room=-8, hall=-6, tier=1, label="ping")


@handler("ui")
def _ui(rig, c, i):
    rig.emit(S.tick(c["pitch"], 0.04, i), c["f"], c["gain"], c.get("pan", 0), room=-9, tier=c["tier"], label="ui")


@handler("wood")
def _wood(rig, c, i):
    rig.emit(S.wood(c["pitch"], 0.14, i), c["f"], c["gain"], c.get("pan", 0), room=-8, tier=c["tier"], label="wood")


@handler("glass_tick")
def _glass(rig, c, i):
    rig.emit(S.bell(float(midi(c["midi"])), 0.8, ratio=3.1, index=1.4, tau=0.16), c["f"], c["gain"], c.get("pan", 0), room=-6, hall=-8, tier=c["tier"], label="glass_tick")


@handler("swish")
def _swish(rig, c, i):
    p = c.get("pan", 0)
    rig.emit(S.whoosh(0.2, 1600, 4000, q=1.0, seed=i, shape="swell", pan0=p - 0.2, pan1=p + 0.2), c["f"], c.get("gain", -27), tier=3, label="swish")


@handler("revswell")
def _revswell(rig, c, i):
    rig.emit(S.reverse_swell(c["dur"], i, (250, 3800)), c["f"], c.get("gain", -14), hall=-6, tier=1, label="revswell")


@handler("impact")
def _impact(rig, c, i):
    """sub hit with its harmonics (reads on a phone) and an optional bell on top"""
    rig.emit(S.sub_hit(c.get("freq", 55.0), c.get("dur", 1.4), drop=c.get("drop", 1.4), click=c.get("click", 0.15)), c["f"], c.get("gain", -8), c.get("pan", 0) * 0.3, hall=-12, tier=1, label="impact")
    if "midi" in c:
        rig.emit(S.bell(float(midi(c["midi"])), 1.6, index=1.0, tau=0.6), c["f"], c.get("gain", -8) - 7, c.get("pan", 0), hall=-5, tier=1, label="impact_bell")


@handler("thunk")
def _thunk(rig, c, i):
    rig.emit(S.sub_hit(c.get("freq", 70.0), 0.55, drop=1.4, click=0.5), c["f"], c["gain"], c.get("pan", 0), room=-9, tier=c["tier"], label="thunk")


@handler("reject")
def _reject(rig, c, i):
    """something has nowhere to land: dull thud plus a small beating dissonance"""
    rig.emit(S.denied(), c["f"], c.get("gain", -8), c.get("pan", 0), room=-9, hall=-14, tier=1, label="reject")


@handler("chord")
def _chord(rig, c, i):
    """strummed bells (+ sub): a resolution or a payoff. notes = midi list, or chord = name in CHORDS"""
    tones = c.get("notes") or CHORDS[c["chord"]]
    for k, m in enumerate(tones):
        rig.emit(S.bell(float(midi(m)), 3.4, ratio=2.0 if k % 2 else 2.756, index=c.get("index", 1.5), tau=1.5), c["f"] + k * 0.9, c["gain"] - 2.2 * k, pan=-0.5 + k * 0.25, hall=-3, tier=1, label="chord")
    if c.get("sub", True):
        rig.emit(S.sub_hit(float(midi(tones[0] - 24)), 2.4, drop=1.25, click=0.0), c["f"], c["gain"] - 3, hall=-12, tier=1, label="chord_sub")


@handler("glide")
def _glide(rig, c, i):
    """the voice of a moving focus element: pitch m0 -> m1 and pan pan0 -> pan1 follow the eased position"""
    n = n_of((c["b"] - c["a"]) / T.FPS)
    u = eased(c["a"], c["b"], c["ease"], c["f"], n)
    f0, f1 = float(midi(c["m0"])), float(midi(c["m1"]))
    ph = 2 * np.pi * np.cumsum(f0 * (f1 / f0) ** u) / SR
    x = np.sin(ph) + 0.2 * np.sin(2 * ph)
    x = x * _env(n, 0.01, 0.03) / (np.max(np.abs(x)) + 1e-9)
    rig.emit(pan_curve(x, c.get("pan0", 0) + (c.get("pan1", 0) - c.get("pan0", 0)) * u), c["f"], c.get("gain", -17), room=-8, hall=-9, tier=1, label="glide")


@handler("sweep")
def _sweep(rig, c, i):
    """a front crossing something: a noise band whose centre follows the eased position and whose loudness follows its speed"""
    dur = (c["b"] - c["a"]) / T.FPS
    n = n_of(dur)
    u = eased(c["a"], c["b"], c["ease"], c["f"], n)
    x = sweep_filter(S.noise(dur, i), c.get("f0", 260) * (c.get("f1", 4600) / c.get("f0", 260)) ** u, q=2.2, kind="bp")
    env = np.maximum(np.gradient(u) * n / (c["b"] - c["a"]) * 2.0, 0.05)
    env = np.minimum(env / np.max(env), 1) ** 0.8
    x = x / (np.max(np.abs(x)) + 1e-9) * env * 0.8
    if c.get("tone", True):
        tf = 220 * (880 / 220) ** u
        x = x + np.sin(2 * np.pi * np.cumsum(tf) / SR) * env * 0.35
    rig.emit(pan_curve(x, c.get("pan0", 0) + (c.get("pan1", 0) - c.get("pan0", 0)) * u), c["f"], c.get("gain", -17), room=-9, hall=-9, tier=1, label="sweep")


@handler("bed")
def _bed(rig, c, i):
    """a continuous texture whose loudness is the RATE of a process (a data stream that speeds up and slows down)"""
    dur = (c["b"] - c["a"]) / T.FPS
    n = n_of(dur)
    u = eased(c["a"], c["b"], c.get("ease", "inOut"), c["f"], n)
    rate = np.maximum(np.gradient(u), 0)
    rate = rate / (np.max(rate) + 1e-12)
    x = sweep_filter(S.noise(dur, 99), 500 * (3600 / 500) ** u, q=0.9, kind="bp") * rate**0.7
    x = x / (np.max(np.abs(x)) + 1e-9)
    tone = np.sin(2 * np.pi * np.cumsum(110 * (440 / 110) ** u) / SR) * (0.25 + 0.75 * u) * 0.5
    rig.emit(fade(pan_curve(x * 0.7 + tone * 0.6, np.zeros(n)), 0.05, 0.12), c["f"], c.get("gain", -20), room=-10, hall=-12, tier=1, label="bed")


@handler("rise")
def _rise(rig, c, i):
    """3D object rising or growing: pitch rides position, loudness rides speed (loud while it moves, gone when it stops)"""
    dur = (c["b"] - c["a"]) / T.FPS
    n = n_of(dur)
    u = eased(c["a"], c["b"], c["ease"], c["f"], n)
    speed = np.maximum(np.gradient(u), 0)
    speed = speed / (np.max(speed) + 1e-12)
    ph = 2 * np.pi * np.cumsum(c.get("f0", 80) * (c.get("f1", 520) / c.get("f0", 80)) ** u) / SR
    x = sum(np.sin(h * ph) / h for h in range(1, 7))
    x = sweep_filter(x, 220 * (4200 / 220) ** u, q=1.1, kind="lp") * speed**0.6 * _env(n)
    nz = sweep_filter(S.noise(dur, i) * 0.22, 300 * (3500 / 300) ** u, q=0.8, kind="bp") * speed**0.8
    sig = x / (np.max(np.abs(x)) + 1e-9) + nz
    rig.emit(pan_stereo(sig / (np.max(np.abs(sig)) + 1e-9), c.get("pan", 0)), c["f"], c.get("gain", -23), hall=-10, tier=c["tier"], label="rise")


@handler("scramble")
def _scramble(rig, c, i):
    """a value being computed: a fast stream of tiny clicks that thins out and settles on one pitch (pair with a ping on lock)"""
    a, b = c["a"], c["b"]
    r = np.random.default_rng(i)
    n_ticks = max(4, int((b - a) * 1.2))
    for k in range(n_ticks):
        u = (k / n_ticks) ** 1.6  # clicks bunch up early, thin out late
        fr = a + u * (b - a)
        pitch = c.get("pitch", 2400) * (1 + 0.5 * (1 - u) * (r.random() - 0.3))
        rig.emit(S.tick(pitch, 0.02, i * 1000 + k, tone=0.1), fr, c.get("gain", -30) + 6 * u, c.get("pan", 0), room=-12, tier=c["tier"], label="scramble")


@handler("note")
def _note(rig, c, i):
    rig.emit(S.pluck(float(midi(c["midi"])), c.get("dur", 0.6), c.get("tau", 0.16), bright=c.get("bright", 1.0)), c["f"], c["gain"], c.get("pan", 0), room=-7, hall=-7, tier=c["tier"], label="note")


@handler("bit")
def _bit(rig, c, i):
    rig.emit(S.bitflip(c["up"], c["base"]), c["f"], c["gain"], c.get("pan", 0), room=-9, tier=c["tier"], label="bit")


@handler("key")
def _key(rig, c, i):
    rig.emit(S.key_click(c["seed"]), c["f"], c.get("gain", -20) + (c["seed"] % 5) * 0.4, c.get("pan", 0), room=-14, tier=c["tier"], label="key")


@handler("enter")
def _enter(rig, c, i):
    rig.emit(S.enter_thock(i), c["f"], c.get("gain", -17), c.get("pan", 0), room=-10, tier=c["tier"], label="enter")


@handler("power_down")
def _pdown(rig, c, i):
    rig.emit(S.power_down(c.get("dur", 1.0), c.get("f0", 300), c.get("f1", 48)), c["f"], c.get("gain", -11), 0.0, room=-9, hall=-6, tier=1, label="power_down")


@handler("shimmer")
def _shimmer(rig, c, i):
    r = np.random.default_rng(i)
    dur = (c["b"] - c["a"]) / T.FPS
    for k in range(c.get("n", 26)):
        tk = r.random() ** 1.3 * dur
        rig.emit(S.bell(float(midi(86 + int(r.integers(0, 9)) * 2)), 0.5, index=0.8, tau=0.1), c["a"] + tk * T.FPS, c.get("gain", -33), pan=float(r.uniform(-0.8, 0.8)), hall=-4, tier=3, label="shimmer")


@handler("marker")
def _marker(rig, c, i):
    pass  # a cue that only marks a moment (the mix reads it, e.g. "mute_music")


def render(cues, extra=None) -> Rig:
    rig = Rig()
    table = dict(HANDLERS)
    if extra:
        table.update(extra)
    for i, c in enumerate(cues):
        fn = table.get(c["t"])
        if fn is None:
            raise ValueError(f"no handler for cue type {c['t']!r}; register one with @handler")
        fn(rig, c, i)
    return rig


_IR = {}


def apply_reverbs(rig: Rig):
    if not _IR:
        _IR["hall"] = make_ir(rt60=2.6, predelay=0.022, seed=11, bright=0.55)
        _IR["room"] = make_ir(rt60=0.42, predelay=0.006, seed=12, bright=0.7)

    def conv(tr, ir):
        L = signal.fftconvolve(tr.buf[:, 0], ir[:, 0])[: tr.n]
        R = signal.fftconvolve(tr.buf[:, 1], ir[:, 1])[: tr.n]
        return np.stack([L, R], axis=1) * 3.2

    return conv(rig.room, _IR["room"]), conv(rig.hall, _IR["hall"])
