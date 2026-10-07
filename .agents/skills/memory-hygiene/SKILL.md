---
name: memory-hygiene
description: >
  Automated working memory assessment and cleanup for Hermes Agent. Classifies
  memory entries as keep/stale/duplicate/artifact-leak using pattern rules,
  generates a consolidation report with proposed replacement text, and writes
  the cleaned memory after approval. Runs weekly via cron or on-demand.
  Prevents the memory bloat that occurs when context compaction summaries,
  resolved troubleshooting, and task completion logs accumulate as permanent
  memory entries.
requires:
  bins: [python3]
  env: [NOTION_API_KEY]
---

# Memory Hygiene (memory-hygiene)

## Overview

Working memory has a hard limit: **2,200 chars** (memory store) + **1,375 chars** (user profile). When entries accumulate past this, Hermes truncates or silently drops context, degrading all downstream behavior.

This skill prevents memory bloat by:
1. Classifying each `§`-separated entry using deterministic pattern rules
2. Generating a consolidation report with keep/drop decisions
3. Writing the cleaned memory **only after approval**

### Architecture

```ascii
  ┌────────────────────────────────────────────────────┐
  │              MEMORY HYGIENE PIPELINE                │
  │                                                     │
  │  SCAN           CLASSIFY          CONSOLIDATE       │
  │  ┌─────────┐   ┌──────────────┐   ┌─────────────┐  │
  │  │ Read raw │   │ Pattern-match│   │ Merge keeps  │  │
  │  │ MEMORY.md│──▶│ each entry   │──▶│ Dedup facts  │  │
  │  │ Split §  │   │ (8 rules)    │   │ Check budget │  │
  │  └─────────┘   └──────────────┘   └─────────────┘  │
  │                                          │          │
  │  REPORT          WRITE                   │          │
  │  ┌─────────┐   ┌──────────────┐          │          │
  │  │ Telegram │   │ Backup old   │          │          │
  │  │ summary  │◀──│ Write new    │◀─────────┘          │
  │  │ Ask Y/N  │   │ Verify size  │                     │
  │  └─────────┘   └──────────────┘                     │
  └────────────────────────────────────────────────────┘
```

### Key Principle

**Never self-modify memory without a classification framework.** The prior failure mode was Allie trying to "review and consolidate" open-endedly, which caused a feedback loop of test writes, backups, and retries. This skill replaces open-ended judgment with deterministic pattern rules.

---

## Setup (One-Time)

### 1. Create the script directory

```bash
mkdir -p ~/.hermes/skills/memory-hygiene/
```

### 2. Deploy the classification script

Copy `resources/memory_classifier.py` to `~/.hermes/skills/memory-hygiene/memory_classifier.py`

### 3. Register the cron

Add one cron to `~/.hermes/config.yaml` under the default (orchestrator) profile:

| Cron ID | Name | Schedule | Model |
|---------|------|----------|-------|
| `MH1` | Weekly Memory Hygiene | `0 6 * * 0` (Sun 6:00 AM CT) | gemini-local |

### 4. Test

```bash
python3 ~/.hermes/skills/memory-hygiene/memory_classifier.py --dry-run
```

---

## Module A: Memory Classifier

**Purpose**: Read MEMORY.md, split on `§` separator, classify each entry, generate a report.

### Classification Rules (in priority order)

Every entry is tested against these 8 rules. First match wins.

| # | Rule | Pattern | Action |
|---|------|---------|--------|
| 1 | **Compaction artifact** | Starts with `[USER CORRECTION] [PRIOR CONTEXT` or contains `CONTEXT COMPACTION — REFERENCE ONLY` or `COMPACTION SUMMARY BELOW` | **DROP** — Context window handoff leaked into memory |
| 2 | **Async delegation noise** | Starts with `[ASYNC DELEGATION BATCH COMPLETE` | **DROP** — Transient subagent result, not memory |
| 3 | **Background process log** | Starts with `[IMPORTANT: Background process` | **DROP** — Process output, not durable knowledge |
| 4 | **Stale correction (resolved)** | Starts with `[USER CORRECTION]` AND contains resolution markers: `✅ Fixed`, `✅ Complete`, `successfully`, `has been updated`, `is now fully operational`, `Fix Complete` | **EXTRACT** — Pull only the root cause lesson (1 line), drop the rest |
| 5 | **Task completion log** | Contains `## What Was Fixed`, `## What Changed`, `## 📊 Current Status`, `successfully implemented`, `all requested`, `Task Completed Successfully` | **DROP** — One-time task result, not persistent knowledge |
| 6 | **Point-in-time snapshot** | Contains `## 📡 SYSTEM HEALTH CHECK`, `Monthly Media Library Health`, `Transaction Sync`, `Daily System Health Check`, `Health Check Summary` | **DROP** — Ephemeral data, belongs in Notion not memory |
| 7 | **Duplicate** | Entry shares >70% content with another KEEP entry (Jaccard similarity on word tokens) | **DROP** — Keep the shorter/newer version |
| 8 | **Instruction/guidance** | Contains `Here's how to`, `You can search for`, `You're right to`, `Suggested Ideas`, `potential improvements`, `Here are some` | **DROP** — Advice given during a session, not durable state |

**Everything that passes all 8 rules** → **KEEP**

### Extract Rule (Rule 4) — How to distill

When an entry matches Rule 4 (resolved `[USER CORRECTION]`), extract ONLY:
- The **root cause** (one sentence)
- The **fix applied** (one sentence)
- Any **recurring lesson** (e.g., "tokens expire every 7 days")

Format: `- [topic]: [root cause] → [fix]. [lesson if any]`

Example:
```
BEFORE (450 chars):
[USER CORRECTION] Here's my analysis: Root cause: Robinhood OAuth tokens have
a 7-day lifetime. When the token expires, the Hermes MCP client tries to
auto-refresh using the stored refresh token, but the refresh flow fails in
this headless environment...  What I've done: 1. ✅ Fixed the current token...

AFTER (95 chars):
- Robinhood OAuth: tokens expire every 7 days. Headless env can't auto-refresh — manual re-auth required
```

### Character Budget Check

After classification:
1. Sum the character count of all KEEP entries + EXTRACT distillations
2. If total > 2,000 chars: flag entries for further compression (shortest diff wins)
3. If total > 2,200 chars: **require manual review** — do not auto-write
4. Target: **≤1,800 chars** to leave headroom for new entries

### Output Format

The classifier produces a structured report:

```
## Memory Hygiene Report — YYYY-MM-DD

### Stats
- Entries scanned: N
- KEEP: N (X chars)
- DROP: N (X chars freed)
- EXTRACT: N (X chars → Y chars)
- Budget: Y/2200 chars (Z% used)

### Dropped Entries (with reasons)
1. [Rule 1: Compaction artifact] "Context compaction — reference only..."
2. [Rule 5: Task completion] "✅ ML2 Monthly Library Health Pipeline Fix..."
3. [Rule 7: Duplicate] "Robinhood MCP fix..." (dup of entry #4)

### Proposed Replacement
---
[clean memory content here]
---

### Action Required
☐ Approve write  ☐ Edit first  ☐ Skip this week
```

---

## Module B: Memory Writer

**Purpose**: After approval, backup the current MEMORY.md and write the cleaned version.

### Algorithm

```python
def write_clean_memory(proposed_content: str):
    """Write cleaned memory after approval. Always backup first."""
    
    import shutil
    from datetime import datetime
    
    memory_path = os.path.expanduser("~/.hermes/memories/MEMORY.md")
    backup_dir = os.path.expanduser("~/.hermes/memories/backups/")
    os.makedirs(backup_dir, exist_ok=True)
    
    # 1. Backup current
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{backup_dir}/MEMORY_{timestamp}.md"
    shutil.copy2(memory_path, backup_path)
    
    # 2. Verify proposed content is within budget
    if len(proposed_content) > 2200:
        raise ValueError(f"Proposed content is {len(proposed_content)} chars — exceeds 2200 limit")
    
    # 3. Write
    with open(memory_path, 'w') as f:
        f.write(proposed_content)
    
    # 4. Verify
    with open(memory_path, 'r') as f:
        written = f.read()
    
    assert written == proposed_content, "Write verification failed"
    
    # 5. Prune old backups (keep last 8)
    backups = sorted(os.listdir(backup_dir))
    while len(backups) > 8:
        os.remove(os.path.join(backup_dir, backups.pop(0)))
    
    return {
        "backup": backup_path,
        "new_size": len(proposed_content),
        "budget_pct": round(len(proposed_content) / 2200 * 100, 1)
    }
```

### Approval Gate

**MANDATORY**: Before calling `write_clean_memory()`, send the proposed replacement to Jon via Telegram with inline buttons:

```
📋 *Memory Hygiene Report*
Scanned: {N} entries
Dropping: {N} ({chars} chars freed)
Keeping: {N} ({chars} chars)
Budget: {pct}% used

*Proposed replacement:*
```{proposed_content}```

Reply "approve" to write, "skip" to cancel.
```

If no response within 30 minutes, **skip** — never auto-write.

---

## Module C: Memory Guard (Inline Protection)

**Purpose**: Prevent future bloat by intercepting bad writes at the source. These rules should be internalized by the orchestrator.

### Write Prevention Rules

Before writing ANY new memory entry, check:

1. **Is this a context compaction artifact?** → REJECT
   - Pattern: starts with `[PRIOR CONTEXT`, `[CONTEXT COMPACTION`, `[END OF PRIOR CONTEXT`
   
2. **Is this a task completion notification?** → REJECT
   - Pattern: starts with `✅`, contains `successfully`, `has been`, `All requested`
   - Instead: if there's a durable lesson, write ONLY the lesson
   
3. **Is this a point-in-time snapshot?** → REJECT
   - Pattern: contains tables with `|` formatting, health check data, transaction lists
   - Instead: write to Notion or cron_outputs/

4. **Is this a duplicate?** → REJECT
   - Before writing, grep existing memory for key phrases from the new entry
   - If >50% phrase overlap with existing entry, don't write

5. **Does this exceed the headroom budget?** → COMPRESS or REJECT
   - Check current memory size first
   - If adding this entry would push past 1,800 chars, compress it to one line
   - If still won't fit, skip the write

### What SHOULD be in memory

| Category | Example | Max chars |
|----------|---------|-----------|
| Infrastructure state | "Robinhood OAuth: 7-day expiry, manual re-auth" | 500 |
| Active pipeline config | "ML2 cron 7b534a60e9e3, Sync Status DB 3ec63..." | 500 |
| Key DB IDs not in skill configs | "INVENT: ff597..." | 300 |
| Resolved-issue lessons | "SSH tunnel: use ubuntu@ not root@" | 200 |
| Bot roster changes | "web-bot: portfolio-manager + impeccable" | 200 |
| **Total target** | | **≤1,800** |

### What should NEVER be in memory

- Full task completion reports
- System health check snapshots
- Transaction sync results
- Context compaction summaries
- Notion database creation confirmations
- Research results (moissanite rings, etc.)
- Multi-paragraph troubleshooting narratives
- Anything with `##` headers and tables — that's a report, not a memory

---

## Cron Automations

| ID | Name | Schedule | Model | Action |
|----|------|----------|-------|--------|
| MH1 | Weekly Memory Hygiene | `0 6 * * 0` (Sun 6 AM CT) | gemini-local | Run classifier, generate report, send to Jon via Telegram, await approval before writing |

### MH1 Cron Message

```
Execute the memory-hygiene skill:
1. Read ~/.hermes/memories/MEMORY.md
2. Split entries on § separator
3. Classify each entry using the 8 rules in Module A
4. Generate the Memory Hygiene Report
5. Send the report and proposed replacement to Jon via Telegram
6. If Jon approves, backup and write. If no response in 30 min, skip.
Write the report to ~/.hermes/cron_outputs/memory_hygiene_latest.json
```

---

## Resource Files

| File | Purpose |
|------|---------|
| `SKILL.md` | This file — classification rules and workflow |
| `resources/memory_classifier.py` | Standalone classifier script (--dry-run mode) |

---

## Integration

### Reads (no ownership)
- `~/.hermes/memories/MEMORY.md` — current working memory
- `~/.hermes/memories/USER_PROFILE.md` — current user profile (if exists)

### Writes (owned)
- `~/.hermes/memories/MEMORY.md` — cleaned replacement (after approval)
- `~/.hermes/memories/backups/MEMORY_*.md` — timestamped backups
- `~/.hermes/cron_outputs/memory_hygiene_latest.json` — latest report

### Depends on
- **system-health**: Module D (Memory & Storage Audit) checks file size. This skill handles content quality.
- **Telegram**: Approval gate for writes
