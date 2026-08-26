#!/usr/bin/env bash
# git-helpers.sh — Git operations: status, diff, commit, branch, rollback
# Source this file: source git-helpers.sh
# Or run directly: ./git-helpers.sh <command> [args]

set -euo pipefail

git_status_summary() {
  echo "=== Git Status ==="
  git status --short 2>/dev/null | head -30 || echo "(no changes)"
  echo ""
  echo "=== Recent Commits ==="
  git log --oneline -5 2>/dev/null || echo "(no commits)"
}

git_diff_summary() {
  local MAX_LINES="${1:-50}"
  echo "=== Unstaged Changes ==="
  git diff --stat 2>/dev/null || echo "(none)"
  echo ""
  git diff 2>/dev/null | head -n "$MAX_LINES" || true
  local TOTAL=$(git diff 2>/dev/null | wc -l)
  if [ "$TOTAL" -gt "$MAX_LINES" ]; then
    echo "... [diff truncated: $TOTAL lines total] ..."
  fi
}

git_commit() {
  local MESSAGE="${1:-}"
  if [ -z "$MESSAGE" ]; then
    echo "Usage: git_commit <message>" >&2
    return 1
  fi
  
  git add -A
  git commit -m "$MESSAGE" 2>&1 || echo "Nothing to commit"
}

git_create_branch() {
  local NAME="$1"
  if [ -z "$NAME" ]; then
    echo "Usage: git_create_branch <branch-name>" >&2
    return 1
  fi
  git checkout -b "$NAME" 2>&1
}

git_undo_to_last_commit() {
  echo "=== Undoing uncommitted changes ==="
  git checkout -- . 2>&1
  echo "Done. Uncommitted changes reverted."
}

git_create_pr_description() {
  local FROM_BRANCH
  FROM_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  local CHANGES
  CHANGES=$(git diff main..."$FROM_BRANCH" --stat 2>/dev/null || git diff HEAD~1 --stat 2>/dev/null || echo "unknown")
  
  cat <<PR
## Summary
Changes in branch: $FROM_BRANCH

## Files Changed
$CHANGES

## Type
- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [ ] Documentation
- [ ] Dependencies
PR
}

# CLI dispatch
case "${1:-}" in
  status) git_status_summary ;;
  diff) git_diff_summary "${2:-50}" ;;
  commit) git_commit "${2:-}" ;;
  branch) git_create_branch "${2:-}" ;;
  undo) git_undo_to_last_commit ;;
  pr-desc) git_create_pr_description ;;
  *)
    echo "Commands: status, diff [lines], commit <msg>, branch <name>, undo, pr-desc" >&2
    exit 1
    ;;
esac
