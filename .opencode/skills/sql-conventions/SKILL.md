---
name: sql-conventions
description: SQL query style, indexing hygiene, and migration safety.
origin: Custom
---
SQL conventions: Use explicit column lists, not SELECT *. Prepend table aliases on all columns. Use CTEs over subqueries for readability. Index columns used in WHERE/JOIN/ORDER BY. Migration safety: add columns as nullable first, backfill, then add NOT NULL. Activate when writing or reviewing SQL queries or migrations.
