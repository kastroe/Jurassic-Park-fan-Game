---
name: pr-ready
description: Pre-flight check before opening a PR — diff against main, run tests, flag unfinished code (TODOs, console.logs, commented-out blocks). Activate when the user says "ready to merge" or "let's open a PR."
origin: Custom
---

# PR Ready Skill

Verifies a branch is ready for a pull request by checking the diff, running tests, and catching unfinished code.

## When to Activate

Activate when:
- The user says "I think this is ready to merge" or "let's open a PR"
- The user asks "is this branch ready?"
- Before creating any pull request

## Workflow

1. Diff against main: `git diff main...HEAD`
2. Check changed files: `git diff --name-only main...HEAD`
3. Run tests: `npm test`
4. Review for: bugs, missed edge cases, style issues, TODOs, console.logs, commented-out code
5. Draft a PR title and description
