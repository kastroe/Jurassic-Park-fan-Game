---
description: Verify license compliance — copyright headers preserved
---

License file: @LICENSE
Copyright headers: !`grep -rn "copyright\|Copyright\|©" --include="*.{ts,tsx,js,md}" . | grep -v node_modules | head -60`
NOTICE file: !`cat NOTICE 2>/dev/null || cat NOTICE.md 2>/dev/null || echo "No NOTICE file found"`

Check compliance with the original license:
1. Is the license file preserved?
2. Are copyright headers intact in all source files that had them?
3. Does a NOTICE file exist if required?
4. Are there any files where copyright attribution was stripped?

This is a compliance check, not a compatibility check.
Report any missing or altered attribution.
