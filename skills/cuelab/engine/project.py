"""A cuelab project is a folder:

    project.json   settings (see DEFAULTS)
    cues.py        def build(C, T): ...   adds cues with C.add(frame, type, ...); optional HANDLERS = {"type": fn} for custom cue types
    music.py       def build(M, T) -> Stems ...   the score;  optional def post(arrays, ctx): ...  per-stem edits before the sum
    checks.py      ROIS = {...};  def checks(S, A): ...   the sync audit (picture measurements vs cues)

Paths in project.json are relative to the project folder.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

DEFAULTS = {
    "video": "../video.mp4",  # the silent video to score (its video stream is copied untouched)
    "timeline": "../timeline.json",  # the same file the video renders from
    "out": "out",
    "target_lufs": -15.0,  # integrated loudness of the master (social video: -14 to -16)
    "ceiling_db": -1.5,  # true-peak ceiling after AAC
    "music_trim": 8.0,  # dB, score against effects
    "sfx_trim": -6.0,
    "duck_db": 6.5,  # how far tier-1 sounds push the music down
    "duck_release": 0.32,
    "hp_hz": 36,  # master high-pass (phone speakers cannot reproduce less; headphones still get it)
    "arc": [],  # [[frame, dB], ...] energy arc of the music bus
    "outro": [],  # [[frame, dB], ...] master fade (end the file near silence so a looped video restarts cleanly)
    "room_tone_dbfs": -50.0,
    "tilt": 0.22,  # fraction of >6.5 kHz removed (pleasant on a phone at low volume)
    "colors": {  # RGB meters for the sync audit: pixels near these colours are counted per ROI
        "focus": [255, 122, 69],
        "data": [124, 196, 255],
        "ok": [94, 234, 212],
        "bad": [255, 77, 109],
        "white": [238, 242, 247],
    },
    "color_tol": 55,
    "latency_cue_types": ["key", "bit", "ui"],
    "grid_frames": 5,  # drum grid used to ignore intended transients in the click detector
    "audio_bitrate": "192k",
}


class Project:
    def __init__(self, path):
        self.dir = os.path.abspath(path)
        cfg = dict(DEFAULTS)
        cfg.update(json.load(open(os.path.join(self.dir, "project.json"), encoding="utf-8")))
        self.cfg = cfg
        self.video = os.path.normpath(os.path.join(self.dir, cfg["video"]))
        self.timeline_path = os.path.normpath(os.path.join(self.dir, cfg["timeline"]))
        self.out = os.path.normpath(os.path.join(self.dir, cfg["out"]))
        os.makedirs(self.out, exist_ok=True)
        os.makedirs(os.path.join(self.out, "stems"), exist_ok=True)

    def module(self, name):
        p = os.path.join(self.dir, name + ".py")
        if not os.path.exists(p):
            return None
        spec = importlib.util.spec_from_file_location(f"cuelab_project_{name}", p)
        m = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = m
        spec.loader.exec_module(m)
        return m
