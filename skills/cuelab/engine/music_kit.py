"""Building blocks for a score that is locked to the picture.

The grid: choose a beat length in frames so that every scene start is a multiple of half a beat. (At 30 fps, 90 BPM is 20 frames per
beat and 5 per sixteenth: scene starts that are multiples of 10 frames land on eighth notes.) Rhythm elements sit on that GLOBAL grid
so they never shift at a cut; chords change AT the cuts so the harmony and the picture move together.

    st = Stems()
    pad_bed(st, HARMONY, CH)                       # continuous harmonic bed, chords change at the frames you list
    for f in beats(a, b, 20): kick(st, f, -21)     # four to the floor between frames a and b
"""
from __future__ import annotations

import numpy as np

import synth as S
import timeline as T
from dsp import Track, midi

BEAT = 20  # frames; override per project via music_kit.BEAT = ...
SIX = 5


class Stems:
    def __init__(self):
        L = T.duration() + 5
        self.pad = Track(L, "pad")
        self.bass = Track(L, "bass")
        self.drums = Track(L, "drums")
        self.arp = Track(L, "arp")
        self.lead = Track(L, "lead")

    def all(self):
        return [self.pad, self.bass, self.drums, self.arp, self.lead]

    def dict(self):
        return {t.name: t for t in self.all()}


def beats(f0, f1, step=None, offset=0):
    """frames from f0+offset to f1 (exclusive) every `step` frames (default one beat)"""
    step = step or BEAT
    f = f0 + offset
    while f < f1 - 1e-6:
        yield f
        f += step


def pad_bed(st: Stems, harmony, CH, attack=0.9, release=1.1, overlap=0.25):
    """harmony: list of (start_frame, end_frame, chord_name, level_dB, brightness 0..1). CH maps name -> (pad midi list, bass root midi).
    Each note overlaps into the next chord by `overlap` s so changes are crossfades, not gaps."""
    for a, b, name, lvl, br in harmony:
        notes, _ = CH[name]
        dur = T.sec(b - a) + 0.35
        for k, m in enumerate(notes):
            x = S.pad_note(float(midi(m)), dur, bright=br, attack=attack if a > 0 else 1.2, release=release, seed=k)
            st.pad.add(x, T.sec(a) - overlap * (a > 0), lvl - 0.6 * k, pan=-0.5 + k * 0.22)


def kick(st, f, gain=-21, dur=0.34, f0=125, f1=44, punch=0.8):
    st.drums.add(S.kick(dur, f0, f1, punch), T.sec(f), gain)


def hat(st, f, gain=-31, dur=0.05, pan=0.25, open_=False):
    st.drums.add(S.hat(dur, int(f), open_), T.sec(f), gain, pan=pan)


def clap(st, f, gain=-24, pan=0.0):
    st.drums.add(S.clap(int(f)), T.sec(f), gain, pan=pan)


def bass(st, f, midi_note, gain=-22, dur=0.45, grit=0.35):
    st.bass.add(S.bass_note(float(midi(midi_note)), dur, grit=grit), T.sec(f), gain)


def pluck(track, f, midi_note, gain=-25, dur=0.3, tau=0.12, bright=1.0, pan=0.0):
    track.add(S.pluck(float(midi(midi_note)), dur, tau, bright=bright), T.sec(f), gain, pan=pan)


def lead(st, f, midi_note, gain=-22, dur=0.9, pan=0.0):
    st.lead.add(S.lead_note(float(midi(midi_note)), dur), T.sec(f), gain, pan=pan)


def riser(st, f, dur_frames, gain=-24, f_from=300, f_to=7000):
    st.lead.add(S.noise_swell(T.sec(dur_frames), int(f), (f_from, f_to), curve=2.0), T.sec(f), gain)


def arp(st, f0, f1, pattern, step=SIX, gain=-25, pan_spread=0.4, tau=0.12):
    """repeat `pattern` (midi list) every `step` frames between f0 and f1, alternating pan"""
    k = 0
    for f in beats(f0, f1, step):
        pluck(st.arp, f, pattern[k % len(pattern)], gain, tau=tau, pan=pan_spread * ((-1) ** k))
        k += 1
