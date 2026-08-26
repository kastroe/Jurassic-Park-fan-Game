---
description: Audit licenses before redistribution
---

Root license: @LICENSE
Dependency licenses: !`npx license-checker --summary 2>/dev/null || pip-licenses 2>/dev/null || echo "No license checker found"`

List any copyleft (GPL/AGPL) or unusual licenses that could conflict with
closed-source or commercial redistribution. Flag files with existing copyright
headers that must be preserved.
