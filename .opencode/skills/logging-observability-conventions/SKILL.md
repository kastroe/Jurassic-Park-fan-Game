---
name: logging-observability-conventions
description: Logging structure, structured logging, and observability patterns.
origin: Custom
---
Logging conventions: Use structured logging (JSON), not plain text. Log at the right level (debug/info/warn/error). Include correlation IDs for request tracing. Never log secrets, PII, or full request bodies. Activate when implementing or reviewing logging.
