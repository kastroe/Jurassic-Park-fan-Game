---
description: Explain a file's role in the wider system
---

@$ARGUMENTS
Callers/importers: !`grep -rn "$ARGUMENTS" --include=*.ts -l .`

Explain what this file does, who depends on it, and what would break if it changed.
