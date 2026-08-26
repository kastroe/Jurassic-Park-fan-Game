---
description: Security audit of opencode.json config
---

Read the config in @opencode.json (repo root) and audit it:
1. Are MCP paths properly scoped? (filesystem should be limited)
2. Are permissions set for dangerous tools?
3. Any hardcoded secrets or API keys?
4. Plugin count — are there unnecessary plugins?
5. Model config — is small_model set for cheap tasks?
6. Any potential conflicts between plugins or MCPs?

Report findings ranked by severity.
