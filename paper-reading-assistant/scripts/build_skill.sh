#!/usr/bin/env bash
# build_skill.sh — repackage the skill source into a distributable .skill zip.
#
# The skill's source of truth lives unzipped in the repo at
# paper-reading-assistant/ (so it is diffable and editable). A .skill file is
# just a zip of that folder. Run this after editing SKILL.md or the scripts to
# regenerate ../paper-reading-assistant.skill for upload / sharing.
#
# Usage:  bash paper-reading-assistant/scripts/build_skill.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"          # paper-reading-assistant/
REPO_ROOT="$(dirname "$SKILL_DIR")"
OUT="$REPO_ROOT/paper-reading-assistant.skill"

cd "$REPO_ROOT"
rm -f "$OUT"
zip -r -X "$OUT" "paper-reading-assistant" \
    -x "*/__pycache__/*" "*.pyc" "*/.DS_Store" >/dev/null
echo "Built $OUT"
