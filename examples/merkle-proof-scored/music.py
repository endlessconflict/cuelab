"""Score for the Merkle proof video. E aeolian, 90 BPM: one beat = 20 frames, one sixteenth = 5 frames.
Scene starts 0, 110, 250, 450, 680, 850, 960 are all multiples of 10 frames, i.e. on eighth notes.

Arc: a bare open fifth while the field appears (the size of the problem), a pulse as the leaves are hashed, a build as the tree grows,
tension while the proof is recomputed, ONE release into E major when the root matches, a dark chord and a designed silence when the
tampered proof fails, a groove for the scale scene, and a hollow-to-major close.
"""
from __future__ import annotations

import music_kit as M
from music_kit import Stems, beats, pad_bed

M.BEAT = 20
E3, B3 = 52, 59

CH = {
    "open": ([40 + 12, 47 + 12, 52 + 12, 59 + 12], 40),
    "Em9": ([52, 55, 59, 62, 66], 40),
    "Cmaj9": ([48, 52, 55, 59, 62], 36),
    "Am9": ([45, 48, 52, 55, 59], 33),
    "Emaj9": ([52, 56, 59, 63, 66], 40),
    "dim": ([53, 56, 59, 62, 65], 41),  # F A C Eb G: the "not E" chord
    "Gmaj7": ([43, 47, 50, 54, 59], 43),
}


def build(T):
    st = Stems()
    S = T.START
    end = T.total_frames()
    pad_bed(
        st,
        [
            (0, 110, "open", -25, 0.35),
            (110, 250, "Em9", -26, 0.45),
            (250, 332, "Cmaj9", -25, 0.5),
            (332, 400, "Am9", -25, 0.5),
            (400, 450, "Em9", -24, 0.55),
            (450, 542, "Am9", -26, 0.4),
            (542, 656, "Cmaj9", -26, 0.45),
            (656, 680, "Emaj9", -21, 0.8),
            (680, 850, "dim", -27, 0.3),
            (850, 905, "Em9", -24, 0.6),
            (905, 960, "Cmaj9", -24, 0.6),
            (960, 1032, "Cmaj9", -26, 0.5),
            (1032, 1130, "Emaj9", -21, 0.75),
        ],
        CH,
    )

    # hook: a low E that arrives with the pillar (54) and the payoff (90)
    M.bass(st, 54, 40, gain=-21, dur=1.6)
    M.bass(st, 90, 40, gain=-19, dur=1.4)

    # leaves (110..250): a pulse that starts with the first row, light hats on the offbeat
    for f in beats(116, 250, 20):
        M.bass(st, f, 40, gain=-24, dur=0.4)
    for f in beats(116, 250, 20, offset=10):
        M.hat(st, f, gain=-34)

    # tree (250..450): the build. kick from the first pair, claps from level 2, arp climbs with the levels
    for f in beats(250, 450, 20):
        M.kick(st, f, gain=-22)
        M.bass(st, f, [36, 36, 33, 33, 40, 40][min(5, int((f - 250) // 34))], gain=-22, dur=0.45)
    for f in beats(250, 450, 5):
        M.hat(st, f, gain=-35 if f % 10 else -31)
    for f in beats(346, 450, 40, offset=20):
        M.clap(st, f, gain=-27)
    M.arp(st, 280, 450, [64, 67, 71, 74, 76, 74, 71, 67], step=10, gain=-27)

    # proof (450..680): sparse tension (a single low pulse), then the release into E major at 656
    for f in beats(452, 640, 40):
        M.bass(st, f, 33 if f < 542 else 36, gain=-24, dur=0.5)
    for f in beats(470, 640, 20, offset=10):
        M.hat(st, f, gain=-36)
    for f in beats(656, 680, 20):
        M.kick(st, f, gain=-20)
        M.bass(st, f, 40, gain=-21, dur=0.4)
    M.arp(st, 656, 680, [64, 68, 71, 76, 71, 68], step=5, gain=-26)

    # tamper (680..850): a heartbeat that slows down and dies, then silence (see post)
    for k, f in enumerate([682, 704, 732, 768, 812]):
        M.kick(st, f, gain=-24 + k, dur=0.4, f0=110, f1=40)
    M.bass(st, 686, 41, gain=-22, dur=2.0)

    # scale (850..960): the groove returns, bright
    for f in beats(850, 960, 20):
        M.kick(st, f, gain=-20)
        M.bass(st, f, [40, 40, 36, 36, 43][min(4, int((f - 850) // 24))], gain=-21, dur=0.35)
        M.bass(st, f + 10, 40, gain=-23, dur=0.25)
    for f in beats(850, 960, 10):
        M.hat(st, f, gain=-29 if f % 20 else -26)
    for f in beats(870, 960, 40):
        M.clap(st, f, gain=-23)
    M.arp(st, 850, 960, [64, 67, 71, 76, 74, 71, 67, 71], step=5, gain=-25)

    # outro (960..1080): thin, then the last chord (pad Emaj9 from 1032); a bell-like lead states the root
    M.lead(st, 966, 76, gain=-25, dur=1.2, pan=-0.3)
    M.lead(st, 990, 71, gain=-26, dur=1.4, pan=0.3)
    M.lead(st, 1032, 80, gain=-23, dur=1.8, pan=0.2)
    return st


def post(arrays, ctx):
    mx, T = ctx["mix"], ctx["T"]
    # the designed silence after the X is drawn (tamper frame 138): music stems only, effects tail continues
    mx.mute([arrays["pad"], arrays["bass"], arrays["drums"], arrays["arp"]], T.g("tamper", 142), T.g("tamper", 168))
