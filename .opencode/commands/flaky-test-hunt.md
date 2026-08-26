---
description: Rerun a test N times to isolate flakiness
subtask: true
---

Test: $ARGUMENTS
!`for i in 1 2 3 4 5; do echo "=== Run $i ===" && npx vitest run --reporter=verbose "$ARGUMENTS" 2>&1 | tail -5; done`

Analyze the results — does this test fail intermittently?
If flaky, identify: shared mutable state? async timing? test isolation?
Suggest a fix.
