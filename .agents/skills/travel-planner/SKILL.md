---
name: travel-planner
description: >
  Budget-aware travel planning with Chase Trifecta and Capital One Venture X points optimization, flight/hotel price monitoring via web scraping, and real-time trip expense tracking via Telegram quick-log. Reads card portfolio data from financial-planner.
requires:
  bins: [python3]
  env: [NOTION_API_KEY]
---

# Travel Planner

## Overview
The `travel-planner` skill enables Allie to assist Jon with comprehensive travel planning, points optimization, flight/hotel price monitoring, and real-time expense tracking. It integrates deeply with Jon's Chase Trifecta and Capital One Venture X portfolio to ensure maximum value extraction from credit card points.

### Architecture Diagram
```ascii
+-------------------+        +--------------------+       +----------------------+
|                   |        |                    |       |                      |
|  Telegram Inputs  +------->+  Travel Planner    +------>+ Notion Databases     |
| (Expense parsing, |        |       Skill        |       | - TRAVEL (Page)      |
|  Price Watches)   |        |                    |       |   - ✈️ Trips         |
|                   |        | - Points Optimizer |       |   - 💸 Trip Expenses |
+-------------------+        | - Price Watch      |       +----------^-----------+
                             | - Expense Tracker  |                  |
+-------------------+        |                    |                  |
|                   |        |                    |       +----------+-----------+
| financial-planner +------->+                    +------>+ External Resources   |
| (Card rewards,    |        +---------+----------+       | - Firecrawl (MCP)    |
|  balances)        |                  |                  | - Transfer Partners  |
+-------------------+                  |                  +----------------------+
                                       v
                             +--------------------+
                             |                    |
                             | Cron Automations   |
                             | - TR1 Price Watch  |
                             |                    |
                             +--------------------+
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
        # Cash vs points earning analysis
        points_earned_csr_portal = flight_cash_price * 10 # 10x on CSR via portal
        points_earned_venture_x = flight_cash_price * 5 # 5x on flights via Cap1
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
**Purpose**: Monitor flight and hotel prices via Firecrawl (or SerpAPI) and alert on significant drops.
**Data Sources**: `resources/price_watches.json`, Firecrawl MCP.

**Algorithm**:
```python
import json

def check_price_watches():
    with open('resources/price_watches.json', 'r') as f:
        watches = json.load(f)
        
    alerts = []
    for watch in watches:
        # Pseudo-code for web scraping / API call
        current_price = firecrawl_search_flight(watch['origin'], watch['destination'], watch['dates'])
        
        drop_percentage = ((watch['initial_price'] - current_price) / watch['initial_price']) * 100
        
        if drop_percentage >= 10.0:
            alerts.append(f"🚨 PRICE DROP ALERT 🚨\n{watch['origin']} to {watch['destination']}\n"
                          f"Was: ${watch['initial_price']} | Now: ${current_price}\n"
                          f"Drop: {drop_percentage:.1f}%!")
                          
        # Update current price in DB
        watch['current_price'] = current_price
        
    with open('resources/price_watches.json', 'w') as f:
        json.dump(watches, f)
        
    return alerts
```

### Module C: Trip Expense Tracker
**Purpose**: Parse quick Telegram logs from Jon during a trip and update the Notion DB in real-time, providing immediate budget feedback and checking for card optimization.
**Data Sources**: `Notion API (✈️ Trips, 💸 Trip Expenses)`.

**Algorithm**:
```python
import re

def parse_telegram_expense(message, active_trip_id, active_trip_budget, current_spend):
    # Match pattern like "$45 dinner on CSR"
    match = re.search(r'\$([\d\.]+)\s+(.*?)(?:\s+on\s+(.*))?$', message, re.IGNORECASE)
    
    if match:
        amount = float(match.group(1))
        description = match.group(2).strip()
        card_used = match.group(3).strip().upper() if match.group(3) else "UNKNOWN"
        
        # Categorization logic
        category = "Other"
        if "dinner" in description.lower() or "food" in description.lower():
            category = "Food"
        elif "hotel" in description.lower():
            category = "Hotel"
            
        optimal_card = determine_best_card_for_cash(category, amount, []) # Simplified
        
        card_warning = ""
        if card_used != "UNKNOWN" and card_used not in optimal_card:
            card_warning = f"⚠️ You used {card_used}, but {optimal_card} would have been better for {category}."
            
        # Add to Notion DB
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

## Cron Automations

### 1. TR1 — Price Watch Check
- **Schedule**: Daily at 6:00 AM CT
- **Model**: Gemini 3 Flash
- **Condition**: Only runs if `resources/price_watches.json` contains active entries.
- **Action**: Executes Module B price checking script via Firecrawl.
- **Message format**: Telegram alert sent if price drop >= 10%. Includes direct booking links if available.

## Resource Files

| File | Purpose |
|------|---------|
| `transfer_partners.json` | Comprehensive list of Chase UR and Venture transfer partners with sweet spots and ratios. |
| `redemption_values.json` | Target CPP thresholds and decision matrices for points vs cash. |
| `price_watches.json` | Active array of flight/hotel routes to monitor. |

## Integration
- **READ**: `financial-planner/resources/chase_rewards.json`, `financial-planner/resources/credit_cards.json`.
- **WRITE**: `resources/price_watches.json`.
- **NOTION**: Full read/write access to `✈️ Trips` and `💸 Trip Expenses`.

## Data Collection Checklist
- [ ] Connect Notion Workspace and ensure correct permissions for new TRAVEL page.
- [ ] Ensure `financial-planner` card balances and current rotating categories are up to date.
- [ ] Ask Jon for any upcoming trips to populate the first entries in the database.
