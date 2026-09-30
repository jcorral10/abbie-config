---
name: appflowy-memory
description: >
  Self-hosted AppFlowy instance management on the Mac Mini server. Covers
  container health monitoring, admin operations, workspace/page CRUD via API,
  Notion-to-AppFlowy migration, backup/restore, and upgrade procedures.
  Use when the user mentions 'AppFlowy', 'notes server', 'self-hosted notes',
  'appflowy backup', 'appflowy upgrade', 'appflowy status', 'migrate from Notion',
  or any AppFlowy-related operations.
requires:
  bins: [curl]
  env: []
---

# AppFlowy Memory — Self-Hosted Instance Management

## 1. Overview

Self-hosted AppFlowy instance running on the Mac Mini home server as a local-first
replacement for Notion. Provides rich-text docs, tables/databases, Kanban boards,
calendars, file attachments, and full-text search — all stored on local disk.

### Architecture

```ascii
┌─────────────────────────────────────────────────────────────────┐
│                    Mac Mini (192.168.1.143)                      │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  nginx    │  │ gotrue   │  │  redis   │  │  appflowy_cloud  │ │
│  │  :8085    │  │  (auth)  │  │ (cache)  │  │  (core API)      │ │
│  └────┬─────┘  └──────────┘  └──────────┘  └──────────────────┘ │
│       │        ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│       │        │ postgres │  │  minio   │  │  worker          │ │
│       │        │ (pgvec)  │  │ (files)  │  │  (background)    │ │
│       │        └──────────┘  └──────────┘  └──────────────────┘ │
└───────┼─────────────────────────────────────────────────────────┘
        │
        ▼
  LAN: http://192.168.1.143:8085
  Admin Console: http://192.168.1.143:8085/console
```

### Key Details

| Item | Value |
|------|-------|
| **Public URL** | `https://appflowy.clevercorral.com` |
| **Admin Console** | `https://appflowy.clevercorral.com/console` |
| **LAN URL** | `https://192.168.1.143:8443` (self-signed cert) |
| **Admin Email** | `writecorral@gmail.com` |
| **Docker Compose dir** | `/home/jonc/appflowy` |
| **Data volumes** | Docker named volumes: `postgres_data`, `minio_data`, `keyword_index_data` |
| **Compose project** | `appflowy` (12 containers including cloudflared) |
| **Free tier** | 1 user seat + 3 guest editors |
| **Cloudflare Tunnel** | `AppFlowy` (`077292fe-4554-4905-85c7-4160134af2f2`) |
| **Domain** | `appflowy.clevercorral.com` (CNAME → tunnel) |
| **MinIO image** | `firstfinger/minio:latest` (Mac Mini Core 2 Duo lacks x86-64-v2) |
| **OAuth Integrations** | Google Drive ✅, Google Calendar ✅, GitHub ✅ |

---

## 2. Operations

> [!CAUTION]
> AppFlowy is ALREADY DEPLOYED and RUNNING on the Mac Mini as a 12-container Docker Compose stack
> at `/home/jonc/appflowy` (AppFlowy-SelfHost-Commercial repo). DO NOT attempt to deploy a
> desktop AppFlowy client (e.g., `pablocastellano/appflowy`, `appflowy/appflowy`). Those are
> GUI desktop apps, not servers. The server stack uses `appflowyinc/*` images orchestrated
> via `docker-compose.yml`. If containers are down, just run `docker compose up -d` in
> `/home/jonc/appflowy`.

### Health Check

```bash
# Quick: are all 12 containers up?
ssh mini "cd ~/appflowy && docker compose ps --format 'table {{.Name}}\t{{.Status}}'"

# API health (from Mac Mini)
ssh mini "curl -sf https://localhost:8443/gotrue/health"

# Public URL health (from anywhere)
curl -sf https://appflowy.clevercorral.com/gotrue/health

# Detailed: check specific service health
ssh mini "docker inspect --format='{{.State.Health.Status}}' appflowy-appflowy_cloud-1"

# Expected services (12): nginx, postgres, redis, gotrue, minio, appflowy_cloud,
#   appflowy_worker, appflowy_search, appflowy_web, admin_frontend, ai, cloudflared
```

### Start / Stop / Restart

```bash
# Start all services
ssh mini "cd ~/appflowy && docker compose up -d"

# Stop all services (data preserved in volumes)
ssh mini "cd ~/appflowy && docker compose down"

# Restart a specific service
ssh mini "cd ~/appflowy && docker compose restart appflowy_cloud"

# View logs
ssh mini "cd ~/appflowy && docker compose logs -f --tail 50 appflowy_cloud"
ssh mini "cd ~/appflowy && docker compose logs -f --tail 50 gotrue"
```

### Upgrade

```bash
# Pull latest images
ssh mini "cd ~/appflowy && docker compose pull"

# Recreate with new images (data preserved)
ssh mini "cd ~/appflowy && docker compose up -d --force-recreate"

# Check version after upgrade
ssh mini "cd ~/appflowy && docker compose logs appflowy_cloud 2>&1 | head -20"
```

### Backup

```bash
# Backup Postgres database
ssh mini "cd ~/appflowy && docker compose exec postgres pg_dumpall -U postgres | gzip > ~/backups/appflowy-pg-$(date +%F).sql.gz"

# Backup MinIO data (file attachments)
ssh mini "docker run --rm -v appflowy_minio_data:/data -v ~/backups:/backup alpine tar czf /backup/appflowy-minio-$(date +%F).tar.gz /data"

# Backup the .env and compose files
ssh mini "tar czf ~/backups/appflowy-config-$(date +%F).tar.gz -C /home/jonc/appflowy .env docker-compose.yml docker/"
```

### Restore

```bash
# Restore Postgres
ssh mini "cd ~/appflowy && docker compose down && gunzip -c ~/backups/appflowy-pg-YYYY-MM-DD.sql.gz | docker compose exec -T postgres psql -U postgres && docker compose up -d"

# Restore MinIO
ssh mini "docker run --rm -v appflowy_minio_data:/data -v ~/backups:/backup alpine tar xzf /backup/appflowy-minio-YYYY-MM-DD.tar.gz -C /"
```

### Full Teardown (DESTRUCTIVE — approval required)

```bash
# Removes containers AND all data volumes
ssh mini "cd ~/appflowy && docker compose down -v"
```

---

## 3. Credentials

All credentials are stored in `/home/jonc/appflowy/.env` on the Mac Mini.

| Credential | Purpose | Env Var |
|------------|---------|---------|
| Admin login | AppFlowy web/console | `GOTRUE_ADMIN_EMAIL` / `GOTRUE_ADMIN_PASSWORD` |
| Postgres | Database access | `POSTGRES_PASSWORD` |
| MinIO | Object storage | `AWS_ACCESS_KEY` / `AWS_SECRET` |
| JWT Secret | Token signing | `GOTRUE_JWT_SECRET` |

> ⚠️ Never log or echo credential values in Telegram messages or session logs.

---

## 4. Notion → AppFlowy Migration

AppFlowy supports importing Notion workspaces. The recommended workflow:

### Option A: Direct Notion Import (Preferred)
1. Open AppFlowy web UI → Settings → Import
2. Select "Import from Notion"
3. Authenticate with Notion OAuth
4. Select workspaces/pages to import
5. AppFlowy handles the conversion automatically

### Option B: Manual Markdown Import
1. Export from Notion: Each page → ⋯ → Export → Markdown & CSV
2. In AppFlowy web UI, use Import to upload the exported files
3. Verify pages, tables, and attachments transferred correctly

### What Transfers
- ✅ Rich text pages → AppFlowy Documents
- ✅ Tables/Databases → AppFlowy Grids
- ✅ Images and file attachments
- ✅ Nested page hierarchy
- ⚠️ Formulas and relations may need manual adjustment
- ⚠️ Notion-specific blocks (toggles, synced blocks) may render differently

---

## 5. API Access (for Allie integration)

AppFlowy Cloud exposes a REST API at `http://192.168.1.143:8085/api/`.

### Authentication Flow
```python
import requests

# 1. Get auth token via GoTrue
auth_resp = requests.post(
    "http://192.168.1.143:8085/gotrue/token?grant_type=password",
    json={
        "email": "writecorral@gmail.com",
        "password": "<admin_password>"  # from .env
    }
)
access_token = auth_resp.json()["access_token"]

# 2. Use token for API calls
headers = {"Authorization": f"Bearer {access_token}"}

# List workspaces
workspaces = requests.get(
    "http://192.168.1.143:8085/api/workspace",
    headers=headers
).json()
```

### Key API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/gotrue/token?grant_type=password` | POST | Login |
| `/api/workspace` | GET | List workspaces |
| `/api/workspace/{id}` | GET | Get workspace details |
| `/api/workspace/{id}/folder` | GET | Get folder structure |

---

## 6. Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| Blank page at :8085 | `docker compose ps` — check web/nginx status | `docker compose restart nginx` |
| Login fails | `docker compose logs gotrue` | Check `GOTRUE_ADMIN_EMAIL/PASSWORD` in `.env` |
| Upload fails | `docker compose logs minio` | Check MinIO health, S3 credentials |
| Slow performance | `free -h` on Mac Mini | Check RAM (7 GB total, ~2 GB for AppFlowy) |
| Container won't start | `docker compose logs <service>` | Check for port conflicts, missing env vars |
| Database errors | `docker compose logs postgres` | May need `docker compose down && docker compose up -d` |

---

## 7. Port Allocation Context

AppFlowy joins the existing Mac Mini service roster:

| Port | Service | Owner |
|------|---------|-------|
| 3000 | AdGuard (web UI) | adguard container |
| 4269 | Free LLM API | freellmapi container |
| 5678 | n8n | n8n container |
| 8010 | Paperless-ngx | paperless container |
| 8080 | AdGuard (DNS admin) | adguard container |
| 8082 | RomM | romm container |
| 8083 | Calibre-Web | calibre-web container |
| **8085** | **AppFlowy** | **appflowy nginx** |
| 8384 | Syncthing | syncthing container |
| 9443 | Portainer | portainer container |
| 32400 | Plex | plex container |
| 51820 | WireGuard | wireguard container |

---

## 8. Integration

### Read
- AppFlowy REST API — workspace, folder, document content
- Docker Compose status — container health

### Write
- AppFlowy REST API — create/update pages, import content
- Docker Compose — start/stop/restart services (approval-gated)

### Cross-Skill
- **system-health**: Add AppFlowy to heartbeat endpoint list
- **home-hub**: Registered in Network Devices
- **media-library**: No direct dependency

### Cross-Bot
- **home-bot** owns this skill
- **orchestrator** can delegate AppFlowy queries to home-bot

---

## 9. Routing

| Request Pattern | Action |
|----------------|--------|
| "AppFlowy status" / "is AppFlowy up?" | Health check via docker compose ps |
| "Restart AppFlowy" | `docker compose restart` (approval-gated) |
| "Backup AppFlowy" | Run backup commands |
| "Upgrade AppFlowy" | Pull + recreate (approval-gated) |
| "Import from Notion" | Guide through import flow |
| "AppFlowy logs" | Show recent container logs |
| "Open AppFlowy" | Return URL: http://192.168.1.143:8085 |
