---
name: coder-boilerplate
description: Executable scripts for test loops, build audit, linting, retry, env detection, and git helpers. Saves tokens vs reimplementing in prompts.
origin: Custom
---

# Coder Boilerplate

Pre-built executable scripts in `scripts/` that the coder agent can invoke via `bash` tool. Each covers a common multi-step pattern that would otherwise consume prompt tokens rewriting the logic.

## Scripts

### `detect-env.sh [path]`
Detect project language, framework, package manager, test framework, build tool. Outputs JSON. Run **first** on any new task — then load only the relevant convention skills based on what it reports.
```
./.opencode/skills/coder-boilerplate/scripts/detect-env.sh
→ {"language":"python","framework":"fastapi","package_manager":"poetry","test_framework":"pytest","build_tool":"make"}
```

### `test-loop.sh [max-retries=1] [test-pattern]`
Auto-detect test framework (pytest, jest, cargo-test, go-test, npm test, maven, gradle), run tests, retry on failure. Exit 0 on pass, 1 on persistent failure.
```
./.opencode/skills/coder-boilerplate/scripts/test-loop.sh 2
```

### `run-with-timeout.sh <timeout_seconds> <command...>`
Run any command with a timeout. Captures stdout/stderr. Truncates output over 200 lines to save context window space. Kills hung processes cleanly.
```
./.opencode/skills/coder-boilerplate/scripts/run-with-timeout.sh 60 "npm run build"
```

### `retry.sh [max-retries=3] [initial-delay=2] -- <command>`
Retry a command with exponential backoff (delay doubles each attempt). Good for network-dependent commands, flaky tests, race conditions.
```
./.opencode/skills/coder-boilerplate/scripts/retry.sh 5 1 -- "curl -s https://api.example.com"
```

### `lint-and-fix.sh [path]`
Auto-detect and run linters/formatters/type-checkers: ruff, black, mypy, eslint, prettier, tsc, cargo fmt, gofmt, golangci-lint. Runs with --fix where supported.
```
./.opencode/skills/coder-boilerplate/scripts/lint-and-fix.sh
```

### `bs-audit.sh [path]`
Build system audit: detect build tool, run build, capture output, parse common error patterns (TS errors, module-not-found, etc). Use before writing a fix after a failed build.
```
./.opencode/skills/coder-boilerplate/scripts/bs-audit.sh
```

### `git-helpers.sh <command> [args]`
Git operations: `status`, `diff [lines]`, `commit <msg>`, `branch <name>`, `undo`, `pr-desc`. Saves typing raw git commands for common workflows.
```
./.opencode/skills/coder-boilerplate/scripts/git-helpers.sh status
./.opencode/skills/coder-boilerplate/scripts/git-helpers.sh diff 100
./.opencode/skills/coder-boilerplate/scripts/git-helpers.sh commit "feat: add user avatars"
```

### `summarize-changes.sh [path]`
Show changed files, diff stats, new/untracked files, repo language breakdown. For context window management — use mid-task to refresh state without re-reading everything.
```
./.opencode/skills/coder-boilerplate/scripts/summarize-changes.sh
```

## Workflow (typical coder session)

```
1. detect-env.sh       → know what you're working with
2. load relevant skills via skill tool (python-conventions, fastapi, pytest, etc.)
3. read repo-conventions skill to match existing patterns
4. implement
5. lint-and-fix.sh     → auto-fix formatting
6. bs-audit.sh         → verify it compiles
7. test-loop.sh 2      → run tests with 2 retries
8. git-helpers.sh commit  → commit with message
9. summarize-changes.sh  → update PROGRESS.md with delta
```
