import re
from datetime import datetime
from typing import List, Dict, Any, Tuple
from backend.app.models.schema import UnifiedAdRecord

PLATFORM_CANONICAL = {
    "meta": "Meta",
    "facebook": "Meta",
    "instagram": "Meta",
    "fb": "Meta",
    "google": "Google",
    "google ads": "Google",
    "adwords": "Google",
    "goog": "Google",
    "linkedin": "LinkedIn",
    "li": "LinkedIn",
    "tiktok": "TikTok",
    "tt": "TikTok",
    "snapchat": "Snapchat",
    "snap": "Snapchat"
}

# ----------------- Nomenclature Parsers ----------------- #

def parse_funnel_stage(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["asc", "advantage+", "advantage +", "advantage_plus"]):
        return "Advantage+ Shopping Campaign"
    if any(k in t for k in ["tof", "tofu", "top of funnel", "prospecting", "cold", "reach", "awareness", "brand"]):
        return "Top of Funnel (Cold Prospecting)"
    if any(k in t for k in ["mof", "mofu", "middle of funnel", "consideration", "engagers", "engagement", "traffic"]):
        return "Middle of Funnel (Engagers/Consideration)"
    if any(k in t for k in ["bof", "bofu", "bottom of funnel", "retargeting", "retarg", "dpa", "abandoner", "cart", "visitors"]):
        return "Bottom of Funnel (Cart Abandoners/Web Visitors)"
    return "Top of Funnel (Cold Prospecting)"

def parse_category(text: str) -> str:
    t = text.lower()
    if "polo" in t:
        return "Polo"
    if any(k in t for k in ["t-shirt", "tshirt", "tee"]):
        return "T-Shirts"
    if "shirt" in t:
        return "Shirts"
    if any(k in t for k in ["hoodie", "sweatshirt", "sweater"]):
        return "Hoodies & Sweatshirts"
    if any(k in t for k in ["catalog", "storewide", "all product", "collection", "apparel"]):
        return "Catalog-Wide / Storewide"
    return "Catalog-Wide / Storewide"

def parse_product_name(text: str, category: str) -> str:
    t = text.lower()
    if "leaf print" in t:
        return "Leaf Print Polo - Slate Color"
    if "black" in t and ("solid" in t or "polo" in t or "classic" in t):
        return "Classic Polo - Solid Black"
    if "royal blue" in t or "blue solid" in t:
        return "Royal Blue Solid Polo"
    if any(k in t for k in ["bundle", "pack", "multiple", "all products", "combo"]):
        return "Multiple Products / Bundle"
    return f"{category} Signature Edition"

def parse_sale_offer(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["black friday", "bfcm", "cyber monday"]):
        return "Black Friday / 20% Off"
    if any(k in t for k in ["eoss", "end of season", "buy 2 get 1", "bogo"]):
        return "End of Season / Buy 2 Get 1"
    if any(k in t for k in ["spring", "flat off", "500 off", "discount", "offer"]):
        return "Spring Sale / Flat ₹500 Off"
    return "Evergreen / Regular Pricing / BAU"

def parse_audience_type(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["broad", "open", "no target"]):
        return "Broad"
    if any(k in t for k in ["lookalike", "lal", "look alike"]):
        return "Lookalike Audience"
    if any(k in t for k in ["interest", "affinity", "in-market", "lifestyle", "category"]):
        return "Interest-Based Targeting"
    if any(k in t for k in ["dynamic", "catalog", "dpa"]):
        return "Dynamic Retargeting (Website catalog interactions)"
    if any(k in t for k in ["retarget", "retarg", "visitors", "abandoners"]):
        return "Retargeting"
    return "Broad"

def parse_concept_angle_hook(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["review", "unboxing", "ugc", "testimonial", "customer"]):
        return "Customer Video Review / Unboxing"
    if any(k in t for k in ["price anchor", "offer-led", "discount", "20off", "deal"]):
        return "Price Anchor / Offer-led Hook"
    if any(k in t for k in ["comparison", "vs", "competitor", "chart"]):
        return "Comparison Chart / Competitor Angle"
    if any(k in t for k in ["no shrinkage", "shrink", "sweat", "problem", "agitation", "wrinkle"]):
        return "Problem-Agitation Hook (e.g., No Shrinkage)"
    if any(k in t for k in ["feature", "material", "fabric", "breathable", "cotton", "pima"]):
        return "Product Feature / Material Focus"
    return "Product Feature / Material Focus"

def parse_format(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["reel", "video", "tiktok", "short", "9x16", "9:16", "mp4"]):
        return "Reel/Video"
    if any(k in t for k in ["carousel", "card", "multi"]):
        return "Carousel"
    if any(k in t for k in ["gif", "motion", "animation"]):
        return "Short Animated GIF / Motion Graphic"
    if any(k in t for k in ["image", "static", "photo", "jpg", "png", "banner"]):
        return "Single Image"
    return "Single Image"

def parse_landing_page(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["collection", "category", "shop-all"]):
        return "Collection Landing Page"
    if any(k in t for k in ["pdp", "product", "detail"]):
        return "Product Detail Page"
    if any(k in t for k in ["home", "main", "root"]):
        return "Homepage"
    if any(k in t for k in ["bundle", "offer", "landing"]):
        return "Custom Bundle Offer Page"
    return "Product Detail Page"

def clean_campaign_name(name: str) -> str:
    if not name:
        return "Untitled Campaign"
    name = re.sub(r"https?://\S+", "", name)
    name = re.sub(r"[?&]utm_[a-zA-Z0-9_=-]+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "Untitled Campaign"

def standardize_date(raw_date: Any) -> str:
    if not raw_date:
        return datetime.utcnow().strftime("%Y-%m-%d")
    date_str = str(raw_date).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    if len(date_str) >= 10 and date_str[4] == "-" and date_str[7] == "-":
        return date_str[:10]
    return datetime.utcnow().strftime("%Y-%m-%d")

def clean_and_normalize_records(
    raw_records: List[UnifiedAdRecord]
) -> Tuple[List[UnifiedAdRecord], Dict[str, Any]]:
    """
    Automated Data Cleaning, Normalization, Nomenclature Tagging,
    and Deduplication Pipeline strictly matching requirement specifications.
    """
    cleaned_records_map: Dict[str, UnifiedAdRecord] = {}
    stats = {
        "input_count": len(raw_records),
        "deduplicated_count": 0,
        "anomalies_corrected": 0,
        "output_count": 0
    }

    for rec in raw_records:
        rec.date = standardize_date(rec.date)

        # Platform name canonicalization
        plat_lower = (rec.platform or "").strip().lower()
        rec.platform = PLATFORM_CANONICAL.get(plat_lower, rec.platform.capitalize() if rec.platform else "Unknown")

        # Clean names
        rec.campaign_name = clean_campaign_name(rec.campaign_name)
        rec.adset_name = re.sub(r"\s+", " ", (rec.adset_name or "Default AdSet")).strip()
        rec.ad_name = re.sub(r"\s+", " ", (rec.ad_name or "Default Ad")).strip()

        # Context string for nomenclature parsing
        full_context = f"{rec.campaign_name} {rec.adset_name} {rec.ad_name}"

        # Automated Nomenclature Extraction
        if not rec.funnel or rec.funnel == "Top of Funnel":
            rec.funnel = parse_funnel_stage(rec.campaign_name)
        if not rec.category_collection or rec.category_collection == "Storewide":
            rec.category_collection = parse_category(full_context)
        if not rec.product_name or rec.product_name == "General Product":
            rec.product_name = parse_product_name(full_context, rec.category_collection)
        if not rec.sale_offer or rec.sale_offer == "Evergreen":
            rec.sale_offer = parse_sale_offer(full_context)
        if not rec.audience_type or rec.audience_type == "Broad":
            rec.audience_type = parse_audience_type(rec.adset_name)
        if not rec.concept_angle_hook or rec.concept_angle_hook == "Feature Focus":
            rec.concept_angle_hook = parse_concept_angle_hook(rec.ad_name)
        if not rec.format or rec.format == "Single Image":
            rec.format = parse_format(rec.ad_name)
        if not rec.landing_page or rec.landing_page == "Product Detail Page":
            rec.landing_page = parse_landing_page(full_context)

        # Metric Sanitization & Bounding
        if rec.spend < 0:
            rec.spend = 0.0
            stats["anomalies_corrected"] += 1
        if rec.purchases_conversion_value < 0:
            rec.purchases_conversion_value = 0.0
            stats["anomalies_corrected"] += 1
        if rec.purchases < 0:
            rec.purchases = 0.0
            stats["anomalies_corrected"] += 1
        if rec.landing_page_views < 0:
            rec.landing_page_views = 0
            stats["anomalies_corrected"] += 1
        if rec.impressions < 0:
            rec.impressions = 0
            stats["anomalies_corrected"] += 1
        if rec.link_clicks < 0:
            rec.link_clicks = 0
            stats["anomalies_corrected"] += 1
        if rec.video_plays_3s < 0:
            rec.video_plays_3s = 0
        if rec.thruplays_15s < 0:
            rec.thruplays_15s = 0
        if rec.adds_to_cart < 0:
            rec.adds_to_cart = 0
        if rec.checkouts_initiated < 0:
            rec.checkouts_initiated = 0

        # Rationality checks
        if rec.link_clicks > rec.impressions and rec.impressions > 0:
            rec.impressions = rec.link_clicks
            stats["anomalies_corrected"] += 1
            
        if rec.landing_page_views > rec.link_clicks and rec.link_clicks > 0:
            rec.link_clicks = rec.landing_page_views
            stats["anomalies_corrected"] += 1

        rec.currency = (rec.currency or "USD").upper().strip()
        rec.record_id = rec.generate_record_id()
        rec.calculate_derived_metrics()

        # Deduplication & Aggregation
        if rec.record_id in cleaned_records_map:
            stats["deduplicated_count"] += 1
            existing = cleaned_records_map[rec.record_id]
            existing.spend = round(existing.spend + rec.spend, 2)
            existing.purchases_conversion_value = round(existing.purchases_conversion_value + rec.purchases_conversion_value, 2)
            existing.purchases = round(existing.purchases + rec.purchases, 2)
            existing.landing_page_views += rec.landing_page_views
            existing.impressions += rec.impressions
            existing.link_clicks += rec.link_clicks
            existing.reach = max(existing.reach, rec.reach)
            existing.video_plays_3s += rec.video_plays_3s
            existing.thruplays_15s += rec.thruplays_15s
            existing.adds_to_cart += rec.adds_to_cart
            existing.checkouts_initiated += rec.checkouts_initiated
            existing.calculate_derived_metrics()
        else:
            cleaned_records_map[rec.record_id] = rec

    cleaned_list = list(cleaned_records_map.values())
    stats["output_count"] = len(cleaned_list)
    return cleaned_list, stats
