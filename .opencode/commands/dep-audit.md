---
description: Audit dependencies for risk before adding one
---

package.json: @package.json
Outdated: !`npm outdated`
Audit: !`npm audit --json`

Summarize security/maintenance risk. If $ARGUMENTS names a new package, research
whether it's well-maintained and if there are better alternatives.
