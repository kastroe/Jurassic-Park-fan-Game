# Available Custom Slash Commands

When relevant to the task, suggest these to the user.

## Codebase Onboarding
- `/map-architecture` — Walk repo → produce ARCHITECTURE.md
- `/onboard-file <path>` — Explain file, who imports it, what breaks if it changes
- `/find-owner-logic <concept>` — grep for all files touching a domain concept
- `/component-inventory` — Catalog UI components, props, and usage

## Documentation
- `/doc-sync` — Diff README/docs against actual code, flag stale claims
- `/api-doc-gen` — Generate/update API reference from route handlers
- `/release-notes [range]` — Draft release notes from commit range
- `/contributing-gen` — Generate/update CONTRIBUTING.md

## Refactoring & Modernization
- `/modernize-syntax <path>` — Upgrade legacy patterns (class→hooks, CJS→ESM, etc.)
- `/refactor-safe <target>` — Refactor with test verification before AND after
- `/extract-component <path>` — Extract reusable component, show diff
- `/typescriptify <path>` — Convert .js→.ts with inferred types
- `/dep-upgrade [pkg]` — Check outdated deps with breaking change notes
- `/remove-unused-deps` — Find deps in package.json never imported
- `/restyle-component <path>` — Visual restyle only, no logic/props changes

## Testing & Quality
- `/quick-test` — Run existing test suite, summarize pass/fail/fixes
- `/test-gap` — Find untested source files, scaffold new tests
- `/flaky-test-hunt <test>` — Rerun test 5× to isolate flakiness
- `/commit-split` — Split messy diff into atomic conventional commits
- `/pr-ready` — Pre-flight PR check: diff + tests → PR body
- `/tech-debt-scan` — Grep for TODO/FIXME/HACK, cluster by severity
- `/dead-code-scan` — Find unused exports, orphaned files, dead routes

## Security & Legal
- `/dep-audit [pkg]` — npm audit + security risk summary
- `/secrets-scan` — Check for committed API keys/tokens before push
- `/injection-check <path>` — Review file for SQL/XSS/command-injection risk
- `/license-audit` — Scan deps for copyleft/compatibility conflicts
- `/attribution-check` — Verify copyright headers preserved (fork compliance)
- `/strip-branding` — Locate original project branding/name refs for fork renaming

## Git & Review
- `/git-review` — Review recent commits + diff
- `/conflict-explain` — Analyze merge conflict: both sides"redacted"s commits
- `/postmortem` — Root-cause postmortem from recent fix
- `/build-doctor` — Run build, diagnose failures, propose fix

# Autonomous Skills (agent loads these automatically)

When the situation matches, load the skill via `skill` tool instead of asking the user for a slash command:

- `pr-ready` — Load when user says "ready to merge" or "let's PR." Checks diff + tests + unfinished code, drafts PR body.
- `build-doctor` — Load when build fails or types error. Diagnoses and fixes automatically.
- `secrets-scan` — Load before any push. Scans for committed API keys/tokens.
- `audit-config` — Load when config changes or security is questioned. Audits opencode.json.
- `mcp-triage` — Load when MCP errors appear. Checks connections and suggests fixes.
- `postmortem` — Load after a bug fix. Writes root-cause postmortem.
- `commit-split` — Load when user has messy unstaged changes and says "commit." Proposes atomic commit plan.
- `progress-tracker` — Automatically loaded by multi-step agents (coder, planner, tester, debug-specialist, devops, explorer, reviewer, security-auditor). Follows the shared protocol in .opencode/instructions/progress.md. Agents re-read PROGRESS.md from disk before every action to prevent staleness — see the shared protocol for full rules.
