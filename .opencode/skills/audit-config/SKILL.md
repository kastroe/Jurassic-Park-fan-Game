---
name: audit-config
description: Security audit of opencode.json — check scoping, permissions, secrets, model config. Activate when config changes or when security is questioned.
origin: Custom
---

# Config Audit Skill

Reviews opencode.json for security and correctness issues.

## When to Activate

Activate when:
- The user asks about security or safety
- opencode.json has been modified
- Setting up OpenCode on a new machine
- Before adding new MCPs or plugins

## Workflow

1. Read opencode.json
2. Check: are MCP paths properly scoped? Permissions set? Secrets hardcoded?
3. Check: plugin count reasonable? Model config set?
4. Report findings ranked by severity
