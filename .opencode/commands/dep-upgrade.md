---
description: Check outdated deps and summarize breaking changes
---

Outdated packages: !`npm outdated --json 2>/dev/null || pip list --outdated 2>/dev/null`

Focus on $ARGUMENTS (or all if not specified).
For each outdated package, summarize:
1. Version delta (current → latest)
2. Is it a major/minor/patch bump?
3. Breaking changes to watch for
4. Recommendation — upgrade now or defer?
