---
description: Compare .env.example against actual env usage in code
---

.env.example: @.env.example

Extract all process.env references from the codebase:
!`grep -rn "process\.env\.\|import.meta.env." --include="*.ts" --include="*.tsx" --include="*.js" . | grep -v node_modules | head -60`

Report which env vars are in code but missing from .env.example,
and which in .env.example are unused.
