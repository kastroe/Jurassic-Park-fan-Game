# Workflow Protocol v2

This document is the canonical, human-readable workflow protocol. The executable
controller is `.opencode/bin/opencode-workflow`. `PROGRESS.md` remains a shared,
append-only compatibility log while v1 consumers migrate; a v2 task directory
is authoritative for its own task.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, and
**MAY** are normative.

## 1. Task boundary and manifest

The orchestrator MUST assign a unique `task-id` matching
`[a-z0-9][a-z0-9._-]{2,63}` and MUST create `.opencode/tasks/{task-id}/`
before dispatch. The directory MUST contain `manifest.yaml`, `events.ndjson`,
and `artifacts/`. `manifest.yaml` is the state ledger; artifacts are evidence.
The helper emits JSON-compatible YAML so it can be read by standard YAML tools.

Every manifest MUST contain:

```yaml
protocol: workflow-v2
created_at: <RFC3339>
updated_at: <RFC3339>
request: {summary: <text>, context: <text>, requested_by: <actor>, workspace_root: <path>}
lifecycle: {state: PLANNING, state_version: 1, last_transition_id: <event-id>}
artifacts: []
commit_proof: {status: PENDING, repository_root: null, branch: null, head_sha: null, changed_paths: [], commands_evidence: []}
archive: {status: ACTIVE, location: null}
```

The optional fields `supersedes_task_id`, `parent_task_id`, `retry_count`,
`last_heartbeat_at`, `blocked_reason`, and `migration_source` MUST be preserved.
Unknown fields MUST be preserved when the helper rewrites a manifest. Secrets,
tokens, credentials, and environment-file contents MUST NOT be recorded.
Artifact paths MUST be relative to the task directory, MUST NOT contain `..`,
and MUST NOT resolve through a symlink outside the task directory.

## 2. Agent rules and evidence

Before every meaningful action an agent MUST read this protocol and its manifest.
An agent MUST claim its role before changing task files, MUST write declared
evidence atomically below `artifacts/`, and MUST record applicable `started`,
`heartbeat`, `artifact_written`, `blocked`, `failed`, or `completed` events.
Agents MUST NOT advance lifecycle state, pass gates, archive tasks, or delete
audit records. Only the orchestrator or explicitly delegated controller MAY do
so. Required artifacts MUST be readable and have machine-detectable status on
the first non-empty line or in metadata; missing, malformed, stale, or ambiguous
evidence is `UNKNOWN`/`BLOCKED`, never an implicit pass.

`events.ndjson` MUST be append-only. Each line MUST contain a monotonically
increasing `event_id`, `task_id`, RFC3339 `timestamp`, `actor`, `type`, and
payload. Replay MUST stop at malformed input and mark the task
`RECOVERY_REQUIRED`; malformed events MUST NOT be silently skipped.

## 3. Lifecycle and transitions

States are `PLANNING`, `READY`, `IMPLEMENTING`, `VERIFYING`, `BLOCKED`,
`RECOVERY_REQUIRED`, `COMPLETED`, `ABORTED`, and `ARCHIVED`.

Allowed transitions:

| From | To | Required condition |
|---|---|---|
| PLANNING | READY | plan evidence exists and plan gate is PASS |
| PLANNING | BLOCKED | explicit missing requirement/decision |
| READY | IMPLEMENTING | implementation role claimed and scope accepted |
| READY | ABORTED | explicit cancellation |
| IMPLEMENTING | VERIFYING | implementation gate is PASS |
| IMPLEMENTING | BLOCKED | explicit dependency/scope/agent failure |
| IMPLEMENTING | RECOVERY_REQUIRED | uncertain write or commit boundary |
| VERIFYING | COMPLETED | all applicable gates pass and commit proof is verified, or approved non-git retention |
| VERIFYING | IMPLEMENTING | actionable verification failure and retry count permits |
| VERIFYING | BLOCKED | required evidence unavailable |
| Any active state | RECOVERY_REQUIRED | inconsistency, corruption, conflict, or stale lease |
| BLOCKED | PLANNING/IMPLEMENTING | blocker resolved with explanation |
| RECOVERY_REQUIRED | prior safe state | replay/reconciliation proves the boundary |
| Any nonterminal | ABORTED | explicit abort with retained evidence |
| COMPLETED/ABORTED | ARCHIVED | archive verification succeeds |

`ARCHIVED` is terminal. No operation MAY skip `RECOVERY_REQUIRED` when the
controller cannot prove which side of an operation completed.

## 4. Gates

Each gate is `PENDING`, `RUNNING`, `PASS`, `FAIL`, `BLOCKED`, or
`NOT_APPLICABLE`. `NOT_APPLICABLE` MUST include an orchestrator reason and is a
pass only where task policy permits it. Completion MUST have no `FAIL`,
`BLOCKED`, `CRITICAL`, or `HIGH` finding and every applicable gate MUST be PASS.

The gates are plan, implementation, tests, review, security, deployment, and
commit. Plan requires a valid `SPEC-*`; implementation requires scope
reconciliation; tests require a first-line status result; review/security reject
CRITICAL or HIGH; deployment is required only when in scope; commit requires
independent proof. Any implementation change MUST invalidate tests, review,
security, deployment, and commit and MUST record that event.

## 5. Commit proof

Before completion the orchestrator MUST independently determine whether the
workspace is a git repository, record repository root, branch, HEAD SHA, status,
changed paths, and command-result hashes, and compare task changes with declared
scope. A commit report is not proof merely because an agent says it committed.
Secret-scan evidence is REQUIRED before push and secret values MUST NOT appear
in evidence. Non-git work MUST use `NO_REPOSITORY`; default policy is BLOCKED.
An explicitly approved non-git completion MUST remain `RETAINED_ACTIVE` and MUST
NOT be destructively archived.

## 6. Crash recovery

On startup, the controller MUST scan manifests, replay events, check artifact
digests and leases, and report stale locks. Manifest, artifact, and event writes
MUST use temporary-file-plus-rename (event appends MUST flush and fsync). A
partial transition or malformed event puts the task in `RECOVERY_REQUIRED`;
history MUST NOT be overwritten. A stale run is aborted at run level and a
mutating task enters recovery. A crash after commit requires re-running git
verification; a crash before commit preserves files and leaves commit pending.
After three retry cycles the task MUST be BLOCKED. Corrupt inputs MUST be copied
to `recovery/` and never be the only deleted copy. Concurrent controllers MUST
not mutate an active lease.

## 7. Archive ownership

Only the orchestrator MAY archive. The central archive is
`~/.opencode/archive/{task-id}/` (override with `OPENCODE_ARCHIVE_DIR`). Archive is verified copy/transfer,
never blind deletion; this helper never deletes active records. The archive MUST
contain the final manifest, events, artifacts, recovery material, and
`archive-receipt.yaml` with source/destination, actor, source manifest digest,
file digests, timestamp, and completion/abort disposition. Every destination
file MUST verify before the source is considered archived. Failed verification
leaves the source intact and requires recovery. Legacy files are copied to
`artifacts/legacy/` and originals are never silently removed.

## 8. Helper reference

Run `.opencode/bin/opencode-workflow [--workspace PATH] [--json] ...`.

| Command | Purpose |
|---|---|
| `task create --id ID --summary TEXT` | Create a v2 task and initial event |
| `task show ID` | Read-only manifest/state summary |
| `task verify ID` | Full read-only validation |
| `task event ID --type TYPE --actor ACTOR` | Append a validated event |
| `task transition ID --to STATE --reason TEXT` | Apply validated lifecycle transition |
| `task gate set ID --gate NAME --status STATUS --evidence PATH` | Set a gate with evidence |
| `task commit-proof ID` | Collect independent git/non-git proof |
| `task inspect ID` | Reconcile/report manifest, events, artifacts, and scope |
| `task archive ID --actor orchestrator` | Completion-gated verified archive |
| `task import-v1 --slug SLUG --workspace PATH` | Copy legacy root artifacts without deletion |

Stable exit codes are: `0` success, `2` usage/schema, `3` not found, `4`
invalid transition/gate, `5` lease conflict, `6` evidence/scope, `7` commit
proof, `8` archive verification, `9` recovery required, and `10` permission/
ownership violation. Output MUST be redacted; `--json` is for machine consumers.

## 9. v1 compatibility

New work MUST use v2 manifests. Root-level `*-{slug}.md` files and shared
`PROGRESS.md` remain readable/importable evidence only. The helper MUST NOT
silently mutate v1 files; `import-v1` is explicit and preserves originals.
