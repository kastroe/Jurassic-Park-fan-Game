---
description: Find hardcoded strings that should be translation keys
agent: build
---

Search for hardcoded display strings in source files:
!`grep -rn "title:\|label:\|placeholder:\|buttonText:\|text:\|heading:\|message:" --include="*.tsx" --include="*.ts" . | grep -v node_modules | grep -v "i18n\|translate\|t(" | head -80`

Also find string literals in JSX:
!`grep -rn ">[A-Z][a-z]" --include="*.tsx" . | grep -v node_modules | head -40`

Report all hardcoded user-facing strings that should be i18n translation keys.
Group by file. For each, suggest the translation key name.
