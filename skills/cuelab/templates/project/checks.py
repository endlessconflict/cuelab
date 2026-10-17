"""The sync audit: what the picture really does, measured, against what the cue sheet says.

ROIS: named regions in full-resolution video pixels (x, y, w, h). For each ROI and each colour in project.json "colors" the audit records
pixel counts and centroids per frame, plus mean luminance and frame-to-frame change ("diff").
checks(S, A): S[roi][signal] is a numpy array indexed by frame; A has first_above, last_move, steps_of, onset, settle, report, stat,
cue_frames and the tolerance windows A.HARD (-1, +2) and A.FADE (-1, +4). Compare each visual event with the cue that should match it.

Write a check for every cue that matters (tier 1) and for every class of repeated cue. A check that cannot measure returns "not measurable":
treat that as a bug in the ROI, not a pass.
"""
from __future__ import annotations

ROIS = {
    "stage": (80, 150, 920, 860),  # the whole stage
    "register": (80, 470, 500, 140),  # the bit strip of the second scene
}


def checks(S, A):
    T = A.T
    scenes = [n for n, _ in T.SCENES]
    g = T.g
    # the PE bit flips to the focus colour at local frame 70 of the second scene
    first = A.first_above(S["register"]["focus"], T.START[scenes[1]] + 50, T.START[scenes[1]] + 110, 20)
    A.report("register: PE bit flips (focus colour appears)", first, g(scenes[1], 70), "bit", tol=A.HARD)
