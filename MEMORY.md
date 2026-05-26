# Memory

## Technical Stack
- **Personal Assistant Platform**: OpenClaw (agent running on a virtual machine)
- **Agent Name**: Abbie
- **LLM Router**: Abacus RouteLLM
- **Primary Goals**:
  - Optimize token usage efficiency.
  - Establish a robust and clean memory structure.
  - Enhance overall utility, skills, and connections.

## Architecture Decisions

### 2026-05-26: Model Routing Strategy
- **Decision**: Adopt tiered model routing (Option A variant)
- **Default**: Kimi K2.6 ($0.95/$4, 262K context) for daily driver
- **Mid-tier**: Sonnet 4.6 or DeepSeek V4 Flash for research/writing
- **Heavy**: Opus 4.6 for deep reasoning only
- **Ultra-cheap**: Gemini 3 Flash for heartbeats and simple crons
- **Killed**: Gemma 4 31B — too weak for agentic tool-calling workflows
- **Rationale**: Bootstrap context alone (~55K tokens) costs ~$0.82/msg on Opus. 23 cron runs/week were on Opus. Heartbeats 4x/day on Opus = ~$23/week wasted.

### Infrastructure Notes
- Abbie runs ~23 cron jobs/week (briefings, logs, plant reminders, financial)
- Heartbeats run every 6 hours
- Antigravity (this agent) runs on-demand via Gemini/Claude, independent billing

### 2026-05-26: Financial Automation System
- **Decision**: Build Notion-based personal finance automation
- **Databases**: 4 linked DBs under existing FINANCE page (Accounts, Budgets, Transactions, Statements)
- **PDF Processing**: pdfplumber + LLM categorization for Chase (credit + checking) and US Bank statements
- **Cron Jobs**: 7 new financial crons (scorecard, dining tripwire, subscription audit, bill-pay, EF tracker, bar mitzvah tracker, statement processor)
- **Skill Location**: `.agents/skills/financial-automation/`
- **Merchant Cache**: Self-learning JSON mapping, pre-seeded with 60+ known merchants

### Household Financial Profile
- **Jon**: $2,860 biweekly (every other Friday), 26 paychecks/yr = ~$74,360/yr
- **Wife**: $1,800 semi-monthly (1st & 15th), 24 paychecks/yr = $43,200/yr
- **Combined monthly base**: $9,320
- **Banks**: Chase (Flex credit card, checking), US Bank (checking/savings)
- **Monthly margin at targets**: $2,096
- **Bar mitzvah**: $6,141 balance, deferred to July 2026
- **ER payment plan**: $150/mo from savings

## Long-Term User Preferences
- Jon approves **auto-escalation** — Abbie can switch models without asking when task complexity warrants it
- Prefers explicit approval gates for side-effect actions (not model switching)
- No native token telemetry from Abacus — Jon checks manually; Abbie should log estimated costs per session
- Heartbeats: 3x/day (08:00, 14:00, 22:00 CT) on cheapest available model
- Weekly synthesis and financial crons should run on mid-tier (Sonnet/DeepSeek), not default
