# Obsidian Task Management System

A Kanban-based task management system for Obsidian that combines the simplicity of Apple Reminders with the depth of Apple Notes. Each task is its own note — click to open, drag between columns, check to complete.

## What's Included

```
obsidian-task-system/
├── templates/
│   ├── Morning Page.md        # Daily note template with embedded board link
│   ├── Task.md                # Template for new task notes
│   ├── Add Task.md            # Templater trigger for quick-add
│   └── scripts/
│       └── addTask.js         # Templater user script — prompts for name & lane
├── wiki/
│   └── Nightly Sweep.md       # Automation spec for nightly task processing
├── archive/
│   └── tasks/
│       └── index.md           # Archive index for completed tasks
└── examples/
    ├── Tasks Board.md         # Starter Kanban board (4 lanes)
    └── daily-notes.json       # Obsidian daily notes plugin config
```

## Required Plugins

- **Dataview** — query engine (optional, used in archive)
- **Templater** — user scripts for quick-add (`Enable User Scripts: true`, folder: `Templates/scripts`)
- **Kanban** (`obsidian-kanban`) — drag-and-drop board

## Setup

1. Copy `templates/` contents into your vault's `Templates/` folder
2. Copy `examples/Tasks Board.md` to your vault root
3. Copy `archive/` and `wiki/` to your vault root
4. Create a `tasks/` folder in your vault root
5. Update `.obsidian/daily-notes.json` with the values from `examples/daily-notes.json`
6. Enable the Kanban plugin
7. In Templater settings: set `User Script Folder` to `Templates/scripts` and enable user scripts
8. Restart Obsidian

## Usage

- **Add a task**: `Cmd+P` → "Templater: Insert Templates/Add Task" (or assign a hotkey)
- **Move a task**: Drag the card between lanes on the board
- **Complete a task**: Check the box or drag to Done
- **Add details**: Click the task name → opens the full note
- **Daily workflow**: Open today's daily note → click "Open Tasks Board" callout

## Board Lanes

| Lane | Purpose |
|:-----|:--------|
| 🎯 Today | What you're doing now |
| ⏳ Waiting On | Blocked on someone else |
| 📋 Backlog | Everything else |
| ✔️ Done | Completed (cleaned up nightly) |

## Nightly Sweep (Automation)

The `wiki/Nightly Sweep.md` spec defines an agent-driven nightly cleanup:
- Checked-off tasks with content → archived to `archive/tasks/YYYY-MM/`
- Checked-off tasks with no content → soft deleted
- Stale tasks (3+ days in Today) → flagged
- Tomorrow's morning page → auto-generated

Designed for use with an AI agent (Alfred, Allie, etc.) but can be adapted to any automation tool.

## Forking for Personal Use

This system was built for a work vault. To adapt for personal use:
- Add financial/health/weather sections to `Morning Page.md`
- Swap agent references (`@alfred:` → `@allie:`)
- Change sync method (Google Drive → Syncthing/iCloud)
