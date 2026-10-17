"""Checks every skill in skills/: frontmatter present with name and description, name equals the folder, description under 1024
characters, and every relative reference (references/..., templates/..., scripts/...) mentioned in SKILL.md exists."""
import glob
import os
import re
import sys

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
bad = 0
for skill_md in glob.glob(os.path.join(root, "skills", "*", "SKILL.md")):
    d = os.path.dirname(skill_md)
    text = open(skill_md, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        print(f"FAIL {skill_md}: no frontmatter")
        bad += 1
        continue
    fm = dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M))
    if fm.get("name") != os.path.basename(d):
        print(f"FAIL {skill_md}: name {fm.get('name')!r} != folder {os.path.basename(d)!r}")
        bad += 1
    desc = fm.get("description", "")
    if not desc or len(desc) > 1024:
        print(f"FAIL {skill_md}: description missing or over 1024 chars ({len(desc)})")
        bad += 1
    for ref in sorted(set(re.findall(r"`((?:references|templates|scripts|engine|examples)/[\w./-]+)`", text))):
        if "*" in ref or ref.endswith("/"):
            ref = ref.rstrip("/")
        p = os.path.join(d, ref)
        if not os.path.exists(p) and not os.path.exists(os.path.join(root, ref)):
            print(f"FAIL {skill_md}: referenced path not found: {ref}")
            bad += 1
    print(f"ok   {os.path.basename(d)}: {len(text.splitlines())} lines, description {len(desc)} chars")
sys.exit(1 if bad else 0)
