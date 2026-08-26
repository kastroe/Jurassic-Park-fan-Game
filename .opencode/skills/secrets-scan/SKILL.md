---
name: secrets-scan
description: Scan working tree for accidentally committed secrets before push. Activate before any git push.
origin: Custom
---

# Secrets Scan Skill

Prevents accidentally pushing API keys, tokens, and credentials.

## When to Activate

Activate when:
- The user says "push" or "let's push this"
- Before any `git push` operation
- When onboarding a new fork or cloning a repo
- The user says "check for security issues"

## Workflow

1. Grep for patterns: api_key, secret, token, password, credential, sk-[a-zA-Z0-9], ghp_, gho_
2. Check .env files are in .gitignore
3. Filter false positives (test files, example files)
4. Report any findings with file paths and severity
