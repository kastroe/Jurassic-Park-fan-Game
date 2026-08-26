---
name: migration-and-refactor-patterns
description: Large-scale rename, restructure, and migration safety patterns.
origin: Custom
---
Migration/refactor patterns: Change one thing at a time. Keep old and new paths working during migration (strangler fig pattern). Use codemods for mechanical changes. Test before and after. Migrate in stages: deprecate → redirect → remove. Activate when planning or executing a large refactor.
