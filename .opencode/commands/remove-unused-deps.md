---
description: Cross-reference package.json imports against actual usage
---

package.json: @package.json

Check each dependency against actual imports in the codebase:
!`grep -rn "from\|require(" --include="*.{ts,tsx,js}" . | grep -v node_modules | head -100`

Report which dependencies in package.json are never imported anywhere.
These are candidates for removal.
