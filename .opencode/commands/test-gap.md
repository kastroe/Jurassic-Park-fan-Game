---
description: Find untested source files and scaffold new test files for them
---

Source files: !`find . -type f \( -name "*.ts" -o -name "*.tsx" \) -not -path "*/node_modules/*" -not -path "*.test.*" -not -path "*.spec.*" | head -50`
Test files: !`find . -type f \( -name "*.test.*" -o -name "*.spec.*" \) -not -path "*/node_modules/*" | head -50`

Identify source files without corresponding test files.
Pick the 3 highest-value untested files (most logic, most imports)
and scaffold a basic test file for each with describe/it blocks.
