"""The score. build(T) returns a Stems object; optional post(arrays, ctx) edits the rendered stems before they are summed.

Choose the grid first: BEAT frames per beat such that every scene start is a multiple of half a beat (see music_kit.py).
Rhythm lives on the global grid; chords change at scene cuts.
"""
from __future__ import annotations

import music_kit as M
from music_kit import Stems, beats, pad_bed

M.BEAT = 20  # 90 BPM at 30 fps

# chord name -> (pad voicing in midi, bass root in midi)
CH = {
    "Em9": ([52, 55, 59, 62, 66], 40),
    "Cmaj9": ([48, 52, 55, 59, 62], 36),
    "Emaj9": ([52, 56, 59, 63, 66], 40),
}


def build(T):
    st = Stems()
    scenes = [n for n, _ in T.SCENES]
    s0, s1 = T.START[scenes[0]], T.START[scenes[1]]
    end = T.total_frames()

    # harmony: (start frame, end frame, chord, level dB, brightness 0..1), chords change at scene cuts
    pad_bed(st, [(s0, s1, "Em9", -25, 0.45), (s1, end, "Cmaj9", -25, 0.5)], CH)

    # a quiet pulse that starts when the second scene starts
    for f in beats(s1, end, M.BEAT):
        M.bass(st, f, CH["Cmaj9"][1], gain=-23)
        M.hat(st, f + 10, gain=-33)
    return st


def post(arrays, ctx):
    """optional: per-stem edits on the rendered numpy arrays (stereo, 48 kHz). Typical uses:
         ctx['mix'].mute([arrays['pad'], arrays['bass']], f0, f1)          # a designed silence
         ctx['mix'].bus_filter_sweep(list(arrays.values()), (a, b, c))      # close then reopen a low-pass lid
    """
    return None
