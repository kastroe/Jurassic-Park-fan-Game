---
description: Map unfamiliar repo architecture into a doc
agent: build
---

File tree: !`find . -type f -name "*.ts*" -not -path "*/node_modules/*" | head -200`
package.json: @package.json

Produce ARCHITECTURE.md: entry points, folder responsibilities, data flow
(API → state → UI), build tooling, and anything that looks non-standard
or "clever" that a newcomer should know about.
