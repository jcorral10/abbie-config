---
name: life-score
description: >
  Composite Life Score (0–100) that unifies all domain health scores into a single household wellness metric. Reads Financial Health Score from financial-planner, Composite Health Score from health-planner, and self-calculates a Growth Score. Business and Career scores are placeholder-ready for future skills. Provides monthly trend tracking and identifies the highest-impact area to focus on.
requires:
  bins: [python3]
  env: [NOTION_API_KEY]
---

# Life Score (life-score)

## Overview

The `life-score` skill serves as Allie's executive summary module, computing a Composite Life Score (0–100). It reads key metrics from active domain-specific skills and unifies them into a single holistic wellness indicator for the household. It self-calculates a Growth Score and provides placeholders for Business and Career scores. Monthly trends are tracked, and actionable recommendations are generated based on the highest-impact areas for improvement.

### Architecture

```ascii
                      +-------------------+
                      |   life-score      |
                      |   (Meta-Skill)    |
                      +---------+---------+
                                |
        +-----------------------+-----------------------+
        |                       |                       |
+-------v-------+       +-------v-------+       +-------v-------+
|  financial-   |       |    health-    |       |   Self-Calc   |
|   planner     |       |    planner    |       |   (Growth)    |
+---------------+       +---------------+       +---------------+
| Net Worth     |       | Health        |       | Books, Skills,|
| Snapshots DB  |       | Snapshots DB  |       | Courses       |
+---------------+       +---------------+       +---------------+
```

---

## Setup (One-Time)

### 1. Create DASHBOARD Page
Create a new Notion page named **DASHBOARD** at the root level alongside FINANCE and Health & Fitness. This will host high-level metrics.

### 2. Create Notion Database: `📊 Life Snapshots`
Create this inline database under the DASHBOARD page.

| Property | Type | Details |
| :--- | :--- | :--- |
| `Month` | Title | Format: YYYY-MM |
| `Life Score` | Number | 0-100 format |
| `Financial Score` | Number | 0-100 format |
| `Health Score` | Number | 0-100 format |
| `Business Score` | Number | 0-100 format |
| `Career Score` | Number | 0-100 format |
| `Growth Score` | Number | 0-100 format |
| `MoM Change` | Number | Signed number showing change from previous month |
| `Trend` | Select | Options: `Rising`, `Stable`, `Declining` |
| `Top Win` | Rich Text | Best performing or most improved domain |
| `Top Focus` | Rich Text | Lowest scoring / highest potential impact area |
| `Notes` | Rich Text | AI-generated summary or user comments |

---

## Modules

### Module A: Score Normalization and Weighting

**Purpose**: Compute the weighted Composite Life Score, handling inactive domains gracefully by redistributing weights.

**Data Sources**:
- `financial-planner`: Financial Health Score from Net Worth Snapshots DB.
- `health-planner`: Composite Health Score from Health Snapshots DB.
- Module B: Calculated Growth Score.

**Target Weights**:
- Financial: 0.25
- Health: 0.25
- Business: 0.20 (Placeholder, initially 0)
- Career: 0.15 (Placeholder, initially fixed at 50)
- Growth: 0.15

**Algorithm**:
```python
def calculate_composite_score(scores, active_domains):
    target_weights = {
        'financial': 0.25,
        'health': 0.25,
        'business': 0.20,
        'career': 0.15,
        'growth': 0.15
    }
    
    # Calculate total weight of active domains
    total_active_weight = sum(target_weights[domain] for domain in active_domains)
    
    # Redistribute weights proportionally
    actual_weights = {
        domain: (target_weights[domain] / total_active_weight)
        for domain in active_domains
    }
    
    composite_score = 0
    for domain in active_domains:
        composite_score += scores[domain] * actual_weights[domain]
        
    return composite_score, actual_weights
```

**Output**: A finalized Composite Life Score (0-100).

### Module B: Growth Score Calculation

**Purpose**: Calculate the domain score for personal growth and learning based on trackable inputs.

**Data Sources**: Self-reported data or tracked habits for reading, courses, and skills.

**Algorithm**:
```python
def calculate_growth_score(books_read, active_courses, skill_sessions, reflection_done):
    # Book component (max 100)
    book_score = min(100, books_read * 33.33)
    
    # Course component (max 100)
    course_score = min(100, active_courses * 50)
    
    # Skill component (max 100)
    skill_score = min(100, skill_sessions * 20)
    
    # Reflection component
    reflection_score = 100 if reflection_done else 0
    
    # Simple average if all metrics are tracked
    # Defaults to 50 if no data is provided
    if all(x == 0 for x in [books_read, active_courses, skill_sessions]) and not reflection_done:
        return 50
        
    return (book_score + course_score + skill_score + reflection_score) / 4
```

**Output**: A Growth Score (0-100).

### Module C: Trend & Action Engine

**Purpose**: Analyze the 3-month rolling trend and determine actionable recommendations based on weight and score differentials.

**Algorithm**:
```python
def analyze_trend_and_focus(history, current_scores, weights):
    # Trend Analysis
    if len(history) >= 2:
        diffs = [history[i] - history[i-1] for i in range(1, len(history))]
        diffs.append(current_scores['composite'] - history[-1])
        
        if all(d >= 0 for d in diffs[-3:]):
            trend = "Rising"
        elif all(d <= 0 for d in diffs[-3:]):
            trend = "Declining"
        else:
            trend = "Stable"
    else:
        trend = "Stable"

    # Focus Area Analysis (Lowest Score * Highest Weight = Biggest Impact)
    improvement_potentials = {
        domain: (100 - current_scores[domain]) * weights[domain]
        for domain in current_scores if domain != 'composite'
    }
    top_focus = max(improvement_potentials, key=improvement_potentials.get)
    
    return trend, top_focus
```

---

## Cron Automations

### 1. LS1: Monthly Life Score Report
- **Schedule**: 3rd of the month at 9:00 PM CT (Ensures financial and health scores have updated on the 1st and 2nd).
- **Model**: DeepSeek V4 Flash
- **Action**: 
  1. Retrieve latest Financial Health Score and Composite Health Score.
  2. Compute Growth Score.
  3. Calculate the Composite Life Score with active weights (e.g., Financial: 0.385, Health: 0.385, Growth: 0.230).
  4. Determine 3-month trend, highest contribution (Top Win), and lowest weighted score (Top Focus).
  5. Check milestone alerts.
  6. Create a row in `📊 Life Snapshots`.
  7. Send Telegram report.
- **Message Format (Telegram)**:
  ```
  📊 Monthly Life Score: {YYYY-MM}
  
  🏆 Composite Score: {score} ({emoji}) | MoM: {change}
  📈 Trend: {trend}
  
  Domain Breakdown:
  • 💰 Financial: {fin_score} (Weight: {fin_weight}%)
  • 🏃‍♂️ Health: {health_score} (Weight: {health_weight}%)
  • 🌱 Growth: {growth_score} (Weight: {growth_weight}%)
  
  🌟 Top Win: {top_win_domain} driving positive impact.
  🎯 Top Focus: {top_focus_domain} presents the highest improvement potential.
  
  💡 Recommendation: {actionable_advice_based_on_focus}
  ```

---

## Interpretation Guidelines

| Range | Rating | Emoji |
|-------|--------|-------|
| 90-100 | Thriving | 🏆 |
| 75-89 | Strong | ✅ |
| 60-74 | Building | ⚠️ |
| 40-59 | Needs Attention | 🔶 |
| 0-39 | Critical | 🚨 |

---

## Milestone Alerts

The engine monitors for the following events and issues specific alerts when triggered:
- **First 80+**: "🎉 Milestone unlocked! Life Score crossed 80 for the first time."
- **Momentum**: "🔥 Momentum! Life Score has increased for 3 consecutive months."
- **Breakthrough**: "🚀 Breakthrough! {Domain} crossed from below 50 to above 70."
- **Intervention**: "🚨 Warning: Life Score has dropped below 50. Initiating strategic review."

---

## Resource Files

| File | Purpose |
| :--- | :--- |
| `prompts/monthly_report.txt` | Prompt for formatting the Monthly Life Score report and actionable advice. |
| `config.json` | Configuration mapping weights, milestones, and Notion DB IDs. |

---

## Integration

| Domain/Skill | READ | WRITE |
| :--- | :--- | :--- |
| `financial-planner` | `Net Worth Snapshots` (Financial Health Score) | None |
| `health-planner` | `Health Snapshots` (Composite Health Score) | None |
| `life-score` | Self (DASHBOARD metrics) | `📊 Life Snapshots` |

---

## Data Collection Checklist

To ensure accurate Growth Score and Life Score calculations, please provide:
1. [ ] Number of books read this month.
2. [ ] Number of active courses.
3. [ ] Number of skill practice sessions completed.
4. [ ] Confirmation if weekly reflections were done.
5. [ ] Links to DASHBOARD and `📊 Life Snapshots` Notion pages once created.
