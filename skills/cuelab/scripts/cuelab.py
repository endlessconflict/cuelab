#!/usr/bin/env python3
"""cuelab command line.

  python cuelab.py new <dir> --video <silent.mp4> --timeline <timeline.json>   scaffold a sound project next to a video
  python cuelab.py build <dir>        render effects and score, mix, master, mux (out/<video>-sound.mp4), cue sheet
  python cuelab.py audit <dir>        measure the picture and compare with the cue sheet (needs checks.py)
  python cuelab.py quality <dir>      loudness, balance, phone and mono simulation, click detector
  python cuelab.py report <dir>       figures, mux check, QA_REPORT.md
  python cuelab.py all <dir>          build + audit + quality + report
  python cuelab.py ease-check <video-project-dir>   compare the Python easing port against Remotion's own curves (needs node, npm install done)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "..", "engine")
sys.path.insert(0, ENGINE)

import timeline as T  # noqa: E402
from project import Project  # noqa: E402


def cmd_new(a):
    dst = os.path.abspath(a.dir)
    if os.path.exists(dst) and os.listdir(dst):
        sys.exit(f"refusing: {dst} exists and is not empty")
    shutil.copytree(os.path.join(HERE, "..", "templates", "project"), dst, dirs_exist_ok=True)
    pj = os.path.join(dst, "project.json")
    cfg = json.load(open(pj, encoding="utf-8"))
    if a.video:
        cfg["video"] = os.path.relpath(os.path.abspath(a.video), dst).replace("\\", "/")
    if a.timeline:
        cfg["timeline"] = os.path.relpath(os.path.abspath(a.timeline), dst).replace("\\", "/")
    json.dump(cfg, open(pj, "w", encoding="utf-8"), indent=2)
    print(f"created {dst}\nnext: edit cues.py (cues), music.py (score), checks.py (audit), then: python cuelab.py all {a.dir}")


def load(path):
    p = Project(path)
    T.load(p.timeline_path)
    return p


def cmd_build(a):
    import mix as MX
    import report as R

    p = load(a.dir)
    MX.build(p)
    final = MX.mux(p)
    print("wrote", final)
    print("cue sheet", R.cue_sheet(p))
    return p, final


def cmd_audit(a):
    import audit as AU

    p = load(a.dir)
    ok, n = AU.run(p, force=getattr(a, "force", False))
    return ok == n


def cmd_quality(a):
    import quality as Q

    Q.run(load(a.dir))


def cmd_report(a):
    import report as R

    p = load(a.dir)
    final = os.path.join(p.out, os.path.splitext(os.path.basename(p.video))[0] + "-sound.mp4")
    print("figure", R.analysis_figure(p))
    R.mux_check(p, final)
    print("report", R.qa_markdown(p))


def cmd_all(a):
    cmd_build(a)
    a.force = True
    good = cmd_audit(a)
    cmd_quality(a)
    cmd_report(a)
    sys.exit(0 if good else 1)


def cmd_ease(a):
    ref = os.path.join(HERE, "ease_ref.mjs")
    out = subprocess.run(["node", ref, os.path.abspath(a.dir)], capture_output=True, text=True)
    if out.returncode:
        sys.exit(out.stderr)
    ref = json.loads(out.stdout)
    T.load(os.path.join(a.dir, "timeline.json"))
    worst = 0.0
    for k in ("out", "inOut", "soft"):
        for f, y in ref[k]:
            worst = max(worst, abs(T.prog(f, 0, 100, k) - y))
    print(f"max easing error vs Remotion: {worst:.2e}")
    sys.exit(0 if worst < 1e-4 else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("dir")
    n.add_argument("--video")
    n.add_argument("--timeline")
    for name in ("build", "audit", "quality", "report", "all", "ease-check"):
        s = sub.add_parser(name)
        s.add_argument("dir")
        if name == "audit":
            s.add_argument("--force", action="store_true")
    a = ap.parse_args()
    {"new": cmd_new, "build": cmd_build, "audit": cmd_audit, "quality": cmd_quality, "report": cmd_report, "all": cmd_all, "ease-check": cmd_ease}[a.cmd](a)


if __name__ == "__main__":
    main()
