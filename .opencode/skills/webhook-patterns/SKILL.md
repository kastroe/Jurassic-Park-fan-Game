---
name: webhook-patterns
description: Webhook delivery patterns, retry logic, and payload conventions.
origin: Custom
---
Webhook patterns: Include idempotency keys in payloads. Retry with exponential backoff (3-5 attempts). Validate signatures with HMAC. Use idempotency keys so receivers can deduplicate. Activate when implementing or consuming webhooks.
