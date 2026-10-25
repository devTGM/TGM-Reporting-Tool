from typing import Dict, Any
from backend.app.database import get_bigquery_config

class LookerStudioService:
    @staticmethod
    def get_dashboard_resources() -> Dict[str, Any]:
        bq = get_bigquery_config()
        project = bq.project_id or "YOUR_GCP_PROJECT"
        dataset = bq.dataset_id or "tgm_reporting"
        table = bq.table_name or "unified_ad_performance"
        full_table = f"`{project}.{dataset}.{table}`"

        return {
            "bigquery": {
                "project_id": project,
                "dataset_id": dataset,
                "table_name": table,
                "full_table_path": f"{project}.{dataset}.{table}"
            },
            "looker_connect_url": "https://lookerstudio.google.com/datasources/create?connectorId=bigQuery",
            "calculated_fields": [
                {
                    "name": "Purchase ROAS",
                    "formula": "SUM(purchases_conversion_value) / NULLIF(SUM(spend), 0)",
                    "type": "Numeric (2 decimal places)",
                    "description": "Purchases conversion value ÷ Amount spent"
                },
                {
                    "name": "Cost per purchase",
                    "formula": "SUM(spend) / NULLIF(SUM(purchases), 0)",
                    "type": "Currency ($)",
                    "description": "Amount spent ÷ Purchases"
                },
                {
                    "name": "Average purchases conversion value",
                    "formula": "SUM(purchases_conversion_value) / NULLIF(SUM(purchases), 0)",
                    "type": "Currency ($)",
                    "description": "Purchases conversion value ÷ Purchases (AOV)"
                },
                {
                    "name": "Purchases rate per landing page views",
                    "formula": "(SUM(purchases) / NULLIF(SUM(landing_page_views), 0)) * 100",
                    "type": "Percent (%)",
                    "description": "(Purchases ÷ Landing page views) × 100"
                },
                {
                    "name": "Cost per landing page view",
                    "formula": "SUM(spend) / NULLIF(SUM(landing_page_views), 0)",
                    "type": "Currency ($)",
                    "description": "Amount spent ÷ Landing page views"
                },
                {
                    "name": "Landing page views rate per link clicks",
                    "formula": "(SUM(landing_page_views) / NULLIF(SUM(link_clicks), 0)) * 100",
                    "type": "Percent (%)",
                    "description": "(Landing page views ÷ Link clicks) × 100"
                },
                {
                    "name": "Frequency",
                    "formula": "SUM(impressions) / NULLIF(SUM(reach), 0)",
                    "type": "Numeric (2 decimal places)",
                    "description": "Impressions ÷ Reach"
                },
                {
                    "name": "CPM (cost per 1,000 impressions)",
                    "formula": "(SUM(spend) / NULLIF(SUM(impressions), 0)) * 1000",
                    "type": "Currency ($)",
                    "description": "(Amount spent ÷ Impressions) × 1,000"
                },
                {
                    "name": "CPC (cost per link click)",
                    "formula": "SUM(spend) / NULLIF(SUM(link_clicks), 0)",
                    "type": "Currency ($)",
                    "description": "Amount spent ÷ Link clicks"
                },
                {
                    "name": "CTR (link click-through rate)",
                    "formula": "(SUM(link_clicks) / NULLIF(SUM(impressions), 0)) * 100",
                    "type": "Percent (%)",
                    "description": "(Link clicks ÷ Impressions) × 100"
                },
                {
                    "name": "3-second video plays rate per impressions",
                    "formula": "(SUM(video_plays_3s) / NULLIF(SUM(impressions), 0)) * 100",
                    "type": "Percent (%)",
                    "description": "Thumbstop Rate: (3-second video plays ÷ Impressions) × 100"
                },
                {
                    "name": "Cost per 3-second video play",
                    "formula": "SUM(spend) / NULLIF(SUM(video_plays_3s), 0)",
                    "type": "Currency ($)",
                    "description": "Amount spent ÷ 3-second video plays"
                },
                {
                    "name": "Cost per 15-second ThruPlay",
                    "formula": "SUM(spend) / NULLIF(SUM(thruplays_15s), 0)",
                    "type": "Currency ($)",
                    "description": "Amount spent ÷ 15-second ThruPlays"
                },
                {
                    "name": "Cost per add to cart",
                    "formula": "SUM(spend) / NULLIF(SUM(adds_to_cart), 0)",
                    "type": "Currency ($)",
                    "description": "Amount spent ÷ Adds to cart"
                },
                {
                    "name": "Add to cart %",
                    "formula": "(SUM(adds_to_cart) / NULLIF(SUM(landing_page_views), 0)) * 100",
                    "type": "Percent (%)",
                    "description": "(Adds to cart ÷ Landing page views) × 100"
                },
                {
                    "name": "Cost per checkout initiated",
                    "formula": "SUM(spend) / NULLIF(SUM(checkouts_initiated), 0)",
                    "type": "Currency ($)",
                    "description": "Amount spent ÷ Checkouts initiated"
                },
                {
                    "name": "checkout initiated %",
                    "formula": "(SUM(checkouts_initiated) / NULLIF(SUM(landing_page_views), 0)) * 100",
                    "type": "Percent (%)",
                    "description": "(Checkouts initiated ÷ Landing page views) × 100"
                }
            ],
            "nomenclature_dimensions": [
                {"name": "CATEGORY/COLLECTION", "level": "Campaign and Creative level", "example": "Polo, T-Shirts, Shirts, Hoodies, Catalog-Wide"},
                {"name": "PRODUCTNAME", "level": "Campaign and Creative level", "example": "Leaf Print Polo, Classic Polo, Royal Blue, Bundle"},
                {"name": "FUNNEL", "level": "Campaign level", "example": "Top of Funnel, Middle of Funnel, Bottom of Funnel, Advantage+"},
                {"name": "(SALENAME+OFFER)", "level": "Campaign and Creative level", "example": "Black Friday / 20% Off, End of Season, Spring Sale, Evergreen"},
                {"name": "AUDIENCETYPE", "level": "Ad Set level", "example": "Broad, Lookalike, Interest, Retargeting, Dynamic"},
                {"name": "CONCEPT/ANGLE-HOOK", "level": "Creative level", "example": "Review/Unboxing, Price Anchor, Comparison, Problem-Agitation, Product Feature"},
                {"name": "FORMAT", "level": "Creative level", "example": "Single Image, Reel/Video, Carousel, Short GIF"},
                {"name": "LANDINGPAGE", "level": "Creative level", "example": "Collection Page, PDP, Homepage, Custom Bundle Page"}
            ],
            "custom_sql_query": f"""
-- Looker Studio Custom Query
-- Connect via BigQuery -> Custom Query
SELECT 
    date,
    DATE_TRUNC(date, WEEK) AS week_period,
    DATE_TRUNC(date, MONTH) AS month_period,
    client_id,
    client_name,
    platform,
    account_id,
    account_name,
    campaign_id,
    campaign_name,
    adset_id,
    adset_name,
    ad_id,
    ad_name,
    audience_segment,
    currency,
    
    -- Nomenclature
    category_collection,
    product_name,
    funnel,
    sale_offer,
    audience_type,
    concept_angle_hook,
    format,
    landing_page,
    
    -- Raw Metrics
    spend,
    purchases_conversion_value,
    purchases,
    landing_page_views,
    reach,
    impressions,
    link_clicks,
    video_plays_3s,
    thruplays_15s,
    adds_to_cart,
    checkouts_initiated
FROM {full_table}
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
            """.strip()
        }
