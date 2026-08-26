---
description: Review a file for SQL/XSS/command-injection risk
---

File: @$ARGUMENTS

Analyze this file for injection vulnerabilities:
1. SQL injection — string concatenation in queries vs parameterized
2. XSS — innerHTML, dangerouslySetInnerHTML, unsanitized user input
3. Command injection — exec/spawn with unsanitized arguments
4. Path traversal — user-controlled file paths without normalization

Rate risk: LOW / MEDIUM / HIGH / CRITICAL and suggest fixes.
