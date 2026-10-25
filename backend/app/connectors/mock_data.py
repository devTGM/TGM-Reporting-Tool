import random
from datetime import datetime, timedelta
from typing import List
from backend.app.models.schema import UnifiedAdRecord
from backend.app.models.client import ClientProfile

CATEGORIES = [
    "Polo",
    "T-Shirts",
    "Shirts",
    "Hoodies & Sweatshirts",
    "Catalog-Wide / Storewide"
]

PRODUCTS = {
    "Polo": [
        "Leaf Print Polo - Slate Color",
        "Classic Polo - Solid Black",
        "Royal Blue Solid Polo"
    ],
    "T-Shirts": [
        "Supima Cotton Tee - Vintage Olive",
        "Classic Crewneck - Heavyweight White",
        "Oversized Minimalist Tee - Charcoal"
    ],
    "Shirts": [
        "Oxford Button Down - Classic Blue",
        "Linen Resort Shirt - Sand Khaki"
    ],
    "Hoodies & Sweatshirts": [
        "French Terry Pullover - Heather Grey",
        "Cozy Oversized Hoodie - Onyx Black"
    ],
    "Catalog-Wide / Storewide": [
        "Multiple Products / Bundle",
        "Starter Capsule 3-Pack Bundle"
    ]
}

FUNNELS = [
    "Top of Funnel (Cold Prospecting)",
    "Middle of Funnel (Engagers/Consideration)",
    "Bottom of Funnel (Cart Abandoners/Web Visitors)",
    "Advantage+ Shopping Campaign"
]

SALES_OFFERS = [
    "Black Friday / 20% Off",
    "End of Season / Buy 2 Get 1",
    "Spring Sale / Flat ₹500 Off",
    "Evergreen / Regular Pricing / BAU"
]

AUDIENCES = [
    "Broad",
    "Lookalike Audience",
    "Interest-Based Targeting",
    "Retargeting",
    "Dynamic Retargeting (Website catalog interactions)"
]

CONCEPTS_HOOKS = [
    "Customer Video Review / Unboxing",
    "Price Anchor / Offer-led Hook",
    "Comparison Chart / Competitor Angle",
    "Problem-Agitation Hook (e.g., No Shrinkage)",
    "Product Feature / Material Focus"
]

FORMATS = [
    "Single Image",
    "Reel/Video",
    "Carousel",
    "Short Animated GIF / Motion Graphic"
]

LANDING_PAGES = [
    "Collection Landing Page",
    "Product Detail Page",
    "Homepage",
    "Custom Bundle Offer Page"
]

PLATFORMS_CFG = {
    "Meta": {"cpm": 14.50, "ctr": 1.65, "cpc": 0.88, "lpv_rate": 0.82, "atc_rate": 0.12, "ic_rate": 0.055, "roas_range": (2.8, 5.2)},
    "Google": {"cpm": 26.00, "ctr": 3.80, "cpc": 1.95, "lpv_rate": 0.90, "atc_rate": 0.15, "ic_rate": 0.075, "roas_range": (3.2, 6.5)},
    "LinkedIn": {"cpm": 42.00, "ctr": 0.72, "cpc": 6.80, "lpv_rate": 0.75, "atc_rate": 0.06, "ic_rate": 0.030, "roas_range": (1.6, 2.9)},
    "TikTok": {"cpm": 8.50, "ctr": 1.95, "cpc": 0.44, "lpv_rate": 0.78, "atc_rate": 0.09, "ic_rate": 0.040, "roas_range": (2.1, 4.2)},
    "Snapchat": {"cpm": 7.20, "ctr": 1.35, "cpc": 0.48, "lpv_rate": 0.72, "atc_rate": 0.08, "ic_rate": 0.035, "roas_range": (1.9, 3.4)}
}

def generate_mock_ad_data(
    client: ClientProfile,
    platforms: List[str],
    start_date: str,
    end_date: str
) -> List[UnifiedAdRecord]:
    """
    Generates realistic daily cross-channel marketing data strictly mapped to the
    nomenclature, input metrics, and formulations specified in the requirements.
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    delta_days = (end_dt - start_dt).days + 1

    records: List[UnifiedAdRecord] = []
    random.seed(sum(ord(c) for c in client.id) + 42)

    for p in platforms:
        plat_title = next((k for k in PLATFORMS_CFG if k.lower() == p.lower()), None)
        if not plat_title:
            continue

        p_cfg = PLATFORMS_CFG[plat_title]

        # Generate campaigns across categories & funnels
        for cat in CATEGORIES:
            prod_list = PRODUCTS[cat]
            for prod in prod_list:
                funnel = random.choice(FUNNELS)
                offer = random.choice(SALES_OFFERS)
                aud = random.choice(AUDIENCES)
                hook = random.choice(CONCEPTS_HOOKS)
                fmt = random.choice(FORMATS)
                lp = random.choice(LANDING_PAGES)

                camp_id = f"c_{abs(hash(cat + funnel)) % 10000}"
                camp_name = f"[{funnel.split(' ')[0]}] | {cat} | {prod[:15]} | {offer.split(' ')[0]}"
                adset_id = f"as_{abs(hash(aud)) % 10000}"
                adset_name = f"Audience - {aud}"
                ad_id = f"ad_{abs(hash(prod + hook + fmt)) % 10000}"
                ad_name = f"{prod} | {hook[:18]} | {fmt}"

                for day_offset in range(delta_days):
                    current_date = (start_dt + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                    day_of_week = (start_dt + timedelta(days=day_offset)).weekday()
                    seasonality = 1.25 if day_of_week >= 5 else 0.95

                    daily_spend = round(random.uniform(45.0, 220.0) * seasonality, 2)
                    cpm = p_cfg["cpm"] * random.uniform(0.9, 1.15)
                    impressions = max(100, int((daily_spend / cpm) * 1000))
                    reach = max(50, int(impressions * random.uniform(0.72, 0.88)))

                    ctr = (p_cfg["ctr"] * random.uniform(0.85, 1.25)) / 100.0
                    link_clicks = max(1, int(impressions * ctr))

                    # Landing Page Views (typically 70-90% of link clicks)
                    lpv = max(1, int(link_clicks * p_cfg["lpv_rate"] * random.uniform(0.9, 1.05)))

                    # Adds to cart (typically 8-15% of LPV)
                    adds_to_cart = max(0, int(lpv * p_cfg["atc_rate"] * random.uniform(0.8, 1.2)))

                    # Checkouts initiated (typically 40-60% of ATC)
                    checkouts_initiated = max(0, int(adds_to_cart * 0.55 * random.uniform(0.85, 1.15)))

                    # Purchases (typically 50-75% of checkouts initiated)
                    purchases = max(0, int(checkouts_initiated * random.uniform(0.55, 0.80)))
                    if purchases == 0 and daily_spend > 100:
                        purchases = 1

                    # Average purchase value (AOV) between $45 and $125
                    aov = random.uniform(48.0, 115.0)
                    purchases_conversion_value = round(purchases * aov, 2)

                    # Creative level video metrics
                    video_plays_3s = int(impressions * random.uniform(0.28, 0.58)) if fmt in ["Reel/Video", "Short Animated GIF / Motion Graphic"] else int(impressions * 0.05)
                    thruplays_15s = int(video_plays_3s * random.uniform(0.22, 0.45)) if fmt == "Reel/Video" else int(video_plays_3s * 0.15)

                    rec = UnifiedAdRecord(
                        date=current_date,
                        client_id=client.id,
                        client_name=client.name,
                        platform=plat_title,
                        account_id=f"act_{client.id[:4]}_{plat_title.lower()}",
                        account_name=f"{client.name} {plat_title} Ads",
                        campaign_id=camp_id,
                        campaign_name=camp_name,
                        campaign_type="Conversion",
                        adset_id=adset_id,
                        adset_name=adset_name,
                        ad_id=ad_id,
                        ad_name=ad_name,
                        audience_segment=aud,
                        currency=client.currency,
                        
                        # Nomenclature Tags
                        category_collection=cat,
                        product_name=prod,
                        funnel=funnel,
                        sale_offer=offer,
                        audience_type=aud,
                        concept_angle_hook=hook,
                        format=fmt,
                        landing_page=lp,
                        
                        # Fetch Numbers (Input Metrics)
                        spend=daily_spend,
                        purchases_conversion_value=purchases_conversion_value,
                        purchases=float(purchases),
                        landing_page_views=lpv,
                        reach=reach,
                        impressions=impressions,
                        link_clicks=link_clicks,
                        video_plays_3s=video_plays_3s,
                        thruplays_15s=thruplays_15s,
                        adds_to_cart=adds_to_cart,
                        checkouts_initiated=checkouts_initiated,
                        source="mock"
                    )
                    rec.calculate_derived_metrics()
                    records.append(rec)

    return records
