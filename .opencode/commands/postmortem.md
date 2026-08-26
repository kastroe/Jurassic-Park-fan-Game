---
description: Write a root-cause postmortem from recent changes
---

Recent commits: !`git log -5 --oneline`
Diff: !`git diff HEAD~1`

Write a short postmortem: what broke, root cause, why it wasn't caught earlier,
and one concrete guardrail (test, lint rule, or check) to prevent recurrence.
Append it to POSTMORTEMS.md.
