---
name: commit-split
description: Split a messy working diff into logical atomic commits. Activate when the user has many unstaged changes and says "commit" without specifying organization.
origin: Custom
---

# Commit Split Skill

Helps organize large changes into clean, atomic commits following conventional commit format.

## When to Activate

Activate when:
- The user says "commit everything" and there are many changed files
- Working tree diff touches multiple unrelated features
- The user asks "how should I split this?"

## Workflow

1. Read the working tree diff: `git diff`
2. Group changes by logical concern
3. Propose 2-5 atomic commits with conventional commit messages
4. Show which files/hunks belong in each commit
5. Do not execute the commits — present the plan for user approval
