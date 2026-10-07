#!/usr/bin/env python3
"""
Memory Classifier for Hermes Agent
Reads MEMORY.md, classifies entries, generates consolidation report.
Usage: python3 memory_classifier.py [--dry-run] [--memory-path PATH]
"""

import os
import re
import sys
import json
from datetime import datetime
from collections import Counter

DEFAULT_MEMORY_PATH = os.path.expanduser("~/.hermes/memories/MEMORY.md")
CHAR_BUDGET = 2200
CHAR_TARGET = 1800
SEPARATOR = "§"


# === Classification Rules ===

def rule_1_compaction_artifact(entry: str) -> bool:
    """Context window handoff leaked into memory."""
    markers = [
        "[PRIOR CONTEXT",
        "CONTEXT COMPACTION — REFERENCE ONLY",
        "COMPACTION SUMMARY BELOW",
        "END OF PRIOR CONTEXT",
        "not a new message",
        "treat it as background reference, NOT as active instructions",
    ]
    return any(m in entry for m in markers)


def rule_2_async_delegation(entry: str) -> bool:
    """Transient subagent result."""
    return entry.strip().startswith("[ASYNC DELEGATION BATCH COMPLETE")


def rule_3_background_process(entry: str) -> bool:
    """Process output log."""
    return entry.strip().startswith("[IMPORTANT: Background process")


def rule_4_resolved_correction(entry: str) -> tuple:
    """
    Resolved [USER CORRECTION] — extract root cause lesson only.
    Returns (True, extracted_lesson) or (False, None).
    """
    if not entry.strip().startswith("[USER CORRECTION]"):
        return False, None

    resolution_markers = [
        "✅ Fixed", "✅ Complete", "✅ Updated", "✅ **",
        "successfully", "has been updated", "is now fully operational",
        "Fix Complete", "All requested", "Task Completed",
        "I've successfully", "have been created",
    ]
    if not any(m in entry for m in resolution_markers):
        return False, None

    # Extract root cause if present
    lesson = None
    root_cause_patterns = [
        r"Root cause[:\s]+(.+?)(?:\.|$)",
        r"root cause[:\s]+(.+?)(?:\.|$)",
        r"The problem[:\s]+(.+?)(?:\.|$)",
        r"was the root cause",
        r"tokens? (?:have|has) a (\d+-day) lifetime",
        r"(?:was|were) using (.+?) instead of (.+)",
    ]
    for pattern in root_cause_patterns:
        match = re.search(pattern, entry, re.IGNORECASE)
        if match:
            lesson = match.group(0).strip()
            break

    return True, lesson


def rule_5_task_completion(entry: str) -> bool:
    """One-time task result."""
    markers = [
        "## What Was Fixed", "## What Changed",
        "## 📊 Current Status", "## 📊 **Current Status",
        "successfully implemented", "all requested",
        "Task Completed Successfully",
        "## ✅ **Task Completed",
        "Here's what was accomplished",
        "All 6 files from the ANTIGRAVITY relay",
    ]
    return any(m in entry for m in markers)


def rule_6_snapshot(entry: str) -> bool:
    """Point-in-time data snapshot."""
    markers = [
        "## 📡 SYSTEM HEALTH CHECK",
        "Monthly Media Library Health",
        "Transaction Sync", "transaction sync",
        "Daily System Health Check",
        "Health Check Summary",
        "📋 Daily System Health",
        "Plaid daily sync complete",
        "new transactions",
    ]
    # Also detect table-heavy entries (3+ pipe-delimited rows)
    pipe_rows = len(re.findall(r"^\s*\|.+\|.+\|", entry, re.MULTILINE))
    if pipe_rows >= 3 and any(m in entry for m in ["Total", "Status", "Category"]):
        return True
    return any(m in entry for m in markers)


def rule_7_duplicate(entry: str, keep_entries: list) -> bool:
    """Duplicate of an existing KEEP entry (>70% Jaccard similarity)."""
    entry_words = set(re.findall(r"\w{4,}", entry.lower()))
    if len(entry_words) < 5:
        return False

    for kept in keep_entries:
        kept_words = set(re.findall(r"\w{4,}", kept.lower()))
        if len(kept_words) < 5:
            continue
        intersection = entry_words & kept_words
        union = entry_words | kept_words
        similarity = len(intersection) / len(union) if union else 0
        if similarity > 0.70:
            return True
    return False


def rule_8_guidance(entry: str) -> bool:
    """Advice/guidance given during a session, not durable state."""
    markers = [
        "Here's how to", "Here are some", "Here are a few",
        "You can search for", "You're right to",
        "Suggested Ideas", "potential improvements",
        "Potential candidates for", "I can see several areas",
        "Doing all of that would **not**",
        "Based on my analysis of the",
        "Excellent! You've successfully",
    ]
    return any(m in entry for m in markers)


# === Main Classifier ===

def classify_entries(memory_text: str) -> dict:
    """Split memory on § and classify each entry."""
    raw_entries = memory_text.split(SEPARATOR)
    entries = [e.strip() for e in raw_entries if e.strip()]

    results = {
        "entries": [],
        "keep": [],
        "drop": [],
        "extract": [],
        "stats": {},
    }

    keep_texts = []

    for i, entry in enumerate(entries):
        preview = entry[:80].replace("\n", " ") + ("..." if len(entry) > 80 else "")
        record = {"index": i, "preview": preview, "chars": len(entry)}

        # Apply rules in priority order
        if rule_1_compaction_artifact(entry):
            record["action"] = "DROP"
            record["rule"] = "Rule 1: Compaction artifact"
            results["drop"].append(record)

        elif rule_2_async_delegation(entry):
            record["action"] = "DROP"
            record["rule"] = "Rule 2: Async delegation noise"
            results["drop"].append(record)

        elif rule_3_background_process(entry):
            record["action"] = "DROP"
            record["rule"] = "Rule 3: Background process log"
            results["drop"].append(record)

        elif (match := rule_4_resolved_correction(entry))[0]:
            _, lesson = match
            record["action"] = "EXTRACT"
            record["rule"] = "Rule 4: Resolved correction"
            record["lesson"] = lesson
            record["original_chars"] = len(entry)
            record["extracted_chars"] = len(lesson) if lesson else 0
            results["extract"].append(record)
            if lesson:
                keep_texts.append(lesson)

        elif rule_5_task_completion(entry):
            record["action"] = "DROP"
            record["rule"] = "Rule 5: Task completion log"
            results["drop"].append(record)

        elif rule_6_snapshot(entry):
            record["action"] = "DROP"
            record["rule"] = "Rule 6: Point-in-time snapshot"
            results["drop"].append(record)

        elif rule_7_duplicate(entry, keep_texts):
            record["action"] = "DROP"
            record["rule"] = "Rule 7: Duplicate"
            results["drop"].append(record)

        elif rule_8_guidance(entry):
            record["action"] = "DROP"
            record["rule"] = "Rule 8: Guidance/advice"
            results["drop"].append(record)

        else:
            record["action"] = "KEEP"
            record["rule"] = "No rule matched — keeping"
            results["keep"].append(record)
            keep_texts.append(entry)

        results["entries"].append(record)

    # Build stats
    keep_chars = sum(r["chars"] for r in results["keep"])
    extract_chars = sum(r.get("extracted_chars", 0) for r in results["extract"])
    drop_chars = sum(r["chars"] for r in results["drop"])
    total_new = keep_chars + extract_chars

    results["stats"] = {
        "total_entries": len(entries),
        "keep_count": len(results["keep"]),
        "drop_count": len(results["drop"]),
        "extract_count": len(results["extract"]),
        "original_chars": len(memory_text),
        "keep_chars": keep_chars,
        "extract_chars": extract_chars,
        "drop_chars": drop_chars,
        "proposed_total_chars": total_new,
        "budget_pct": round(total_new / CHAR_BUDGET * 100, 1),
        "within_target": total_new <= CHAR_TARGET,
        "within_budget": total_new <= CHAR_BUDGET,
    }

    return results


def build_proposed_memory(results: dict, original_text: str) -> str:
    """Build the proposed cleaned memory from KEEP + EXTRACT entries."""
    raw_entries = original_text.split(SEPARATOR)
    entries = [e.strip() for e in raw_entries if e.strip()]

    pieces = []
    for record in results["entries"]:
        if record["action"] == "KEEP":
            pieces.append(entries[record["index"]])
        elif record["action"] == "EXTRACT" and record.get("lesson"):
            pieces.append(record["lesson"])

    return "\n\n§\n\n".join(pieces)


def format_report(results: dict, proposed: str) -> str:
    """Format human-readable report."""
    s = results["stats"]
    lines = [
        f"## Memory Hygiene Report — {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "### Stats",
        f"- Entries scanned: {s['total_entries']}",
        f"- KEEP: {s['keep_count']} ({s['keep_chars']} chars)",
        f"- DROP: {s['drop_count']} ({s['drop_chars']} chars freed)",
        f"- EXTRACT: {s['extract_count']} ({s['extract_chars']} chars distilled)",
        f"- Proposed total: {s['proposed_total_chars']}/{CHAR_BUDGET} chars ({s['budget_pct']}%)",
        f"- Within target (≤{CHAR_TARGET}): {'✅' if s['within_target'] else '⚠️ Over target'}",
        "",
        "### Dropped Entries",
    ]

    for r in results["drop"]:
        lines.append(f"  - [{r['rule']}] \"{r['preview']}\"")

    if results["extract"]:
        lines.append("")
        lines.append("### Extracted Lessons")
        for r in results["extract"]:
            lesson = r.get("lesson", "(no lesson extracted)")
            lines.append(f"  - {r['preview'][:40]}... → {lesson}")

    lines.append("")
    lines.append("### Proposed Replacement")
    lines.append("```")
    lines.append(proposed)
    lines.append("```")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Classify and clean Hermes MEMORY.md")
    parser.add_argument("--dry-run", action="store_true", help="Report only, don't write")
    parser.add_argument("--memory-path", default=DEFAULT_MEMORY_PATH, help="Path to MEMORY.md")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    args = parser.parse_args()

    if not os.path.exists(args.memory_path):
        print(f"ERROR: {args.memory_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(args.memory_path, "r") as f:
        memory_text = f.read()

    results = classify_entries(memory_text)
    proposed = build_proposed_memory(results, memory_text)

    if args.json:
        output = {
            "stats": results["stats"],
            "entries": results["entries"],
            "proposed": proposed,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(output, indent=2))
    else:
        report = format_report(results, proposed)
        print(report)

    if not args.dry_run:
        print("\n⚠️  --dry-run not set. To write, call write_clean_memory() after approval.")


if __name__ == "__main__":
    main()
