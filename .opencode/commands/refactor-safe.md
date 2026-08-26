---
description: Refactor with test verification before/after
agent: build
subtask: true
---

Target: $ARGUMENTS
Current tests: !`npm test -- --grep "$ARGUMENTS"`

Confirm tests pass now. Refactor $ARGUMENTS for clarity without changing behavior.
Re-run the same tests and show me the before/after diff of just the test output.
