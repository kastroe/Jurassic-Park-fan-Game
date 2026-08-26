# OpenCode Agent System

Internal reference for the OpenCode configuration in `the repository-root `opencode.json``.

> **Source of truth:** `opencode.json` defines the runtime agents, permissions, models, and MCP servers. This README is explanatory documentation and must not contradict it.
>
> **Workflow source of truth:** `.opencode/instructions/progress.md` is the canonical workflow protocol. It defines progress logging, artifact handoff, deployment gates, commit verification, and audit-trail cleanup. Update that file when workflow behavior changes.

## Runtime overview

- **Primary agent:** `orchestrator`
- **Default model:** `deepinfra/deepseek-ai/DeepSeek-V4-Flash`
- **Configured providers:** DeepInfra
- **Configured MCP servers:** 6
- **Local skill library:** `.opencode/skills/`
- **Slash commands:** `.opencode/commands/`
- **Persistent MCP memory:** the path given by `MEMORY_FILE_PATH`

The orchestrator routes requests by meaning. Non-trivial implementation work should normally follow:

```text
planner → coder → tester → reviewer
                         ↘ security-auditor when security is relevant
```

Test failures loop through `debug-specialist` and then back to `coder`, with a maximum of three retry cycles before escalation.

## Agents

| Agent | Role | Model |
|---|---|---|
| `orchestrator` | Primary semantic router and workflow coordinator | Default model |
| `planner` | Architecture and implementation planning; writes `SPEC-{slug}.md` | Default model |
| `explorer` | Read-only codebase search; writes `FINDINGS-{slug}.md` | `deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo` |
| `coder` | General implementation and bug fixes; writes `FILES_MODIFIED-{slug}.md` | Default model |
| `tester` | Writes and runs tests; writes `TEST_RESULTS-{slug}.md` | Default model |
| `reviewer` | Code quality and PR-readiness review; writes `REVIEW_RESULTS-{slug}.md` | Default model |
| `security-auditor` | Security and vulnerability review; writes `AUDIT_RESULTS-{slug}.md` | Default model |
| `debug-specialist` | Root-cause analysis after test failures; writes `DEBUG_LOG-{slug}.md` | Default model |
| `devops` | Infrastructure, CI/CD, and deployment; writes `DEPLOY_LOG-{slug}.md` | Default model |
| `researcher` | External web and documentation research via Hound; writes `RESEARCH-{slug}.md` | Default model |
| `writer` | Documentation and prose | Default model |
| `growth-marketer` | Marketing and growth work | Default model |
| `sales-agent` | Sales outreach and CRM-oriented work | Default model |
| `support-agent` | Product support and how-to responses | Default model |

Agents not listed above are not part of the active runtime configuration. In particular, references to `plan-checker`, `backend-coder`, `frontend-coder`, `performance-optimizer`, `brand-creative`, or `product-strategist` are historical and should not be treated as available agents unless added to `opencode.json`.

## Permissions

The live configuration currently prioritizes autonomy over isolation. Review `opencode.json` before using this setup with untrusted prompts, untrusted repositories, or sensitive credentials.

### Global permissions

| Capability | Current setting |
|---|---|
| File read | Allowed globally, including `.env` patterns |
| File edit | Allowed globally |
| Bash | Allowed globally, including destructive commands configured in the file |
| Glob / grep | Allowed globally |
| Web fetch / web search | Denied globally; research uses the Hound MCP instead |

Per-agent permissions add restrictions or capabilities. Notable examples:

- `explorer` is intended to be read-only by role, although its current bash permission includes a broad fallback.
- `coder` can edit, run shell commands, and access the language/framework convention skills.
- `researcher` is intended for Hound-based research and does not receive edit operations.
- `reviewer` and `security-auditor` are responsible for review artifacts used by deployment gates.

This README does not reproduce every permission rule. The JSON configuration is authoritative.

## MCP servers

| Server | Type | Purpose | Persistence / credentials |
|---|---|---|---|
| `github` | Local | GitHub repository and issue operations | Reads `GITHUB_TOKEN` from the environment |
| `filesystem` | Local | Filesystem operations scoped to the configured `OPENCODE_WORKSPACE` | No external credential |
| `memory` | Local | Knowledge-graph memory | Persists to the path given by `MEMORY_FILE_PATH` via `MEMORY_FILE_PATH` |
| `sequential-thinking` | Local | Structured reasoning support | No external credential |
| `playwright` | Local | Browser automation and page inspection | No external credential |
| `hound` | Local | Web search, fetch, crawl, and research | Uses the local `hound` executable/configuration |

Most MCP commands currently use `npx -y`. This is convenient but means package versions may change between cache refreshes. Pin versions when reproducibility or security requires it.

### Memory model

There are two separate persistence mechanisms:

1. **Task/audit state:** `PROGRESS.md` and namespaced task artifacts in the project. These are the authoritative records for an active workflow.
2. **Cross-session knowledge memory:** the `memory` MCP server's JSONL file at the path given by `MEMORY_FILE_PATH`.

The memory MCP is now configured for durable storage, but persistence does not mean every fact is automatically recalled. Agents must explicitly use the memory tools when they need to retrieve or store long-lived facts. Do not use MCP memory as a replacement for required task artifacts.

The `harness-memory` package is also present in `.opencode/package.json`; it is a separate local package and should not be confused with the configured `memory` MCP server. Treat it as an optional/legacy memory layer unless its plugin wiring is explicitly restored and verified.

## Workflow and audit protocol

`.opencode/instructions/progress.md` is the **canonical workflow document**. Agents must follow it rather than duplicating workflow rules in this README.

It defines:

- Reading `PROGRESS.md` from disk before actions.
- Append-only agent entries.
- Namespaced artifacts such as `SPEC-{slug}.md` and `TEST_RESULTS-{slug}.md`.
- Test failure loopback through `debug-specialist` and `coder`.
- Deployment gating on reviewer and security-auditor results.
- Mandatory completion-commit verification before cleanup.
- Archive-first audit retention; cleanup must not destroy the trail.
- Workflow Protocol v2 task manifests, append-only events, explicit gates, commit proof, crash recovery, and central archive ownership.

The v2 controller is `.opencode/bin/opencode-workflow`. Active v2 work lives in `.opencode/tasks/{task-id}/` with `manifest.yaml`, `events.ndjson`, and `artifacts/`; use `task import-v1` for explicit, non-destructive migration of legacy root artifacts. The orchestrator prompt contains routing and gate enforcement. The detailed protocol belongs in `progress.md` so it has one maintained home.

## Artifact convention

| Agent | Artifact |
|---|---|
| `planner` | `SPEC-{slug}.md` |
| `coder` | `FILES_MODIFIED-{slug}.md` |
| `tester` | `TEST_RESULTS-{slug}.md` |
| `debug-specialist` | `DEBUG_LOG-{slug}.md` |
| `reviewer` | `REVIEW_RESULTS-{slug}.md` |
| `security-auditor` | `AUDIT_RESULTS-{slug}.md` |
| `devops` | `DEPLOY_LOG-{slug}.md` |
| `explorer` | `FINDINGS-{slug}.md` |
| `researcher` | `RESEARCH-{slug}.md` |

The filesystem is the shared bus between agents. Agents should pass file paths and short context summaries rather than replaying full conversation history.

## Directory layout

```text
opencode.json                 Runtime configuration
.opencode/
├── README.md                 This reference
├── commands/                 Custom slash commands
├── bin/
│   └── opencode-workflow     Workflow Protocol v2 controller
├── instructions/
│   ├── commands.md           Command catalog and skill-loading guidance
│   └── progress.md           Canonical workflow and audit protocol
├── tasks/                    Active v2 task directories (one manifest per task)
├── skills/                   Local skills and conventions
├── agent/                    Reserved for agent definition files
└── plugins/                  Reserved for OpenCode plugins
```

`agent/` and `plugins/` may be empty; active agent definitions and MCP configuration currently live in `opencode.json`.

## Operational checklist

Before changing the setup:

1. Read `opencode.json` and this README.
2. Read `.opencode/instructions/progress.md` for workflow behavior.
3. Keep credentials in environment variables; do not place API keys or bearer tokens in config files.
4. Run a JSON validation check after editing `opencode.json`.
5. Run `opencode mcp list` after MCP changes.
6. Verify the persistent memory path is writable and owner-only.
7. Reconcile this README whenever agents, permissions, models, MCP servers, or persistence paths change.

For security-sensitive configuration changes, use the `audit-config` and `secrets-scan` skills before committing or sharing the configuration.
