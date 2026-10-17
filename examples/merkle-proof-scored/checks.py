"""Sync audit for the Merkle video: what the picture really does, measured, against the cue sheet (see ../../skills/cuelab/references/06-sync-audit.md).

ROIs are in full-resolution video pixels (x, y, w, h); they were calibrated by measuring the colour bounding boxes of known frames
(for example the focus-colour bounding box of the proof scene at frame 480 puts leaf 5 at x 608..680, y 620..706).
"""
from __future__ import annotations

import numpy as np

ROIS = {
    "hook_field": (80, 440, 920, 560),
    "hook_pillar": (560, 520, 320, 200),
    "hook_numeral": (640, 820, 360, 190),
    **{f"row{i}": (660, 214 + 94 * i, 340, 70) for i in range(8)},
    "tree_L1": (0, 630, 1080, 100),
    "tree_L2": (0, 440, 1080, 100),
    "tree_root": (440, 240, 200, 110),
    "proof_leaf": (560, 600, 240, 120),
    **{f"prow{k}": (80, 796 + 46 * k, 16, 46) for k in range(3)},
    "proof_root": (380, 130, 320, 120),
    "tam_leaf": (560, 600, 240, 120),
    "tam_L1": (0, 440, 1080, 110),
    "tam_L2": (0, 290, 1080, 110),
    "tam_root": (380, 130, 220, 110),
    "tam_x": (610, 130, 120, 110),
    "tam_char": (430, 790, 80, 60),
    **{f"bar{i}": (190 + 185 * i, 250, 150, 650) for i in range(4)},
    "outro_card": (80, 150, 920, 500),
    "caps": (80, 1030, 920, 200),
    "full": (0, 0, 1080, 1350),
}


def checks(S, A):
    T = A.T
    g, START = T.g, T.START
    cues = A.cues

    # ----------------------------------------------------------------------------------------------- hook
    A.report("hook: field wave starts (first change)", A.first_above(S["hook_field"]["diff"], 4, 60, 0.1), g("hook", 16), "sweep", tol=(-6, 2))
    A.report("hook: pillar appears (first change)", A.first_above(S["hook_pillar"]["diff"], 50, 100, 0.1), g("hook", 56), "rise", tol=A.FADE)
    A.report("hook: numeral 20 appears (first change)", A.first_above(S["hook_numeral"]["diff"], 80, 112, 1.0), g("hook", 90), "impact", tol=A.HARD)

    # ----------------------------------------------------------------------------------------------- leaves: each hash locks at s + 34 (its colour changes to data)
    for i in range(8):
        s = 6 + 7 * i
        vis = A.first_above(S[f"row{i}"]["data"], g("leaves", s + 30), g("leaves", s + 44), 8)
        A.report(f"leaves: row {i} hash locks", vis, g("leaves", s + 34), "glass_tick", tol=A.HARD)

    # ----------------------------------------------------------------------------------------------- tree: a node leaves the focus colour when it locks (s + 36)
    for band, items in (("tree_L1", [30, 38, 46, 54]), ("tree_L2", [96, 106]), ("tree_root", [150])):
        lo, hi = min(items) + 30, max(items) + 44
        drops = A.edges(S[band]["focus"], g("tree", lo), g("tree", hi), 55, rising=False)
        want = [g("tree", s + 36) for s in items]
        errs = [w - d for d, w in zip(drops[-len(want):], want)] if len(drops) >= len(want) else []
        A.stat(f"tree: {band} nodes lock (focus colour leaves)", errs, A.HARD, note=f"{len(drops)} edges seen, {len(want)} expected")

    # ----------------------------------------------------------------------------------------------- proof
    lum = np.asarray(S["proof_leaf"]["lum"]) - S["proof_leaf"]["lum"][g("proof", 12)]  # the leaf lights up (its focus-coloured edges are there from frame 0)
    A.report("proof: leaf 5 lights up", A.first_above(lum, g("proof", 12), g("proof", 40), 1.0), g("proof", 15), "ping", tol=A.FADE)
    for k, R in enumerate([92, 130, 168]):
        strip = S[f"prow{k}"]["focus"]
        on = A.first_above(strip, g("proof", R - 4), g("proof", R + 12), 6)
        A.report(f"proof: verifier row {k + 1} becomes active", on, g("proof", R), "ping", tol=A.FADE)
        off = A.edges(strip, g("proof", R + 14), g("proof", R + 34), 6, rising=False)
        A.report(f"proof: verifier row {k + 1} settles (value fixed)", off[0] if off else None, g("proof", R + 22), "glass_tick", tol=A.HARD)
    A.report("proof: root turns ok (match)", A.first_above(S["proof_root"]["ok"], g("proof", 200), g("proof", 232), 25), g("proof", 207), "chord", tol=(-6, 2))

    # ----------------------------------------------------------------------------------------------- tamper
    A.report("tamper: the character turns bad", A.first_above(S["tam_char"]["bad"], g("tamper", 15), g("tamper", 45), 6), g("tamper", 22), "reject", tol=A.FADE)
    for name, at in (("tam_leaf", 36), ("tam_L1", 66), ("tam_L2", 92), ("tam_root", 118)):
        A.report(f"tamper: {name} turns bad", A.first_above(S[name]["bad"], g("tamper", at - 6), g("tamper", at + 20), 15), g("tamper", at), "glass_tick", tol=A.FADE)
    A.report("tamper: X mark is drawn", A.first_above(S["tam_x"]["bad"], g("tamper", 132), g("tamper", 160), 10), g("tamper", 138), "impact", tol=(-6, 2))

    # ----------------------------------------------------------------------------------------------- scale: bars grow from 4 + 10i
    for i in range(4):
        a = 4 + 10 * i
        A.report(f"scale: bar {i} starts growing", A.first_above(S[f"bar{i}"]["diff"], g("scale", a - 2), g("scale", a + 16), 0.2), g("scale", a), "glide", tol=(-8, 2))

    # ----------------------------------------------------------------------------------------------- outro: code lines
    A.report("outro: first code line", A.first_above(S["outro_card"]["diff"], g("outro", 2), g("outro", 14), 0.2), g("outro", 5), "ui", tol=A.FADE)

    # ----------------------------------------------------------------------------------------------- wipes and captions
    fd = S["full"]["diff"]
    errs = []
    for name in ["leaves", "tree", "proof", "tamper", "scale", "outro"]:
        s0 = START[name]
        pk = int(np.argmax(fd[s0 - 3 : s0 + 14])) + s0 - 3
        cue = [c["f"] for c in cues if c["t"] == "wipe" and abs(c["f"] - (s0 - 2)) < 1][0]
        errs.append(cue + 8.0 - pk)
    A.stat("wipes: whoosh peak vs visual peak (6 cuts)", errs, (-2, 2))
    cap = S["caps"]["diff"]
    errs = []
    for c in cues:
        if c["t"] == "cap" and c.get("line") == 0:
            gf = int(round(c["f"] - 1))
            seg = cap[gf - 2 : gf + 12]
            o = A.onset(seg, 0, len(seg), 0.2, base=0.0)
            if o is not None:
                errs.append(c["f"] - (gf - 2 + o))
    A.stat("captions: tick vs first visible rise (first lines)", errs, (-1, 4))
