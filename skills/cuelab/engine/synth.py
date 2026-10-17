"""Instrument and effect voices. Each returns a float array (mono unless noted), peak normalised near 1.0, so
placement gain in cues/score is the only loudness decision.

Timbre language (mirrors the picture's colour rules):
  hw / firmware (purple)  -> glass: FM bells, detuned saw pads, hollow woodblock ticks
  acid (the focal element) -> "ping": the only bright pure sine pluck in the piece, always the current step
  mechanical               -> filtered-noise clicks (typing, bit flips)
  danger-free              -> nothing harsh: no sawtooth leads, no high-frequency noise bursts above ~9 kHz
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from dsp import (SR, TWO_PI, bp, delay_taps, env_adsr, env_exp, fade, hp, lp, midi, n_of, noise, pan_curve, pan_stereo, phase_of,
                 saw_add, sine, square_add, sat, sweep_filter, tt)


def _norm(x, peak=1.0):
    """peak-normalise and always end on a 4 ms fade so no voice can leave a click when its buffer stops"""
    x = fade(x, 0.0, 0.004) if x.ndim == 1 and len(x) > 400 else x
    m = np.max(np.abs(x)) + 1e-12
    return x / m * peak


# ----------------------------------------------------------------------------------------------- small UI voices
def tick(freq=3000.0, dur=0.035, seed=0, tone=0.35):
    """short filtered click: noise burst + faint sine, the base 'UI' sound"""
    n = noise(dur, seed)
    x = bp(n, freq * 0.7, min(freq * 1.5, 9000)) * env_exp(dur, 0.0004, dur * 0.18)
    x += tone * sine(freq * 0.5, dur) * env_exp(dur, 0.0004, dur * 0.25)
    return _norm(x)


def wood(freq=520.0, dur=0.12, seed=0):
    """hollow woodblock: used for 'empty slot' ticks (a slot with nothing in it sounds hollow)"""
    t = tt(dur)
    x = np.sin(TWO_PI * freq * t * (1 + 0.03 * np.exp(-t * 90))) * np.exp(-t / 0.028)
    x += 0.5 * np.sin(TWO_PI * freq * 2.37 * t) * np.exp(-t / 0.012)
    x += 0.3 * bp(noise(dur, seed), freq, freq * 2.5) * np.exp(-t / 0.004)
    return _norm(x)


def key_click(seed=0, bright=1.0):
    """mechanical keyboard key: low thock body + high click, slightly different every time (seeded)"""
    r = np.random.default_rng(seed)
    f0 = 170 + 50 * r.random()
    dur = 0.075
    t = tt(dur)
    body = np.sin(TWO_PI * f0 * t * (1 + 0.25 * np.exp(-t * 60))) * np.exp(-t / 0.014)
    click = bp(noise(dur, seed + 1000), 2200 + 1200 * r.random(), 5800) * np.exp(-t / 0.0022) * (0.9 * bright)
    tap = lp(noise(dur, seed + 2000), 1400) * np.exp(-t / 0.006) * 0.8
    return _norm(body * 0.7 + click + tap)


def enter_thock(seed=0):
    t = tt(0.16)
    x = np.sin(TWO_PI * 110 * t * (1 + 0.4 * np.exp(-t * 40))) * np.exp(-t / 0.05)
    x += lp(noise(0.16, seed), 900) * np.exp(-t / 0.012) * 0.8
    x += bp(noise(0.16, seed + 1), 1800, 5200) * np.exp(-t / 0.003) * 0.5
    return _norm(x)


def bitflip(up=True, base=660.0, dur=0.085):
    """two short blips; up = 0->1 (rises a fourth), down = 1->0 (falls)"""
    f0, f1 = (base, base * 1.3348) if up else (base * 1.3348, base)
    h = n_of(dur / 2)
    a = sine(f0, dur / 2) * env_exp(dur / 2, 0.0008, 0.016)
    b = sine(f1, dur / 2) * env_exp(dur / 2, 0.0008, 0.022)
    a2 = square_add(f0, dur / 2, 5000) * env_exp(dur / 2, 0.0006, 0.01) * 0.25
    b2 = square_add(f1, dur / 2, 5000) * env_exp(dur / 2, 0.0006, 0.012) * 0.25
    return _norm(np.concatenate([a + a2, b + b2]))


# ----------------------------------------------------------------------------------------------- the acid leitmotif
def ping(freq, dur=0.7, bright=1.0):
    """the instruction pointer: pure sine + faint octave, instant attack, short bloom. Only ever used for the acid element."""
    t = tt(dur)
    f = freq * (1 + 0.006 * np.exp(-t * 60))
    x = np.sin(TWO_PI * np.cumsum(f) / SR)
    x += 0.30 * bright * np.sin(TWO_PI * np.cumsum(f * 2) / SR) * np.exp(-t / 0.06)
    x += 0.10 * bright * np.sin(TWO_PI * np.cumsum(f * 3.01) / SR) * np.exp(-t / 0.03)
    x *= env_exp(dur, 0.0008, 0.16)
    return _norm(x)


def pluck(freq, dur=0.9, tau=0.22, bright=1.0, seed=0):
    """additive pluck: harmonics decay faster the higher they are (used for the stack pushes and arps)"""
    t = tt(dur)
    x = np.zeros_like(t)
    for h in range(1, 9):
        if freq * h > 9000:
            break
        x += (1.0 / h**1.1) * np.sin(TWO_PI * freq * h * t + 0.7 * h) * np.exp(-t / (tau / (1 + 0.8 * (h - 1) / max(bright, 0.2))))
    x *= np.minimum(1, t / 0.0015)
    return _norm(x)


def bell(freq, dur=2.6, ratio=2.756, index=2.2, tau=0.8, seed=0):
    """glass bell (FM). index decays so it starts bright and mellows: the 'purple' hw timbre."""
    t = tt(dur)
    mod_env = np.exp(-t / (tau * 0.35))
    mod = np.sin(TWO_PI * freq * ratio * t) * index * mod_env
    x = np.sin(TWO_PI * freq * t + mod) * np.exp(-t / tau)
    x += 0.35 * np.sin(TWO_PI * freq * 2.0 * t + 0.5 * mod) * np.exp(-t / (tau * 0.6))
    x *= np.minimum(1, t / 0.002)
    return _norm(fade(x, 0, 0.05))


# ----------------------------------------------------------------------------------------------- hits and impacts
def sub_hit(freq=40.0, dur=1.6, drop=1.6, click=0.15):
    t = tt(dur)
    f = freq * (1 + (drop - 1) * np.exp(-t * 18))
    x = np.sin(TWO_PI * np.cumsum(f) / SR) * env_exp(dur, 0.002, dur * 0.28)
    x += click * lp(noise(dur, 5), 400) * np.exp(-t / 0.02)
    # a faint 2nd and 3rd harmonic so small speakers still hint at the note
    x += 0.75 * np.sin(TWO_PI * np.cumsum(f * 2) / SR) * np.exp(-t / 0.28)
    x += 0.38 * np.sin(TWO_PI * np.cumsum(f * 3) / SR) * np.exp(-t / 0.2)
    x += 0.16 * np.sin(TWO_PI * np.cumsum(f * 4) / SR) * np.exp(-t / 0.14)
    return _norm(x)


def kick(dur=0.38, f0=130.0, f1=44.0, punch=1.0):
    t = tt(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 28)
    x = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / 0.14)
    x += 0.5 * punch * bp(noise(dur, 3), 1500, 4200) * np.exp(-t / 0.0035)
    x += 0.22 * np.sin(TWO_PI * np.cumsum(f * 2) / SR) * np.exp(-t / 0.06)
    return _norm(sat(x, 1.6))


def hat(dur=0.06, seed=0, open_=False):
    d = 0.22 if open_ else dur
    n = noise(d, seed)
    x = hp(n, 7000) * env_exp(d, 0.0003, d * (0.35 if open_ else 0.16))
    return _norm(lp(x, 11000))


def clap(seed=0):
    d = 0.22
    t = tt(d)
    n = bp(noise(d, seed), 900, 3200)
    e = np.zeros_like(t)
    for off in (0.0, 0.011, 0.023):
        k = int(off * SR)
        e[k:] += np.exp(-(t[: len(t) - k]) / 0.004) * 0.7
    e += np.exp(-t / 0.07) * 0.55 * (t > 0.03)
    return _norm(n * e)


def denied():
    """the return address has nowhere to land: a dull thud plus a small beating dissonance, short and muted"""
    d = 0.5
    t = tt(d)
    thud = np.sin(TWO_PI * np.cumsum(95 * (1 - 0.45 * (1 - np.exp(-t * 10)))) / SR) * np.exp(-t / 0.09)
    clack = lp(noise(d, 8), 1200) * np.exp(-t / 0.012) * 0.9
    beat = (np.sin(TWO_PI * 311.1 * t) + np.sin(TWO_PI * 329.6 * t)) * 0.28 * np.exp(-t / 0.11)  # E-flat against E: a minor second
    return _norm(thud + clack + beat)


# ----------------------------------------------------------------------------------------------- motion sounds
def whoosh(dur=0.5, f0=400.0, f1=3500.0, q=1.2, seed=0, shape="swell", pan0=0.0, pan1=0.0, air=0.3):
    """filtered noise sweep. returns stereo. shape: swell (rise+fall), rise, fall"""
    n = noise(dur, seed)
    x = sweep_filter(n, (f0, f1), q=q, kind="bp")
    x += air * hp(n, 2500) * 0.3
    t = np.linspace(0, 1, len(x))
    if shape == "swell":
        e = np.sin(np.pi * t) ** 1.6
    elif shape == "rise":
        e = t**2.2 * np.minimum(1, (1 - t) * 12)
    else:
        e = (1 - t) ** 2.0 * np.minimum(1, t * 40)
    x = _norm(x * e)
    pans = np.linspace(pan0, pan1, len(x))
    return pan_curve(x, pans)


def glide(f0, f1, dur, shape="exp", bright=0.4, pans=None, tau=None):
    """sine glide, the 'travel' voice of the acid dot (pitch/pan follow the dot)"""
    n = n_of(dur)
    t = np.linspace(0, 1, n)
    if isinstance(shape, np.ndarray):
        u = shape
    elif shape == "exp":
        u = t
    else:
        u = t
    f = f0 * (f1 / f0) ** u
    ph = TWO_PI * np.cumsum(f) / SR
    x = np.sin(ph) + bright * np.sin(2 * ph) * 0.3
    e = np.minimum(1, np.arange(n) / (0.004 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.03 * SR))
    if tau:
        e *= np.exp(-np.arange(n) / SR / tau)
    x = _norm(x * e)
    return pan_curve(x, pans) if pans is not None else x


def power_down(dur=1.1, f0=330.0, f1=55.0):
    """falling pitch with a closing filter: CAR is torn down"""
    n = n_of(dur)
    t = np.linspace(0, 1, n)
    f = f0 * (f1 / f0) ** (t**0.8)
    x = np.zeros(n)
    for h in range(1, 12):
        x += np.sin(TWO_PI * np.cumsum(f * h) / SR) / h
    x = sweep_filter(x, (3200, 120), q=1.4, kind="lp")
    x *= np.exp(-t * 1.6) * np.minimum(1, t * 60)
    return _norm(x)


def power_up(dur=0.9, f0=70.0, f1=440.0):
    n = n_of(dur)
    t = np.linspace(0, 1, n)
    f = f0 * (f1 / f0) ** (t**1.4)
    x = np.zeros(n)
    for h in range(1, 10):
        x += np.sin(TWO_PI * np.cumsum(f * h) / SR) / h
    x = sweep_filter(x, (200, 5200), q=1.2, kind="lp")
    x *= np.minimum(1, t * 40) * np.minimum(1, (1 - t) * 8) * (0.3 + 0.7 * t)
    return _norm(x)


def reverse_swell(dur=0.45, seed=0, f=(300, 4200)):
    """inhale before the silence"""
    n = noise(dur, seed)
    x = sweep_filter(n, f, q=0.9, kind="bp")
    t = np.linspace(0, 1, len(x))
    return _norm(x * t**3.0)


# ----------------------------------------------------------------------------------------------- music voices
def pad_note(freq, dur, bright=0.55, attack=0.8, release=1.2, detune_cents=7, seed=0):
    """warm detuned saw trio through a low-pass: the harmonic bed"""
    n = n_of(dur + release)
    x = np.zeros(n)
    for c in (-detune_cents, 0, detune_cents):
        f = freq * 2 ** (c / 1200)
        x += saw_add(f, dur + release, ph0=c * 0.13, maxf=6500, rolloff=1.15)
    x = lp(x, 400 + 3600 * bright, order=2)
    e = env_adsr(dur + release, a=attack, d=0.2, s=0.85, r=release)
    return _norm(x * e)


def bass_note(freq, dur, seed=0, grit=0.35):
    """sine sub + filtered saw; the saw carries the pitch on small speakers"""
    t = tt(dur)
    x = np.sin(TWO_PI * freq * t) * 0.9
    x += 0.5 * lp(saw_add(freq, dur, maxf=2500, rolloff=1.3), 650)
    x += grit * 0.25 * np.sin(TWO_PI * freq * 2 * t)
    e = env_exp(dur, 0.004, dur * 0.7, 1.4)
    return _norm(sat(x * e, 1.5))


def lead_note(freq, dur, tau=0.4):
    """soft sine/triangle-ish lead for the few melodic payoffs"""
    t = tt(dur)
    x = np.sin(TWO_PI * freq * t) + 0.35 * np.sin(TWO_PI * freq * 2 * t) * np.exp(-t / 0.2) + 0.12 * np.sin(TWO_PI * freq * 3 * t) * np.exp(-t / 0.1)
    x *= env_adsr(dur, 0.012, 0.1, 0.8, min(0.3, dur * 0.5))
    return _norm(x)


def noise_swell(dur, seed=0, f=(200, 6000), q=0.8, curve=2.0):
    n = noise(dur, seed)
    x = sweep_filter(n, f, q=q, kind="lp")
    t = np.linspace(0, 1, len(x))
    return _norm(x * t**curve * np.minimum(1, (1 - t) * 30))


def room_tone(dur, seed=0, level=1.0):
    """very quiet pink noise floor so 'silence' still sounds like a room, not a dropped signal"""
    x = lp(noise(dur, seed, "pink"), 1800)
    return x / (np.max(np.abs(x)) + 1e-9) * level
