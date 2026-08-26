---
description: Draft release notes from a commit range
agent: build
---

$ARGUMENTS
Recent commits: !`git log --oneline --no-decorate -30`

Draft release notes from the commit range.
Group by type: Features, Bug Fixes, Performance, Documentation, Maintenance.
Use conventional commit types (feat/fix/perf/docs/chore) to classify each.
Include migration notes for any breaking changes.
