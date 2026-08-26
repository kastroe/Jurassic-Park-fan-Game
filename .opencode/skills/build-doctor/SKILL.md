---
name: build-doctor
description: Run the build/diagnostics and fix failures automatically. Activate when the build fails, types error, or tests crash.
origin: Custom
---

# Build Doctor Skill

Diagnoses and fixes build failures, type errors, and test crashes automatically.

## When to Activate

Activate when:
- A build command fails (npm run build, tsc, etc.)
- TypeScript type errors appear
- Tests crash on startup (not test logic failures)
- The user says "the build is broken"

## Workflow

1. Run the build: `npm run build` or `tsc --noEmit`
2. Read the full error output (not just the last line)
3. Classify: type error? missing module? syntax? config?
4. Propose and apply the minimal fix
5. Re-run to confirm
