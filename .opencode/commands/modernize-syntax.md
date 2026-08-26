---
description: Upgrade a file from old patterns (class → hooks, callback → async)
agent: build
---

File: @$ARGUMENTS

Modernize this file:
- Class components → functional with hooks
- .then()/.catch() → async/await
- var → const/let
- CommonJS require → ESM import/export
- PropTypes → TypeScript types
- any legacy patterns you see

Do NOT change business logic, only syntax patterns.
