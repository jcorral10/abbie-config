---
name: design-intelligence
description: >
  Design trend intelligence and creative direction engine for the Corral
  digital storefront. Monitors macro and micro design trends across POD
  platforms, generates actionable design briefs with specific palettes,
  typography, and aesthetic direction, and validates designs against
  commercial quality gates before listing. Feeds design briefs to the
  digital-storefront-planner and automation skills.
requires:
  bins: [python3, curl]
  env:
    - NOTION_API_KEY
    - NOTION_DB_TREND_REGISTRY
    - NOTION_DB_DESIGN_BRIEFS
    - NOTION_DB_PRODUCT_IDEAS
---

# Design Intelligence

> **Layer**: Creative Direction (trend research → design brief → quality gate)
> **Owner**: Allie (Hermes Agent)
> **Feeds Into**: digital-storefront-planner (ideation), digital-storefront-automation (creation)
> **Data Store**: Notion (2 new databases + reads from existing Business DBs)
> **Alerts**: Telegram (design briefs for approval), Google Chat (trend reports)

---

## Overview

This skill is the **creative eye** that ensures every product Allie creates
is commercially viable and aesthetically current. It operates on a 3-stage
pipeline:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DESIGN INTELLIGENCE ENGINE                         │
│                                                                         │
│  Stage 1: TREND RADAR          Stage 2: DESIGN BRIEF    Stage 3: QA    │
│  ┌────────────────────┐       ┌──────────────────┐     ┌────────────┐  │
│  │ Web trend scan     │       │ Match trend to   │     │ Squint     │  │
│  │ Platform velocity  │──────▶│ product type     │────▶│ Test       │  │
│  │ Palette extraction │       │ Generate brief   │     │ Thumbnail  │  │
│  │ Decay detection    │       │ Approval gate    │     │ Identity   │  │
│  └────────────────────┘       └──────────────────┘     │ Mockup QA  │  │
│         │                            │                  └────────────┘  │
│         ▼                            ▼                        │         │
│  ┌──────────────┐             ┌──────────────┐         ┌──────▼──────┐ │
│  │ Notion:      │             │ Notion:      │         │ Storefront  │ │
│  │ Trend        │             │ Design       │         │ Automation  │ │
│  │ Registry     │             │ Briefs       │         │ (create)    │ │
│  └──────────────┘             └──────────────┘         └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### The Intersection Formula (Core Creative Principle)

Every design MUST apply the **2026 Intersection Formula**:

```
Specific Identity/Subculture + Specific Relatable Situation + Distinct Micro-Aesthetic
```

**Bad**: "Coffee Lover" on a mug
**Good**: "Anxious Barista Who Reads Gothic Sci-Fi" styled as a 1970s linocut matchbook

This formula is the single biggest differentiator between mediocre POD
listings and bestsellers. Enforce it in every design brief.

---

## Setup (One-Time)

### Step 1: Create Notion Databases

Create two new databases under the **BUSINESS** page.

### Step 2: Seed the Trend Registry

Use `resources/trend_seed_data.json` to populate the initial trend registry
with the 6 verified 2026 micro-aesthetics and 9 verified color palettes.

### Step 3: Register Cron Jobs

```bash
hermes cron add DI1-weekly-trend-radar
hermes cron add DI2-design-brief-generator
hermes cron add DI3-trend-decay-check
```

### Step 4: Install Dependencies

```bash
pip install requests beautifulsoup4 Pillow
```

---

## Notion Database Schemas

### 🎨 Trend Registry (14 properties)

| Property | Type | Details |
|----------|------|---------|
| Trend Name | Title | Named aesthetic movement (e.g., "Sardinecore Bistro") |
| Category | Select | Aesthetic / Color / Typography / Illustration / Motif / Layout |
| Status | Select | 🔥 Rising / ✅ Peak / 📉 Declining / ❄️ Dead |
| Momentum Score | Number (0-100) | Composite velocity score from trend sources |
| Discovered Date | Date | When first identified |
| Peak Date | Date | When momentum score peaked (auto-set) |
| Source | Multi-Select | Pinterest Predicts / WGSN / eRank / Google Trends / Etsy Trending / Dribbble / TikTok / Manual |
| Platform Velocity | Select | 🚀 Accelerating / ➡️ Stable / 📉 Decelerating |
| Product Fit | Multi-Select | T-Shirts / Mugs / Wall Art / Stickers / Planners / All |
| Color Palette | Rich Text | Hex codes as CSV (e.g., "#2F6364, #D32E5E, #F0EEE9") |
| Typography | Rich Text | Recommended font names (e.g., "Recoleta + Inter") |
| Description | Rich Text | What this trend looks like, feels like, and who it appeals to |
| Competitor Saturation | Select | Low / Medium / High / Oversaturated |
| Last Checked | Date | Last time momentum was re-evaluated |

### 📐 Design Briefs (16 properties)

| Property | Type | Details |
|----------|------|---------|
| Brief Name | Title | Short creative name (e.g., "Sardinecore Kitchen Art Set") |
| Status | Select | 📝 Draft / 👀 Awaiting Approval / ✅ Approved / 🎨 In Production / 🚀 Listed / ❌ Rejected |
| Trend | Relation → Trend Registry | Which trend(s) this brief applies |
| Product Type | Select | T-Shirt / Mug / Wall Art / Sticker Pack / Planner / Canvas / Enamel Mug |
| Target Niche | Rich Text | The specific identity intersection (e.g., "Italian grandma energy + apartment dweller + foodie") |
| Aesthetic Direction | Rich Text | Detailed visual direction paragraph |
| Color Palette | Rich Text | Exact hex codes for this design (e.g., "#2F6364, #FFB832, #F0EEE9") |
| Typography Direction | Rich Text | Specific fonts and hierarchy (e.g., "Hero: Recoleta Bold 72pt. Support: Inter 14pt") |
| Illustration Style | Select | Linocut / Risograph / Retro Mascot / Botanical Line / Faux-Textile / Matchbook / Photo-Collage |
| Mockup Direction | Rich Text | Lifestyle mockup requirements (lighting, setting, model demographic) |
| Squint Test Notes | Rich Text | What the design must communicate at 150×150px thumbnail size |
| Estimated Price | Number ($) | Target price point based on market position |
| Differentiation Notes | Rich Text | How this differs from top 5 competitors in same niche |
| Created | Created Time | Auto-set |
| Approved Date | Date | When Jon approved (null until approved) |
| Product Idea Link | Relation → Product Ideas | Links to storefront planner's idea DB |

---

## Module A: Trend Radar

Scans multiple trend sources weekly to maintain a living registry of what's
commercially viable right now.

### Data Sources (Tier 1 — Automated)

| Source | Method | Signal |
|--------|--------|--------|
| Google Trends | Web search API | Search velocity for aesthetic keywords |
| Pinterest Predicts | Web scrape annual report | 6-9 month forward indicators |
| eRank / EverBee | Web search for trending tags | Etsy-specific keyword velocity |
| Etsy Trending | Scrape trending/editors picks | Platform-endorsed aesthetics |
| TikTok/Instagram | Search hashtag velocity | Micro-aesthetic community growth |
| Dribbble/Behance | Search curated galleries | Professional design direction |

### Data Sources (Tier 2 — Manual/Annual)

| Source | Method | Signal |
|--------|--------|--------|
| WGSN/Coloro | Read annual reports (Jon provides) | Color and mood forecasting |
| Pantone COTY | Annual announcement | Mass-market color direction |
| Creative Market | Blog trend reports | Font and asset sales velocity |

### Trend Scoring Algorithm

```python
def score_trend(trend: dict) -> int:
    """Score a trend 0-100 for commercial viability."""
    weights = {
        "search_velocity": 0.25,      # Google Trends / eRank momentum
        "platform_presence": 0.20,    # Etsy trending, Pinterest boards
        "social_velocity": 0.15,      # TikTok/IG hashtag growth rate
        "competitor_gap": 0.20,       # Inverse of saturation on Etsy
        "product_versatility": 0.10,  # How many product types it works on
        "trend_freshness": 0.10,      # Newer trends score higher
    }

    scores = {}

    # Search velocity: compare 30-day vs 90-day search volume
    velocity_ratio = trend["search_30d"] / max(trend["search_90d_avg"], 1)
    scores["search_velocity"] = min(100, int(velocity_ratio * 50))

    # Platform presence: count of trending/featured placements
    scores["platform_presence"] = min(100, trend["platform_mentions"] * 20)

    # Social velocity: hashtag growth rate (posts per week delta)
    scores["social_velocity"] = min(100, int(trend["hashtag_growth_pct"] * 2))

    # Competitor gap: fewer competitors = higher score
    saturation = trend["etsy_listing_count"]
    if saturation < 500:
        scores["competitor_gap"] = 95
    elif saturation < 2000:
        scores["competitor_gap"] = 75
    elif saturation < 10000:
        scores["competitor_gap"] = 50
    elif saturation < 50000:
        scores["competitor_gap"] = 25
    else:
        scores["competitor_gap"] = 10

    # Product versatility: how many product types it maps to
    scores["product_versatility"] = min(100, len(trend["product_types"]) * 20)

    # Trend freshness: days since discovery (newer = higher)
    days_old = trend["days_since_discovery"]
    if days_old < 30:
        scores["trend_freshness"] = 100
    elif days_old < 90:
        scores["trend_freshness"] = 75
    elif days_old < 180:
        scores["trend_freshness"] = 50
    else:
        scores["trend_freshness"] = 25

    # Weighted composite
    composite = sum(scores[k] * weights[k] for k in weights)
    return int(composite)
```

### Trend Status Lifecycle

```
🔥 Rising  →  ✅ Peak  →  📉 Declining  →  ❄️ Dead
   (score ≥ 60)  (velocity slowing)  (score < 40)  (score < 20 for 60+ days)
```

- **Rising**: Actively accelerating. Create products NOW.
- **Peak**: High presence but velocity flattening. Still profitable but watch for decline.
- **Declining**: Past peak. Don't start new products, but existing listings may still sell.
- **Dead**: Remove from active consideration. Archive.

---

## Module B: Design Brief Generator

Takes a trend + product type and produces a complete creative direction
document that tells the product creator exactly what to build.

### Brief Generation Pipeline

```python
def generate_brief(trend: dict, product_type: str, niche: str) -> dict:
    """Generate a complete design brief from trend + product type + niche."""

    brief = {
        "name": f"{trend['name']} — {product_type.title()}",
        "trend": trend["name"],
        "product_type": product_type,
        "target_niche": niche,
    }

    # 1. Apply the Intersection Formula
    # The niche must be a specific identity intersection, NOT a broad category
    if len(niche.split()) < 5:
        brief["warning"] = "Niche too broad. Apply intersection formula."
        # Auto-suggest intersection expansion
        brief["niche_suggestions"] = expand_niche_intersection(niche, trend)

    # 2. Select color palette from trend or seasonal palette
    brief["color_palette"] = select_palette(trend, product_type)

    # 3. Typography direction
    brief["typography"] = select_typography(trend, product_type)

    # 4. Illustration style
    brief["illustration_style"] = match_illustration_style(trend)

    # 5. Aesthetic direction paragraph
    brief["aesthetic_direction"] = compose_aesthetic_direction(
        trend, product_type, niche, brief["color_palette"],
        brief["typography"], brief["illustration_style"]
    )

    # 6. Squint test requirements
    brief["squint_test"] = generate_squint_test_requirements(
        product_type, brief["typography"]
    )

    # 7. Mockup direction
    brief["mockup_direction"] = generate_mockup_direction(product_type)

    # 8. Competitive differentiation
    brief["differentiation"] = analyze_competitor_gap(
        trend, product_type, niche
    )

    # 9. Pricing recommendation
    brief["estimated_price"] = recommend_price(product_type, trend)

    return brief
```

### The Squint Test (Mandatory Quality Gate)

Every design brief includes a **Squint Test** specification:

```python
def generate_squint_test_requirements(product_type: str, typography: dict) -> str:
    """Define what the design must communicate at 150x150px thumbnail size.

    The Squint Test: shrink the design to thumbnail size and squint.
    If you can't instantly identify:
      1. What it IS (product category)
      2. What it SAYS (primary message)
      3. Who it's FOR (identity signal)
    ...then the design fails and must be reworked.
    """
    rules = [
        "Hero text must be readable at 150x150px — minimum 40% of composition",
        f"Use {typography['hero_font']} at maximum weight for hero element",
        "Maximum 2 visual focal points (1 preferred)",
        "High contrast between text and background (min 4.5:1 ratio)",
        "No fine detail that becomes noise at thumbnail scale",
    ]

    if product_type in ("t-shirt", "mug"):
        rules.append("Design must read on both light AND dark product blanks")
    if product_type == "sticker_pack":
        rules.append("Individual stickers must be distinguishable in pack preview")
    if product_type == "wall_art":
        rules.append("Gallery wall context must be visible in listing thumbnail")

    return "\n".join(f"- {r}" for r in rules)
```

### Mockup Direction Standards

```python
MOCKUP_STANDARDS = {
    "t-shirt": {
        "staging": "Lifestyle model shot, warm ambient lighting, urban or cozy interior",
        "blank": "Heavyweight 240+ GSM boxy fit (Comfort Colors 1717 style)",
        "wash": "Mineral/pigment wash preferred (charcoal, terracotta, sage)",
        "avoid": "Standard white-backdrop flat lay, thin-fit blanks",
    },
    "mug": {
        "staging": "Warm hands holding mug, steam visible, cozy desk/kitchen setting",
        "blank": "Ceramic 11oz or enamel camp mug depending on design aesthetic",
        "wrap": "Wraparound designs preferred over center-stamp for premium feel",
        "avoid": "Floating mug on white background, handle-forward angle",
    },
    "wall_art": {
        "staging": "Gallery wall context showing complementary pieces, natural light",
        "frame": "Thin natural wood or matte black frame on textured wall",
        "sets": "Show as coordinated set of 2-3 if selling bundles",
        "avoid": "Single print floating on white, no room context",
    },
    "sticker_pack": {
        "staging": "Applied to laptop, water bottle, or journal in lifestyle shot",
        "layout": "Kiss-cut sheet layout showing all stickers clearly",
        "count": "6-10 themed stickers per sheet for high perceived value",
        "avoid": "Flat scan of sheet only, no application context",
    },
    "planner": {
        "staging": "Open on desk with pen, coffee, and plants visible",
        "theme": "Warm cream or dark mode backgrounds, NOT pure white",
        "pages": "Show 3-4 interior spreads in carousel images",
        "avoid": "Cover-only listing photos, blinding white pages",
    },
}
```

---

## Module C: Design Quality Assurance

Validates a completed design against commercial viability standards before
it proceeds to listing.

### Quality Gate Checklist (Score 0-100)

| Check | Max Points | Criteria |
|-------|-----------|----------|
| Squint Test | 25 | Readable at 150×150px, instant category/message/audience recognition |
| Intersection Formula | 20 | Specific identity + specific situation + distinct aesthetic (not generic) |
| Trend Alignment | 15 | Uses current Rising/Peak trend palette, typography, and motifs |
| Thumbnail Contrast | 15 | 4.5:1 minimum contrast ratio, hero element >40% of composition |
| Mockup Quality | 15 | Lifestyle staging per mockup standards (not flat white default) |
| Differentiation | 10 | Visually distinct from top 5 competitors in same niche search |

**Minimum passing score: 70/100**

Designs scoring below 70 are sent back with specific improvement notes.
Designs scoring 85+ are flagged as "high confidence" for priority listing.

### Anti-Patterns (Auto-Fail)

These patterns cause an automatic failure regardless of score:

```python
AUTO_FAIL_PATTERNS = [
    "Raw unedited AI-generated imagery (glossy, plastic texture, floating artifacts)",
    "Generic broad niche ('Dog Lover', 'Coffee Mom', 'Gym Rat')",
    "Text unreadable at thumbnail size",
    "Default POD provider mockup (white background, flat product render)",
    "More than 2 fonts in a single design",
    "Clip art or stock vector assemblage without cohesive style",
    "Pure white (#FFFFFF) backgrounds on planners or wall art",
    "Crowded composition with no clear visual hierarchy",
]
```

---

## Module D: Trend-to-Product Matcher

Maps trending aesthetics to optimal product types based on the research
showing which aesthetics sell best on which products.

### Aesthetic × Product Affinity Matrix

| Aesthetic | T-Shirt | Mug | Wall Art | Stickers | Planner |
|-----------|---------|-----|----------|----------|---------|
| Sardinecore / Bistro Nostalgia | ★★★ | ★★★★★ | ★★★★★ | ★★★★ | ★★ |
| Vintage Matchbook / Motel Ephemera | ★★★★★ | ★★★★ | ★★★★ | ★★★★★ | ★★ |
| Neo-Western / Southwestern | ★★★★ | ★★★ | ★★★★★ | ★★★ | ★★ |
| Playful Maximalism / Circus-Core | ★★★★ | ★★★ | ★★★ | ★★★★★ | ★★★★ |
| Soft Stitch / Heritage Craft | ★★★ | ★★★ | ★★★★★ | ★★★ | ★★★ |
| Moody Gothic Botanical | ★★★★ | ★★★★ | ★★★★★ | ★★★★★ | ★★★ |

### Price Positioning by Product Type

| Product Type | Penetration | Value | Premium |
|-------------|-------------|-------|---------|
| T-Shirt (heavyweight) | $19.99 | $24.99 | $34.99 |
| Mug (ceramic 11oz) | $14.99 | $18.99 | $24.99 |
| Wall Art (set of 2-3) | $12.99 | $19.99 | $29.99 |
| Sticker Pack (6-10 pcs) | $4.99 | $7.99 | $12.99 |
| Digital Planner | $5.99 | $9.99 | $14.99 |

---

## Cron Automations

### DI1: Weekly Trend Radar

| Field | Value |
|-------|-------|
| Schedule | Sunday 8:00 AM CT |
| Cron | `0 8 * * 0` |
| Model | `sonnet-4.6` |

**Pipeline:**
1. Search Google Trends for all active trend keywords in the Trend Registry
2. Search eRank/Etsy for keyword velocity changes
3. Search TikTok/Instagram for hashtag growth on aesthetic tags
4. Re-score all active trends using the scoring algorithm
5. Identify new emerging trends not yet in registry
6. Update Trend Registry statuses (Rising → Peak → Declining → Dead)
7. Post trend report summary to Google Chat with top 3 opportunities

### DI2: Design Brief Generator

| Field | Value |
|-------|-------|
| Schedule | Wednesday 10:00 AM CT |
| Cron | `0 10 * * 3` |
| Model | `sonnet-4.6` |

**Pipeline:**
1. Pull all Rising/Peak trends from Trend Registry (score ≥ 60)
2. Cross-reference against existing Design Briefs to avoid duplicates
3. Cross-reference against Product Ideas DB for approved ideas needing briefs
4. Generate 2-3 new design briefs applying the Intersection Formula
5. Run each brief through the Quality Gate checklist (Module C)
6. Save briefs to Notion Design Briefs DB with status "Awaiting Approval"
7. Send top brief to Jon via Telegram for approval with:
   - Trend name and momentum score
   - Target niche (intersection formula applied)
   - Color palette preview (hex codes)
   - Typography direction
   - Estimated price and competitor gap

### DI3: Trend Decay Monitor

| Field | Value |
|-------|-------|
| Schedule | 1st and 15th at 9:00 AM CT |
| Cron | `0 9 1,15 * *` |
| Model | `deepseek-v4-flash` |

**Pipeline:**
1. Pull all trends with status Rising or Peak
2. Compare current momentum score vs. score from 14 days ago
3. Flag trends with >15% score decline as "velocity warning"
4. Auto-transition trends below score 40 to Declining
5. Auto-transition trends below score 20 for 60+ days to Dead
6. Alert on any trend transitions via Telegram
7. Flag any active Design Briefs linked to declining trends

---

## Integration

| System | Direction | Purpose |
|--------|-----------|--------|
| Notion Trend Registry | Read/Write | Maintain living trend database |
| Notion Design Briefs | Read/Write | Store and manage design briefs |
| Notion Product Ideas | Read | Check for approved ideas needing design direction |
| Notion Products | Read | Avoid creating briefs for existing products |
| Google Trends | Read | Search velocity signals |
| Etsy (via web search) | Read | Platform-specific trend presence |
| TikTok/Instagram (via web search) | Read | Social velocity signals |
| Pinterest Predicts | Read | Forward-looking trend indicators |
| Telegram | Write | Design brief approvals and trend alerts |
| Google Chat | Write | Weekly trend report cards |
| digital-storefront-planner | Feed | Design briefs feed into product ideation |
| digital-storefront-automation | Feed | Approved briefs trigger product creation |

---

## Resource Files

| File | Purpose |
|------|---------|
| `SKILL.md` | This skill definition |
| `resources/trend_seed_data.json` | Initial 2026 trend registry with 6 aesthetics + 9 palettes |
| `resources/aesthetic_product_matrix.json` | Trend × product affinity scores |
| `resources/typography_library.json` | Curated font pairings with use cases |
| `resources/quality_gate_config.json` | QA scoring weights and thresholds |
