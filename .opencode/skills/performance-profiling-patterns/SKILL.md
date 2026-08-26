---
name: performance-profiling-patterns
description: Performance analysis patterns, profiling, and optimization strategies.
origin: Custom
---
Performance profiling: Measure before optimizing. Profile to find hotspots (CPU, memory, I/O). Common patterns: N+1 queries, missing indexes, large payloads, blocking IO. Batch DB queries, cache hot paths, lazy-load expensive operations. Activate when diagnosing performance issues.
