---
description: Pre-flight check before opening a PR
agent: build
---

Diff against main: !`git diff main...HEAD`
Changed files: !`git diff --name-only main...HEAD`
Test output: !`npm test`

Review the diff above for bugs, missed edge cases, and style issues.
Then write a PR title and description summarizing the change.
Flag anything that looks unfinished (TODOs, console.logs, commented code).
