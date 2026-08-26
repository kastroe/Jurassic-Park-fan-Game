---
name: data-modeling
description: Schema design, normalization tradeoffs, and data modeling patterns.
origin: Custom
---
Data modeling: Normalize to 3NF by default. Denormalize only when query performance requires it. Use UUIDs for distributed systems, auto-increment for single-DB. Prefer timestamp columns over datetime. Activate when designing or reviewing data models.
