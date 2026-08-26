#!/usr/bin/env bash
# summarize-changes.sh — Summarize file changes for context management
# Usage: ./summarize-changes.sh [path]
# Shows changed files, diff stats, and new/untracked files
set -euo pipefail

TARGET="${1:-.}"
cd "$TARGET"

echo "=== Changed Files ==="
git diff --name-status 2>/dev/null | head -30
echo ""

echo "=== New/Untracked Files ==="
git ls-files --others --exclude-standard 2>/dev/null | head -20
echo ""

echo "=== Diff Stats ==="
git diff --stat 2>/dev/null || echo "(no changes)"
echo ""

echo "=== Repo Language Breakdown ==="
if command -v tokei &>/dev/null; then
  tokei --sort code 2>/dev/null | head -15
elif command -v cloc &>/dev/null; then
  cloc --quiet . 2>/dev/null | head -15
else
  echo "(install tokei or cloc for language stats)"
fi
