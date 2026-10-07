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

## Module D: SEO & Listing Optimization
Injects intelligent metadata to ensure products index properly on Etsy.

```python
def generate_listing_metadata(design_theme, product_type):
    # Query LLM or predefined logic for SEO
    title = f"Vintage {design_theme} {product_type} - Unique Gift"
    description = f"<p>Beautifully crafted {product_type} featuring {design_theme}.</p>"
    tags = [design_theme.lower()[:20], product_type.lower()[:20], "gift ideas", "aesthetic", "custom"]
    return title, description, tags[:13]
```

## Module E: Notion Sync
Maintains synchronization between Printify/Etsy and Notion for inventory tracking.

### Schema: Products Database
| Property | Type | Details |
|---|---|---|
| Name | Title | Product Listing Title |
| Printify ID | Rich Text | Internal Printify identifier |
| Etsy Listing ID | Rich Text | External Etsy identifier |
| Status | Select | Draft, Published, Active, Inactive |
| Base Cost | Number | Manufacturing cost |
| Retail Price | Number | Listing price |
| Design Reference | Files | Original design file |
| Revenue Tracking | Number | Total accumulated sales |

# Cron Automations
- `PS1_daily_order_sync`: Runs daily at 00:00. Fetches new Printify orders and records sales numbers in Notion.
- `PS2_weekly_health_check`: Runs Sundays at 02:00. Verifies all products mapped as 'Published' in Notion are still active in Printify/Etsy and stock/providers haven't discontinued the blueprint.

# Resource Files
- `resources/popular_blueprints.json`: Cache of top 10 POD blueprints
- `resources/product_type_advisor.json`: Logic mapping for aspects and DPIs

# Integration
To trigger manually:
`python3 scripts/printify_client.py --test`
