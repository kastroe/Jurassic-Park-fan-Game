---
description: Locate original project branding refs for fork renaming
agent: build
---

Search for original project name/branding across the codebase:
!`grep -rn "original_project_name\|original_org\|original_logo\|original_copyright" --include="*.{ts,tsx,js,json,md}" . | grep -v node_modules | head -60`

Also search for:
- Copyright headers referencing the original project/org
- Logo files, brand assets in /assets, /public, /img
- Package name references in package.json, README, docs

Create a checklist of items to rebrand. Do NOT modify anything —
surface for human review. Flag legal/copyright notices that must be preserved.
