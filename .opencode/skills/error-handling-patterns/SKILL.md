---
name: error-handling-patterns
description: Error handling conventions, typed errors, and recovery patterns.
origin: Custom
---
Error handling: Use typed/custom error types, not generic strings. Wrap errors with context at each layer (e.g. fmt.Errorf("...: %w")). Handle errors at the edge (middleware, controller). Never swallow errors silently. Activate when reviewing error handling patterns.
