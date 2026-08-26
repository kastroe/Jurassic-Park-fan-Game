---
name: caching-patterns
description: Caching strategies for Redis, CDN, and in-memory caches.
origin: Custom
---
Caching patterns: Cache on read, invalidate on write. Use Redis for distributed caching, in-memory for single-process. Set TTLs, never unbounded caches. Cache-aside pattern: read from cache, miss → load from DB → populate cache. Activate when designing or implementing caching.
