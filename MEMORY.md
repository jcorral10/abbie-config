# Memory

## Technical Stack
- **Personal Assistant Platform**: Hermes Agent v0.20.0 Herald (running on Abacus AI SuperComputer, migrated 2026-07-30, upgraded 2026-08-06)
- **SuperComputer**: IP 208.122.8.11, port 22 (SSH, blocked at infra level), port 9119 (Hermes Gateway), port 8787 (Bridge API), $10/mo
  - **Cloudflare Tunnel**: systemd quick tunnel → `https://accessing-participate-hon-terminal.trycloudflare.com` (URL changes on restart, check `sudo journalctl -u cloudflared`)
  - **Bridge API Key**: `X-Bridge-Key: UCn0ayC8rB8VS0s3JhdZ7YsNBfzga5jxNF2PhX4qBeM`
  - **SSH**: Key authorized for `ubuntu` user, sshd on port 22, but Abacus infra blocks inbound port 22. Use tunnel+bridge instead.
  - **Hevy Webhook**: POST /webhook/hevy on bridge server, subscribed at hevy.com/settings?developer
- **Agent Name**: Allie (previously Abbie on OpenClaw)
- **Main Model**: deepseek/deepseek-v4-flash via OpenRouter
- **Fallback Model**: anthropic/claude-sonnet-4-6
- **Auxiliary Models**: gemini-3.5-flash via local endpoint (localhost:8081) — handles compression, vision, web_extract, session_search, approval
- **Local LLM**: Gemma 4 E4B IT Q4_K_M via llama.cpp (localhost:8082) — sensitive crons (finance, tax). ~5-6 tok/s generation. Draft model: Gemma 4 E2B at `/home/ubuntu/.local/models/gemma-4-E2B-it-Q4_K_M.gguf` (3.1 GB), ready for speculative decoding test.
  - **MCP SDK**: v1.29.0 (v2.0 breaks claude-agent-sdk dependency — stateless migration blocked until upstream fix)
  - **Approvals allowlist**: `python3 *`, `Check *` auto-approved. Circuit breaker active.
  - **Cron structured outputs**: 6 crons write JSON to `~/.hermes/cron_outputs/` for reliable inter-skill data flow (added 2026-08-08)
- **TTS**: Edge TTS (Aria voice), fallbacks: ElevenLabs, OpenAI, xAI, Mistral
- **Process Manager**: supervisord
- **Terminal**: Docker container (nikolaik/python3.11-nodejs20) with persistent shell
- **Primary Goals**:
  - Optimize token usage efficiency.
  - Establish a robust and clean memory structure.
  - Enhance overall utility, skills, and connections.

## Connected Platforms
- **Telegram**: DM with Jon (@JonCorr, ID 7605388765)
- **Hermes Gateway**: API server, supervisord-managed
- **Google Chat**: Alerts via webhook
- **Terminal**: Local backend, persistent shell, Docker

## Skills Library
- **33 categories, ~280+ skills** under `~/.hermes/skills/`
- Key categories: productivity, software-development, devops, autonomous-ai-agents, research, creative, mcp, github, bioinformatics (300+), cad-skill, media, smart-home, mlops, data-science, red-teaming, gaming
- Custom skills: financial-automation, financial-planner, health-automation, health-planner, digital-storefront-automation, digital-storefront-planner, invention-processor, project-board, billing-dispute-ai, patent-prior-art-scout, openscad, jupyter-live-kernel, native-mcp, job-search, resume-tailoring
- **MCP**: Native MCP client for stdio/HTTP servers

## Hermes Config Highlights
- Max turns per session: 90
- Gateway timeout: 30 min
- Approvals: smart mode (auto-approve safe ops, buttons for destructive)
- Cron approval mode: deny (no auto-execute)
- Delegation: max 3 parallel subagents, max spawn depth 1
- Context compression: enabled (40% threshold, 15% target, 400 msg hard limit)
- Memory: 2,200 chars (memory store) + 1,375 chars (user profile)
- Security: Tirith policy engine enabled
- Fallback providers chain: OpenRouter → Anthropic

## Architecture Decisions

### 2026-06-08: Migration from OpenClaw to Hermes
- **Decision**: Full migration from OpenClaw to Hermes Agent (now v0.15.2)
- **Impact**: New skill format, new config structure, new platform integrations
- **Previous**: OpenClaw with Abacus RouteLLM, `openclaw.json` config
- **Current**: Hermes with OpenRouter primary, local Gemini auxiliary at localhost:8081
- **Notion integration**: Unchanged — same NOTION_API_KEY, pages must be explicitly shared

### 2026-05-27: Invention Idea Processor
- **Decision**: Build `#invent` trigger skill for IP/market analysis
- **Notion DB**: INVENT page (`52b3ad05-9b6a-431a-b994-de8b79cb16ea`) with Ideas DB (16 properties)
- **Skill Location**: `~/.hermes/skills/` (migrated from `.agents/skills/invention-processor/`)
- **Triggers**: `#invent` tag, "invention idea" phrase, and secondary patterns
- **Pipeline**: Detect → Capture (Notion) → IP Screen (web search) → Market Analysis → Cross-Reference → Improvement Suggestions → Report

### 2026-05-26: Financial Automation System
- **Decision**: Build Notion-based personal finance automation
- **Notion DB**: FINANCE page (`31e8275a-14ea-41b1-98c6-d3ec92de2bf9`) with 7 child DBs (Accounts, Categories, Budgets, Transactions, Statements, Bills & Budget, Financial Roadmap)
- **PDF Processing**: pdfplumber + LLM categorization for Chase (credit + checking) and US Bank statements
- **Cron**: Monthly Financial Update on 1st of month @ 9am (deepseek-v4-flash)
- **Merchant Cache**: Self-learning JSON mapping, pre-seeded with 60+ known merchants

### Notion Databases (Allie's Control Plane)
- **ALLIE page** (`36d63d55-66c5-8163-8bc9-c438cb43ce3b`): MEMORY, SKILLS, DAILY LOGS, 📋 Project Board (`39563d55-66c5-81c3-827b-e124fc4bba17`)
- **INVENT page** (`52b3ad05-9b6a-431a-b994-de8b79cb16ea`): Ideas DB (16 properties)
- **FINANCE page** (`31e8275a-14ea-41b1-98c6-d3ec92de2bf9`): Accounts, Categories, Budgets, Transactions, Statements, Bills & Budget, Financial Roadmap
- **Health & Fitness page** (`36d63d55-66c5-8125-8c68-ee03bf91096c`): Workouts, PRs, Medications, Lab Results, Lab Markers
- **ANTIGRAVITY page** (`37963d55-66c5-8152-9240-c6c2a34391ed`): Bridge between Antigravity (Mac) and Allie (VM)
  - Inbound Relay DB (`37963d55-66c5-813f-ba47-fc8e8f5acb67`): Antigravity → Allie messages
  - Outbound Relay DB (`37963d55-66c5-8127-a0f1-f32b446d828b`): Allie → Antigravity messages
  - Knowledge Index DB (`37963d55-66c5-8135-9d38-f46005672025`): Shared resource catalog
  - Bridge script: `scripts/notion_bridge.py` (config: `scripts/.notion_config.json`, gitignored)

### Household Financial Profile
- **Jon**: $2,860 biweekly (every other Friday), 26 paychecks/yr = ~$74,360/yr
- **Wife**: $1,800 semi-monthly (1st & 15th), 24 paychecks/yr = $43,200/yr
- **Combined monthly base**: $9,320
- **Banks**: Chase (Sapphire Reserve, Freedom Flex, Freedom Unlimited, checking), US Bank (checking/savings), Capital One (Venture X upgrade in progress), Amazon Prime Card, Crypto.com Ruby
- **Total fixed obligations**: $5,720.86/mo (USB Autopay $4,655 + Flex Autopay $903 + Other $163)
- **Monthly margin at targets**: ~$1,149 (corrected from $2,096 on 2026-06-09 after discovering $1,462/mo in untracked bills)
- **Bar mitzvah**: $6,141 balance, deferred to July 2026
- **ER payment plan**: $150/mo from savings, ~16 months remaining
- **Northwestern Mutual**: Whole life/IBC, $1M/30yr, $95.46/mo
- **Investments**: Schwab ($10/mo), Jack Custodial IRA ($3/mo), Jaime 401k (Alight), Jon 401k (TBD)

### Active Crons (updated 2026-07-28 after LLM upgrade)
1. Monthly Financial Update — 1st @ 9am (llama-local)
2. hevy-daily-sync — Daily @ 10am
3. hevy-body-metrics-sync — Sundays @ 8am
4. weekly-training-intelligence — Sundays @ 7pm (gemini-local, moved from llama-local)
5. drive-health-reader — Daily @ 8am & 6pm
6. weekly-cost-review — Mondays @ 7:30am (staggered from 10am)
7. weekly-fitness-overview — Mondays @ 7:15am (gemini-local, staggered from 9am)
8. HM1 - Weekly Home Maint — Mondays @ 7:00am (gemini-local, staggered from 8am)
9. HM2 - Seasonal Home Maint Prep — quarterly (gemini-local)
10. LS1 - Monthly Life Score — 3rd @ 9pm (gemini-local)
11. TX1/TX2/TX3 — tax crons (llama-local)
12. CAL2 — calendar (llama-local)

**Not deployed**: 7 financial-planner crons (#8–#14) from SKILL.md were never created on the VM


### 2026-06-09: Financial Planner Upgrade
- **Decision**: Upgrade Allie from budget tracker to personal accountant/financial planner
- **New Skill**: `financial-planner` with 5 modules (Net Worth, Cash Flow, Debt Payoff, Credit Card Rewards, Financial Health Score)
- **Data Corrections**: Discovered $1,462/mo in untracked bills, 5 incorrect amounts, 6 credit cards (skill only knew 1)
- **Scripts**: debt_calculator.py, cash_flow_forecast.py, rewards_optimizer.py — all tested and working
- **Deployment**: Commit 4d1000a pushed to abbie-config, task sent to Allie via bridge
- **Pending**: Jon needs to provide interest rates, debt balances, 401(k) details

### 2026-07-14: Digital Storefront System
- **Decision**: Build two-layer digital business operating system for Etsy digital product sales
- **New Skills**: `digital-storefront-automation` (tactical: Etsy API, product files, orders, revenue) + `digital-storefront-planner` (strategic: niche research, SEO, pricing, business health, autonomous growth loop)
- **Platform**: Etsy API v3 (OAuth 2.0 PKCE)
- **Notion DB**: BUSINESS page (under ALLIE) with 7 child DBs:
  - ⚙️ Shop Config: `39d63d55-66c5-813e-8c5f-ea2515926d27`
  - 💡 Product Ideas: `39d63d55-66c5-81c4-8307-eb50ddaaf96d`
  - 📦 Products: `39d63d55-66c5-81bf-b824-e62a7c44ce31`
  - 🏪 Listings: `39d63d55-66c5-81cd-97b9-c55e5e345757`
  - 🧾 Orders: `39d63d55-66c5-8102-90ff-d99238dcee7d`
  - 🔍 SEO Keywords: `39d63d55-66c5-815f-a797-e85017d20447`
  - 📊 Business Snapshots: `39d63d55-66c5-8195-8f56-cf7101ec8601`
- **Automation Scripts**: etsy_client.py (1041 lines, full API client), product_manager.py (1041 lines, file lifecycle), revenue_sync.py (743 lines, order/fee sync)
- **Planner Scripts**: niche_researcher.py (1197 lines, trend/demand/competition scoring), seo_optimizer.py (1316 lines, keyword research + listing audit), pricing_engine.py (838 lines, competitive analysis), product_creator.py (1562 lines, generates printable PDFs, SVGs, spreadsheets, social templates, wall art, resumes, checklists)
- **8 Cron Jobs**: B1 Daily Sales Sync (11PM), B2 Listing Health (Mon/Thu 9AM), B3 Product Upload Monitor (8AM), B4 Weekly Niche Scout (Sun 10AM), B5 SEO Audit (Wed 9AM), B6 Monthly Business Review (1st 10AM), B7 Competitor Watch (1st/15th 8AM), B8 Growth Loop Trigger (Sat 11AM)
- **Autonomous Growth Loop**: SCAN → VALIDATE → IDEATE → CREATE → OPTIMIZE → LIST → MONITOR → ITERATE (approval gates at CREATE and LIST via Telegram)
- **Total**: 10,246 lines across 17 files
- **Deployment**: Commit eaf5e8f pushed, skills installed on VM 2026-07-14, Notion DBs created, Python deps installed
- **Pending**: Etsy developer account + API keys (`ETSY_API_KEY`, `ETSY_SHARED_SECRET`, `ETSY_SHOP_ID`), `GOOGLE_CHAT_WEBHOOK_BUSINESS`, then deploy crons B1-B8

### 2026-06-10: Health & Fitness System
- **Decision**: Build two-layer health operating system mirroring the financial architecture
- **New Skills**: `health-automation` (tactical data collection) + `health-planner` (strategic intelligence)
- **Data Sources**: Hevy API (workouts, body metrics, PRs), Apple Health via Health Auto Export ($24.99 lifetime → webhook), Notion DBs (medications, labs), Telegram (supplements, injuries)
- **Hevy API**: REST API with `api-key` header auth. Endpoints: workouts, workouts/events (delta sync), body_measurements, exercise_templates, exercise_history, routines
- **Apple Health Bridge**: Health Auto Export iOS app → POST JSON to `https://VM/api/health` → FastAPI receiver (`health_webhook.py`) → SQLite (`health_data.db`)
- **Scripts**: hevy_sync.py (1094 lines, workout+body metrics+PR sync), health_webhook.py (824 lines, FastAPI receiver), lab_interpreter.py (1376 lines, PDF parser+trends)
- **New Notion DBs**: Body Metrics, Injuries, Family Health Calendar, Health Snapshots
- **Enhanced Notion DBs**: Medications (9 new supplement fields), Lab Markers (optimal ranges + categories)
- **10 Cron Jobs**: H1 Hevy Sync (daily 10PM), H2 Body Metrics (Sat 8AM), H3 Weekly Summary (Sun 7PM), H4 Supplement Reorder (Wed 9AM), H5 Recovery Score (daily 7AM), H6 Training Intel (Sun 7:15PM), H7 Health Score (1st 8:30PM), H8 Biomarker Trends (on new labs), H9 Family Cal (Mon 8AM), H10 Supplement Schedule (daily 7AM/9PM)
- **Resources**: 45+ lab reference ranges, 15 supplement timing profiles, 41 exercise form library entries, health score weights
- **Deployment**: Commit 50aa6f4 pushed to abbie-config
- **Pending**: Jon needs to set up Health Auto Export on iPhone, confirm VM HTTPS endpoint accessibility, provide Hevy API key to Allie's env

## Long-Term User Preferences
- Jon approves **auto-escalation** — Allie can switch models without asking when task complexity warrants it
- Prefers explicit approval gates for side-effect actions (not model switching)
- Heartbeats currently disabled at user request
- Weekly synthesis and financial crons should run on mid-tier model
- Antigravity (this agent) runs on-demand via Gemini/Claude, independent billing from Allie

### 2026-07-20: Robinhood MCP Integration
- **Decision**: Connected Robinhood Agentic Trading MCP to both Antigravity (Mac) and Allie (Hermes VM)
- **MCP URL**: `https://agent.robinhood.com/mcp/trading`
- **Agentic Account**: 959217308 (nickname "Agentic", cash account, individual)
- **Walled Off**: Main brokerage (••••4705) and Roth IRA (••••2482) — `agentic_allowed=false`
- **Allie Role**: Primary trader — executes trades via Hermes MCP with Jon's Telegram approval
- **Antigravity Role**: **Suggestion mode only** — can research, pull quotes, analyze positions, and propose trades but NEVER execute `place_equity_order` or `place_option_order` unless Jon explicitly requests execution
- **First Trade**: Allie bought 0.141 shares of GOOGL @ $354.74
- **Config Files**: `~/.gemini/config/mcp_config.json`, `~/.gemini/settings.json` (Antigravity); `~/.hermes/config.yaml` (Allie)

### 2026-07-27: World Monitor Integration (PARKED)
- **Decision**: Build geopolitical intelligence layer for Allie using World Monitor MCP (42 tools)
- **Status**: ⏸️ PARKED — waiting for Jon to subscribe to World Monitor Pro ($39.99/mo) or API Starter
- **Files Built** (ready to deploy):
  - NEW: `.agents/skills/world-intelligence/` (SKILL.md 336 lines + 2 resource JSONs)
  - ENHANCED: `stock-weekly-briefing/SKILL.md` (geopolitical correlation layer added)
  - ENHANCED: `stock-market-macro/SKILL.md` (WM data sources, commodity correlation added)
- **Push Script**: `scripts/push_skills_to_notion.py` updated with correct SKILLS list
- **Notion Push**: Not yet run (Notion API was unreachable during build session)
- **Blocker**: `WORLDMONITOR_API_KEY` env var needed on VM
- **Crons**: WI1 (daily pulse 6:30AM), WI2 (risk monitor q6h), WI3 (cyber Mon 8:30AM), WI4 (market corr Sun 5PM)
- **To Resume**: Jon subscribes → provides API key → run push script → tell Allie to install

### 2026-07-28: Local LLM Upgrade (Qwen2.5-7B → Qwen3-4B)
- **Decision**: Replace Qwen2.5-7B Q4_K_M with Qwen3-4B Q4_K_M for faster CPU inference
- **Results**: Generation speed 0.75 → 3.8 tok/s (5x), prompt speed 7.8 → 20.4 tok/s (2.6x), model size 4.5 → 2.4 GB (-47%)
- **Scripts**: `scripts/llm-upgrade.sh` (VM automation), `scripts/push_llm_upgrade.py` (Notion bridge)
- **Deployment**: Commit 49f3cb6 pushed, Allie executed via Telegram instruction
- **Fixes Applied**: `pip install python-telegram-bot` (fixed weekly-fitness-overview + HM1 delivery errors)
- **Cron Changes**: 5 non-sensitive crons moved from llama-local → gemini-local; Monday AM staggered (7:00/7:15/7:30)
- **Open Items**:
  - New llama.cpp build (AVX-512+AMX) segfaults on Qwen3 model load — using stable system binary for now
  - Draft model (Qwen3-0.6B, 462 MB) staged at `~/.local/models/` for speculative decoding when build is fixed
  - When AVX-512 build works: expect another ~2-3x (→ ~8-12 tok/s) plus spec decoding boost

### 2026-07-30: Abacus AI SuperComputer Migration + HTTP Bridge
- **Decision**: Allie moved from raw Ubuntu VM to Abacus AI SuperComputer; build direct HTTP bridge replacing Notion relay
- **Platform Changes**: Always-on guaranteed uptime, built-in DB + S3 storage, public hosting, GitHub integration, 100+ AI models
- **Bridge Server**: `bridge/server/main.py` — FastAPI on port 8787 with 7 endpoints (health, relay, files, status)
- **Bridge Client**: `scripts/bridge.py` — CLI replacing `notion_bridge.py` for direct HTTP communication
- **Auth**: Shared API key (`BRIDGE_API_KEY` env var), stored in `.bridge_config.json` (gitignored)
- **Config-as-Code**: New `configs/` directory with `model_routing.yaml` and `skill_manifest.yaml`
- **SSH**: ed25519 key generated at `~/.ssh/id_ed25519`, pending Allie adding to `authorized_keys`
- **Notion Relay**: Kept as permanent fallback

### 2026-07-31: Local LLM Upgrade (Qwen3-4B → Gemma 4 E4B)
- **Decision**: Replace Qwen3-4B Q4_K_M with Gemma 4 E4B IT Q4_K_M for sensitive crons
- **Rationale**: Better agentic/tool-use performance, ~30-50% faster CPU inference, official Google GGUF builds (stronger supply chain provenance), Apache 2.0 license
- **Model Specs**: 4.0 GB Q4_K_M, ~4.5B active params (PLE architecture), verification test 3.5s round trip
- **Draft Model**: Gemma 4 E2B IT Q4_K_M (2.9 GB) staged for speculative decoding
- **Script**: `scripts/gemma4-upgrade.sh` — executed by Allie in 6m 28s
- **Deployment**: Allie also rebuilt llama.cpp from source (cmake + ggml 0.18.0) and self-patched hermes-env-operations skill
- **n8n Evaluated and Rejected**: n8n would consume 500 MB-1 GB idle RAM (6-12% of 8 GB budget), add web UI attack surface, and create redundant orchestration layer on top of Hermes-native crons

### 2026-08-16: Firecrawl "Website Not Supported" Fix
- **Problem**: `web_search` and `web_extract` tools returned "Website Not Supported: Failed to search. You are not authorized" despite valid API key
- **Root Cause**: Abacus AI VPS image's `/etc/environment` was overriding `FIRECRAWL_API_KEY` and `FIRECRAWL_API_URL` with a broken proxy at `routellm.abacus.ai` (HTTP 500)
- **Fix**: (1) Upgraded `firecrawl-py` from 4.17.0 → 4.35.1, (2) Set correct `FIRECRAWL_API_KEY`, `FIRECRAWL_BASE_URL`, and `FIRECRAWL_API_URL` directly in Hermes systemd service file to override `/etc/environment`
- **Lesson**: Always check `/etc/environment` on Abacus AI VPS images — the base image injects environment overrides that can silently hijack API keys
- **Bridge Observability**: Added 5 new endpoints (cron-report, cron-reports, files/list, metrics) + request counter middleware to bridge server; 3 new client commands (reports, ls, metrics)
- **Bridge SSL Fix**: Added ssl.CERT_NONE context + 30s timeout to bridge.py for Cloudflare tunnel compatibility

### 2026-08-24: Bot Mode Activation
- **Decision**: Split monolithic Allie into specialist bot profiles using Hermes Bot Mode
- **Profiles Created**:
  - `default` (Allie coordinator) — deepseek-v4-flash — routes requests, project board, life score, calendar — 3 crons
  - `finance-bot` — deepseek-v4-flash (changed 2026-08-25, was llama-local — 18K system prompt overflowed 16K ctx). llama-local fallback for explicit PII — 6 crons
  - `health-bot` — gemini-local (port 8081 down, falls back to deepseek) — 5 crons
  - `home-bot` — gemini-local (same fallback) — 3 crons
  - `storefront-bot` — deepseek-v4-flash — 0 crons (pending Etsy API keys)
  - `market-bot` — deepseek-v4-flash, Robinhood MCP (exclusive) — 1 cron
  - `ops-bot` — gemini-local (system health, cron audit, watchdog, token analysis) — 6 crons (SH1-SH6)
- **Total**: 23 bot-profile crons + 1 system monitor on default
- **Config**: `agent.bot_mode_protocol: true` in config.yaml
- **SOUL Files**: `bot-souls/` directory in repo, installed to each profile
- **Model Pinning Fix**: finance-bot provider corrected to llama-local (was falling through to OpenRouter)
- **n8n Acknowledged**: Morning Briefing, Smart Notion Relay, HA Event Reactor on Mac Mini (192.168.1.143:5678) — not duplicated
- **CAL2**: Scoped to smart conflict detection only (n8n sends raw calendar/weather at 7 AM)
- **Scripts**: `scripts/bot-mode-activate.sh` (Phase 1), `scripts/bot-mode-cron-migrate.sh` (Phase 2)
- **Commits**: c4aeb54, 1a41c30, e4206c3, 00c2ec5

### 2026-08-24: Repo Transfer
- **Decision**: Transferred `abbie-config` repo from `joncorral-Hills` to `jcorral10` (personal account)
- **Reason**: Personal/household repo doesn't belong under work org
- **Remote URL**: `https://github.com/jcorral10/abbie-config.git`
- **Action needed**: Allie's VM clone also needs `git remote set-url origin https://github.com/jcorral10/abbie-config.git`

### 2026-08-25: ops-bot (System Health Monitor)
- **Decision**: Add 9th specialist bot profile for infrastructure and ops monitoring
- **New Skill**: `system-health` with 6 modules (Heartbeat Monitor, Cron Auditor, Token & API Audit, Memory & Storage Audit, Watchdog, Weekly Ops Report)
- **Bot Profile**: `ops-bot` — gemini-local (lightweight checks don't need cloud inference)
- **Self-Heal Policy**: Alert & Approval only — no auto-remediation, all fixes via Telegram approval buttons
- **Token Analysis**: Tracks token consumption per bot/skill/cron, identifies optimization opportunities (model downgrades, frequency reduction, prompt compression) — does NOT enforce budget ceilings since OpenRouter auto-reloads
- **Notion DB**: 📡 System Health DB under ALLIE page (weekly Ops Score snapshots, incident log)
- **Cron Registry**: `resources/cron_registry.json` — master inventory of all ~51 crons across 22 skills with deployed/not-deployed status
- **Ops Score**: Composite 0–100 metric (Uptime 25%, Cron Reliability 25%, API Health 20%, Resource Efficiency 15%, Hygiene 15%)
- **Structured Output**: `ops_score_latest.json` for Life Score consumption (potential future 6th domain)
- **Crons**: SH1 (heartbeat q2h), SH2 (cron audit daily 5:30AM), SH3 (API audit daily 5AM), SH4 (storage weekly Sun 5AM), SH5 (watchdog q4h), SH6 (weekly report Sun 6PM)
- **Deployed**: ✅ All files pushed, Notion DB created, 6 crons registered, first heartbeat completed

### 2026-08-25: Memory Audit — 85% → 19%
- **Problem**: Memory store at 85% (1,888/2,200 chars, 11 entries) — shared across all 9 bot profiles, wasting context on bot-specific data
- **Fix**: Removed 8 entries (duplicates, bot-specific data offloaded to soul files, stuck "m" artifact)
- **Result**: 3 entries remain (418 chars, 19%): Project Board DB ID, Brave Search API, Cron mode workaround
- **Offloads**: ops-bot soul ← System Health DB ID + cron refs; finance-bot soul ← financial snapshot pointer; calendar-automation resources ← Google Calendar IDs

### 2026-08-25: finance-bot Model Change (llama-local → deepseek-v4-flash)
- **Problem**: Hermes system prompt is ~18K tokens, overflows llama-local's 16K context window (90 min startup on CPU)
- **Fix**: Changed finance-bot primary model to deepseek-v4-flash (4s response); llama-local retained as fallback for explicit PII
- **SOUL rule preserved**: "Never send raw PII to cloud models" — Plaid data fetched locally, LLM only sees analysis

### 2026-08-25: gemini-local Fix (gemini-web2api → curl-based proxy)
- **Problem**: gemini-web2api v1.1.0 SSL/TLS negotiation fails silently with Python's httpx — port 8081 DOWN, context compression failing
- **Fix**: Allie built curl-based proxy at `~/.local/bin/gemini-local-proxy.py` — forwards OpenAI-compatible requests to Gemini via curl subprocess
- **Result**: Port 8081 ✅, compression working, ~60s cold start / ~2s warm
- **Architecture**: gemini-local (8081, free Gemini proxy) + llama-local (8082, Gemma 4 E4B CPU) + deepseek-v4-flash (OpenRouter, default)

### 2026-08-26: CleverCorral.com — HA Cloudflare Tunnel (COMPLETE ✅)
- **Domain**: clevercorral.com on Cloudflare, DNS Full, SSL Active
- **Tunnel**: Abbie2Clock (remote-managed, token-based), connector on HA OS (linux_arm64)
- **Route**: `ha.clevercorral.com` → `http://homeassistant.local.hass.io:8123` (configured via add-on `external_hostname`)
- **Root Cause of 400 errors**: HA 2026.8 migrated `http` integration from YAML to `.storage/http` (`yaml_migration_done: true`). All `configuration.yaml` edits were silently ignored. Fix: edit `.storage/http` directly to add trusted_proxies
- **Trusted Proxies** (in `.storage/http`, NOT configuration.yaml): `127.0.0.1/32`, `172.30.32.0/23`, `192.168.1.0/24`
- **Docker network**: Add-on containers use `172.30.32.0/23` (not just `172.30.33.1`)
- **API verified**: 364 entities accessible via `https://ha.clevercorral.com/api/states`
- **HA Token**: In `~/.env` as `HA_TOKEN` (Long-Lived Access Token, expires ~2036)

