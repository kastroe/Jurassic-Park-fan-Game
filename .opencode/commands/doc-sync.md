---
description: Diff README/docs against actual code — flag stale claims
agent: build
---

README: @README.md
API surface: !`grep -rn "export\|async function\|app\.\(get\|post\|put\|delete\|patch\)" --include="*.ts" --include="*.tsx" . | grep -v node_modules | grep -v ".test." | head -80`

Compare the README/docs against the actual code. Flag:
1. Features documented but not implemented
2. Features implemented but not documented
3. Outdated API examples or endpoint paths
4. Setup instructions that don't match current config
