---
description: Generate/update CONTRIBUTING.md for the project
agent: plan
---

package.json: @package.json
README: @README.md
License: @LICENSE
Project structure: !`find . -type d -maxdepth 2 -not -path "*/node_modules/*" -not -path "*/.git/*" | sort`
Test setup: !`grep -rn "test|vitest|jest|mocha" package.json | head -10`

Generate or update CONTRIBUTING.md covering:
1. How to set up the dev environment
2. How to run tests, lint, typecheck
3. Code style and commit conventions
4. PR workflow (branch naming, review process)
5. Where to ask questions
6. License and attribution requirements
