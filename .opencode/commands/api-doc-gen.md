---
description: Generate/update API reference from route handlers
agent: plan
---

Route handlers: !`grep -rn "app\.\(get\|post\|put\|delete\|patch\|Router\)" --include="*.ts" --include="*.tsx" . | grep -v node_modules | head -60`

Parse the route definitions and generate an API reference doc.
For each endpoint include: method, path, request params, response shape,
auth requirements, and link to the handler file:line.
