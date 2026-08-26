---
description: Find unused exports, orphaned files, dead routes
---

Look for:
1. Exported functions/components that nothing imports
2. Files not imported anywhere
3. Routes defined but never linked to
4. Deprecated props or APIs still in use

Search patterns:
!`grep -rn "export const\|export function\|export default" --include="*.ts" --include="*.tsx" . | grep -v node_modules | head -50`

Report the most likely candidates for removal.
