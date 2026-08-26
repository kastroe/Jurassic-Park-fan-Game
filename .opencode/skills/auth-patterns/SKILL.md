---
name: auth-patterns
description: Authentication and authorization implementation patterns (not security audit).
origin: Custom
---
Auth patterns: Use OAuth 2.0 / OIDC for third-party auth. JWT for stateless sessions (short TTL), refresh tokens for rotation. Session-based auth for server-rendered apps. Use RBAC or ABAC for authorization. Activate when implementing auth flows.
