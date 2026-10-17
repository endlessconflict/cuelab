#!/bin/bash
# Copies the skill into your user skills folder so Claude Code can load it everywhere.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/cuelab"
mkdir -p "$(dirname "$dest")"
rm -rf "$dest"
cp -r "$here/skills/cuelab" "$dest"
echo "installed to $dest"
