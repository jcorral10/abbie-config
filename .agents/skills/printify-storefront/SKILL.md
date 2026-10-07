---
name: printify-storefront
description: >
  Print-on-demand storefront automation via Printify API. Receives designs from Jon,
  maps them to product types (t-shirts, mugs, phone cases, tote bags, etc.), creates
  Printify products with proper print area placement, generates mockups, and publishes
  to Etsy. Handles the full receive-to-list pipeline for physical POD products.
requires:
  bins: [python3, curl]
  pip: [requests]
  env:
    - PRINTIFY_API_TOKEN
    - PRINTIFY_SHOP_ID
    - NOTION_API_KEY
    - NOTION_DB_PRODUCTS
---

# Overview
This skill handles the automated pipeline for translating custom artwork into physical products published on an Etsy storefront. It leverages the Printify API to create, mock up, and publish merchandise while synchronizing product status, sales, and analytics with a Notion database.

# Setup
1. Export Printify API token to `PRINTIFY_API_TOKEN`.
2. Find the Printify shop ID and export it to `PRINTIFY_SHOP_ID`.
3. Ensure Notion integration is set up with `NOTION_API_KEY` and the relevant product database ID is exported to `NOTION_DB_PRODUCTS`.
4. Install requirements: `pip install requests`

# Modules

## Module A: Design Intake
Receives a design file from Jon via:
- Telegram file upload (Allie receives the image)
- HTTP bridge file push
- Shared folder on VM

When Jon sends a design, Allie should:
1. Save the file locally
2. Analyze dimensions and DPI
3. Determine which product types the design works on (based on aspect ratio, resolution)
4. Present Jon with product type options via Telegram
5. Wait for Jon's selection

```python
def process_incoming_design(file_path):
    # Analyze dimensions, format, and resolution
    image = Image.open(file_path)
    width, height = image.size
    dpi = image.info.get('dpi', (72, 72))
    aspect_ratio = width / height
    
    # Send telegram prompt back with compatible product types
    eligible_products = advise_product_types(aspect_ratio, min(dpi))
    prompt_user_for_selection(file_path, eligible_products)
```

## Module B: Printify Product Creator
Core pipeline using Printify API v1:

1. Upload image: `POST /v1/uploads/images.json`
2. Get blueprint variants: `GET /v1/catalog/blueprints/{id}/print_providers/{id}/variants.json`
3. Create product: `POST /v1/shops/{shop_id}/products.json`
4. Publish to Etsy: `POST /v1/shops/{shop_id}/products/{product_id}/publish.json`

```python
def create_and_publish_product(client, shop_id, image_data, title, desc, tags, blueprint_id, provider_id, variants):
    # 1. Upload image
    upload_res = client.upload_image(file_name=image_data['name'], url=image_data['url'])
    image_id = upload_res['id']
    
    # 2. Format print areas
    print_areas = [{
        "variant_ids": variants,
        "placeholders": [{
            "position": "front",
            "images": [{
                "id": image_id,
                "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0
            }]
        }]
    }]
    
    # 3. Create Product
    product = client.create_product(
        title=title, description=desc, tags=tags, 
        blueprint_id=blueprint_id, print_provider_id=provider_id, 
        variants=variants, print_areas=print_areas
    )
    
    # 4. Publish to Etsy
    client.publish_product(product['id'])
    return product['id']
```

## Module C: Product Type Advisor
Maps an uploaded design to optimal merchandise categories.

| Aspect Ratio | Best Products | Minimum DPI Strategy |
|---|---|---|
| Square (1:1) | Mugs, stickers, phone cases, coasters | Typically requires 300 DPI at 10x10 inches |
| Portrait (3:4, 2:3) | T-shirts, hoodies, tote bags, posters | Requires high resolution (e.g. 4500x5400) |
| Landscape (4:3, 16:9) | Desk mats, mouse pads, laptop sleeves | Scaled down for high PPI output |
| Any | All-over print items | Depends on the physical dimensions |

## Module D: SEO & Listing Optimization (MANDATORY)

**Every listing MUST go through this module before creation.** Load `resources/etsy_seo_guide.json` and `resources/pricing_matrix.json` before generating any listing metadata.

### D.1: Title Generation

Load the title templates from `etsy_seo_guide.json → title_rules → templates`. Select the template matching the product type, then fill it in.

**Rules (non-negotiable):**
- Front-load the primary keyword in the first 40 characters
- Include the product type name (T-Shirt, Mug, Tote Bag, etc.)
- Add an occasion or recipient (Gift for Mom, Birthday Gift, etc.)
- Include the aesthetic name from design-intelligence (Sardinecore, Neo-Western, etc.)
- Use pipe `|` or dash `-` as separators
- Max 140 characters
- Never use ALL CAPS

```python
def generate_title(design_theme, product_type, aesthetic, occasion, recipient):
    """Generate an SEO-optimized Etsy title."""
    # Load template from etsy_seo_guide.json
    template = seo_guide["title_rules"]["templates"][product_type]
    
    title = template.format(
        Design_Theme=design_theme,
        Product_Type=PRODUCT_TYPE_DISPLAY[product_type],
        Occasion=occasion,
        Recipient=recipient,
        Aesthetic=aesthetic,
        Material=MATERIAL_MAP[product_type],
        Size=SIZE_MAP.get(product_type, ""),
    )
    
    # Validate: primary keyword in first 40 chars
    assert len(title) <= 140, "Title exceeds Etsy limit"
    return title
```

**Example output:**
`Vintage Motel Sign T-Shirt - Retro Road Trip Gift for Travelers | Matchbook Aesthetic Cotton Tee`

### D.2: Tag Generation

Generate exactly **13 tags** using the broad/mid-tail/long-tail strategy from `etsy_seo_guide.json → tag_strategy`.

**Tag allocation (all 13 slots MUST be filled):**
- 4 broad tags (product type, general theme, material, audience)
- 5 mid-tail tags (theme + product combos, occasion + product, style descriptors)
- 4 long-tail tags (specific niche, micro-aesthetic, identity + product)

```python
def generate_tags(design_theme, product_type, aesthetic, niche_keywords):
    """Generate 13 SEO-optimized tags. Each tag max 20 chars."""
    tags = []
    
    # 4 broad
    broad = get_product_keywords(product_type)[:2]  # From etsy_seo_guide
    broad += [f"{aesthetic} design", "unique gift"]
    tags.extend(broad[:4])
    
    # 5 mid-tail
    mid = [
        f"{design_theme[:10]} {product_type[:8]}",
        f"gift for {determine_recipient(design_theme)}",
        f"{aesthetic} {product_type[:8]}",
        determine_occasion_tag(design_theme),
        f"{aesthetic} art",
    ]
    tags.extend(mid[:5])
    
    # 4 long-tail (niche-specific)
    long = extract_niche_tags(niche_keywords, design_theme)
    tags.extend(long[:4])
    
    # Validate: exactly 13, each ≤ 20 chars, no duplicates
    tags = [t[:20] for t in tags]
    return list(dict.fromkeys(tags))[:13]
```

**Rules:**
- Never repeat words already in the title
- Each tag ≤ 20 characters
- No single generic words ("cool", "nice", "awesome")
- Include at least 1 gift tag and 1 occasion tag

### D.3: Description Generation

Generate HTML-formatted descriptions using the template from `etsy_seo_guide.json → description_template → html_template`.

**Structure (in order):**
1. **Hook line** — emotionally compelling, speaks to buyer identity (not generic "great product")
2. **Design story** — 2-3 sentences about the aesthetic, what makes it unique
3. **Product specs** — bullet list from `etsy_seo_guide.json → product_type_specs`
4. **Sizing info** — from the same specs section
5. **Gift positioning** — who it's perfect for, what occasions
6. **Shipping & production** — "made to order" disclosure, turnaround time
7. **CTA** — "Favorite this item" and "Follow our shop"

**Rules:**
- First 160 characters = Google snippet — make them count
- Naturally weave 2-3 keywords into the first paragraph
- Use `<ul><li>` for specs — scannable content converts better
- Always mention "print on demand" or "made to order"
- Include care instructions from `product_type_specs`

```python
def generate_description(design_theme, product_type, aesthetic, seo_guide):
    """Generate HTML description following the template."""
    specs = seo_guide["product_type_specs"][product_type]
    template = seo_guide["description_template"]["html_template"]
    
    hook = generate_hook(design_theme, aesthetic)  # Identity-driven, not generic
    story = generate_design_story(design_theme, aesthetic)
    
    description = template.format(
        HOOK_LINE=hook,
        DESIGN_STORY=story,
        SPEC_1=specs["specs"][0],
        SPEC_2=specs["specs"][1],
        SPEC_3=specs["specs"][2],
        SPEC_4=specs["specs"][3],
        RECIPIENT_1=determine_recipients(design_theme)[0],
        RECIPIENT_2=determine_recipients(design_theme)[1],
        RECIPIENT_3=determine_recipients(design_theme)[2],
        SIZING_INFO=specs["sizing_note"],
        PRINT_METHOD="direct-to-garment" if product_type in ["t-shirt", "hoodie", "tote_bag"] else "sublimation",
    )
    return description
```

### D.4: Pricing

Load `resources/pricing_matrix.json` and calculate the retail price for each product.

**Pricing formula:**
```
retail_price = round_to_99(base_cost_avg / (1 - target_margin_pct / 100))
```

**Decision logic:**
```python
def calculate_price(product_key, design_score=None, season=None):
    """Calculate retail price from pricing matrix."""
    product = pricing_matrix["products"][product_key]
    
    # Start at target price
    price = product["target_price"]
    
    # Premium designs (design-intelligence score 80+) get premium pricing
    if design_score and design_score >= 80:
        price = product["premium_price"]
    
    # New shop / building reviews: use floor price for first 30 days
    if shop_review_count < 5:
        price = product["floor_price"]
    
    # Apply seasonal multiplier
    if season:
        multiplier = pricing_matrix["seasonal_multipliers"].get(season, 1.0)
        price = round_to_99(price * multiplier)
    
    # Validate against competitor range
    assert price >= product["floor_price"], "Below minimum margin"
    
    return price
```

**Price tiers (from pricing_matrix.json):**
| Product | Floor | Target | Premium |
|---|---|---|---|
| T-Shirt (Bella+Canvas) | $22.99 | $26.99 | $29.99 |
| Hoodie | $37.99 | $44.99 | $49.99 |
| Mug 11oz | $13.99 | $16.99 | $19.99 |
| Sticker (single) | $3.99 | $4.99 | $5.99 |
| Phone Case | $24.99 | $28.99 | $34.99 |
| Tote Bag | $17.99 | $21.99 | $24.99 |
| Poster | $17.99 | $22.99 | $29.99 |

### D.5: Pre-Creation Checklist

Before calling `client.create_product()`, verify:
- [ ] Title ≤ 140 chars, primary keyword in first 40 chars
- [ ] Exactly 13 tags, each ≤ 20 chars, no duplicates
- [ ] Description has hook + story + specs + sizing + gift + shipping + CTA
- [ ] Price pulled from pricing_matrix, not hardcoded
- [ ] Image meets minimum DPI for selected blueprint (from popular_blueprints.json)

---

## Module E: Notion Sync
Maintains synchronization between Printify/Etsy and Notion for inventory tracking.

### Schema: Products Database
| Property | Type | Details |
|---|---|---|
| Name | Title | SEO-optimized listing title |
| Printify ID | Rich Text | Internal Printify product identifier |
| Etsy Listing ID | Rich Text | External Etsy listing identifier |
| Status | Select | Options: Draft, Published, Active, Inactive, Sold Out |
| Product Type | Select | Options: T-Shirt, Hoodie, Mug, Stickers, Phone Case, Tote Bag, Poster, Desk Mat, Notebook |
| Base Cost | Number (Dollar) | Manufacturing cost from pricing matrix |
| Retail Price | Number (Dollar) | Listed retail price |
| Margin % | Number (Percent) | Calculated gross margin percentage |
| Design Reference | Files | Original design file from Jon |
| Blueprint | Rich Text | Printify blueprint name and ID |
| Tags | Rich Text | All 13 Etsy tags, comma-separated |
| Revenue | Number (Dollar) | Total accumulated sales |
| Units Sold | Number | Total units sold |
| Created | Created Time | Auto-set |
| Last Synced | Date | Last time data was pulled from Printify/Etsy |
| Design Brief | Relation | Link to Design Briefs DB (from design-intelligence) |

---

# Cron Automations
- `PS1_daily_order_sync`: Runs daily at 00:00. Fetches new Printify orders via `GET /v1/shops/{shop_id}/orders.json`, records revenue and unit counts in Notion Products DB.
- `PS2_weekly_health_check`: Runs Sundays at 02:00. For each "Published" or "Active" product in Notion, calls `GET /v1/shops/{shop_id}/products/{id}.json` to verify the product still exists, the blueprint/provider haven't been discontinued, and the Etsy listing is live. Flags issues in Notion Status field.

# Resource Files
- `resources/popular_blueprints.json`: Top 10 POD blueprints with IDs, providers, DPI requirements, and cost ranges
- `resources/product_type_advisor.json`: Aspect ratio → product type mapping with minimum DPI requirements
- `resources/etsy_seo_guide.json`: Complete Etsy SEO reference — title formulas, tag strategy (broad/mid/long-tail), HTML description template, product-type-specific keywords and specs
- `resources/pricing_matrix.json`: Base costs per blueprint, Etsy fee breakdown, floor/target/premium prices, seasonal multipliers, margin calculations

# Integration
Test connection: `python3 scripts/printify_client.py --test`

When creating a product, always follow this order:
1. Load `etsy_seo_guide.json` and `pricing_matrix.json`
2. Run Module D (all 5 sub-steps) to generate title, tags, description, price
3. Run Module B to upload image, create product, and optionally publish
4. Run Module E to sync to Notion
