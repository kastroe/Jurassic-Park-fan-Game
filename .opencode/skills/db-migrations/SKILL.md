---
name: db-migrations
description: Database migration patterns, safety practices, and versioning conventions.
origin: Custom
---
DB migrations: Use timestamped migration files. Always add columns as nullable, backfill data, then add NOT NULL. Test rollbacks. One migration per logical change. Avoid long-running transactions. Activate when writing or reviewing database migrations.
