#!/usr/bin/env python3
"""
Push media-library skill to Allie via Notion pages.

Creates a transfer page under ANTIGRAVITY with child pages for each skill file,
then sends a relay message with activation instructions.

Usage:
    python3 scripts/push_media_library.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, ".notion_config.json")
NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

SKILLS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), ".agents", "skills")

SKILLS = ["media-library"]


def load_config():
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    env_key = os.environ.get("NOTION_API_KEY")
    if env_key:
        config["api_key"] = env_key
    return config


def notion_request(method, endpoint, api_key, body=None):
    url = f"{BASE_URL}/{endpoint}"
    cmd = [
        "curl", "-s", "-X", method, url,
        "-H", f"Authorization: Bearer {api_key}",
        "-H", f"Notion-Version: {NOTION_VERSION}",
        "-H", "Content-Type: application/json",
    ]
    if body:
        cmd += ["-d", json.dumps(body)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Invalid response: {result.stdout[:500]}")
        sys.exit(1)
    if "status" in data and data["status"] >= 400:
        print(f"Notion API error {data['status']}: {data.get('message', data)}")
        return None
    return data


def text_to_blocks(content, max_len=1900):
    blocks = []
    lines = content.split("\n")
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_len and current_chunk:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": current_chunk}}]
                }
            })
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
    if current_chunk.strip():
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": current_chunk}}]
            }
        })
    return blocks


def create_page_with_content(api_key, parent_id, title, content, is_database=False):
    blocks = text_to_blocks(content)
    initial_blocks = blocks[:100]
    remaining_blocks = blocks[100:]
    parent_key = "database_id" if is_database else "page_id"
    body = {
        "parent": {parent_key: parent_id},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": initial_blocks
    }
    result = notion_request("POST", "pages", api_key, body)
    if not result:
        print(f"  ❌ Failed to create page: {title}")
        return None
    page_id = result["id"]
    for i in range(0, len(remaining_blocks), 100):
        batch = remaining_blocks[i:i+100]
        notion_request("PATCH", f"blocks/{page_id}/children", api_key, {"children": batch})
    return page_id


def send_relay_message(api_key, db_id, message, context=None):
    properties = {
        "Message": {"title": [{"text": {"content": message}}]},
        "Source": {"select": {"name": "Antigravity"}},
        "Status": {"select": {"name": "New"}},
        "Timestamp": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
        "Category": {"multi_select": [{"name": "Task"}]},
    }
    if context:
        properties["Context"] = {"rich_text": [{"text": {"content": context[:2000]}}]}
    return notion_request("POST", "pages", api_key, {
        "parent": {"database_id": db_id},
        "properties": properties,
    })


def main():
    config = load_config()
    api_key = config["api_key"]
    parent_page_id = config["page_id"]
    inbound_db = config["databases"]["inbound_relay"]

    print("📦 Pushing media-library skill to Notion for Allie...\n")

    transfer_page = create_page_with_content(
        api_key, parent_page_id,
        f"📦 Media Library Skill Transfer — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "New media-library skill for home-bot.\n\n"
        "Provides search, browse, and content retrieval across Mac Mini services:\n"
        "- 📚 Calibre-Web (books)\n"
        "- 🎮 RomM (ROMs/games)\n"
        "- 🎬 Jellyfin (movies/TV/music)\n"
        "- 📄 Paperless-ngx (documents)\n\n"
        "Each child page title is the destination file path on the VM.\n"
        "Install under ~/.hermes/skills/smart-home/ or the home-bot profile.\n\n"
        "ALSO INCLUDED: 5 importable n8n workflow JSON files in resources/n8n_workflows/.\n"
        "These need to be imported into n8n on the Mac Mini.\n"
    )

    if not transfer_page:
        print("❌ Failed to create transfer page. Aborting.")
        sys.exit(1)

    print(f"✅ Transfer page created: {transfer_page}\n")

    file_count = 0
    for skill_name in SKILLS:
        skill_dir = os.path.join(SKILLS_DIR, skill_name)
        if not os.path.exists(skill_dir):
            print(f"  ⚠️  Skill directory not found: {skill_dir}")
            continue

        for root, dirs, files in os.walk(skill_dir):
            for filename in sorted(files):
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, os.path.join(SKILLS_DIR, ".."))
                vm_path = f".agents/{rel_path}"

                with open(filepath, "r") as f:
                    try:
                        content = f.read()
                    except UnicodeDecodeError:
                        print(f"  ⚠️  Skipping binary file: {filepath}")
                        continue

                print(f"  📄 {vm_path} ({len(content)} chars)...", end=" ")
                page_id = create_page_with_content(api_key, transfer_page, vm_path, content)
                if page_id:
                    print("✅")
                    file_count += 1
                else:
                    print("❌")

    print(f"\n📊 Pushed {file_count} files for media-library skill.\n")

    relay_msg = (
        f"New skill transfer ready: media-library ({file_count} files). "
        "Check '📦 Media Library Skill Transfer' page under ANTIGRAVITY. "
        "Each child page title is the destination file path. "
        "Install for home-bot and follow the Setup (One-Time) section in SKILL.md."
    )

    context = (
        "MEDIA LIBRARY SKILL — Install for home-bot\n\n"
        "SETUP STEPS:\n"
        "1. Read SKILL.md and all resource files from the transfer page\n"
        "2. Save files to ~/.hermes/skills/smart-home/media-library/ (or appropriate location)\n"
        "3. Create Notion MEDIA page (top-level, sibling to FINANCE) with 4 child DBs:\n"
        "   - 📚 Books, 🎮 Games, 🎬 Video & Music, 📄 Documents\n"
        "   - Schema for each DB is in SKILL.md Section 2\n"
        "4. Update resources/notion_db_ids.json with the actual DB IDs\n"
        "5. The 5 n8n workflow JSONs need to be imported on the Mac Mini\n"
        "   - Jon will handle n8n import + API key setup\n"
        "6. Register crons ML1 + ML2 under home-bot profile\n"
        "7. Add media-library to home-bot's skill list\n\n"
        "NEEDS FROM JON:\n"
        "- Jellyfin API key → n8n env JELLYFIN_API_KEY\n"
        "- Paperless-ngx API token → n8n env PAPERLESS_TOKEN\n"
        "- n8n workflow import on Mac Mini\n"
        "- Confirm Calibre-Web + RomM localhost auth requirements"
    )

    result = send_relay_message(api_key, inbound_db, relay_msg, context)
    if result:
        print("✅ Relay message sent to Allie.")
    else:
        print("❌ Failed to send relay message.")

    print("\n🎉 Done! Allie should pick up the transfer on her next relay check.")


if __name__ == "__main__":
    main()
