---
name: portfolio-manager
description: >
  Manages Jon Corral's static portfolio website (joncorral.com) via Telegram
  natural language commands. Handles content updates, style changes, case study
  creation, resume updates, image management, and GitHub Pages deployment with
  approval gates. Consults work-bot for professional context. Future expansion
  to Etsy storefront and landing pages.
requires:
  bins: [git, python3]
  env: [GITHUB_TOKEN]
---

# Portfolio Manager

## Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                    PORTFOLIO UPDATE PIPELINE                          │
│                                                                        │
│  Telegram NL ──▶ Parse ──▶ Edit Files ──▶ Diff ──▶ Approval ──▶ Deploy │
│                                                                        │
│  Modules:                                   Cross-Bot:                 │
│  A. Content Updates                         H. work-bot consultation   │
│  B. Style Changes                              (projects, skills,      │
│  C. Page Management                             achievements)          │
│  D. Resume Updates                                                     │
│  E. Image Management                        Future:                    │
│  F. Preview & Approval Gate                 I. Etsy storefront pages   │
│  G. Rollback                                                           │
└────────────────────────────────────────────────────────────────────────┘
```

### Dependencies
- `resources/site_map.json` — NL label → file path + CSS selector mapping
- `resources/brand_guide.json` — design tokens, fonts, colors, voice rules

---

## Workspace Context

| Key | Value |
|-----|-------|
| **Path** | `~/workspaces/portfolio/` |
| **Repo** | `jcorral10/joncorral-portfolio` |
| **Branch** | `main` |
| **Deploy** | `git push origin main` → GitHub Pages auto-deploys (~60s) |
| **Tech** | Static HTML/CSS/JS — no framework, no build step |
| **Domain** | `joncorral.com` (CNAME file — **never modify**) |

---

## Site Architecture Reference

```
joncorral-portfolio/
├── index.html          ← Main page (all sections below)
├── index.css           ← All styles (29KB, CSS custom properties at :root)
├── index.js            ← Interactions (nav, scroll, cursor, marquee, reveals)
├── resume.html         ← Standalone resume page
├── CNAME               ← Domain config (DO NOT TOUCH)
├── assets/
│   ├── favicon.svg
│   └── images/         ← headshot.jpg, headshot.png, headshot-raw.png,
│                         hero-bg.png, wabi-accent.png, ai-section-bg.png,
│                         work-social.png, work-email.png, work-product.png,
│                         work-ai.png
└── work/
    ├── work.css        ← Shared work page styles
    ├── social.html     ← Social & Digital (TEMPLATE for new pages)
    ├── email.html      ← Email & CRM
    ├── digital.html    ← Digital & Interactive
    ├── print.html      ← Print & Collateral
    ├── direct-mail.html
    ├── radio.html      ← Radio & Broadcast
    └── video.html      ← Video & Motion
```

### Section IDs (index.html)

| Section ID | Content | Key Elements |
|------------|---------|--------------|
| `#hero` | Hero section | `.hero__greeting` (subtitle), `.hero__title` (h1 tagline), `.hero__subtitle` (description), `.hero__actions` (CTA buttons), `.hero__portrait` (headshot) |
| `#about` | About section | `.section-title` (h2), 3x `<p>` in `.about__prose`, `.about__stats` sidebar (4 stat blocks: years, campaigns, AI systems, industries) |
| `#work` | Work/Services grid | 10 service cards `.service` numbered 01–10, cards 01–02 and 05–09 linked to `/work/*.html`, cards 03–04 and 10 are `.service--muted` |
| `#ai-edge` | AI capabilities | 4x `.ai-cap` cards (Knowledge Bases, Prompt Templates, Automated QA, Workflow Integration), `.ai-edge__quote` philosophy block |
| (marquee) | Skills ticker | `.marquee__item` spans (Brand Voice, NotebookLM, Prompt Engineering, Social Campaigns, Email Strategy, Product Copy, Obsidian, SEO, Content Strategy, Regulatory Compliance, Editorial, CRM, Gemini, Google Docs) |
| `#contact` | Contact section | `.contact__title` (h2), `.contact__desc`, email + LinkedIn buttons |
| (footer) | Footer | `.footer__copy` (© year), `.footer__note` (tagline) |

### CSS Design Tokens (:root in index.css)

```css
/* Wabi-sabi palette */
--ink: #1A1A1A;          --ink-soft: #3D3D3D;
--ink-muted: #6B6B6B;    --ink-whisper: #767676;
--paper: #FAF8F5;        --paper-warm: #F5F0EA;     --paper-dark: #EDE8E0;
--vermillion: #C84032;   --vermillion-soft: rgba(200, 64, 50, 0.08);
--indigo: #2C4A6E;       --indigo-soft: rgba(44, 74, 110, 0.06);

/* Typography */
--font-serif: 'Cormorant Garamond', 'Georgia', serif;   /* headings */
--font-sans: 'Inter', system-ui, -apple-system, sans-serif;  /* body */

/* Scale (clamp-based responsive) */
--text-xs: 0.75rem  ...  --text-5xl: clamp(3rem, 1.5rem + 7.5vw, 6.5rem)
--space-xs: 0.25rem  ...  --space-section: clamp(6rem, 5rem + 6vw, 12rem)
--max-width: 1100px;     --max-width-narrow: 720px;
```

### Brand Voice Rules

| Rule | Value |
|------|-------|
| **Tagline** | "Let's write something worth reading." |
| **Philosophy** | "Craft first. Always." |
| **AI stance** | AI sharpens the craft but doesn't replace the writer |
| **Tone** | Warm, professional, intentional, not salesy |
| **Design** | Wabi-sabi — warm, organic, restrained, breathing room |

---

## Module A: Content Updates

**Purpose**: Parse NL request → identify target file + element → edit HTML text → stage for approval.

**Targets**: hero tagline, hero subtitle, about paragraphs, stats numbers/labels, work card descriptions, AI capability descriptions, contact text, footer text, marquee items, SEO meta tags.

**Algorithm**:

```python
import os, json
from bs4 import BeautifulSoup

WORKSPACE = os.path.expanduser("~/workspaces/portfolio/")
SITE_MAP = json.load(open("resources/site_map.json"))

def update_content(nl_command: str):
    """
    NL → element resolution → HTML edit → git commit (no push yet).
    """
    # 1. Resolve NL command to target element via site_map
    #    LLM matches intent keywords to site_map keys
    #    e.g. "update the tagline" → SITE_MAP["hero_tagline"]
    target = resolve_target_from_nl(nl_command, SITE_MAP)
    # target = {"file": "index.html", "selector": ".hero__title", "type": "html"}

    # 2. Read the file
    file_path = os.path.join(WORKSPACE, target["file"])
    with open(file_path, "r") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # 3. Find the element
    element = soup.select_one(target["selector"])
    old_text = element.get_text(strip=True)

    # 4. Generate new content from NL command
    #    For "type": "html" → preserve inner HTML structure (e.g. <br>, <em>)
    #    For "type": "text" → plain text replacement
    new_content = extract_new_content_from_command(nl_command, old_text)

    # 5. Apply the edit
    if target["type"] == "html":
        element.clear()
        element.append(BeautifulSoup(new_content, "html.parser"))
    else:
        element.string = new_content

    # 6. Write back
    with open(file_path, "w") as f:
        f.write(str(soup))

    # 7. Stage commit (do NOT push — Module F handles approval)
    git_commit(f"content: update {target['selector']}")
```

**NL Mapping Examples**:
- "update the tagline" → `hero_tagline` → `.hero__title`
- "change my bio" → `about_prose_*` → `.about__prose p`
- "update the stats to 12 years" → `about_stat_years` → `.stat__number` (first)
- "add Figma to my skills ticker" → `marquee_items` → add `.marquee__item` span
- "update SEO description" → `seo_description` → `meta[name="description"]`

---

## Module B: Style Changes

**Purpose**: Interpret visual requests → map to CSS custom properties → edit `index.css` → stage for approval.

**Safety Rules**:
- ONLY modify CSS custom property **values** in `:root {}` unless Jon explicitly asks for structural CSS changes
- NEVER delete existing CSS rules
- ALWAYS preserve the wabi-sabi design language unless Jon explicitly asks to change it
- Reference `resources/brand_guide.json` for valid token names

**Algorithm**:

```python
import re

def update_styles(nl_command: str):
    """
    NL → CSS variable mapping → value replacement → git commit.
    """
    css_path = os.path.join(WORKSPACE, "index.css")
    with open(css_path, "r") as f:
        css_content = f.read()

    # Map NL to CSS variables
    # "make it darker" → --paper: darker value, --paper-warm: darker, etc.
    # "change accent to blue" → --vermillion: new blue, --vermillion-soft: rgba variant
    changes = map_nl_to_css_vars(nl_command, BRAND_GUIDE["design_tokens"])

    for var_name, new_value in changes.items():
        # Replace the value in :root block
        pattern = rf"({re.escape(var_name)}:\s*)[^;]+"
        css_content = re.sub(pattern, rf"\g<1>{new_value}", css_content, count=1)

    with open(css_path, "w") as f:
        f.write(css_content)

    git_commit(f"style: update {', '.join(changes.keys())}")
```

---

## Module C: Page Management

**Purpose**: Create, edit, or remove work case study pages.

**New Page Workflow**:

```python
import shutil

def create_work_page(nl_command: str):
    """
    1. Copy social.html as template → work/<slug>.html
    2. Update content (title, category, description, SEO meta)
    3. Add service card to #work grid in index.html
    4. Commit changes
    """
    slug = generate_slug(nl_command)  # e.g. "hills-seo"
    template = os.path.join(WORKSPACE, "work/social.html")
    new_page = os.path.join(WORKSPACE, f"work/{slug}.html")

    # 1. Copy template
    shutil.copy2(template, new_page)

    # 2. Edit new page content
    with open(new_page, "r") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Update: title, meta description, og tags, .work-hero__category,
    #         .work-hero__title, .work-hero__desc
    # Remove template-specific content (social media account links, etc.)
    details = extract_case_study_details(nl_command)
    apply_case_study_content(soup, details)

    with open(new_page, "w") as f:
        f.write(str(soup))

    # 3. Add card to index.html work grid
    add_work_card_to_index(slug, details)

    git_commit(f"pages: add {slug} case study")
```

**Work Card Template** (injected into index.html `#work .services__grid`):
```html
<a href="work/{slug}.html" class="service service--linked reveal" id="work-card-{slug}">
  <p class="service__number">{next_number}</p>
  <h3 class="service__title">{title}</h3>
  <p class="service__desc">{description}</p>
  <span class="service__link">View work →</span>
</a>
```

---

## Module D: Resume Updates

**Purpose**: Edit `resume.html` with new experience, skills, or certifications.

```python
def update_resume(nl_command: str):
    """
    Parse NL command for resume changes.
    Consult work-bot if needed for current project details.
    Edit resume.html preserving existing structure.
    """
    resume_path = os.path.join(WORKSPACE, "resume.html")

    # Optionally consult work-bot for latest professional context
    if needs_professional_context(nl_command):
        context = consult_work_bot(
            "What are Jon's current projects, skills, job title, "
            "and professional achievements for his resume?"
        )
        nl_command = f"{nl_command}\nProfessional context: {context}"

    with open(resume_path, "r") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    apply_resume_changes(soup, nl_command)

    with open(resume_path, "w") as f:
        f.write(str(soup))

    git_commit("resume: update content")
```

---

## Module E: Image Management

**Purpose**: Accept images from Telegram uploads or Notion → optimize → place in `assets/images/` → update HTML references.

**Image Sources**:
1. **Telegram**: Hermes saves uploaded images to `~/downloads/` with original filename
2. **Notion**: Download from Notion page attachment via API

```python
from PIL import Image

MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
MAX_DIMENSION = 1920

def process_image(source_path: str, target_name: str, usage_context: str):
    """
    1. Copy/download image to workspace
    2. Optimize if > 2MB (resize, compress)
    3. Save to assets/images/
    4. Update HTML src references if usage_context specifies where
    """
    target_path = os.path.join(WORKSPACE, f"assets/images/{target_name}")

    img = Image.open(source_path)

    # Resize if too large
    if os.path.getsize(source_path) > MAX_SIZE_BYTES:
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    # Save optimized
    if target_name.endswith(".jpg") or target_name.endswith(".jpeg"):
        img.save(target_path, "JPEG", quality=85, optimize=True)
    else:
        img.save(target_path, optimize=True)

    # Update HTML references if context tells us where to use it
    if usage_context:
        update_image_reference(usage_context, f"assets/images/{target_name}")

    git_commit(f"images: add {target_name}")
```

---

## Module F: Preview & Approval Gate

**Purpose**: NEVER auto-deploy. Always show diff and wait for Jon's approval.

**Protocol**:

```python
def request_approval_and_deploy():
    """
    1. Generate human-readable diff summary
    2. Send to Jon via Telegram
    3. Wait for explicit approval
    4. Push to deploy (or discard)
    5. Confirm live status
    """
    # 1. Generate diff
    diff_output = subprocess.check_output(
        ["git", "diff", "--stat", "HEAD~1"],
        cwd=WORKSPACE, text=True
    )
    changed_files = parse_changed_files(diff_output)
    summary = generate_human_readable_summary(diff_output)

    # 2. Send approval request
    send_telegram_message(
        f"📝 **Portfolio Update Ready**\n\n"
        f"{summary}\n\n"
        f"**Files changed:** {', '.join(changed_files)}\n\n"
        f"Reply **approve** to deploy, or **discard** to cancel."
    )

    # 3. Wait for response
    response = wait_for_telegram_reply()

    if response.lower() in ["yes", "approve", "go", "ship it", "deploy", "lgtm"]:
        # 4. Push
        subprocess.run(["git", "push", "origin", "main"], cwd=WORKSPACE, check=True)

        # 5. Wait for GitHub Pages deploy + confirm
        import time; time.sleep(60)
        send_telegram_message("✅ Live at https://joncorral.com")
    else:
        # Discard changes
        subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=WORKSPACE)
        send_telegram_message("❌ Changes discarded. Site unchanged.")
```

---

## Module G: Rollback

**Purpose**: Revert the last deployment on Jon's command.

**Trigger phrases**: "revert", "undo", "roll back", "put it back", "that was bad"

```python
def execute_rollback():
    """
    1. Show what will be reverted
    2. Wait for approval
    3. git revert + push
    """
    last_commit_msg = subprocess.check_output(
        ["git", "log", "-1", "--format=%s"],
        cwd=WORKSPACE, text=True
    ).strip()

    send_telegram_message(
        f"🔄 **Rollback Prepared**\n\n"
        f"Reverting: \"{last_commit_msg}\"\n\n"
        f"Reply **approve** to roll back."
    )

    response = wait_for_telegram_reply()
    if response.lower() in ["yes", "approve", "go", "do it"]:
        subprocess.run(["git", "revert", "HEAD", "--no-edit"], cwd=WORKSPACE, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=WORKSPACE, check=True)
        import time; time.sleep(60)
        send_telegram_message("✅ Rollback complete. Site reverted to previous state.")
```

---

## Module H: Work-Bot Consultation (Cross-Bot)

**Purpose**: Consult work-bot for professional context when updating portfolio content.

**When to use**:
- Updating resume page with current projects/skills
- Adding new work case studies referencing professional capabilities
- Refreshing the about section's professional narrative
- Updating skills/tools in the marquee ticker
- Any content that references Jon's professional identity

```python
def consult_work_bot(query: str) -> str:
    """Query work-bot for professional context."""
    return message_agent(
        target="work-bot",
        message=query
    )

def needs_professional_context(command: str) -> bool:
    """Check if command requires work-bot consultation."""
    triggers = [
        "resume", "experience", "skills", "projects",
        "achievements", "professional", "work history",
        "job title", "certifications", "about me"
    ]
    return any(t in command.lower() for t in triggers)
```

---

## Module I: Etsy Storefront & Landing Pages (Stub)

> **Status**: Implementation TBD pending Etsy API keys and storefront-bot coordination.

**Planned scope**:
- Create/manage Etsy product listing pages
- Build landing pages for digital products
- Coordinate with `storefront-bot` for product data, pricing, descriptions
- Maintain consistent brand aesthetic across portfolio + storefront

**Blocker**: `ETSY_API_KEY`, `ETSY_SHARED_SECRET`, `ETSY_SHOP_ID`

---

## Setup (One-Time)

### Step 1: Clone the repo on VM
```bash
mkdir -p ~/workspaces
cd ~/workspaces
git clone https://github.com/jcorral10/joncorral-portfolio.git portfolio
cd portfolio
git config user.name "Allie (web-bot)"
git config user.email "bot@joncorral.com"
```

### Step 2: Configure GitHub credentials
```bash
# Use the GITHUB_TOKEN from ~/.env
git remote set-url origin https://${GITHUB_TOKEN}@github.com/jcorral10/joncorral-portfolio.git
```

### Step 3: Verify push access
```bash
# Make a trivial test commit
echo "<!-- bot-verified -->" >> index.html
git add -A && git commit -m "test: verify web-bot push access"
git push origin main
# Then revert
git revert HEAD --no-edit && git push origin main
```

### Step 4: Install Python deps (if not present)
```bash
pip install beautifulsoup4 Pillow
```

---

## Resource Files

| File | Purpose |
|------|---------|
| `SKILL.md` | This file — skill instructions |
| `resources/site_map.json` | NL label → file path + CSS selector mapping |
| `resources/brand_guide.json` | Design tokens, typography, colors, brand voice rules |

---

## Integration

### Ownership Map

| Database/Resource | Owner | web-bot Access |
|-------------------|-------|----------------|
| Portfolio repo (GitHub) | web-bot | READ/WRITE |
| Work Life DB (Notion) | work-bot | READ (via cross-bot query) |
| Etsy DBs (Notion) | storefront-bot | READ (future, via cross-bot) |

### Communication

| Direction | Method | Purpose |
|-----------|--------|---------|
| Orchestrator → web-bot | CLI wrapper / `message_agent()` | Delegate site update requests |
| web-bot → work-bot | `message_agent(target="work-bot")` | Get professional context |
| web-bot → storefront-bot | `message_agent(target="storefront-bot")` | Etsy coordination (future) |
| web-bot → Jon | Telegram message | Approval gates, confirmations |
