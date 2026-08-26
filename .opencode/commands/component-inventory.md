---
description: Catalog every UI component, its props, and where it's used
---

Find all component files:
!`find . -type f \( -name "*.tsx" -o -name "*.jsx" \) -not -path "*/node_modules/*" | head -80`

For each component, extract: component name, props interface, file path.
List components by category (page, layout, shared, feature).
Note which have tests and which don't.
