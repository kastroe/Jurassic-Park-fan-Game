---
name: postmortem
description: Generate a root-cause postmortem after a bug fix. Activate after any bug fix commit.
origin: Custom
---

# Postmortem Skill

Turns bug fixes into durable knowledge by writing structured postmortems.

## When to Activate

Activate when:
- A bug fix commit has been made
- The user says "that was a tricky bug"
- A customer-reported issue was resolved

## Workflow

1. Check recent commits: `git log -5 --oneline`
2. Check the fix diff: `git diff HEAD~1`
3. Write postmortem: what broke, root cause, why it wasn't caught earlier
4. Propose one concrete guardrail (test, lint rule, or check) to prevent recurrence
5. Append to POSTMORTEMS.md
