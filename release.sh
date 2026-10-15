#!/usr/bin/env bash
# Publish the current main to github.com/andrewdvass/pocket-ceo without force-pushing
# and without SELLER-NOTES.md. Run from the repo root after committing on main.
set -euo pipefail
v=$(python3 -c "import json;print(json.load(open('plugin/.claude-plugin/plugin.json'))['version'])")
git diff --quiet && git diff --cached --quiet || { echo "Commit your changes on main first."; exit 1; }
git checkout -q publish
git checkout main -- .
git rm -q --cached --ignore-unmatch SELLER-NOTES.md
git add -A
git commit -qm "Pocket CEO v$v" || echo "Nothing new to publish."
git checkout -q main
git push origin publish:main
echo "Published v$v"
