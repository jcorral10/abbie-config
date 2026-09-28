---
tags: [system, automation, spec]
created: 2026-09-28
updated: 2026-09-28
---

# 🌙 Nightly Sweep — Automation Spec

> Defines the logic Alfred (or Allie, in the personal fork) executes each night to process completed tasks, generate tomorrow's morning page, and keep the board clean.

---

## Architecture

Tasks are **individual notes** in `tasks/`. Each has a `status` property:

| Status | Meaning | Board Column |
|:-------|:--------|:-------------|
| `backlog` | Do eventually | 📋 Backlog |
| `today` | Do today | 🎯 Today |
| `waiting` | Blocked on someone | ⏳ Waiting On |
| `done` | Completed | ✔️ Recently Completed → archive |

Jon manages tasks by changing the `status` property. That's it. No annotations, no special syntax. Alfred handles everything else.

---

## Trigger

- **Nightly sweep**: `0 23 * * *` (11:00 PM CT, daily)
- **Morning refresh**: `0 6 * * *` (6:00 AM CT, daily)
- **Agent**: Alfred (work vault) / Allie (personal vault, future)

---

## Step 1: Process Completed Tasks (11 PM)

Scan `tasks/` for notes where `status = "done"`.

For each completed task note, Alfred reads the content and makes a judgment call:

### Auto-Classification Rules

| Signal | Action |
|:-------|:-------|
| Note body is empty or < 50 chars | **Delete** the file (trivial task — "Buy milk") |
| Note body has meaningful content, links, or attachments | **Archive** — move to `archive/tasks/YYYY-MM/` with completion date in frontmatter |
| Note title matches a common recurring pattern (e.g., "Pay electric bill") | **Archive + flag** — add `recurring: true` to frontmatter, suggest recurrence to Jon next morning |
| Note body contains reference material (receipts, ticket numbers, links) | **Archive** — always keep, add `reference: true` tag |

### Archive Process

1. Add `completed: YYYY-MM-DD` to frontmatter
2. Move file from `tasks/` → `archive/tasks/YYYY-MM/`
3. No other changes — the note stays intact with all its content

### Delete Process

1. Move to `.trash/` (Obsidian's soft delete) — recoverable for 7 days

---

## Step 2: Stale Task Detection (11 PM)

Scan `tasks/` for notes that have been in the same status for too long:

| Condition | Action |
|:----------|:-------|
| `status: today` for 3+ days | Add `⚠️` to the note title; bump `priority: high` |
| `status: today` for 7+ days | Send Telegram nudge: "Task open 7 days: [title]. Move to backlog or finish?" |
| `status: waiting` for 14+ days | Send Telegram nudge: "Still waiting on [waiting_on] for: [title]. Follow up?" |
| `status: backlog` for 30+ days | No action (backlog is intentionally long-term) |

Track age via `file.cday` (creation date) and `file.mday` (last modified).

---

## Step 3: Generate Tomorrow's Morning Page (11 PM)

1. Create `YYYY-MM-DD.md` from `Templates/Morning Page.md`
2. Replace template variables (date, navigation links)
3. **Auto-populate the schedule table**:
   - Query Google Calendar API for tomorrow's events (work hours 8–5 CT)
   - Format: `| 9:00 AM | Team standup |`
   - Weekends/holidays: `| — | No scheduled meetings |`
4. The Tasks section auto-populates via Dataview (no manual insertion needed)

---

## Step 4: Morning Refresh (6 AM)

1. Re-query Google Calendar for last-minute changes
2. Update the schedule table in today's morning page
3. **Do not** touch tasks — those are Jon's to manage

---

## Step 5: Weekly Rollup (Sunday 9 PM)

Append to `archive/tasks/index.md`:

```markdown
### Week of YYYY-MM-DD
- **Completed**: X tasks
- **Deleted**: Y | **Archived**: Z
- **Currently open**: A (today) + B (waiting) + C (backlog)
- **Stale alerts sent**: D
```

---

## Data Flow

```
┌─────────────────────────────────────────────┐
│              NIGHTLY SWEEP (11 PM)           │
│                                              │
│  tasks/ folder                               │
│  ├── status: done                            │
│  │   ├── empty body → 🗑️ .trash/            │
│  │   └── has content → 📦 archive/tasks/     │
│  ├── status: today (3+ days) → ⚠️ flag      │
│  └── status: waiting (14+ days) → 📱 nudge  │
│                                              │
│  Morning Page (YYYY-MM-DD.md)                │
│  ├── 📅 Schedule (Google Calendar)            │
│  └── ✅ Tasks (Dataview → tasks/ folder)     │
└─────────────────────────────────────────────┘
```

---

## Forking for Personal Use (Allie)

When adapting this for the personal vault on the new Mac Mini:

1. Replace `@alfred:` with `@allie:` globally
2. Add personal sections to the template:
   - 💰 Financial Snapshot (from Plaid sync)
   - 💪 Health & Fitness (from Hevy sync)
   - 🌤️ Weather (from weather API)
3. Add personal task types:
   - `@allie: pay [amount]` — trigger finance-bot to log payment
   - `@allie: buy [item]` — add to shopping list
   - `@allie: schedule [event]` — add to Google Calendar
4. Change calendar source from work Google Calendar to personal
5. Add journal/photo section for end-of-day personal reflections
6. Configure Syncthing sync instead of Google Drive

---

## Implementation Priority

| Phase | What | Agent | Status |
|:------|:-----|:------|:-------|
| 1 | Template created, manual use | Jon | ✅ Done |
| 2 | Alfred auto-generates tomorrow's page | Alfred | 🔲 Next |
| 3 | Alfred nightly sweep processes tasks | Alfred | 🔲 Queued |
| 4 | Stale task detection + nudges | Alfred | 🔲 Queued |
| 5 | Weekly rollup stats | Alfred | 🔲 Queued |
| 6 | Fork for personal vault (Allie) | Jon/Allie | 🔲 Future |
