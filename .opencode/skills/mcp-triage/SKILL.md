---
name: mcp-triage
description: Check MCP connection status, diagnose failures, suggest fixes. Activate when MCP errors appear or the user says "MCP is broken."
origin: Custom
---

# MCP Triage Skill

Diagnoses and fixes MCP server connection issues.

## When to Activate

Activate when:
- The user says "MCP isn't working" or "MCP failed"
- An MCP server returns errors
- After adding or modifying MCP configuration
- On session startup when MCPs show as disconnected

## Workflow

1. Run `opencode mcp list`
2. Identify failed MCPs
3. For each failure:
   - 401/403 → missing or invalid auth
   - Connection closed → npx package issue or timeout
   - Needs auth → missing env var
4. Check env vars are set
5. Suggest specific fix for each failure
