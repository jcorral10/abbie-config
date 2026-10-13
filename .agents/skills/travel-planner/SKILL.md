---
name: travel-planner
description: >
  Full-service travel assistant with real-time search across 20+ providers (Booking.com, Google Flights, Skyscanner, Vrbo, Turo, SeatGeek, etc.) via the travel_search.py CLI script. Budget-aware planning with Chase Trifecta and Capital One Venture X points optimization, flight/hotel price monitoring, and real-time trip expense tracking via Telegram quick-log.
requires:
  bins: [python3]
  env: [NOTION_API_KEY, FIRECRAWL_API_KEY]
---

# Travel Planner

## ⚠️ CRITICAL BEHAVIORAL RULES

**Rule 1: YOU CAN SEARCH FOR REAL-TIME TRAVEL PRICES. NEVER SAY YOU CANNOT.**

You have `scripts/travel_search.py` — a CLI tool that searches 20+ real-time travel providers. Run it via `terminal`. When Jon asks you to find hotels, flights, vacation rentals, car rentals, or event tickets — **SEARCH FIRST, explain limitations only if a specific search fails**.

**Rule 2: NEVER write a wall of text about your limitations.**

If Jon asks "find me a hotel in Hermann, Missouri" — your response should be search results, NOT paragraphs about what you can't do. Run the script, format the output, and present results.

**Rule 3: Search multiple providers and compare.**

The script automatically searches Booking.com AND Vrbo for hotels, Google Flights AND Skyscanner for flights. Present results in a clean comparison table.

**Rule 4: Always tie results back to Jon's points strategy.**

After presenting search results, recommend whether to book with cash (earning points) or redeem points, using Module A logic.

**Rule 5: How to call the search script.**

Use `terminal` to run:
```bash
# Hotels / vacation rentals
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py hotels \
  --destination "Hermann, Missouri" --checkin 2026-11-15 --checkout 2026-11-17 --adults 2

# Flights
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py flights \
  --origin "Kansas City" --destination "Tokyo" --departure 2026-03-15 --return-date 2026-03-25 --adults 2

# Cheapest dates calendar
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py flight-calendar \
  --origin "Kansas City" --destination "Los Angeles"

# Car rentals (Turo)
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py cars \
  --latitude 38.7046 --longitude -90.3882 --start 2026-11-15T10:00 --end 2026-11-17T10:00

# Events (SeatGeek)
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py events \
  --query "concerts" --location "Kansas City"

# Travel advisories
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py advisories --country Japan
```

The script outputs JSON to stdout. Parse it and format a clean table for Jon.

## Overview
The `travel-planner` skill gives Allie full travel search, booking optimization, price monitoring, and expense tracking capabilities. It integrates with Jon's Chase Trifecta and Capital One Venture X portfolio for maximum points value.

### Architecture Diagram
```ascii
+-------------------+        +--------------------+       +----------------------+
|                   |        |                    |       |                      |
|  Telegram Inputs  +------->+  Travel Planner    +------>+ Notion Databases     |
| (Expense parsing, |        |       Skill        |       | - TRAVEL (Page)      |
|  Price Watches)   |        |                    |       |   - ✈️ Trips         |
|                   |        | - Module A: Points |       |   - 💸 Trip Expenses |
+-------------------+        | - Module B: Watch  |       +----------^-----------+
                              | - Module C: Track  |                  |
+-------------------+        | - Module D: Search |       +----------+-----------+
|                   |        |                    |       |                      |
| financial-planner +------->+                    +------>+ terminal             |
| (Card rewards,    |        +---------+----------+       |  travel_search.py    |
|  balances)        |                  |                  |  (stdlib HTTP)       |
+-------------------+                  |                  +----------+-----------+
                                       v                             |
                              +--------------------+       +---------v-----------+
                              |                    |       |                     |
                              | Cron Automations   |       | Firecrawl API       |
                              | - TR1 Price Watch  |       | (Alexandria)        |
                              +--------------------+       | - Booking.com       |
                                                           | - Google Flights    |
                                                           | - Skyscanner        |
                                                           | - Vrbo, Turo, etc.  |
                                                           +---------------------+
```

## Setup (One-Time)

### Create the TRAVEL Page
1. Create a new root page named **TRAVEL** as a sibling to FINANCE and Health & Fitness.

### Create the `✈️ Trips` Database
Create this inline database on the TRAVEL page:
| Property         | Type        | Details |
|------------------|-------------|---------|
| Trip Name        | Title       | E.g., "Japan 2026", "NYC Weekend" |
| Destination      | Rich Text   | City/Country names |
| Start Date       | Date        | Trip start |
| End Date         | Date        | Trip end |
| Status           | Select      | `Planning`, `Booked`, `Active`, `Completed`, `Cancelled` |
| Budget           | Number      | Format as Dollar |
| Actual Spend     | Rollup      | Sum of 'Amount' from Trip Expenses Relation |
| Budget Remaining | Formula     | `prop("Budget") - prop("Actual Spend")` |
| Points Used      | Number      | Total points/miles spent |
| Points Value     | Number      | Estimated cash value of points (Format as Dollar) |
| Cash Saved       | Number      | Format as Dollar (Total cash offset by points) |
| Payment Method   | Rich Text   | How it was booked/paid |
| Notes            | Rich Text   | Itineraries, flight info |

### Create the `💸 Trip Expenses` Database
Create this inline database on the TRAVEL page:
| Property         | Type        | Details |
|------------------|-------------|---------|
| Expense          | Title       | Description (e.g., "Dinner at Nobu") |
| Trip             | Relation    | Target: `✈️ Trips` |
| Category         | Select      | `Flight`, `Hotel`, `Rental Car`, `Food`, `Activities`, `Transportation`, `Shopping`, `Other` |
| Amount           | Number      | Format as Dollar |
| Payment Method   | Select      | `Chase Sapphire Reserve`, `Chase Freedom Flex`, `Chase Freedom Unlimited`, `Capital One Venture X`, `Cash`, `Other` |
| Date             | Date        | Date of transaction |
| Optimal Card     | Rich Text   | What should have been used based on rules |
| Notes            | Rich Text   | Additional details |

## Modules

### Module A: Points & Miles Optimizer
**Purpose**: Determine the best way to book travel using Jon's specific credit card setup (Chase Trifecta + Venture X).
**Data Sources**: `financial-planner/resources/chase_rewards.json`, `financial-planner/resources/credit_cards.json`, `resources/transfer_partners.json`, `resources/redemption_values.json`.

**Context**:
- **Chase Sapphire Reserve (CSR)**: 1.5¢/point via portal, 3x dining/travel/streaming, 10x via Chase Travel portal.
- **Chase Freedom Flex (CFF)**: 5x quarterly rotating categories.
- **Chase Freedom Unlimited (CFU)**: 1.5x everything.
- *Note*: All UR points pool into CSR for the 1.5¢ multiplier.
- **Capital One Venture X**: 2x everything, 1¢/mile via portal, transfer partners.

**Transfer Partner Sweet Spots**:
- Hyatt (UR 1:1): Best hotel value (Category 1-4 for 5K-15K/night).
- United (UR 1:1): Domestic economy (12.5K OW).
- Air Canada Aeroplan (UR/Venture 1:1): Star Alliance awards.
- Turkish Miles&Smiles (UR 1:1): United metal sweet spots.
- British Airways Avios (UR 1:1): Short-haul domestic.
- Air France/KLM Flying Blue (UR 1:1): Promo rewards.
- IHG/Marriott (UR 1:1): Niche stays (5th night free).

**Algorithm**:
```python
def optimize_redemption(flight_cash_price, reward_flight_points, hotel_cash_price, reward_hotel_points, transfer_partner):
    csr_portal_value_flight = flight_cash_price / 0.015
    venture_portal_value_flight = flight_cash_price / 0.01
    
    # Calculate Cents Per Point (CPP) for transfer partner
    transfer_cpp = (flight_cash_price / reward_flight_points) * 100
    
    recommendation = ""
    if transfer_cpp >= 2.0:
        recommendation = f"Transfer UR to {transfer_partner} (Value: {transfer_cpp:.2f} CPP). Excellent value."
    elif csr_portal_value_flight <= reward_flight_points:
        recommendation = "Book via Chase Portal using CSR (1.5 CPP guaranteed value)."
    else:
        points_earned_csr_portal = flight_cash_price * 10
        points_earned_venture_x = flight_cash_price * 5
        recommendation = f"Pay cash and EARN points. Best card: CSR via Portal (+{points_earned_csr_portal} UR) or Venture X via Portal (+{points_earned_venture_x} Miles)."
        
    return recommendation

def determine_best_card_for_cash(category, price, current_quarter_cff_categories):
    if category in current_quarter_cff_categories:
        return "Chase Freedom Flex (5x)"
    elif category in ["Dining", "Travel"]:
        return "Chase Sapphire Reserve (3x)"
    elif category == "Everything Else":
        return "Capital One Venture X (2x)"
    return "Chase Freedom Unlimited (1.5x)"
```

### Module B: Booking Price Watch
**Purpose**: Monitor flight and hotel prices and alert on significant drops.
**Data Sources**: `resources/price_watches.json`, `scripts/travel_search.py`.

**How to set a price watch**:
When Jon says "watch flights from MCI to LAX in December", add an entry to `resources/price_watches.json` with the baseline price.

**How to check prices**:
Use `terminal` to run the search script:
```bash
# Check flight prices for a watched route
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py flights \
  --origin "Kansas City" --destination "Los Angeles" --departure 2026-12-20 --return-date 2026-12-22

# Check flexible dates for cheapest windows
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py flight-calendar \
  --origin "Kansas City" --destination "Los Angeles"

# Check hotel prices for a watched destination
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py hotels \
  --destination "Hermann, Missouri" --checkin 2026-12-20 --checkout 2026-12-22
```

Parse the JSON output, compare against the baseline in `price_watches.json`, and alert via Telegram if price drop >= 10%.

### Module C: Trip Expense Tracker
**Purpose**: Parse quick Telegram logs from Jon during a trip and update the Notion DB in real-time, providing immediate budget feedback and checking for card optimization.
**Data Sources**: `Notion API (✈️ Trips, 💸 Trip Expenses)`.

**Algorithm**:
```python
import re

def parse_telegram_expense(message, active_trip_id, active_trip_budget, current_spend):
    match = re.search(r'\$([\d\.]+)\s+(.*?)(?:\s+on\s+(.*))?$', message, re.IGNORECASE)
    
    if match:
        amount = float(match.group(1))
        description = match.group(2).strip()
        card_used = match.group(3).strip().upper() if match.group(3) else "UNKNOWN"
        
        category = "Other"
        if "dinner" in description.lower() or "food" in description.lower():
            category = "Food"
        elif "hotel" in description.lower():
            category = "Hotel"
            
        optimal_card = determine_best_card_for_cash(category, amount, [])
        
        card_warning = ""
        if card_used != "UNKNOWN" and card_used not in optimal_card:
            card_warning = f"⚠️ You used {card_used}, but {optimal_card} would have been better for {category}."
            
        notion_api.create_expense(
            trip_id=active_trip_id,
            expense_name=description,
            amount=amount,
            category=category,
            payment_method=card_used,
            optimal_card=optimal_card
        )
        
        new_total = current_spend + amount
        remaining = active_trip_budget - new_total
        
        response = (f"✅ Logged ${amount:.2f} for {description}.\n"
                    f"Trip Total: ${new_total:.2f} (Remaining: ${remaining:.2f})\n"
                    f"{card_warning}")
        return response
```

### Module D: Live Travel Search (via travel_search.py)
**Purpose**: Search real-time travel data across 20+ providers. This is the core capability that makes Allie a real travel assistant.

**How it works**:
All searches go through `scripts/travel_search.py` — a Python CLI script run via `terminal`. The script calls the Firecrawl Alexandria API directly (no MCP needed) and outputs structured JSON.

#### D1: Accommodation Search
**When Jon asks**: "find hotels in [place]", "search B&Bs in [place]", "vacation rentals in [place]", "where to stay in [place]"

**Action**: Run via terminal:
```bash
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py hotels \
  --destination "Hermann, Missouri" --checkin 2026-11-15 --checkout 2026-11-17 --adults 2
```

**The script automatically**:
1. Resolves the destination on Booking.com AND Vrbo
2. Searches both providers with prices
3. Returns combined results sorted by price

**Format the JSON output as**:
```
| # | Property | Source | Price/Night | Rating | Type | Key Features |
|---|----------|--------|-------------|--------|------|--------------|
| 1 | ...      | Booking| $150        | 9.2    | B&B  | Breakfast, WiFi |
| 2 | ...      | Vrbo   | $180        | 4.8/5  | Cabin| Kitchen, Hot tub |
```

**Add points recommendation**: "At $150/night ($300 total), book via Chase Portal with CSR to earn 3,000 UR points (3x travel). Or transfer 20K Hyatt points if available at a Hyatt property (>2.0 CPP value)."

#### D2: Flight Search
**When Jon asks**: "find flights to [place]", "how much to fly to [place]", "cheapest flights"

**Action**: Run via terminal:
```bash
# Specific dates
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py flights \
  --origin "Kansas City" --destination "Los Angeles" --departure 2026-12-20 --return-date 2026-12-27 --adults 2

# Flexible dates — find cheap travel windows
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py flight-calendar \
  --origin "Kansas City" --destination "Los Angeles"
```

Jon's home airport is **MCI** (Kansas City International). The script handles airport resolution automatically.

**Format the JSON output as**:
```
| # | Route | Airline | Stops | Duration | Price | Source |
|---|-------|---------|-------|----------|-------|--------|
| 1 | MCI→LAX | Delta | Nonstop | 3h50m | $204 | Google |
| 2 | MCI→LAX | United | Nonstop | 3h45m | $220 | Skyscanner |
```

**Add points recommendation**: Check if transfer partners offer better value. Example: "$204 cash price = 13,600 UR via Chase Portal (1.5 CPP). Turkish Miles&Smiles charges 7,500 miles for domestic UA flights — transfer 7,500 UR for 2.72 CPP. Excellent value!"

#### D3: Car Rental Search
**When Jon asks**: "rent a car in [place]", "car rental [place]"

**Action**: Get coordinates for the destination (use web_search if needed), then:
```bash
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py cars \
  --latitude 38.7046 --longitude -90.3882 --start 2026-11-15T10:00 --end 2026-11-17T10:00
```

Recommend payment card: Venture X for 2x on everything, or CSR for 3x if booked through Chase Travel.

#### D4: Events & Activities Search
**When Jon asks**: "things to do in [place]", "events in [place]", "concerts near [place]"

**Action**:
```bash
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py events \
  --query "concerts" --location "Kansas City"
```

#### D5: Travel Advisories
**When Jon asks about international travel**: Check advisories before booking.

**Action**:
```bash
python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py advisories --country Japan
```

#### D6: Fallback — web_search + web_extract
**If travel_search.py fails** (e.g., Firecrawl API error, Alexandria unavailable), fall back to:
1. `web_search` with domain-restricted queries: `"hotels in Hermann Missouri" site:booking.com`
2. `web_extract` on the resulting URLs to scrape pricing info
3. Present whatever you find — partial results are better than a wall of text about limitations

## Cron Automations

### 1. TR1 — Price Watch Check
- **Schedule**: Daily at 6:00 AM CT
- **Model**: Gemini 3 Flash
- **Condition**: Only runs if `resources/price_watches.json` contains active entries.
- **Action**: For each active watch, run the search script via terminal. Compare against baseline and alert if drop >= 10%.
- **Command**: `python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py flights --origin "Kansas City" --destination "<watched_dest>" --departure <date>`
- **Message format**: Telegram alert with price comparison and direct booking links.

## Resource Files

| File | Purpose |
|------|---------|
| `transfer_partners.json` | Chase UR and Venture transfer partners with sweet spots and ratios. |
| `redemption_values.json` | Target CPP thresholds and decision matrices for points vs cash. |
| `price_watches.json` | Active array of flight/hotel routes to monitor. |
| `provider_reference.json` | Complete catalog of Alexandria travel providers and their capabilities. |

## Scripts

| File | Purpose |
|------|---------|
| `scripts/travel_search.py` | CLI tool for real-time travel search via Firecrawl Alexandria API. Run via `terminal`. Uses only Python stdlib (no pip dependencies). Requires `FIRECRAWL_API_KEY` env var. |

## Integration
- **READ**: `financial-planner/resources/chase_rewards.json`, `financial-planner/resources/credit_cards.json`.
- **WRITE**: `resources/price_watches.json`.
- **NOTION**: Full read/write access to `✈️ Trips` and `💸 Trip Expenses`.
- **FIRECRAWL API**: Via `scripts/travel_search.py` (called from `terminal`). Requires `FIRECRAWL_API_KEY` in environment.

## Quick Reference: Script Commands

| Task | Command |
|------|---------|
| Search hotels/B&Bs | `python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py hotels --destination "..." --checkin YYYY-MM-DD --checkout YYYY-MM-DD` |
| Search flights (specific dates) | `python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py flights --origin "..." --destination "..." --departure YYYY-MM-DD --return-date YYYY-MM-DD` |
| Find cheapest flight dates | `python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py flight-calendar --origin "..." --destination "..."` |
| Search car rentals | `python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py cars --latitude X --longitude Y --start ISO_DATETIME --end ISO_DATETIME` |
| Search events | `python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py events --query "..." --location "..."` |
| Travel advisories | `python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py advisories --country "..."` |

## Data Collection Checklist
- [ ] Connect Notion Workspace and ensure correct permissions for new TRAVEL page.
- [ ] Ensure `financial-planner` card balances and current rotating categories are up to date.
- [ ] Ask Jon for any upcoming trips to populate the first entries in the database.
- [ ] Verify `FIRECRAWL_API_KEY` is set in the environment (already configured in Hermes systemd service).
- [ ] Test the search script: `python3 ~/.hermes/skills/travel-planner/scripts/travel_search.py hotels --destination "Kansas City" --checkin 2026-11-01 --checkout 2026-11-02`

