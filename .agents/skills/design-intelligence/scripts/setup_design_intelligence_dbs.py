#!/usr/bin/env python3
"""
setup_design_intelligence_dbs.py — Creates all properties for the Trend Registry
and Design Briefs Notion databases, then seeds the Trend Registry with initial data.

Usage:
  python3 setup_design_intelligence_dbs.py \
    --trend-db <TREND_REGISTRY_DB_ID> \
    --briefs-db <DESIGN_BRIEFS_DB_ID> \
    --notion-key <NOTION_API_KEY>

Or set NOTION_API_KEY as an environment variable.
"""

import argparse
import json
import os
import sys
import time

import requests

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def notion_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def update_database(api_key: str, db_id: str, properties: dict, title: str = None) -> dict:
    """PATCH /databases/{db_id} to add/update properties."""
    body = {"properties": properties}
    if title:
        body["title"] = [{"type": "text", "text": {"content": title}}]
    resp = requests.patch(
        f"{NOTION_API}/databases/{db_id}",
        headers=notion_headers(api_key),
        json=body,
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  ❌ Error updating database: {resp.status_code}")
        print(f"     {resp.text[:500]}")
        sys.exit(1)
    return resp.json()


def create_page(api_key: str, db_id: str, properties: dict) -> dict:
    """POST /pages to create a row in a database."""
    body = {"parent": {"database_id": db_id}, "properties": properties}
    resp = requests.post(
        f"{NOTION_API}/pages",
        headers=notion_headers(api_key),
        json=body,
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        print(f"  ⚠️  Error creating page: {resp.status_code} — {resp.text[:300]}")
        return {}
    return resp.json()


# ─── Property builders for database schema ───

def select_prop(options: list) -> dict:
    return {"select": {"options": [{"name": o} for o in options]}}

def multi_select_prop(options: list) -> dict:
    return {"multi_select": {"options": [{"name": o} for o in options]}}

def number_prop(fmt: str = "number") -> dict:
    return {"number": {"format": fmt}}

def date_prop() -> dict:
    return {"date": {}}

def rich_text_prop() -> dict:
    return {"rich_text": {}}

def created_time_prop() -> dict:
    return {"created_time": {}}

def relation_prop(db_id: str) -> dict:
    return {"relation": {"database_id": db_id, "single_property": {}}}


# ─── Property builders for page content ───

def title_val(text: str) -> dict:
    return {"title": [{"type": "text", "text": {"content": str(text)[:2000]}}]}

def rich_text_val(text: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": str(text)[:2000]}}]}

def number_val(n) -> dict:
    return {"number": float(n) if n is not None else None}

def select_val(name: str) -> dict:
    return {"select": {"name": name}}

def multi_select_val(names: list) -> dict:
    return {"multi_select": [{"name": n} for n in names]}

def date_val(iso: str) -> dict:
    return {"date": {"start": iso}}


def setup_trend_registry(api_key: str, db_id: str):
    """Add all 14 properties to the Trend Registry database."""
    print("\n🎨 Setting up Trend Registry properties...")

    properties = {
        "Category": select_prop([
            "Aesthetic", "Color", "Typography", "Illustration", "Motif", "Layout"
        ]),
        "Status": select_prop([
            "🔥 Rising", "✅ Peak", "📉 Declining", "❄️ Dead"
        ]),
        "Momentum Score": number_prop("number"),
        "Discovered Date": date_prop(),
        "Peak Date": date_prop(),
        "Source": multi_select_prop([
            "Pinterest Predicts", "WGSN", "eRank", "Google Trends",
            "Etsy Trending", "Dribbble", "TikTok", "Manual"
        ]),
        "Platform Velocity": select_prop([
            "🚀 Accelerating", "➡️ Stable", "📉 Decelerating"
        ]),
        "Product Fit": multi_select_prop([
            "T-Shirts", "Mugs", "Wall Art", "Stickers", "Planners", "All"
        ]),
        "Color Palette": rich_text_prop(),
        "Typography": rich_text_prop(),
        "Description": rich_text_prop(),
        "Competitor Saturation": select_prop([
            "Low", "Medium", "High", "Oversaturated"
        ]),
        "Last Checked": date_prop(),
    }

    result = update_database(api_key, db_id, properties)
    prop_count = len(result.get("properties", {}))
    print(f"  ✅ Trend Registry: {prop_count} properties configured")
    return result


def setup_design_briefs(api_key: str, db_id: str, trend_db_id: str, product_ideas_db_id: str = None):
    """Add all 16 properties to the Design Briefs database."""
    print("\n📐 Setting up Design Briefs properties...")

    properties = {
        "Status": select_prop([
            "📝 Draft", "👀 Awaiting Approval", "✅ Approved",
            "🎨 In Production", "🚀 Listed", "❌ Rejected"
        ]),
        "Trend": relation_prop(trend_db_id),
        "Product Type": select_prop([
            "T-Shirt", "Mug", "Wall Art", "Sticker Pack",
            "Planner", "Canvas", "Enamel Mug"
        ]),
        "Target Niche": rich_text_prop(),
        "Aesthetic Direction": rich_text_prop(),
        "Color Palette": rich_text_prop(),
        "Typography Direction": rich_text_prop(),
        "Illustration Style": select_prop([
            "Linocut", "Risograph", "Retro Mascot", "Botanical Line",
            "Faux-Textile", "Matchbook", "Photo-Collage"
        ]),
        "Mockup Direction": rich_text_prop(),
        "Squint Test Notes": rich_text_prop(),
        "Estimated Price": number_prop("dollar"),
        "Differentiation Notes": rich_text_prop(),
        "Created": created_time_prop(),
        "Approved Date": date_prop(),
    }

    # Only add Product Idea Link if we have the DB ID
    if product_ideas_db_id:
        properties["Product Idea Link"] = relation_prop(product_ideas_db_id)

    result = update_database(api_key, db_id, properties)
    prop_count = len(result.get("properties", {}))
    print(f"  ✅ Design Briefs: {prop_count} properties configured")
    return result


def seed_trend_registry(api_key: str, db_id: str):
    """Seed the Trend Registry with initial 2026 trend data."""
    print("\n🌱 Seeding Trend Registry with 2026 trends...")

    # Load seed data
    seed_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "resources", "trend_seed_data.json"
    )
    # Try alternate path if running from workspace root
    if not os.path.exists(seed_path):
        seed_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "resources", "trend_seed_data.json"
        )
    if not os.path.exists(seed_path):
        # Look relative to the skill directory
        for candidate in [
            ".agents/skills/design-intelligence/resources/trend_seed_data.json",
            "resources/trend_seed_data.json",
        ]:
            if os.path.exists(candidate):
                seed_path = candidate
                break

    if not os.path.exists(seed_path):
        print(f"  ⚠️  Seed data not found. Skipping seeding.")
        print(f"     Looked for: trend_seed_data.json")
        return

    with open(seed_path, "r") as f:
        seed_data = json.load(f)

    today = time.strftime("%Y-%m-%d")
    created = 0

    for aesthetic in seed_data.get("aesthetics", []):
        properties = {
            "Name": title_val(aesthetic["name"]),
            "Category": select_val(aesthetic["category"]),
            "Status": select_val(aesthetic["status"]),
            "Momentum Score": number_val(aesthetic["momentum_score"]),
            "Discovered Date": date_val(today),
            "Source": multi_select_val(aesthetic["source"]),
            "Platform Velocity": select_val(aesthetic["platform_velocity"]),
            "Product Fit": multi_select_val(aesthetic["product_fit"]),
            "Color Palette": rich_text_val(aesthetic["color_palette"]),
            "Typography": rich_text_val(aesthetic["typography"]),
            "Description": rich_text_val(aesthetic["description"]),
            "Competitor Saturation": select_val(aesthetic["competitor_saturation"]),
            "Last Checked": date_val(today),
        }

        result = create_page(api_key, db_id, properties)
        if result:
            created += 1
            print(f"  ✅ Seeded: {aesthetic['name']} (score: {aesthetic['momentum_score']})")
        else:
            print(f"  ❌ Failed: {aesthetic['name']}")

        time.sleep(0.35)  # Notion rate limit: ~3 req/s

    # Also seed the color palettes as individual entries
    for color in seed_data.get("color_palettes", []):
        properties = {
            "Name": title_val(color["name"]),
            "Category": select_val("Color"),
            "Status": select_val("✅ Peak"),
            "Momentum Score": number_val(75),
            "Discovered Date": date_val(today),
            "Source": multi_select_val([color["source"].split("/")[0].strip()
                                        if "/" in color["source"]
                                        else "Manual"]),
            "Platform Velocity": select_val("➡️ Stable"),
            "Product Fit": multi_select_val(["All"]),
            "Color Palette": rich_text_val(color["hex"]),
            "Description": rich_text_val(f"{color['mood']}. Best for: {color['use']}"),
            "Competitor Saturation": select_val("Medium"),
            "Last Checked": date_val(today),
        }

        result = create_page(api_key, db_id, properties)
        if result:
            created += 1
            print(f"  ✅ Seeded color: {color['name']} ({color['hex']})")

        time.sleep(0.35)

    print(f"\n  🎉 Seeded {created} entries total")


def main():
    parser = argparse.ArgumentParser(description="Set up Design Intelligence Notion databases")
    parser.add_argument("--trend-db", required=True, help="Trend Registry database ID")
    parser.add_argument("--briefs-db", required=True, help="Design Briefs database ID")
    parser.add_argument("--product-ideas-db", default=None, help="Product Ideas database ID (optional)")
    parser.add_argument("--notion-key", default=None, help="Notion API key (or set NOTION_API_KEY env var)")
    parser.add_argument("--skip-seed", action="store_true", help="Skip seeding trend data")
    args = parser.parse_args()

    api_key = args.notion_key or os.environ.get("NOTION_API_KEY")
    if not api_key:
        print("❌ NOTION_API_KEY required. Pass via --notion-key or environment variable.")
        sys.exit(1)

    print("=" * 60)
    print("  Design Intelligence — Notion Database Setup")
    print("=" * 60)

    # Step 1: Set up Trend Registry properties
    setup_trend_registry(api_key, args.trend_db)

    # Step 2: Set up Design Briefs properties
    setup_design_briefs(api_key, args.briefs_db, args.trend_db, args.product_ideas_db)

    # Step 3: Seed trend data
    if not args.skip_seed:
        seed_trend_registry(api_key, args.trend_db)
    else:
        print("\n⏭️  Skipping seed data (--skip-seed)")

    print("\n" + "=" * 60)
    print("  ✅ Setup complete!")
    print("=" * 60)
    print(f"\n  Trend Registry DB: {args.trend_db}")
    print(f"  Design Briefs DB:  {args.briefs_db}")
    print("\n  Next: Tell Allie to pull latest and set these env vars:")
    print(f"    NOTION_DB_TREND_REGISTRY={args.trend_db}")
    print(f"    NOTION_DB_DESIGN_BRIEFS={args.briefs_db}")


if __name__ == "__main__":
    main()
