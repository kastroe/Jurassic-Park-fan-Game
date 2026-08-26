---
description: Run the build and diagnose failures
agent: build
---

!`npm run build 2>&1 || npm run typecheck 2>&1 || tsc --noEmit 2>&1`

If the build failed, diagnose:
1. What is the actual error? (not just the last line)
2. Is it a type error, syntax error, missing module, or config issue?
3. What's the minimal fix?
4. Show the fix and re-run to confirm.
