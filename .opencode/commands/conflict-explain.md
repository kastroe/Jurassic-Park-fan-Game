---
description: Explain merge conflict intent before resolving
agent: plan
---

Conflict markers: !`grep -rn "<<<<<<<\|=======\|>>>>>>>" --include="*.{ts,tsx,js,md,json}" . | grep -v node_modules | head -40`

For each conflict, analyze both sides:
1. What does "ours" (current branch) intend?
2. What does "theirs" (incoming branch) intend?
3. Why they conflict
4. Recommended resolution strategy

Present this so I can make an informed decision on how to resolve.
