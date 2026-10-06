#!/usr/bin/env bash
# WorkBuddy skills installer for macOS / Linux
# usage: bash install.sh [copy|link|list]
#
#   copy  (default) - copy each skill into ~/.workbuddy/skills/
#   link            - symlink each skill (repo stays the live copy)
#   list            - only print skills found in this repo, install nothing

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO_DIR/skills"
DEST="${WORKBUDDY_SKILLS:-$HOME/.workbuddy/skills}"
MODE="${1:-copy}"

case "$MODE" in
  copy|link|list) ;;
  *) echo "[FAIL] unknown mode: $MODE"; echo "       usage: install.sh [copy|link|list]"; exit 2 ;;
esac

[ -d "$SRC" ] || { echo "[FAIL] skills folder not found: $SRC"; exit 2; }

if [ "$MODE" = "list" ]; then
  echo "Skills in this repo:"
  for d in "$SRC"/*/; do
    [ -d "$d" ] || continue
    n="$(basename "$d")"
    if [ -f "$d/SKILL.md" ]; then echo "  [*] $n"; else echo "  [-] $n  (no SKILL.md)"; fi
  done
  exit 0
fi

echo "Source : $SRC"
echo "Target : $DEST"
echo "Mode   : $MODE"
echo

mkdir -p "$DEST"

ok=0; fail=0
for d in "$SRC"/*/; do
  [ -d "$d" ] || continue
  n="$(basename "$d")"
  d="${d%/}"
  rm -rf "${DEST:?}/$n"
  if [ "$MODE" = "copy" ]; then
    cp -R "$d" "$DEST/$n"
  else
    ln -s "$d" "$DEST/$n"
  fi
  if [ -f "$DEST/$n/SKILL.md" ]; then
    if [ "$MODE" = "link" ]; then echo "  [OK]   $n  (linked)"; else echo "  [OK]   $n"; fi
    ok=$((ok+1))
  else
    echo "  [FAIL] $n"
    fail=$((fail+1))
  fi
done

echo
echo "Done. installed=$ok  failed=$fail"
echo "Restart your WorkBuddy session for new skills to load."
[ "$fail" -eq 0 ] || exit 1
