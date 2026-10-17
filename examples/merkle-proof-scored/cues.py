"""Cue sheet for the Merkle proof video (sourceframe/examples/merkle-proof, 36 s).

Sound language of this piece:
  data (a hash, a node)       glass: a bell that rings when a value is fixed (locked)
  the focus element           the ping: a pure bright sine, only when the focus colour appears or lands
  computation                 a scramble: a fast thinning stream of clicks that settles on the glass note
  the ledger (verified)       a major chord (the only major chord of the piece) when the root matches
  tampering                   minor seconds and a muted thud, no resolution
Key: E aeolian, 90 BPM (20 frames per beat, every scene start is a multiple of 10 frames).
Each block quotes the scene file and the local frames the cue follows.
"""
from __future__ import annotations

import math

E5, G5, A5, B5, D6, E6, G6, A6 = 76, 79, 81, 83, 86, 88, 91, 93


def pan_x(px):
    """screen x (0..1080) to stereo position"""
    return max(-0.85, min(0.85, (px / 1080 * 2 - 1) * 0.8))


def build(C, T):
    g = T.g

    # ============================================================================ scene cuts (Video.tsx: wipe from the right, OVL frames)
    for name in ["leaves", "tree", "proof", "tamper", "scale", "outro"]:
        C.add(T.START[name] - 2, "wipe", tier=2)

    # ============================================================================ captions (Captions: it.from + i*5, one tick per line)
    CAPS = {
        "hook": [(26, 2), (90, 1)],
        "leaves": [(8, 2), (82, 2)],
        "tree": [(10, 2), (104, 2)],
        "proof": [(8, 2), (88, 2)],
        "tamper": [(8, 2), (98, 2)],
        "scale": [(6, 2), (70, 2)],
        "outro": [(10, 2)],
    }
    for sc, items in CAPS.items():
        for fr, nl in items:
            for i in range(nl):
                C.add(g(sc, fr + i * 5 + 1), "cap", tier=3, line=i)

    # ============================================================================ HOOK (Hook.tsx)
    C.add(g("hook", 4), "title_rise", tier=2, pan=-0.3, gain=-17)    # title(4, "One in a")
    C.add(g("hook", 12), "title_rise", tier=2, pan=-0.1, gain=-17)   # title(12, "million")
    # reveal = prog(f, 8, 52, inOut): a diagonal wave sweeps the million-point field; the audit shows the first visible change at frame 19-22
    # (the inOut ease starts slowly), so the sound starts at 16 and rides the same curve
    C.add(g("hook", 16), "sweep", tier=1, a=g("hook", 16), b=g("hook", 52), ease="inOut", f0=300, f1=6500, pan0=-0.75, pan1=0.75, tone=False, gain=-17)
    C.add(g("hook", 31), "ui", tier=3, pitch=1800, pan=-0.7, gain=-27)        # label "1,000,000 leaves" fades in (30..44)
    # pillar: rise = prog(f, 54, 74, out), 140 units tall at 0.66 px/unit = ~92 px
    C.add(g("hook", 56), "rise", tier=2, a=g("hook", 56), b=g("hook", 74), ease="out", f0=60, f1=420, pan=0.15, gain=-20)
    C.add(g("hook", T.landing(54, 74, "out", 92.0)), "thunk", tier=2, gain=-17, pan=0.15, freq=64.0)
    C.add(g("hook", 68), "ping", tier=1, midi=E6, gain=-13, pan=0.2, dur=0.9)  # label "leaf 440,650" in focus colour (66..80)
    # numeral 20: prog(f, 88, 104, out): the payoff
    C.add(g("hook", 90), "impact", tier=1, freq=82.4, dur=1.6, gain=-9, pan=0.5, midi=E5)
    C.add(g("hook", 91), "ping", tier=1, midi=B5 + 12, gain=-12, pan=0.55, dur=1.2)

    # ============================================================================ LEAVES (Leaves.tsx)
    # row i starts at s = 6 + 7i: data slides in (14 f), the hash resolves from noise s+14 .. s+34 and locks at s+34
    C.add(g("leaves", 1), "ui", tier=3, pitch=1700, gain=-27, pan=0.0)      # column headers fade in
    LADDER = [E5, G5, A5, B5, D6, E6, G6, A6]
    for i in range(8):
        s = 6 + 7 * i
        C.add(g("leaves", s + 1), "ui", tier=2, pitch=2000 + 90 * i, pan=-0.4, gain=-24)        # the data text arrives
        C.add(g("leaves", s + 9), "ui", tier=3, pitch=1500, pan=0.0, gain=-29)                  # the arrow draws
        C.add(g("leaves", s + 14), "scramble", tier=2, a=g("leaves", s + 14), b=g("leaves", s + 34), pitch=2300 + 60 * i, pan=0.5, gain=-30)
        C.add(g("leaves", s + 34), "glass_tick", tier=2, midi=LADDER[i], gain=-16, pan=0.35 + 0.0 * i)   # the hash locks: one note of the ladder
    C.add(g("leaves", 6 + 7 * 5 + 34), "ping", tier=1, midi=E6, gain=-15, pan=0.3, dur=0.9)   # row 5 is the leaf we will prove: the focus is born

    # ============================================================================ TREE (Tree.tsx)
    # leaves fade in at idx*2 (14 f); level 1 node j computes from s = 30 + 8j, level 2 from 96 + 10j, root from 150.
    # a node scrambles s+14 .. s+36 and locks at s+36; its beams grow s .. s+22
    for i in range(8):
        C.add(g("tree", i * 2 + 4), "glass_tick", tier=3, midi=D6 + (i % 4) * 2, gain=-27, pan=pan_x(540 + (i - 3.5) * 112))
    NODES = [(1, 0, 30, -3.0), (1, 1, 38, -1.0), (1, 2, 46, 1.0), (1, 3, 54, 3.0), (2, 0, 96, -2.0), (2, 1, 106, 2.0), (3, 0, 150, 0.0)]
    NOTE = {(1, 0): E5, (1, 1): G5, (1, 2): A5, (1, 3): B5, (2, 0): D6, (2, 1): E6}
    for lvl, j, s, x in NODES:
        px = pan_x(540 + x * 112)
        C.add(g("tree", s + 1), "swish", tier=3, pan=px, gain=-25)
        C.add(g("tree", s + 14), "scramble", tier=2, a=g("tree", s + 14), b=g("tree", s + 36), pitch=2200, pan=px, gain=-28)
        if lvl < 3:
            C.add(g("tree", s + 36), "glass_tick", tier=2, midi=NOTE[(lvl, j)], gain=-14, pan=px)
    # the root locks: a chord, a low hit, and the label ROOT (168..182)
    C.add(g("tree", 150 + 36), "chord", tier=1, notes=[64, 71, 76, 83, 86], gain=-12, index=1.4)
    C.add(g("tree", 168), "ui", tier=3, pitch=1600, pan=0.0, gain=-26)

    # ============================================================================ PROOF (Proof.tsx)
    C.add(g("proof", 15), "ping", tier=1, midi=E6, gain=-13, pan=0.1, dur=0.9)        # leaf 5 turns focus (leafHi 14..30): "prove this"
    for k in range(3):                                                                   # siblings lift: sibIn(k) = prog(44+10k, 62+10k)
        C.add(g("proof", 46 + 10 * k), "glass_tick", tier=2, midi=[G5, B5, D6][k], gain=-15, pan=[0.1, 0.45, -0.4][k])
    C.add(g("proof", 80), "ui", tier=3, pitch=1600, gain=-26, pan=0.0)                  # verifier card fades in (78..92)
    ROWS = [92, 130, 168]                                                                # ROWS_AT: row k computes ROWS[k] .. +22, node k lights focus
    for k, R in enumerate(ROWS):
        C.add(g("proof", R), "ping", tier=1, midi=[E5, G5, B5][k], gain=-13, pan=0.0, dur=0.8)                   # the focus moves up one node
        C.add(g("proof", R), "scramble", tier=2, a=g("proof", R), b=g("proof", R + 22), pitch=2400, pan=-0.3, gain=-29)
        C.add(g("proof", R + 22), "glass_tick", tier=2, midi=[E5, G5, B5][k] + 12, gain=-15, pan=0.2)             # value fixed
    # compare: cmp = prog(f, 206, 220, out): root turns mint, a check mark is drawn
    C.add(g("proof", 207), "chord", tier=1, notes=[64, 68, 71, 76, 80], gain=-13, index=1.3)                       # E major: the only major chord of the piece
    C.add(g("proof", 207), "glide", tier=1, a=g("proof", 206), b=g("proof", 220), ease="out", m0=83, m1=95, pan0=0.3, pan1=0.85, gain=-21)
    C.add(g("proof", 208), "marker", tier=1, name="match")

    # ============================================================================ TAMPER (Tamper.tsx)
    C.add(g("tamper", 5), "ui", tier=3, pitch=1500, gain=-26)                            # diff card fades in (4..18)
    C.add(g("tamper", 22), "reject", tier=1, gain=-11, pan=-0.2)                         # FLIP_AT: the character turns bad ("2" to "9")
    C.add(g("tamper", 22), "bit", tier=2, up=False, base=520, gain=-14, pan=-0.3)
    # NODE_AT = [36, 66, 92, 118]: each path node turns rose and scrambles to its new hash for 18 frames; minor seconds descend
    for k, (at, midi_n) in enumerate([(36, 76), (66, 75), (92, 74), (118, 73)]):
        C.add(g("tamper", at), "scramble", tier=2, a=g("tamper", at), b=g("tamper", at + 18), pitch=1800, pan=0.0, gain=-27)
        C.add(g("tamper", at), "glass_tick", tier=1, midi=midi_n, gain=-13 + k * 0.8, pan=0.0)
    C.add(g("tamper", 138), "impact", tier=1, freq=61.7, dur=1.6, gain=-8, pan=0.2)       # the X is drawn (NODE_AT[3] + 20 .. +32)
    C.add(g("tamper", 138), "reject", tier=1, gain=-8, pan=0.3)
    C.add(g("tamper", 146), "marker", tier=1, name="silence", silence=g("tamper", 166))   # a designed silence follows the X

    # ============================================================================ SCALE (Scale.tsx)
    C.add(g("scale", 1), "ui", tier=3, pitch=1600, gain=-27)                              # floor fades in (0..10)
    BARS = [(8, 3, -3.3), (1000, 10, -1.1), (1_000_000, 20, 1.1), (1_000_000_000, 30, 3.3)]
    for i, (n, h, x) in enumerate(BARS):
        a, b = 4 + 10 * i, 30 + 10 * i                                                    # bar grows with prog(f, a, b, out)
        top = 52 + round(h * 1.2)
        C.add(g("scale", a), "glide", tier=1 if i == 2 else 2, a=g("scale", a), b=g("scale", b), ease="out", m0=48, m1=top, pan0=pan_x(540 + x * 84), pan1=pan_x(540 + x * 84), gain=-16)
        C.add(g("scale", T.landing(a, b, "out", 55.0 * h / 3)), "glass_tick", tier=2, midi=top, gain=-14, pan=pan_x(540 + x * 84))
    C.add(g("scale", T.landing(24, 50, "out", 200.0)), "ping", tier=1, midi=E6, gain=-12, pan=0.25, dur=1.0)   # the focus bar (a million) lands
    C.add(g("scale", 72), "chord", tier=1, notes=[64, 71, 76, 83, 86], gain=-12, index=1.4, sub=False)        # "Twenty hashes."

    # ============================================================================ OUTRO (Outro.tsx)
    # code lines arrive at start + 4i (CodeCard start=4 step=4, 11 lines): a soft tick per line, rising
    for i in range(11):
        C.add(g("outro", 4 + 4 * i + 1), "ui", tier=2, pitch=1700 + 70 * i, pan=-0.2, gain=-25)
    for at in (34, 52, 70):
        C.add(g("outro", at + 2), "ui", tier=3, pitch=1500, pan=0.0, gain=-26)           # three statements fade in
    C.add(g("outro", 72), "chord", tier=1, notes=[52, 59, 64, 71, 76, 80], gain=-12, index=1.2)  # last word: E major, a verified claim
