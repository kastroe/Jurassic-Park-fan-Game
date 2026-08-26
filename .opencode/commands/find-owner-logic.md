---
description: Locate all files touching a domain concept
---

Searching for domain concept: $ARGUMENTS

All files that reference this:
!`grep -rn "$ARGUMENTS" --include="*.ts" --include="*.tsx" -l . | grep -v node_modules | head -30`

Summarize: which files own the logic, which just reference it,
and what would need to change to modify this domain concept.
