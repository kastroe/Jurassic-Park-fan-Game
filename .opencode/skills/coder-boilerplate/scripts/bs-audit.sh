#!/usr/bin/env bash
# bs-audit.sh — Build system audit: run build, capture errors, parse output
# Usage: ./bs-audit.sh [path]
# Detects build tool and runs it, parsing common error formats
set -euo pipefail

TARGET="${1:-.}"
cd "$TARGET"

detect_build() {
  if [ -f "Cargo.toml" ]; then echo "cargo build"; return; fi
  if [ -f "package.json" ] && grep -q '"build"' package.json 2>/dev/null; then echo "npm run build"; return; fi
  if [ -f "go.mod" ] || ls *.go 1>/dev/null 2>&1; then echo "go build ./..."; return; fi
  if [ -f "Makefile" ] && grep -q '^build:' Makefile 2>/dev/null; then echo "make build"; return; fi
  if [ -f "justfile" ] && grep -q '^build' justfile 2>/dev/null; then echo "just build"; return; fi
  if [ -f "pyproject.toml" ]; then echo "python -m build"; return; fi
  if [ -f "pom.xml" ]; then echo "mvn compile"; return; fi
  if [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then echo "gradle build"; return; fi
  echo "unknown"
}

BUILD_CMD=$(detect_build)
echo "=== Build Audit ==="
echo "Detected: $BUILD_CMD"
echo ""

if [ "$BUILD_CMD" = "unknown" ]; then
  echo "No build system detected. Check for: Makefile, Cargo.toml, package.json, go.mod, pyproject.toml"
  exit 1
fi

OUTFILE=$(mktemp)
trap 'rm -f "$OUTFILE"' EXIT

if eval "$BUILD_CMD" 2>&1 | tee "$OUTFILE"; then
  echo ""
  echo "=== BUILD SUCCEEDED ==="
  exit 0
else
  echo ""
  echo "=== BUILD FAILED ==="
  
  # Parse common error patterns
  echo ""
  echo "--- Extracted Errors ---"
  grep -nE "(error|Error|ERROR|failed|FAILED|Cannot find|Module not found|TS[0-9]+)" "$OUTFILE" | head -20 || echo "(no recognizable error patterns)"
  
  exit 1
fi
