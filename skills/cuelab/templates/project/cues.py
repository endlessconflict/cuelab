"""The cue sheet. Every sound event of the video, on the global frame where the picture does the thing.

build(C, T) is called once. C.add(frame, type, tier=..., gain=..., pan=..., **params). T is the timeline module:
  T.g("scene", local_frame)                 global frame of a scene-local frame (scene names come from timeline.json)
  T.inv_prog(y, a, b, "inOut")              the frame at which an eased motion reaches y (a dot crossing a node, a row finishing)
  T.landing(a, b, "out", dist_px)           the frame at which a motion has visibly stopped
  T.prog(f, a, b, ease)                     the picture's own easing, ported exactly

Rules that this file exists to enforce (see references/02-cue-sheet.md):
  * quote the picture's source constant next to every cue (file and local frame) so a change in the picture is easy to follow
  * sound the moment the eye sees it, not the moment the animation clock starts (hidden things, fades, slow-start easings)
  * discrete steps (a column becomes known, a character appears) on the first frame they are visible: math.ceil of the crossing time
  * continuous motions are one cue with a, b and ease so the sound follows the motion (pitch = position, loudness = speed)
  * tier 1 = the focal element / the lesson (music ducks under it), tier 2 = interface detail, tier 3 = ambience and captions
"""
from __future__ import annotations

import math  # noqa: F401  (use math.ceil for discrete steps)

# Notes (midi): E4 64, G4 67, A4 69, B4 71, D5 74, E5 76 ...


def build(C, T):
    g = T.g
    scenes = [n for n, _ in T.SCENES]

    # scene cuts: a right-to-left whoosh centred on the wipe (the wipe runs T.OVL frames from each scene start)
    for name in scenes[1:]:
        C.add(T.START[name] - 2, "wipe", tier=2)

    # captions: one soft tick per caption line, on the frame the line starts to rise (Captions.tsx: it.from + i * 5)
    CAPS = {  # scene -> [(from, n_lines)] in scene-local frames, copied from the scene files
        scenes[0]: [(40, 1), (92, 2)],
        scenes[1]: [(8, 2), (100, 2)],
    }
    for sc, items in CAPS.items():
        for fr, nl in items:
            for i in range(nl):
                C.add(g(sc, fr + i * 5 + 1), "cap", tier=3, line=i)

    # a focal ping when the focus element appears (the pure bright sine is reserved for the picture's focus element)
    C.add(g(scenes[0], 50), "ping", tier=1, midi=81, gain=-12, pan=0.2)

    # a continuous motion: a block rising from frame 10 to 50 (ease "out")
    C.add(g(scenes[0], 10), "rise", tier=2, a=g(scenes[0], 10), b=g(scenes[0], 50), ease="out", pan=0.0, dist_px=180.0)
    C.add(g(scenes[0], T.landing(10, 50, "out", 180.0)), "thunk", tier=2, gain=-18)

    # a state flip: the PE bit flips at local frame 70 in the second scene
    C.add(g(scenes[1], 70), "bit", tier=1, up=True, base=600.0, gain=-11, pan=-0.6)
    C.add(g(scenes[1], 70), "ping", tier=1, midi=84, gain=-14, pan=-0.6)
