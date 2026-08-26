#!/usr/bin/env bash
# detect-env.sh — Detect project language, framework, package manager, and test framework
# Usage: ./detect-env.sh [path]
# Outputs JSON with detected tools
set -euo pipefail

TARGET="${1:-.}"
cd "$TARGET"

LANG=""
FRAMEWORK=""
PKG_MANAGER=""
TEST_FRAMEWORK=""
BUILD_TOOL=""

# Language detection
if [ -f "Cargo.toml" ]; then LANG="rust"; fi
if ls *.go 1>/dev/null 2>&1; then LANG="go"; fi
if [ -f "pom.xml" ] || [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then LANG="java"; fi
if [ -f "package.json" ]; then LANG="javascript"; fi
if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then LANG="python"; fi
if [ -f "Gemfile" ]; then LANG="ruby"; fi
if [ -f "composer.json" ]; then LANG="php"; fi
if [ -f "*.csproj" ]; then LANG="csharp"; fi 2>/dev/null
if [ -f "go.mod" ]; then LANG="go"; fi

# Package manager detection
if [ -f "Cargo.lock" ]; then PKG_MANAGER="cargo"; fi
if [ -f "package-lock.json" ]; then PKG_MANAGER="npm"; fi
if [ -f "yarn.lock" ]; then PKG_MANAGER="yarn"; fi
if [ -f "pnpm-lock.yaml" ]; then PKG_MANAGER="pnpm"; fi
if [ -f "poetry.lock" ]; then PKG_MANAGER="poetry"; fi
if [ -f "Pipfile.lock" ]; then PKG_MANAGER="pipenv"; fi
if [ -f "Gemfile.lock" ]; then PKG_MANAGER="bundler"; fi
if [ -f "go.sum" ]; then PKG_MANAGER="go-mod"; fi
if [ -f "Cargo.toml" ]; then PKG_MANAGER="cargo"; fi

# Framework detection
if [ -f "package.json" ]; then
  if grep -q '"react"' package.json 2>/dev/null; then FRAMEWORK="react"; fi
  if grep -q '"next"' package.json 2>/dev/null; then FRAMEWORK="nextjs"; fi
  if grep -q '"vue"' package.json 2>/dev/null; then FRAMEWORK="vue"; fi
  if grep -q '"svelte"' package.json 2>/dev/null; then FRAMEWORK="svelte"; fi
  if grep -q '"express"' package.json 2>/dev/null; then FRAMEWORK="${FRAMEWORK:-express}"; fi
fi
if [ -f "manage.py" ]; then FRAMEWORK="${FRAMEWORK:-django}"; fi
if [ -f "app.py" ] || grep -q 'from fastapi' *.py 2>/dev/null; then FRAMEWORK="${FRAMEWORK:-fastapi}"; fi
if [ -f "Gemfile" ] && grep -q 'rails' Gemfile 2>/dev/null; then FRAMEWORK="${FRAMEWORK:-rails}"; fi

# Test framework detection
if [ -f "pyproject.toml" ] && grep -q 'pytest' pyproject.toml 2>/dev/null; then TEST_FRAMEWORK="pytest"; fi
if [ -f "package.json" ]; then
  if grep -q '"jest"' package.json 2>/dev/null; then TEST_FRAMEWORK="${TEST_FRAMEWORK:-jest}"; fi
  if grep -q '"vitest"' package.json 2>/dev/null; then TEST_FRAMEWORK="${TEST_FRAMEWORK:-vitest}"; fi
fi
if [ -f "Cargo.toml" ]; then TEST_FRAMEWORK="${TEST_FRAMEWORK:-cargo-test}"; fi
if ls *_test.go 1>/dev/null 2>&1; then TEST_FRAMEWORK="${TEST_FRAMEWORK:-go-test}"; fi

# Build tool
if [ -f "Makefile" ]; then BUILD_TOOL="make"; fi
if [ -f "justfile" ]; then BUILD_TOOL="just"; fi
if [ -f "Cargo.toml" ]; then BUILD_TOOL="${BUILD_TOOL:-cargo}"; fi
if [ -f "package.json" ] && grep -q '"build"' package.json 2>/dev/null; then BUILD_TOOL="${BUILD_TOOL:-npm}"; fi

cat <<JSON
{
  "language": "${LANG:-unknown}",
  "framework": "${FRAMEWORK:-unknown}",
  "package_manager": "${PKG_MANAGER:-unknown}",
  "test_framework": "${TEST_FRAMEWORK:-unknown}",
  "build_tool": "${BUILD_TOOL:-unknown}"
}
JSON
