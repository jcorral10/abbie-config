---
name: invention-processor
description: >
  Detects, captures, and analyzes invention ideas via #invent tag or explicit 
  mention. Performs IP novelty screening and market viability analysis, 
  cross-references against existing ideas in the Notion INVENT database, and 
  provides structured improvement suggestions.
requires:
  bins: [python3, pip]
  env: [NOTION_API_KEY]
---

# Invention Idea Processor

## Overview

This skill enables Abbie to function as Jon's invention idea processor:
1. **Trigger Detection**: Recognizes `#invent` tags or explicit invention language
2. **Idea Capture**: Creates structured entries in the Notion INVENT database
3. **IP Novelty Screen**: Web search + LLM analysis for prior art and conflicts
4. **Market Viability**: Competitive landscape, market sizing, monetization paths
5. **Cross-Reference**: Compares against all existing ideas, suggests improvements

---

## Trigger Detection

### Primary Triggers (always activate)
- Message contains `#invent` tag (case-insensitive)
- Message contains "invention idea" or "I have an invention" (case-insensitive)

### Secondary Triggers (activate if context supports it)
- "idea for a product"
- "idea for an app"
- "what if we built"
- "what if there was a"
- "patent idea"
- "new product concept"

### Detection Regex
```
Primary:  (?i)#invent|invention\s+idea|i\s+have\s+an\s+invention
Secondary: (?i)idea\s+for\s+a\s+(product|app|device|service|tool)|what\s+if\s+we\s+built|what\s+if\s+there\s+was|patent\s+idea|new\s+product\s+concept
```

### On Detection
1. Extract the core idea from the message (strip conversational fluff, greetings, etc.)
2. Acknowledge: `💡 Invention idea detected. Capturing and analyzing...`
3. Proceed to the Processing Pipeline

---

## Notion Database

- **Database ID**: `ff59713b-9715-470d-98f8-f957e56f3850`
- **Parent Page**: INVENT (shared with Abbie's integration)

### Schema Discovery

Before first use, run the schema discovery step:
```bash
python3 .agents/skills/invention-processor/scripts/notion_invent.py schema
```

This reads the live database schema and outputs the property map. The script 
adapts to whatever properties exist. If key properties are missing, it will 
note what to add manually in Notion.

### Recommended Properties

If adding properties to the INVENT database, these are ideal:

| Property | Type | Purpose |
|----------|------|---------|
| Name | Title | Idea name/title |
| Description | Rich Text | One-paragraph summary |
| Category | Select | See `resources/idea_categories.json` |
| Stage | Select | `💡 Raw` → `🔍 Analyze` → `✅ Validated` → `📦 Shelved` |
| IP Score | Number | 1-10 novelty assessment |
| Market Score | Number | 1-10 viability assessment |
| Related Ideas | Relation | Links to similar ideas in same DB |
| Date Added | Date | When the idea was captured |
| Tags | Multi-select | Free-form tags for filtering |

Create a **Board view** called "Idea Pipeline" grouped by `Stage`.

If these properties don't exist, the skill stores all analysis in the page body.

---

## Processing Pipeline

### Step 1: DETECT & CAPTURE
- **Model**: Kimi K2.6 (default)
- **Action**:
  1. Parse the idea from the user's message
  2. Generate a concise title (5-10 words max)
  3. Generate a one-paragraph description
  4. Create a Notion page in the INVENT database:
     - Set title property to the generated name
     - Set Description (if property exists) to the paragraph summary
     - Set Stage = "💡 Raw" (if property exists)
     - Set Category (if property exists) using `resources/idea_categories.json`
     - Set Date Added = today (if property exists)
  5. Store the raw user input as the first block in the page body
  6. Respond: `💡 Captured: "[Idea Title]" — running IP and market analysis...`

### Step 2: IP NOVELTY SCREEN
- **Model**: Sonnet 4.6 (mid-tier — requires reasoning + web search)
- **Action**:
  1. Generate 3-5 targeted search queries using templates from `resources/ip_search_queries.json`
  2. Search the web for:
     - Existing patents (Google Patents, patent databases)
     - Existing products or services that solve the same problem
     - Academic research or prior art
  3. Analyze findings with LLM:
     - **Novelty Score** (1-10): How original is this idea?
       - 1-3: Heavily patented / many existing products
       - 4-6: Some prior art exists but differentiation possible
       - 7-10: Highly novel, minimal prior art found
     - **Key Differentiators**: What makes this idea unique vs. existing solutions?
     - **Potential Conflicts**: Specific patents or products that overlap
     - **Freedom to Operate Notes**: High-level assessment (NOT legal advice)
  4. Update the Notion page:
     - Set IP Score property (if exists)
     - Append IP analysis section to page body using `resources/analysis_template.md`

### Step 3: MARKET VIABILITY
- **Model**: Sonnet 4.6 (mid-tier)
- **Action**:
  1. Search the web for:
     - Market size and growth trends for the problem domain
     - Direct and indirect competitors
     - Target audience demographics
     - Industry trends and timing
  2. Analyze findings with LLM:
     - **Market Score** (1-10): How viable is this commercially?
       - 1-3: Niche market, heavy competition, unclear demand
       - 4-6: Moderate market with some competition
       - 7-10: Large/growing market, clear demand, gap exists
     - **Target Audience**: Who would buy/use this?
     - **Competitors**: Top 3-5 existing solutions
     - **Monetization Paths**: How could this make money?
     - **Timing Assessment**: Is the market ready for this?
  3. Update the Notion page:
     - Set Market Score property (if exists)
     - Append market analysis section to page body

### Step 4: CROSS-REFERENCE
- **Model**: Kimi K2.6 (default — comparing text, not deep reasoning)
- **Action**:
  1. Fetch all existing ideas from the INVENT database:
     ```bash
     python3 .agents/skills/invention-processor/scripts/notion_invent.py list
     ```
  2. For each existing idea, compare semantic similarity to the new idea
  3. Identify:
     - **Overlapping ideas**: Ideas solving a similar problem
     - **Synergies**: Ideas that could combine to create something stronger
     - **Contradictions**: Ideas that conflict or compete with each other
     - **Technology Reuse**: Shared components or infrastructure
  4. If the INVENT database has a "Related Ideas" relation property, link them
  5. Append cross-reference section to page body

### Step 5: IMPROVEMENT SUGGESTIONS
- **Model**: Sonnet 4.6 (mid-tier — creative synthesis)
- **Action**:
  1. Based on all analysis from Steps 2-4, generate actionable improvements:
     - **Technical improvements**: Better approaches, materials, architectures
     - **Market positioning**: Niche-down, pivot angle, unique selling proposition
     - **Combination plays**: Merge with existing ideas from the database
     - **Risk mitigation**: How to navigate IP conflicts found
     - **MVP definition**: Smallest viable version to test the idea
  2. Append improvement section to page body
  3. Set Stage = "✅ Validated" (if property exists)

### Step 6: REPORT
- **Model**: Kimi K2.6 (default)
- **Action**:
  1. Compose a concise summary message with:
     - Idea title
     - IP Score and one-line summary
     - Market Score and one-line summary
     - Top 2-3 improvement suggestions
     - Link to the Notion page
  2. Send via Google Chat (if webhook configured)
  3. Reply to the user with the summary

---

## Error Handling

- **Notion API failure**: Log error, store analysis locally in 
  `memory/invention_backlog.json`, retry on next heartbeat
- **Web search failure**: Skip that section, note "Web search unavailable" in 
  the report, still complete LLM-only analysis
- **Database schema mismatch**: Fall back to page-body-only mode (no property 
  writes), log warning for Jon to review
- **Rate limiting**: If Notion returns 429, exponential backoff (1s, 2s, 4s, max 30s)

---

## Conversational Commands

Jon rarely opens Notion directly. He interacts with ideas through natural conversation
via Telegram. Allie must recognize these conversational patterns and route them to
`invent-bot` for processing.

### Stage Queries (read-only, low cost)

| Jon says... | Action |
|:------------|:-------|
| "What's in my raw ideas?" | Query INVENT DB where Stage = "💡 Raw", return titles + dates |
| "What ideas are being analyzed?" | Query where Stage = "🔍 Analyze" |
| "Show me validated ideas" | Query where Stage = "✅ Validated" |
| "What's shelved?" | Query where Stage = "📦 Shelved" |
| "List ideas" / "List all ideas" | Return all ideas grouped by Stage with scores |
| "How many ideas do I have?" | Return count by Stage |
| "Tell me about [idea name]" | Fetch the full page content for that idea |

**Response format** for queries — keep it tight:
```
💡 Raw Ideas (3):
• Smart Collar GPS — added Sep 12
• Modular Hydro Wall — added Sep 18  
• AI Recipe Scaler — added Sep 25
```

### Analysis Triggers (on-demand, higher cost)

| Jon says... | Action |
|:------------|:-------|
| "Analyze [idea name]" | Run full pipeline (Steps 2-6) on that idea. Move Stage → "🔍 Analyze" at start, → "✅ Validated" when done |
| "Analyze idea: [description]" | Capture as new idea (Step 1) THEN run full pipeline |
| "#invent [description]" | Same as above — capture + analyze |
| "Refresh [idea name]" | Re-run IP + Market analysis on an existing idea |
| "Synthesize" / "Synthesize my ideas" / "Synthesize all ideas" | Run cross-idea synthesis (see below) |
| "What connects to [idea name]?" | Run cross-reference (Step 4) for just that idea |

### Synthesis Command

When Jon says "synthesize" or "synthesize my ideas":

1. Fetch ALL ideas from the INVENT database (all stages)
2. Run cross-reference analysis across the full set
3. Identify:
   - **Clusters**: Ideas grouped by shared technology, target market, or problem domain
   - **Combinations**: Ideas that would be stronger merged (Idea A's mechanism + Idea B's market)
   - **Gaps**: Patterns across ideas that point to unserved markets or missing components
   - **IP Stacking**: Ideas whose patents could build a defensible portfolio together
4. Write results to a dedicated "Synthesis Report" page in Notion (create if not exists)
5. Reply with a conversational summary:
   ```
   🔗 Synthesis complete — 12 ideas analyzed.
   
   Clusters found:
   • Health/Wearable (3 ideas) — Smart Collar, Hydro Tracker, Sleep Vest
   • Kitchen/Food (2 ideas) — Recipe Scaler, Portion Plate
   
   Best combinations:
   • Smart Collar + Hydro Tracker → Pet health platform play
   • Recipe Scaler + Portion Plate → Full meal-prep ecosystem
   
   Gap spotted:
   • 3 ideas touch "real-time monitoring" but none address data privacy — 
     a privacy-first approach could differentiate all of them.
   
   Full report: [Notion link]
   ```

### Stage Management

| Jon says... | Action |
|:------------|:-------|
| "Move [idea] to analyze" | Set Stage = "🔍 Analyze" |
| "Shelve [idea]" | Set Stage = "📦 Shelved" |
| "Unshelve [idea]" | Set Stage = "💡 Raw" |
| "Validate [idea]" | Set Stage = "✅ Validated" |

---

## Memory Isolation

**All invention-related work is delegated to `invent-bot`.**

Allie's role is **routing only** — she recognizes the conversational trigger, passes the
command to invent-bot, and relays the response back to Jon. She does NOT:
- Store idea details in her own working memory
- Retain analysis results in her context
- Accumulate idea state across conversations

### Why
- Ideas can be detailed and context-heavy. Storing them in Allie's working memory
  crowds out other domains (finance, health, home, etc.)
- Invent-bot maintains its own context of the INVENT database
- This keeps token usage efficient — queries only cost tokens when Jon asks

### Routing Pattern
```
Jon (Telegram) → Allie → recognizes idea command
                        → delegates to invent-bot
                        → invent-bot queries Notion INVENT DB
                        → invent-bot returns result
                        → Allie relays to Jon
                        → Allie forgets the details (no memory write)
```

### What Allie DOES remember
- That the INVENT database exists and has X ideas (count only)
- That invent-bot handles all idea operations
- The stage vocabulary: Raw, Analyze, Validated, Shelved
- Jon's preference: on-demand only, no proactive analysis

### What Allie does NOT remember
- Individual idea titles, descriptions, or scores
- Analysis results or synthesis reports
- Idea relationships or clusters

---

## Important Disclaimers

Every analysis report MUST include this footer:

> ⚠️ **Disclaimer**: This analysis is AI-generated and does not constitute legal 
> or financial advice. IP novelty scores are based on publicly searchable 
> information and may miss unpublished patents or trade secrets. Consult a 
> patent attorney for formal freedom-to-operate assessments.

---

## Files in This Skill

| File | Purpose |
|------|---------|
| `SKILL.md` | This file — instructions and architecture |
| `scripts/notion_invent.py` | Notion API operations (CRUD, schema discovery) |
| `resources/analysis_template.md` | Structured report template for page body |
| `resources/ip_search_queries.json` | Patent and product search query templates |
| `resources/idea_categories.json` | Idea taxonomy for auto-categorization |
