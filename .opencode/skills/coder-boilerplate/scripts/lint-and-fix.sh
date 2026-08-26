#!/usr/bin/env bash
# lint-and-fix.sh — Auto-detect and run linter/formatter/type-checker
# Usage: ./lint-and-fix.sh [path]
# Detects: ruff, eslint, prettier, rustfmt, gofmt, black, mypy, tsc
set -euo pipefail

TARGET="${1:-.}"
cd "$TARGET"

PASS=0
FAIL=0

check_cmd() {
  if command -v "$1" &>/dev/null; then return 0; else return 1; fi
}

run_linter() {
  local NAME="$1"
  shift
  echo "=== $NAME ==="
  if "$@" 2>&1; then
    echo "  ✅ $NAME passed"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $NAME found issues"
    FAIL=$((FAIL + 1))
  fi
  echo ""
}

# Python
if [ -f "pyproject.toml" ] || [ -f "ruff.toml" ] || [ -f ".ruff.toml" ]; then
  if check_cmd ruff; then run_linter "ruff" ruff check "$TARGET" --fix; fi
fi
if check_cmd black; then run_linter "black" black --check --diff "$TARGET" || echo "  Run: black $TARGET"; fi
if check_cmd mypy && [ -f "pyproject.toml" ] || [ -f "mypy.ini" ]; then
  run_linter "mypy" mypy "$TARGET" || true
fi

# JavaScript/TypeScript
if [ -f "package.json" ]; then
  if check_cmd npx; then
    if grep -q '"eslint"' package.json 2>/dev/null || [ -f ".eslintrc" ] || [ -f ".eslintrc.json" ]; then
      run_linter "eslint" npx eslint "$TARGET" --fix || true
    fi
    if grep -q '"prettier"' package.json 2>/dev/null || [ -f ".prettierrc" ]; then
      run_linter "prettier" npx prettier --check "$TARGET" || echo "  Run: npx prettier --write $TARGET"
    fi
    if [ -f "tsconfig.json" ]; then
      run_linter "tsc" npx tsc --noEmit || true
    fi
  fi
fi

# Rust
if [ -f "Cargo.toml" ]; then
  if check_cmd cargo; then
    run_linter "cargo fmt" cargo fmt --check || echo "  Run: cargo fmt"
    run_linter "cargo check" cargo check 2>&1 || true
  fi
fi

# Go
if ls *.go 1>/dev/null 2>&1; then
  if check_cmd go; then run_linter "gofmt" gofmt -d "$TARGET" 2>/dev/null || echo "  Run: gofmt -w $TARGET"; fi
  if check_cmd golangci-lint; then run_linter "golangci-lint" golangci-lint run "$TARGET" 2>&1 || true; fi
fi

echo "=== Results: $PASS passed, $FAIL failed ==="
exit $(( FAIL > 0 ? 1 : 0 ))
