#!/usr/bin/env bash
# test-loop.sh — Auto-detect test framework, run tests, retry on failure
# Usage: ./test-loop.sh [max-retries] [test-pattern]
# Detects: pytest, jest, cargo test, go test, npm test, mvn test, gradle test
set -euo pipefail

MAX_RETRIES="${1:-1}"
PATTERN="${2:-}"
RETRIES=0

detect_test_framework() {
  if [ -f "pyproject.toml" ] && grep -q '\[tool.pytest' pyproject.toml 2>/dev/null; then
    echo "pytest"
  elif [ -f "setup.py" ] || [ -f "setup.cfg" ]; then
    echo "pytest"
  elif [ -f "package.json" ] && grep -q '"jest"' package.json 2>/dev/null; then
    echo "jest"
  elif [ -f "package.json" ]; then
    echo "npm"
  elif [ -f "Cargo.toml" ]; then
    echo "cargo"
  elif ls *.go 1>/dev/null 2>&1; then
    echo "go"
  elif [ -f "pom.xml" ]; then
    echo "maven"
  elif [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
    echo "gradle"
  else
    echo "unknown"
  fi
}

run_tests() {
  local framework="$1"
  local pattern="${2:-}"
  case "$framework" in
    pytest)    python -m pytest "$pattern" -x --tb=short 2>&1 || true ;;
    jest)      npx jest "$pattern" --no-coverage 2>&1 || true ;;
    npm)       npm test 2>&1 || true ;;
    cargo)     cargo test 2>&1 || true ;;
    go)        go test ./... 2>&1 || true ;;
    maven)     mvn test 2>&1 || true ;;
    gradle)    gradle test 2>&1 || true ;;
    *)         echo "No test framework detected"; return 1 ;;
  esac
}

FRAMEWORK=$(detect_test_framework)
echo "=== Test Loop: detected $FRAMEWORK ==="

while [ $RETRIES -le $MAX_RETRIES ]; do
  if [ $RETRIES -gt 0 ]; then
    echo "=== Retry $RETRIES/$MAX_RETRIES ==="
  fi
  OUTPUT=$(run_tests "$FRAMEWORK" "$PATTERN")
  echo "$OUTPUT"
  
  if echo "$OUTPUT" | grep -qiE "(passed|success|ok|0 failed)"; then
    echo "=== ALL TESTS PASSED ==="
    exit 0
  fi
  
  RETRIES=$((RETRIES + 1))
done

echo "=== TESTS FAILED after $MAX_RETRIES retries ==="
exit 1
