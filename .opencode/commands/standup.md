---
description: Summarize yesterday's work for standup
---

Commits since yesterday: !`git log --since=yesterday --oneline --author="$(git config user.name)"`

Summarize this into 3 bullets: what I did, what I'm doing today, any blockers
(infer blockers from WIP/TODO commits if present).
