---
description: Scan for TODO/FIXME/HACK/deprecated across the repo
---

TODOs: !`grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.ts" --include="*.tsx" --include="*.js" . | grep -v node_modules | head -80`

Cluster these by severity (security > correctness > performance > style)
and by file. Flag anything that looks like a bug waiting to happen, not
just a missing feature.
