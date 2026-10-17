"""Small numpy/scipy DSP kit: oscillators, envelopes, filters, reverb, delay, mixing. No external audio libraries.
Everything is deterministic (seeded) so a rebuild gives the same samples.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

SR = 48000
TWO_PI = 2 * np.pi


def rng(seed) -> np.random.Generator:
    return np.random.default_rng(abs(hash(("cbr", seed))) % (2**32) if not isinstance(seed, int) else seed)


def midi(n):
    return 440.0 * 2.0 ** ((np.asarray(n, dtype=float) - 69.0) / 12.0)


def db(x):
    return 10.0 ** (np.asarray(x, dtype=float) / 20.0)


def n_of(dur: float) -> int:
    return max(1, int(round(dur * SR)))


def tt(dur: float) -> np.ndarray:
    return np.arange(n_of(dur)) / SR


# ---------------------------------------------------------------- envelopes
def env_exp(dur, attack=0.002, tau=0.1, curve=1.0):
    """linear attack, exponential decay (tau = time constant seconds)"""
    n = n_of(dur)
    t = np.arange(n) / SR
    a = np.minimum(1.0, t / max(attack, 1 / SR))
    d = np.exp(-(t / tau) ** curve)
    e = a * d
    # kill the click at the very end
    k = min(n, int(0.004 * SR))
    e[-k:] *= np.linspace(1, 0, k)
    return e


def env_adsr(dur, a=0.01, d=0.1, s=0.7, r=0.2):
    n = n_of(dur)
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    nr = min(nr, n)
    e = np.ones(n) * s
    na = min(na, n)
    if na:
        e[:na] = np.linspace(0, 1, na) ** 1.5
    nd = min(nd, max(0, n - na))
    if nd:
        e[na : na + nd] = np.linspace(1, s, nd)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    return e


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    n = x.shape[0]
    if fin > 0:
        k = min(n, int(fin * SR))
        w = np.linspace(0, 1, k) ** 2
        x[:k] *= w if x.ndim == 1 else w[:, None]
    if fout > 0:
        k = min(n, int(fout * SR))
        w = np.linspace(1, 0, k) ** 2
        x[-k:] *= w if x.ndim == 1 else w[:, None]
    return x


# ---------------------------------------------------------------- oscillators
def phase_of(freq, dur):
    n = n_of(dur)
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,)) if np.ndim(freq) == 0 else np.interp(np.arange(n), np.linspace(0, n - 1, len(freq)), freq)
    return TWO_PI * np.cumsum(f) / SR


def sine(freq, dur, ph0=0.0):
    return np.sin(phase_of(freq, dur) + ph0)


def saw_add(freq, dur, ph0=0.0, maxf=9000.0, rolloff=1.0):
    """band-limited saw by additive synthesis (freq scalar). rolloff>1 darkens."""
    f = float(freq)
    n = n_of(dur)
    t = np.arange(n) / SR
    k = int(min(60, maxf // max(f, 1)))
    out = np.zeros(n)
    for h in range(1, k + 1):
        out += np.sin(TWO_PI * f * h * t + ph0 * h) / (h**rolloff)
    return out * (2 / np.pi)


def square_add(freq, dur, maxf=8000.0):
    f = float(freq)
    n = n_of(dur)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for h in range(1, int(min(50, maxf // max(f, 1))) + 1, 2):
        out += np.sin(TWO_PI * f * h * t) / h
    return out * (4 / np.pi) * 0.5


def noise(dur, seed=0, color="white"):
    r = np.random.default_rng(seed)
    x = r.standard_normal(n_of(dur))
    if color == "pink":
        b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
        a = [1, -2.494956002, 2.017265875, -0.522189400]
        x = signal.lfilter(b, a, x)
    return x / (np.max(np.abs(x)) + 1e-9)


# ---------------------------------------------------------------- filters
def _sos(kind, fc, q=0.707, order=2):
    fc = float(np.clip(fc, 20, SR * 0.45))
    if kind == "lp":
        return signal.butter(order, fc, "lowpass", fs=SR, output="sos")
    if kind == "hp":
        return signal.butter(order, fc, "highpass", fs=SR, output="sos")
    raise ValueError(kind)


def lp(x, fc, order=2):
    return signal.sosfilt(_sos("lp", fc, order=order), x, axis=0)


def hp(x, fc, order=2):
    return signal.sosfilt(_sos("hp", fc, order=order), x, axis=0)


def bp(x, f1, f2, order=2):
    sos = signal.butter(order, [float(np.clip(f1, 20, SR * 0.45)), float(np.clip(f2, 30, SR * 0.46))], "bandpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def _rbj(kind, fc, q):
    w0 = TWO_PI * np.clip(fc, 20, SR * 0.45) / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * q)
    if kind == "lp":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
    elif kind == "hp":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
    elif kind == "bp":
        b = [alpha, 0, -alpha]
    else:
        raise ValueError(kind)
    a = [1 + alpha, -2 * cw, 1 - alpha]
    return np.array([[b[0] / a[0], b[1] / a[0], b[2] / a[0], 1.0, a[1] / a[0], a[2] / a[0]]])


def sweep_filter(x, fc_curve, q=1.0, kind="lp", block=96):
    """time-varying biquad: fc_curve is an array (one value per sample) or (start,end) tuple (exp sweep)."""
    n = len(x)
    if isinstance(fc_curve, tuple):
        fc = np.exp(np.linspace(np.log(fc_curve[0]), np.log(fc_curve[1]), n))
    else:
        fc = np.asarray(fc_curve, dtype=float)
    out = np.zeros(n)
    zi = np.zeros((1, 2))
    for i in range(0, n, block):
        sos = _rbj(kind, float(fc[min(i + block // 2, n - 1)]), q)
        y, zi = signal.sosfilt(sos, x[i : i + block], zi=zi)
        out[i : i + block] = y
    return out


# ---------------------------------------------------------------- spatial / fx
def pan_stereo(x, pan=0.0):
    """equal-power pan, pan in [-1, 1] (-1 = left). mono -> (n,2)"""
    p = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    return np.stack([x * np.cos(p), x * np.sin(p)], axis=1)


def pan_curve(x, pans):
    """per-sample pan (array in [-1,1]) for moving sources"""
    p = (np.clip(pans, -1, 1) + 1) * np.pi / 4
    return np.stack([x * np.cos(p), x * np.sin(p)], axis=1)


def make_ir(rt60=1.6, predelay=0.012, seed=1, bright=0.6, early=True, length=None):
    r = np.random.default_rng(seed)
    length = length or rt60 * 1.15 + predelay
    n = n_of(length)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for ch in range(2):
        nz = r.standard_normal(n)
        lo = lp(nz, 500) * np.exp(-6.9 * np.maximum(0, t - predelay) / (rt60 * 1.25))
        mid = bp(nz, 500, 3500) * np.exp(-6.9 * np.maximum(0, t - predelay) / rt60)
        hi = hp(nz, 3500) * np.exp(-6.9 * np.maximum(0, t - predelay) / (rt60 * (0.25 + 0.5 * bright)))
        body = lo * 0.9 + mid * 1.0 + hi * 0.45 * bright
        body[t < predelay] = 0
        ir[:, ch] = body
        if early:
            for d, a in [(0.019, 0.5), (0.031, 0.38), (0.047, 0.3), (0.063, 0.22)]:
                k = int((predelay + d * (1 + 0.15 * ch)) * SR)
                if k < n:
                    ir[k, ch] += a * (1 if (k + ch) % 2 else -1)
    ir /= np.sqrt(np.sum(ir**2)) + 1e-9
    return ir


def reverb(x, ir, wet=0.3, dry=1.0, tail=True):
    """x mono or stereo -> stereo, output longer by the tail"""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    L = signal.fftconvolve(x[:, 0], ir[:, 0])
    R = signal.fftconvolve(x[:, 1], ir[:, 1])
    wetsig = np.stack([L, R], axis=1) * 3.2  # IR is energy-normalised; this gain makes wet comparable to dry
    out = np.zeros_like(wetsig)
    out[: len(x)] += x * dry
    out += wetsig * wet
    return out


def delay_taps(x, time, fb=0.4, taps=4, pingpong=True, lpf=4000.0):
    """feedback delay as a finite number of taps, returns stereo with the tail appended"""
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    d = int(time * SR)
    out = np.zeros((len(x) + d * taps + 1, 2))
    out[: len(x)] += x
    cur = x.copy()
    for k in range(1, taps + 1):
        cur = lp(cur, lpf) * fb
        sh = cur if not pingpong else cur[:, ::-1] if k % 2 else cur
        out[k * d : k * d + len(x)] += sh
    return out


def sat(x, drive=2.0):
    return np.tanh(x * drive) / np.tanh(drive)


def stereo_widen(x, width=1.2):
    m = (x[:, 0] + x[:, 1]) / 2
    s = (x[:, 0] - x[:, 1]) / 2 * width
    return np.stack([m + s, m - s], axis=1)


# ---------------------------------------------------------------- mixing buffer
class Track:
    """stereo float buffer of fixed length with sample-accurate placement"""

    def __init__(self, dur_s: float, name="track"):
        self.name = name
        self.n = int(round(dur_s * SR))
        self.buf = np.zeros((self.n, 2))
        self.log = []  # (t_sec, label, peak_db)

    def add(self, sig, t_sec: float, gain_db=0.0, pan=0.0, label=""):
        if sig.ndim == 1:
            sig = pan_stereo(sig, pan)
        s = int(round(t_sec * SR))
        if s >= self.n:
            return
        a = max(0, -s)
        b = min(len(sig), self.n - s)
        if b <= a:
            return
        g = db(gain_db)
        self.buf[s + a : s + b] += sig[a:b] * g
        if label:
            pk = float(np.max(np.abs(sig[a:b]))) * g
            self.log.append((t_sec, label, 20 * np.log10(pk + 1e-12)))

    def peak_db(self):
        return 20 * np.log10(np.max(np.abs(self.buf)) + 1e-12)
