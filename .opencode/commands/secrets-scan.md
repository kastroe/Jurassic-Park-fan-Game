---
description: Scan for accidentally committed secrets before pushing
---

Search for potential secrets in the working tree:
!`grep -rn "api[_-]key\|api[_-]secret\|secret\|token\|password\|credential\|sk-[a-zA-Z0-9]\|ghp_\|gho_\|ghu_" --include="*.{ts,tsx,js,py,env}" . | grep -v node_modules | grep -v ".example" | grep -v ".test." | head -50`

Flag anything that looks like a real secret. Check if .env is in .gitignore.
