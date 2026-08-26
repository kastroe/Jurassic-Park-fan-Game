---
name: orm-conventions
description: ORM usage patterns for Prisma, SQLAlchemy, GORM, ActiveRecord, etc.
origin: Custom
---
ORM conventions: Use the ORM's migration system for schema changes. Prefer query builders over raw SQL unless performance demands it. Use relations/eager loading to avoid N+1. Keep model files focused, use service layers for complex queries. Activate when writing or reviewing ORM code.
