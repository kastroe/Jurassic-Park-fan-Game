---
description: Convert a .js file to .ts with proper types
agent: build
subtask: true
---

File: @$ARGUMENTS

Convert this file from JavaScript to TypeScript:
1. Rename to .ts or .tsx
2. Add proper type annotations inferred from usage
3. Replace PropTypes with TypeScript interfaces
4. Add return types to functions
5. Fix any type errors

Show a summary of types added and any design decisions made.
