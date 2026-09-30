---
name: media-library
description: >
  Search, browse, and retrieve content from the Mac Mini media server. Covers books
  (Calibre-Web), ROMs (RomM), movies/TV/music (Plex), and documents (Paperless-ngx).
  Queries Notion catalog DBs for discovery, and n8n webhooks for on-demand content
  retrieval. Use when the user asks about books, games, movies, TV shows, music, or
  documents on the home server — 'what books do I have', 'find a game', 'summarize
  this book', 'what movies', 'find that document', 'library stats'.
requires:
  bins: [python3]
  env: [NOTION_API_KEY]
---

# Media Library

## 1. Overview

Unified media catalog and content retrieval skill for the Corral home server. All
media metadata lives in 4 Notion databases synced nightly from Mac Mini services via
n8n cron workflows. On-demand content (book text, document OCR, screenshots) flows
through an n8n webhook gateway.

```ascii
┌─────────────────────────────────────────────────────────────────────────┐
│                          MEDIA LIBRARY SKILL                           │
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────────┐  │
│  │ Module A:     │    │ Module B:     │    │ Module C:                 │  │
│  │ Catalog Search│    │ Book Reader   │    │ Collection Stats          │  │
│  │ (Notion API)  │    │ (n8n webhook) │    │ (Notion API)              │  │
│  └──────┬───────┘    └──────┬───────┘    └───────────┬───────────────┘  │
│         │                   │                         │                  │
│  ┌──────┴───────┐    ┌──────┴───────┐    ┌───────────┴───────────────┐  │
│  │ Module D:     │    │ Module E:     │    │ Crons:                    │  │
│  │ Recommend     │    │ Doc Lookup    │    │ ML1 Weekly Digest         │  │
│  │ (Notion API)  │    │ (n8n webhook) │    │ ML2 Monthly Health        │  │
│  └──────────────┘    └──────────────┘    └───────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
         │                   │                         │
         ▼                   ▼                         ▼
┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────────────┐
│   Notion DBs    │  │  n8n Gateway    │  │  Mac Mini Local Services     │
│ 📚 Books        │  │  POST /webhook/ │  │  Calibre-Web   :8083         │
│ 🎮 Games        │  │  media-gateway  │  │  RomM          :8082         │
│ 🎬 Video/Music  │  │  (clevercorral) │  │  Plex          :32400        │
│ 📄 Documents    │  │                 │  │  Paperless-ngx :8010         │
└─────────────────┘  └────────┬────────┘  └──────────────────────────────┘
                              │                         ▲
                              └─────────────────────────┘
                                   localhost API calls
```

### Dependency Chain
```
resources/notion_db_ids.json     ← All modules read DB IDs
resources/n8n_endpoints.json     ← Modules B, E read gateway URL
📚 Books DB (Notion)             ← Module A, C, D read; n8n sync writes
🎮 Games DB (Notion)             ← Module A, C, D read; n8n sync writes
🎬 Video & Music DB (Notion)     ← Module A, C, D read; n8n sync writes
📄 Documents DB (Notion)         ← Module A, E read; n8n sync writes
n8n Media Content Gateway        ← Module B, E call via webhook
```

### Parent Notion Pages
- **MEDIA page**: New top-level page (sibling to FINANCE, Health & Fitness, HOME)

---

## 2. Setup (One-Time)

### Step 1: Create Notion MEDIA Page & Databases

Create a **MEDIA** page in Notion as a top-level sibling to FINANCE.

#### 📚 Books Database

| Property | Type | Details |
|:---|:---|:---|
| Title | Title | Book title |
| Author | Rich Text | Author name(s) |
| Format | Multi-Select | `EPUB`, `PDF`, `MOBI`, `AZW3`, `CBZ`, `CBR` |
| Tags | Multi-Select | Calibre tags (genre, topic, etc.) |
| Series | Rich Text | Series name |
| Series Index | Number | Position in series |
| Publisher | Rich Text | Publisher name |
| Date Added | Date | When added to Calibre |
| Rating | Number | 0–5 scale |
| File Size MB | Number | Total file size |
| Has Cover | Checkbox | Cover image exists |
| Calibre ID | Number | Internal Calibre ID |
| File Path | Rich Text | Path on Mac Mini |
| Status | Select | `Unread`, `Reading`, `Read`, `Reference` |
| Jon's Notes | Rich Text | Manual notes |

#### 🎮 Games Database

| Property | Type | Details |
|:---|:---|:---|
| Title | Title | Game name |
| Platform | Select | `NES`, `SNES`, `N64`, `GBA`, `GBC`, `GB`, `Genesis`, `PS1`, `DS`, `PSP`, `Arcade`, `Other` |
| Genre | Multi-Select | Game genres |
| Region | Select | `USA`, `EUR`, `JPN`, `World` |
| File Name | Rich Text | ROM filename |
| File Size MB | Number | File size |
| Has Screenshot | Checkbox | Screenshot available |
| RomM ID | Number | Internal RomM ID |
| Status | Select | `Not Played`, `Playing`, `Completed`, `Shelved` |
| Rating | Number | 0–5 scale |
| Jon's Notes | Rich Text | Manual notes |

#### 🎬 Video & Music Database

| Property | Type | Details |
|:---|:---|:---|
| Title | Title | Movie/show/album name |
| Type | Select | `Movie`, `TV Show`, `Music Album` |
| Genre | Multi-Select | Genres |
| Year | Number | Release year |
| Studio | Rich Text | Studio or artist |
| Season/Episode | Rich Text | For TV: "S01E05" format |
| Duration Min | Number | Runtime in minutes |
| Quality | Select | `SD`, `720p`, `1080p`, `4K` |
| File Size MB | Number | File size |
| Plex ID | Rich Text | Internal Plex ID |
| Status | Select | `Unwatched`, `Watching`, `Watched` |
| Jon's Notes | Rich Text | Manual notes |

#### 📄 Documents Database

| Property | Type | Details |
|:---|:---|:---|
| Title | Title | Document title |
| Correspondent | Rich Text | Sender/source |
| Document Type | Select | Paperless document type |
| Tags | Multi-Select | Paperless tags |
| Date Created | Date | Document date |
| Date Added | Date | Ingestion date |
| ASN | Number | Archive serial number |
| Has OCR | Checkbox | OCR text available |
| Paperless ID | Number | Internal Paperless ID |
| File Path | Rich Text | Original filename |

### Step 2: Record Database IDs

After creating the databases, update `resources/notion_db_ids.json` with actual IDs.

### Step 3: Import n8n Workflows

Import the 5 workflow JSON files from `resources/n8n_workflows/` into n8n on the
Mac Mini. Configure required credentials:

| Credential | Where to Get |
|:---|:---|
| `NOTION_TOKEN` | Already configured in n8n env |
| `PLEX_TOKEN` | Plex → Settings → Account → Authorized Devices (or from browser URL) |
| `PAPERLESS_TOKEN` | Paperless → Settings → API Token |

### Step 4: Register Crons

Add 2 crons to `~/.hermes/config.yaml` under the `home-bot` profile:

| ID | Name | Schedule | Model |
|:---|:---|:---|:---|
| `ML1` | Weekly Library Digest | `0 9 * * 0` (Sun 9 AM CT) | gemini-local |
| `ML2` | Monthly Library Health | `0 10 1 * *` (1st of month 10 AM CT) | gemini-local |

### Step 5: Activate n8n Workflows

In n8n, activate the 4 catalog sync workflows and the content gateway webhook.

---

## 3. Modules

### Module A: Catalog Search

**Purpose**: Search and browse the media catalog across all 4 Notion databases.

**Data Sources**: 📚 Books, 🎮 Games, 🎬 Video & Music, 📄 Documents (Notion DBs)

**Algorithm**:
```python
def catalog_search(query, media_type=None, filters=None):
    """
    Search media catalog in Notion.
    
    Args:
        query: Search keyword(s)
        media_type: Optional filter — 'books', 'games', 'video', 'documents', or None for all
        filters: Optional dict of property filters (e.g., {'Platform': 'SNES', 'Status': 'Unread'})
    """
    db_ids = load_json("resources/notion_db_ids.json")
    
    targets = {
        "books": db_ids["books_db_id"],
        "games": db_ids["games_db_id"],
        "video": db_ids["video_db_id"],
        "documents": db_ids["documents_db_id"]
    }
    
    if media_type:
        targets = {media_type: targets[media_type]}
    
    results = []
    for name, db_id in targets.items():
        # Build Notion filter
        notion_filter = build_title_search_filter(query)
        if filters:
            notion_filter = combine_filters(notion_filter, property_filters(filters))
        
        # Query Notion
        pages = notion_query(db_id, filter=notion_filter, page_size=20)
        results.extend([
            {"source": name, "title": get_title(p), "properties": extract_props(p)}
            for p in pages
        ])
    
    # Sort by relevance (title match quality)
    results.sort(key=lambda r: fuzzy_score(r["title"], query), reverse=True)
    
    return results[:20]  # Top 20 results
```

**Output**: List of matching media items with source, title, and key properties.

**Routing**:
| Pattern | Behavior |
|:---|:---|
| "What books do I have by [author]?" | Search Books DB, filter by Author contains |
| "What SNES games do I have?" | Search Games DB, filter Platform = SNES |
| "Find [keyword] in my library" | Search all 4 DBs |
| "Show me unread books" | Query Books DB, filter Status = Unread |
| "What movies haven't I watched?" | Query Video DB, filter Status = Unwatched |

---

### Module B: Book Reader

**Purpose**: Retrieve book content from Calibre-Web for summarization and Q&A.

**Data Sources**: n8n Media Content Gateway → Calibre-Web

**Algorithm**:
```python
def read_book(calibre_id, format="epub", max_chars=50000):
    """
    Retrieve book text content via n8n webhook.
    
    Args:
        calibre_id: Calibre book ID (from Notion 📚 Books DB)
        format: Preferred format ('epub' recommended for text extraction)
        max_chars: Maximum characters to return (default 50K)
    """
    endpoints = load_json("resources/n8n_endpoints.json")
    gateway_url = endpoints["n8n_base_url"] + endpoints["webhooks"]["media_gateway"]
    
    response = http_post(gateway_url, json={
        "action": "get_book_content",
        "source": "calibre",
        "id": calibre_id,
        "format": format,
        "max_chars": max_chars
    })
    
    if response["status"] != "ok":
        return {"error": response.get("message", "Content retrieval failed")}
    
    return {
        "title": response["title"],
        "content": response["content"],
        "truncated": response.get("content_truncated", False),
        "total_chars": response.get("total_chars", len(response["content"]))
    }
```

**Output**: Book text content (plaintext extracted from epub), truncated to max_chars.

**Usage**:
1. User asks to summarize a book
2. Look up the book in Notion 📚 Books DB → get Calibre ID
3. Call `read_book(calibre_id)` to fetch content
4. Summarize the returned text using the LLM

---

### Module C: Collection Stats

**Purpose**: Report library sizes, recent additions, and consumption progress.

**Data Sources**: All 4 Notion DBs

**Algorithm**:
```python
def collection_stats():
    """Generate a comprehensive media library report."""
    db_ids = load_json("resources/notion_db_ids.json")
    
    stats = {}
    for name, db_id in [
        ("books", db_ids["books_db_id"]),
        ("games", db_ids["games_db_id"]),
        ("video", db_ids["video_db_id"]),
        ("documents", db_ids["documents_db_id"])
    ]:
        # Total count
        all_items = notion_query(db_id, page_size=1)
        stats[name] = {
            "total": all_items.get("total", 0)
        }
        
        # Status breakdown
        if name == "books":
            for status in ["Unread", "Reading", "Read", "Reference"]:
                count = notion_count(db_id, filter={"Status": status})
                stats[name][status.lower()] = count
        elif name == "games":
            for status in ["Not Played", "Playing", "Completed", "Shelved"]:
                count = notion_count(db_id, filter={"Status": status})
                stats[name][status.lower().replace(" ", "_")] = count
        elif name == "video":
            for status in ["Unwatched", "Watching", "Watched"]:
                count = notion_count(db_id, filter={"Status": status})
                stats[name][status.lower()] = count
        
        # Recent additions (last 7 days)
        recent = notion_query(db_id, filter={"Date Added": {"past_week": True}}, page_size=5)
        stats[name]["recent"] = [get_title(p) for p in recent.get("results", [])]
    
    return stats
```

**Output**: Structured stats object with totals, status breakdowns, and recent additions.

---

### Module D: Content Recommend

**Purpose**: Suggest media based on preferences, tags, and consumption history.

**Data Sources**: Notion DBs (Tags, Rating, Status fields)

**Algorithm**:
```python
def recommend(media_type, count=5):
    """
    Recommend unread/unwatched items based on tags from highly-rated consumed items.
    
    1. Find items with Rating >= 4 and Status = Read/Completed/Watched
    2. Extract their tags/genres
    3. Find unread/unwatched items with matching tags
    4. Sort by tag overlap count, return top N
    """
    db_ids = load_json("resources/notion_db_ids.json")
    db_id = db_ids[f"{media_type}_db_id"]
    
    # Get highly-rated consumed items
    consumed_status = {"books": "Read", "games": "Completed", "video": "Watched"}
    liked = notion_query(db_id, filter={
        "and": [
            {"Status": consumed_status[media_type]},
            {"Rating": {"gte": 4}}
        ]
    })
    
    # Extract tag frequencies
    tag_freq = Counter()
    for item in liked.get("results", []):
        tags = get_multi_select(item, "Tags" if media_type != "video" else "Genre")
        tag_freq.update(tags)
    
    if not tag_freq:
        # No rated items — return random unread
        unconsumed_status = {"books": "Unread", "games": "Not Played", "video": "Unwatched"}
        random_picks = notion_query(db_id, filter={"Status": unconsumed_status[media_type]}, page_size=count)
        return [{"title": get_title(p), "reason": "Random pick"} for p in random_picks.get("results", [])]
    
    # Find unconsumed items with matching tags
    top_tags = [tag for tag, _ in tag_freq.most_common(5)]
    unconsumed_status = {"books": "Unread", "games": "Not Played", "video": "Unwatched"}
    candidates = notion_query(db_id, filter={
        "and": [
            {"Status": unconsumed_status[media_type]},
            {"or": [{"Tags": {"contains": tag}} for tag in top_tags]}
        ]
    })
    
    # Score by tag overlap
    scored = []
    for item in candidates.get("results", []):
        item_tags = set(get_multi_select(item, "Tags" if media_type != "video" else "Genre"))
        overlap = len(item_tags & set(top_tags))
        scored.append({"title": get_title(item), "score": overlap, "matching_tags": list(item_tags & set(top_tags))})
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:count]
```

---

### Module E: Document Lookup

**Purpose**: Find and retrieve OCR'd document text from Paperless-ngx.

**Data Sources**: Notion 📄 Documents DB → n8n gateway → Paperless-ngx

**Algorithm**:
```python
def document_lookup(query=None, paperless_id=None, include_content=False):
    """
    Find documents by keyword or retrieve full OCR text by ID.
    """
    db_ids = load_json("resources/notion_db_ids.json")
    
    if paperless_id and include_content:
        # Retrieve full OCR text via n8n gateway
        endpoints = load_json("resources/n8n_endpoints.json")
        gateway_url = endpoints["n8n_base_url"] + endpoints["webhooks"]["media_gateway"]
        response = http_post(gateway_url, json={
            "action": "get_document_text",
            "source": "paperless",
            "id": paperless_id
        })
        return response
    
    # Search by keyword in Notion
    results = notion_query(db_ids["documents_db_id"], filter=build_title_search_filter(query))
    return [
        {
            "title": get_title(p),
            "correspondent": get_text(p, "Correspondent"),
            "type": get_select(p, "Document Type"),
            "tags": get_multi_select(p, "Tags"),
            "date": get_date(p, "Date Created"),
            "paperless_id": get_number(p, "Paperless ID")
        }
        for p in results.get("results", [])
    ]
```

---

## 4. Cron Automations

### Cron ML1: Weekly Library Digest
- **Schedule**: Sunday at 9:00 AM CT
- **Model**: gemini-local
- **Action**:
  1. Query all 4 Notion DBs for items added in the last 7 days
  2. Query status changes (Unread→Reading, Unwatched→Watching)
  3. Compile digest
- **Message Format** (Telegram):
  ```
  📚 **Weekly Media Library Digest**
  
  **New Additions:**
  📖 Books: 3 new (The Art of War, Clean Code, Dune Messiah)
  🎮 Games: 0 new
  🎬 Video: 2 new (Blade Runner 2049, Breaking Bad S5)
  📄 Docs: 5 new
  
  **Currently Active:**
  📖 Reading: Dune (72% through series)
  🎬 Watching: Breaking Bad S3E07
  🎮 Playing: Zelda: A Link to the Past
  
  **Library Totals:**
  📖 142 books (38 unread) | 🎮 287 games (241 not played)
  🎬 89 videos (23 unwatched) | 📄 156 documents
  ```

### Cron ML2: Monthly Library Health
- **Schedule**: 1st of each month at 10:00 AM CT
- **Model**: gemini-local
- **Action**:
  1. Report total items per category with month-over-month change
  2. Check n8n sync workflow status (last successful run)
  3. Flag any sync errors or stale data (items not synced in >48h)
  4. Report storage usage if available
- **Message Format** (Telegram):
  ```
  📊 **Monthly Media Library Health — September 2026**
  
  | Category | Total | Δ MoM | Sync Status |
  |----------|-------|-------|-------------|
  | 📖 Books | 142 | +8 | ✅ Last sync: 6h ago |
  | 🎮 Games | 287 | +0 | ✅ Last sync: 6h ago |
  | 🎬 Video | 89 | +5 | ✅ Last sync: 6h ago |
  | 📄 Docs  | 156 | +12 | ✅ Last sync: 6h ago |
  
  **Issues:** None
  **Storage:** ~/media = 847 GB used
  ```

---

## 5. Resource Files

| File | Description |
|:---|:---|
| `resources/notion_db_ids.json` | Notion database IDs for all 4 media catalogs |
| `resources/n8n_endpoints.json` | n8n webhook URL, local service endpoints, sync schedules |
| `resources/n8n_workflows/books_catalog_sync.json` | Importable n8n workflow — syncs Calibre → Notion |
| `resources/n8n_workflows/games_catalog_sync.json` | Importable n8n workflow — syncs RomM → Notion |
| `resources/n8n_workflows/video_music_catalog_sync.json` | Importable n8n workflow — syncs Plex → Notion |
| `resources/n8n_workflows/documents_catalog_sync.json` | Importable n8n workflow — syncs Paperless → Notion |
| `resources/n8n_workflows/media_content_gateway.json` | Importable n8n workflow — webhook for content retrieval |

---

## 6. Integration

### Read
- `resources/notion_db_ids.json` — DB IDs for all queries
- `resources/n8n_endpoints.json` — gateway URL, service configs
- 📚 Books DB — catalog search, stats, recommendations
- 🎮 Games DB — catalog search, stats, recommendations
- 🎬 Video & Music DB — catalog search, stats, recommendations
- 📄 Documents DB — catalog search, document lookup

### Write
- 📚 Books DB — status updates, notes, ratings (via Jon or skill)
- 🎮 Games DB — status updates, notes, ratings
- 🎬 Video & Music DB — status updates, notes
- 📄 Documents DB — (read-only; Paperless owns metadata)

### Cross-Skill
- **system-health**: n8n gateway health monitored by SH1 heartbeat (already configured)
- **home-hub**: Network inventory includes Mac Mini services
- **home-maintenance**: No direct dependency

### Cross-Bot
- **home-bot** owns this skill
- **orchestrator** can delegate media queries to home-bot
- No other bot dependencies

---

## 7. Routing

| Request Pattern | Module | Data Source |
|:---|:---|:---|
| "What books do I have by [author]?" | Catalog Search | Notion 📚 |
| "Summarize [book title]" | Book Reader | n8n → Calibre-Web |
| "What [platform] games do I have?" | Catalog Search | Notion 🎮 |
| "What movies haven't I watched?" | Catalog Search | Notion 🎬 (filter: Unwatched) |
| "How big is my media library?" | Collection Stats | All 4 Notion DBs |
| "Find the tax document from [date]" | Document Lookup | Notion 📄 |
| "Show me that [document] text" | Document Lookup | n8n → Paperless |
| "What have I been reading?" | Catalog Search | Notion 📚 (filter: Reading) |
| "Recommend a [book/game/movie]" | Recommend | Notion (Tags + Rating) |
| "Mark [title] as [status]" | Catalog Search (write) | Notion (update Status) |
| "Rate [title] [N]/5" | Catalog Search (write) | Notion (update Rating) |
| "What's new in my library?" | Collection Stats | All 4 DBs (recent additions) |

---

## 8. Data Collection Checklist

Information needed from Jon to fully operationalize this skill:

- [ ] Create Notion MEDIA page and 4 child databases (or confirm Allie should create them)
- [ ] Provide Notion database IDs after creation → update `notion_db_ids.json`
- [ ] Get Plex token (see instructions below) → add to n8n env as `PLEX_TOKEN`
- [ ] Generate Paperless-ngx API token (Settings → API Token) → add to n8n env as `PAPERLESS_TOKEN`
- [ ] Confirm Calibre-Web auth: does OPDS/download require auth on localhost? If so, add creds to n8n
- [ ] Confirm RomM API auth: does `/api/roms` require auth on localhost? If so, add creds to n8n
- [ ] Import 5 n8n workflow JSONs into n8n on Mac Mini
- [ ] Activate the 4 sync workflows + 1 gateway webhook in n8n
- [ ] Confirm the first sync run populates Notion correctly
