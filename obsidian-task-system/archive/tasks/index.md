---
tags: [system, archive]
created: 2026-09-28
updated: 2026-09-28
---

# 📦 Task Archive

> Completed tasks that Alfred archived based on `@alfred:` instructions.
> Each entry preserves the original task text, completion date, source daily note, and any attached context.

---

## How This Works

When you check off a task in your Morning Page and it has an `@alfred: archive` instruction, Alfred moves it here with metadata. Tasks are grouped by month for easy browsing.

### Querying the Archive

Find all archived tasks with a specific tag:
```dataview
TASK
FROM "archive/tasks"
WHERE completed
SORT completion DESC
```

Find tasks completed this month:
```dataview
TASK
FROM "archive/tasks"
WHERE completed AND completion >= date(today) - dur(30 days)
SORT completion DESC
```

---

## Archive Log

<!-- Alfred appends completed tasks below, grouped by month -->

### September 2026

*No archived tasks yet — archive begins when the nightly sweep runs.*
