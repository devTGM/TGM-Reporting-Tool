from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import hashlib

class UnifiedAdRecord(BaseModel):
    """
    Standardized Cross-Channel Marketing Ad Record
    Strictly conformed to TGM Reporting Requirements Sheet:
    - Dimensions: Account, Campaign, Ad Set, Ad, Audience Segments
    - Nomenclature Tags: Category, Product, Funnel, Sale/Offer, Audience Type, Concept/Hook, Format, Landing Page
    - Input Metrics: Amount spent, Purchases conversion value, Purchases, Landing page views, Reach, Impressions, Link clicks, 3s video plays, 15s ThruPlays, Adds to cart, Checkouts initiated
    - Calculated Metrics: ROAS, Cost per purchase, Average purchase value, Purchase rate per LPV, Cost per LPV, LPV rate per click, Frequency, CPM, CPC, CTR, 3s play rate, Cost per 3s play, Cost per ThruPlay, Cost per ATC, ATC %, Cost per Checkout, Checkout %
    """
    record_id: Optional[str] = Field(None, description="MD5 hash for unique deduplication")
    date: str = Field(..., description="Date of performance (YYYY-MM-DD)")
    client_id: str = Field(..., description="Agency client identifier")
    client_name: str = Field(..., description="Agency client name")
    platform: str = Field(..., description="Ad platform: Meta, Google, LinkedIn, TikTok, Snapchat")
    
    # Hierarchy Dimensions
    account_id: str = Field(..., description="Platform ad account ID")
    account_name: Optional[str] = Field("Primary Account", description="Account Level name")
    campaign_id: str = Field(..., description="Campaign ID")
    campaign_name: str = Field(..., description="Campaign name")
    campaign_type: Optional[str] = Field("General", description="Campaign objective/type")
    adset_id: Optional[str] = Field("default", description="Ad set ID")
    adset_name: Optional[str] = Field("Default AdSet", description="Ad set name")
    ad_id: Optional[str] = Field("default", description="Ad ID")
    ad_name: Optional[str] = Field("Default Ad", description="Ad name")
    audience_segment: Optional[str] = Field("All Audiences", description="Audience segments")
    currency: str = Field("USD", description="Currency code (USD, EUR, INR, etc.)")
    
    # Automated Nomenclature Classification Tags
    category_collection: Optional[str] = Field("Storewide", description="Category / Collection (Polo, T-Shirts, Shirts, Hoodies, Catalog-Wide)")
    product_name: Optional[str] = Field("General Product", description="Specific Product Name")
    funnel: Optional[str] = Field("Top of Funnel", description="Funnel Stage (Top of Funnel, Middle of Funnel, Bottom of Funnel, Advantage+)")
    sale_offer: Optional[str] = Field("Evergreen", description="Sale & Offer (Black Friday, End of Season, Flat Off, Evergreen)")
    audience_type: Optional[str] = Field("Broad", description="Audience Type (Broad, Lookalike, Interest, Retargeting, Dynamic)")
    concept_angle_hook: Optional[str] = Field("Feature Focus", description="Concept / Angle Hook (Unboxing, Price Anchor, Comparison, Agitation, Feature)")
    format: Optional[str] = Field("Single Image", description="Creative Format (Single Image, Reel/Video, Carousel, GIF)")
    landing_page: Optional[str] = Field("Product Detail Page", description="Landing Page (Collection Page, PDP, Homepage, Bundle Page)")
    
    # Fetch Numbers (Input Raw Metrics)
    spend: float = Field(0.0, description="Amount spent")
    purchases_conversion_value: float = Field(0.0, description="Purchases conversion value")
    purchases: float = Field(0.0, description="Purchases count")
    landing_page_views: int = Field(0, description="Landing page views")
    reach: int = Field(0, description="Reach")
    impressions: int = Field(0, description="Impressions")
    link_clicks: int = Field(0, description="Link clicks")
    video_plays_3s: int = Field(0, description="3-second video plays (Creative level)")
    thruplays_15s: int = Field(0, description="15-second ThruPlays")
    adds_to_cart: int = Field(0, description="Adds to cart")
    checkouts_initiated: int = Field(0, description="Checkouts initiated")

    # Formulate (Calculated Metrics)
    purchase_roas: float = Field(0.0, description="Purchase ROAS: Purchases conversion value ÷ Amount spent")
    cost_per_purchase: float = Field(0.0, description="Cost per purchase: Amount spent ÷ Purchases")
    avg_purchase_conversion_value: float = Field(0.0, description="Average purchases conversion value: Purchases conversion value ÷ Purchases")
    purchase_rate_per_lpv: float = Field(0.0, description="Purchases rate per landing page views: (Purchases ÷ Landing page views) × 100")
    cost_per_lpv: float = Field(0.0, description="Cost per landing page view: Amount spent ÷ Landing page views")
    lpv_rate_per_link_clicks: float = Field(0.0, description="Landing page views rate per link clicks: (Landing page views ÷ Link clicks) × 100")
    frequency: float = Field(1.0, description="Frequency: Impressions ÷ Reach")
    cpm: float = Field(0.0, description="CPM (cost per 1,000 impressions): (Amount spent ÷ Impressions) × 1,000")
    cpc: float = Field(0.0, description="CPC (cost per link click): Amount spent ÷ Link clicks")
    ctr: float = Field(0.0, description="CTR (link click-through rate): (Link clicks ÷ Impressions) × 100")
    video_plays_3s_rate_per_impressions: float = Field(0.0, description="3-second video plays rate per impressions: (3-second video plays ÷ Impressions) × 100")
    cost_per_video_play_3s: float = Field(0.0, description="Cost per 3-second video play: Amount spent ÷ 3-second video plays")
    cost_per_thruplay_15s: float = Field(0.0, description="Cost per 15-second ThruPlay: Amount spent ÷ 15-second ThruPlays")
    cost_per_add_to_cart: float = Field(0.0, description="Cost per add to cart: Amount spent ÷ Adds to cart")
    add_to_cart_pct: float = Field(0.0, description="Add to cart %: (Adds to cart ÷ Landing page views) × 100")
    cost_per_checkout_initiated: float = Field(0.0, description="Cost per checkout initiated: Amount spent ÷ Checkouts initiated")
    checkout_initiated_pct: float = Field(0.0, description="checkout initiated %: (Checkouts initiated ÷ Landing page views) × 100")

    # Metadata
    synced_at: Optional[str] = Field(None, description="Timestamp of sync")
    source: Optional[str] = Field("api", description="Source: api, mock, csv")

    def generate_record_id(self) -> str:
        """Generates deterministic unique MD5 hash for zero-duplicate deduplication"""
        raw_key = f"{self.date}|{self.platform.lower()}|{self.client_id}|{self.account_id}|{self.campaign_id}|{self.adset_id}|{self.ad_id}"
        return hashlib.md5(raw_key.encode("utf-8")).hexdigest()

    def calculate_derived_metrics(self):
        """Calculates formulated metrics with zero-division safety per spreadsheet formulas"""
        self.spend = round(float(self.spend), 2)
        self.purchases_conversion_value = round(float(self.purchases_conversion_value), 2)
        self.purchases = round(float(self.purchases), 2)

        # 1. Purchase ROAS: Purchases conversion value ÷ Amount spent
        self.purchase_roas = round(self.purchases_conversion_value / self.spend, 2) if self.spend > 0 else 0.0

        # 2. Cost per purchase: Amount spent ÷ Purchases
        self.cost_per_purchase = round(self.spend / self.purchases, 2) if self.purchases > 0 else 0.0

        # 3. Average purchases conversion value: Purchases conversion value ÷ Purchases
        self.avg_purchase_conversion_value = round(self.purchases_conversion_value / self.purchases, 2) if self.purchases > 0 else 0.0

        # 4. Purchases rate per landing page views: (Purchases ÷ Landing page views) × 100
        self.purchase_rate_per_lpv = round((self.purchases / self.landing_page_views) * 100.0, 2) if self.landing_page_views > 0 else 0.0

        # 5. Cost per landing page view: Amount spent ÷ Landing page views
        self.cost_per_lpv = round(self.spend / self.landing_page_views, 2) if self.landing_page_views > 0 else 0.0

        # 6. Landing page views rate per link clicks: (Landing page views ÷ Link clicks) × 100
        self.lpv_rate_per_link_clicks = round((self.landing_page_views / self.link_clicks) * 100.0, 2) if self.link_clicks > 0 else 0.0

        # 7. Frequency: Impressions ÷ Reach
        self.frequency = round(self.impressions / self.reach, 2) if self.reach > 0 else 1.0

        # 8. CPM: (Amount spent ÷ Impressions) × 1,000
        self.cpm = round((self.spend / self.impressions) * 1000.0, 2) if self.impressions > 0 else 0.0

        # 9. CPC: Amount spent ÷ Link clicks
        self.cpc = round(self.spend / self.link_clicks, 2) if self.link_clicks > 0 else 0.0

        # 10. CTR: (Link clicks ÷ Impressions) × 100
        self.ctr = round((self.link_clicks / self.impressions) * 100.0, 2) if self.impressions > 0 else 0.0

        # 11. 3-second video plays rate per impressions: (3-second video plays ÷ Impressions) × 100
        self.video_plays_3s_rate_per_impressions = round((self.video_plays_3s / self.impressions) * 100.0, 2) if self.impressions > 0 else 0.0

        # 12. Cost per 3-second video play: Amount spent ÷ 3-second video plays
        self.cost_per_video_play_3s = round(self.spend / self.video_plays_3s, 3) if self.video_plays_3s > 0 else 0.0

        # 13. Cost per 15-second ThruPlay: Amount spent ÷ 15-second ThruPlays
        self.cost_per_thruplay_15s = round(self.spend / self.thruplays_15s, 3) if self.thruplays_15s > 0 else 0.0

        # 14. Cost per add to cart: Amount spent ÷ Adds to cart
        self.cost_per_add_to_cart = round(self.spend / self.adds_to_cart, 2) if self.adds_to_cart > 0 else 0.0

        # 15. Add to cart %: (Adds to cart ÷ Landing page views) × 100
        self.add_to_cart_pct = round((self.adds_to_cart / self.landing_page_views) * 100.0, 2) if self.landing_page_views > 0 else 0.0

        # 16. Cost per checkout initiated: Amount spent ÷ Checkouts initiated
        self.cost_per_checkout_initiated = round(self.spend / self.checkouts_initiated, 2) if self.checkouts_initiated > 0 else 0.0

        # 17. checkout initiated %: (Checkouts initiated ÷ Landing page views) × 100
        self.checkout_initiated_pct = round((self.checkouts_initiated / self.landing_page_views) * 100.0, 2) if self.landing_page_views > 0 else 0.0

        if not self.record_id:
            self.record_id = self.generate_record_id()
        if not self.synced_at:
            self.synced_at = datetime.utcnow().isoformat()

# Full BigQuery Schema Fields matching the sheet
BIGQUERY_SCHEMA_FIELDS = [
    {"name": "record_id", "type": "STRING", "mode": "REQUIRED", "description": "MD5 unique record hash"},
    {"name": "date", "type": "DATE", "mode": "REQUIRED", "description": "Date of ad performance"},
    {"name": "client_id", "type": "STRING", "mode": "REQUIRED", "description": "Client ID"},
    {"name": "client_name", "type": "STRING", "mode": "NULLABLE", "description": "Client Name"},
    {"name": "platform", "type": "STRING", "mode": "REQUIRED", "description": "Platform Name (Meta, Google, etc.)"},
    {"name": "account_id", "type": "STRING", "mode": "NULLABLE", "description": "Account Level ID"},
    {"name": "account_name", "type": "STRING", "mode": "NULLABLE", "description": "Account Level Name"},
    {"name": "campaign_id", "type": "STRING", "mode": "NULLABLE", "description": "Campaign ID"},
    {"name": "campaign_name", "type": "STRING", "mode": "NULLABLE", "description": "Campaign Name"},
    {"name": "campaign_type", "type": "STRING", "mode": "NULLABLE", "description": "Campaign Type"},
    {"name": "adset_id", "type": "STRING", "mode": "NULLABLE", "description": "Ad Set ID"},
    {"name": "adset_name", "type": "STRING", "mode": "NULLABLE", "description": "Ad Set Name"},
    {"name": "ad_id", "type": "STRING", "mode": "NULLABLE", "description": "Ad ID"},
    {"name": "ad_name", "type": "STRING", "mode": "NULLABLE", "description": "Ad Name"},
    {"name": "audience_segment", "type": "STRING", "mode": "NULLABLE", "description": "Audience Segments"},
    {"name": "currency", "type": "STRING", "mode": "NULLABLE", "description": "Currency Code"},
    
    # Nomenclature Tags
    {"name": "category_collection", "type": "STRING", "mode": "NULLABLE", "description": "Nomenclature: Category/Collection"},
    {"name": "product_name", "type": "STRING", "mode": "NULLABLE", "description": "Nomenclature: Product Name"},
    {"name": "funnel", "type": "STRING", "mode": "NULLABLE", "description": "Nomenclature: Funnel Stage"},
    {"name": "sale_offer", "type": "STRING", "mode": "NULLABLE", "description": "Nomenclature: Sale/Offer"},
    {"name": "audience_type", "type": "STRING", "mode": "NULLABLE", "description": "Nomenclature: Audience Type"},
    {"name": "concept_angle_hook", "type": "STRING", "mode": "NULLABLE", "description": "Nomenclature: Concept/Angle Hook"},
    {"name": "format", "type": "STRING", "mode": "NULLABLE", "description": "Nomenclature: Creative Format"},
    {"name": "landing_page", "type": "STRING", "mode": "NULLABLE", "description": "Nomenclature: Landing Page Type"},

    # Input Metrics
    {"name": "spend", "type": "FLOAT64", "mode": "NULLABLE", "description": "Amount spent"},
    {"name": "purchases_conversion_value", "type": "FLOAT64", "mode": "NULLABLE", "description": "Purchases conversion value"},
    {"name": "purchases", "type": "FLOAT64", "mode": "NULLABLE", "description": "Purchases count"},
    {"name": "landing_page_views", "type": "INT64", "mode": "NULLABLE", "description": "Landing page views"},
    {"name": "reach", "type": "INT64", "mode": "NULLABLE", "description": "Reach"},
    {"name": "impressions", "type": "INT64", "mode": "NULLABLE", "description": "Impressions"},
    {"name": "link_clicks", "type": "INT64", "mode": "NULLABLE", "description": "Link clicks"},
    {"name": "video_plays_3s", "type": "INT64", "mode": "NULLABLE", "description": "3-second video plays"},
    {"name": "thruplays_15s", "type": "INT64", "mode": "NULLABLE", "description": "15-second ThruPlays"},
    {"name": "adds_to_cart", "type": "INT64", "mode": "NULLABLE", "description": "Adds to cart"},
    {"name": "checkouts_initiated", "type": "INT64", "mode": "NULLABLE", "description": "Checkouts initiated"},

    # Formulate Metrics
    {"name": "purchase_roas", "type": "FLOAT64", "mode": "NULLABLE", "description": "Purchase ROAS"},
    {"name": "cost_per_purchase", "type": "FLOAT64", "mode": "NULLABLE", "description": "Cost per purchase"},
    {"name": "avg_purchase_conversion_value", "type": "FLOAT64", "mode": "NULLABLE", "description": "Average purchase value"},
    {"name": "purchase_rate_per_lpv", "type": "FLOAT64", "mode": "NULLABLE", "description": "Purchases rate per LPV %"},
    {"name": "cost_per_lpv", "type": "FLOAT64", "mode": "NULLABLE", "description": "Cost per LPV"},
    {"name": "lpv_rate_per_link_clicks", "type": "FLOAT64", "mode": "NULLABLE", "description": "LPV rate per link click %"},
    {"name": "frequency", "type": "FLOAT64", "mode": "NULLABLE", "description": "Frequency"},
    {"name": "cpm", "type": "FLOAT64", "mode": "NULLABLE", "description": "CPM"},
    {"name": "cpc", "type": "FLOAT64", "mode": "NULLABLE", "description": "CPC"},
    {"name": "ctr", "type": "FLOAT64", "mode": "NULLABLE", "description": "CTR %"},
    {"name": "video_plays_3s_rate_per_impressions", "type": "FLOAT64", "mode": "NULLABLE", "description": "3-second video plays rate per impressions %"},
    {"name": "cost_per_video_play_3s", "type": "FLOAT64", "mode": "NULLABLE", "description": "Cost per 3s video play"},
    {"name": "cost_per_thruplay_15s", "type": "FLOAT64", "mode": "NULLABLE", "description": "Cost per 15s ThruPlay"},
    {"name": "cost_per_add_to_cart", "type": "FLOAT64", "mode": "NULLABLE", "description": "Cost per add to cart"},
    {"name": "add_to_cart_pct", "type": "FLOAT64", "mode": "NULLABLE", "description": "Add to cart %"},
    {"name": "cost_per_checkout_initiated", "type": "FLOAT64", "mode": "NULLABLE", "description": "Cost per checkout initiated"},
    {"name": "checkout_initiated_pct", "type": "FLOAT64", "mode": "NULLABLE", "description": "Checkout initiated %"},
    {"name": "synced_at", "type": "TIMESTAMP", "mode": "NULLABLE", "description": "Synced timestamp"},
    {"name": "source", "type": "STRING", "mode": "NULLABLE", "description": "Source origin"}
]
