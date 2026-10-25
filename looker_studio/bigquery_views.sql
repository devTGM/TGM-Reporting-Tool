-- ==============================================================================
-- TGM Reporting Studio: BigQuery Warehouse & Looker Studio Views
-- Partitioned & Clustered Schema for High-Performance Marketing Analytics
-- Built to match the exact Google Sheets agency reporting specifications:
-- 11 Input Raw Metrics, 17 Formulated Metrics, 8 Taxonomy/Nomenclature Dimensions
-- ==============================================================================

-- 1. Unified Ad Performance Base Table
-- Replace `YOUR_PROJECT_ID` with your Google Cloud Project ID
CREATE TABLE IF NOT EXISTS `YOUR_PROJECT_ID.tgm_reporting.unified_ad_performance` (
  record_id STRING NOT NULL,
  date DATE NOT NULL,
  client_id STRING NOT NULL,
  client_name STRING,
  platform STRING NOT NULL, -- Meta, Google, LinkedIn, TikTok, Snapchat
  account_id STRING,
  account_name STRING,
  campaign_id STRING,
  campaign_name STRING,
  campaign_type STRING,
  adset_id STRING,
  adset_name STRING,
  ad_id STRING,
  ad_name STRING,
  audience_segment STRING,
  currency STRING,

  -- 8 Nomenclature / Taxonomy Dimensions
  category_collection STRING,
  product_name STRING,
  funnel STRING,
  sale_offer STRING,
  audience_type STRING,
  concept_angle_hook STRING,
  format STRING,
  landing_page STRING,

  -- 11 Input Raw Metrics
  spend FLOAT64,
  purchases_conversion_value FLOAT64,
  purchases FLOAT64,
  landing_page_views INT64,
  reach INT64,
  impressions INT64,
  link_clicks INT64,
  video_plays_3s INT64,
  thruplays_15s INT64,
  adds_to_cart INT64,
  checkouts_initiated INT64,

  -- 17 Formulated (Calculated) Metrics
  purchase_roas FLOAT64,
  cost_per_purchase FLOAT64,
  avg_purchase_conversion_value FLOAT64,
  purchase_rate_per_lpv FLOAT64,
  cost_per_lpv FLOAT64,
  lpv_rate_per_link_clicks FLOAT64,
  frequency FLOAT64,
  cpm FLOAT64,
  cpc FLOAT64,
  ctr FLOAT64,
  video_plays_3s_rate_per_impressions FLOAT64,
  cost_per_video_play_3s FLOAT64,
  cost_per_thruplay_15s FLOAT64,
  cost_per_add_to_cart FLOAT64,
  add_to_cart_pct FLOAT64,
  cost_per_checkout_initiated FLOAT64,
  checkout_initiated_pct FLOAT64,

  synced_at TIMESTAMP,
  source STRING
)
PARTITION BY date
CLUSTER BY platform, client_id, campaign_name
OPTIONS(
  description = "TGM Agency unified multi-channel ad reporting table"
);

-- ------------------------------------------------------------------------------
-- 2. View: Daily Cross-Channel Flat Overview (Primary Looker Studio Connector)
-- Safe division and zero-handling ensure no errors in Looker Studio reports
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.tgm_reporting.v_looker_studio_daily_overview` AS
SELECT 
  date,
  client_id,
  client_name,
  platform,
  account_id,
  account_name,
  campaign_id,
  campaign_name,
  campaign_type,
  adset_id,
  adset_name,
  ad_id,
  ad_name,
  audience_segment,
  currency,

  -- 8 Taxonomy / Nomenclature Dimensions
  category_collection,
  product_name,
  funnel,
  sale_offer,
  audience_type,
  concept_angle_hook,
  format,
  landing_page,

  -- 11 Input Raw Metrics
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
  checkouts_initiated,

  -- 17 Formulated Metrics (Safe Division)
  SAFE_DIVIDE(purchases_conversion_value, spend) AS purchase_roas,
  SAFE_DIVIDE(spend, purchases) AS cost_per_purchase,
  SAFE_DIVIDE(purchases_conversion_value, purchases) AS avg_purchase_conversion_value,
  SAFE_DIVIDE(purchases, landing_page_views) * 100.0 AS purchase_rate_per_lpv,
  SAFE_DIVIDE(spend, landing_page_views) AS cost_per_lpv,
  SAFE_DIVIDE(landing_page_views, link_clicks) * 100.0 AS lpv_rate_per_link_clicks,
  SAFE_DIVIDE(impressions, reach) AS frequency,
  SAFE_DIVIDE(spend, impressions) * 1000.0 AS cpm,
  SAFE_DIVIDE(spend, link_clicks) AS cpc,
  SAFE_DIVIDE(link_clicks, impressions) * 100.0 AS ctr,
  SAFE_DIVIDE(video_plays_3s, impressions) * 100.0 AS video_plays_3s_rate_per_impressions,
  SAFE_DIVIDE(spend, video_plays_3s) AS cost_per_video_play_3s,
  SAFE_DIVIDE(spend, thruplays_15s) AS cost_per_thruplay_15s,
  SAFE_DIVIDE(spend, adds_to_cart) AS cost_per_add_to_cart,
  SAFE_DIVIDE(adds_to_cart, landing_page_views) * 100.0 AS add_to_cart_pct,
  SAFE_DIVIDE(spend, checkouts_initiated) AS cost_per_checkout_initiated,
  SAFE_DIVIDE(checkouts_initiated, landing_page_views) * 100.0 AS checkout_initiated_pct,
  synced_at
FROM `YOUR_PROJECT_ID.tgm_reporting.unified_ad_performance`;

-- ------------------------------------------------------------------------------
-- 3. View: Weekly Nomenclature Performance Rollup
-- Powers the 8 Weekly Breakdown Tables in Looker Studio
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.tgm_reporting.v_looker_studio_weekly_nomenclature` AS
SELECT 
  DATE_TRUNC(date, WEEK) AS week_start_date,
  client_id,
  client_name,
  platform,
  currency,
  
  -- Nomenclature Dimensions
  category_collection,
  product_name,
  funnel,
  sale_offer,
  audience_type,
  concept_angle_hook,
  format,
  landing_page,

  -- Aggregated Raw Metrics
  SUM(spend) AS spend,
  SUM(purchases_conversion_value) AS purchases_conversion_value,
  SUM(purchases) AS purchases,
  SUM(landing_page_views) AS landing_page_views,
  SUM(reach) AS reach,
  SUM(impressions) AS impressions,
  SUM(link_clicks) AS link_clicks,
  SUM(video_plays_3s) AS video_plays_3s,
  SUM(thruplays_15s) AS thruplays_15s,
  SUM(adds_to_cart) AS adds_to_cart,
  SUM(checkouts_initiated) AS checkouts_initiated,

  -- Aggregated Calculated Ratios
  SAFE_DIVIDE(SUM(purchases_conversion_value), SUM(spend)) AS purchase_roas,
  SAFE_DIVIDE(SUM(spend), SUM(purchases)) AS cost_per_purchase,
  SAFE_DIVIDE(SUM(purchases_conversion_value), SUM(purchases)) AS avg_purchase_conversion_value,
  SAFE_DIVIDE(SUM(purchases), SUM(landing_page_views)) * 100.0 AS purchase_rate_per_lpv,
  SAFE_DIVIDE(SUM(spend), SUM(landing_page_views)) AS cost_per_lpv,
  SAFE_DIVIDE(SUM(landing_page_views), SUM(link_clicks)) * 100.0 AS lpv_rate_per_link_clicks,
  SAFE_DIVIDE(SUM(spend), SUM(impressions)) * 1000.0 AS cpm,
  SAFE_DIVIDE(SUM(spend), SUM(link_clicks)) AS cpc,
  SAFE_DIVIDE(SUM(link_clicks), SUM(impressions)) * 100.0 AS ctr,
  SAFE_DIVIDE(SUM(video_plays_3s), SUM(impressions)) * 100.0 AS video_plays_3s_rate_per_impressions,
  SAFE_DIVIDE(SUM(spend), SUM(video_plays_3s)) AS cost_per_video_play_3s,
  SAFE_DIVIDE(SUM(spend), SUM(thruplays_15s)) AS cost_per_thruplay_15s,
  SAFE_DIVIDE(SUM(spend), SUM(adds_to_cart)) AS cost_per_add_to_cart,
  SAFE_DIVIDE(SUM(adds_to_cart), SUM(landing_page_views)) * 100.0 AS add_to_cart_pct,
  SAFE_DIVIDE(SUM(spend), SUM(checkouts_initiated)) AS cost_per_checkout_initiated,
  SAFE_DIVIDE(SUM(checkouts_initiated), SUM(landing_page_views)) * 100.0 AS checkout_initiated_pct
FROM `YOUR_PROJECT_ID.tgm_reporting.unified_ad_performance`
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13;

-- ------------------------------------------------------------------------------
-- 4. View: Creative-Level Video & Thumbstop Performance
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW `YOUR_PROJECT_ID.tgm_reporting.v_looker_studio_creative_performance` AS
SELECT 
  ad_id,
  ad_name,
  platform,
  concept_angle_hook,
  format,
  landing_page,
  MIN(date) AS first_active_date,
  MAX(date) AS last_active_date,
  SUM(spend) AS spend,
  SUM(impressions) AS impressions,
  SUM(link_clicks) AS link_clicks,
  SUM(landing_page_views) AS landing_page_views,
  SUM(video_plays_3s) AS video_plays_3s,
  SUM(thruplays_15s) AS thruplays_15s,
  SUM(purchases) AS purchases,
  SUM(purchases_conversion_value) AS purchases_conversion_value,
  SAFE_DIVIDE(SUM(video_plays_3s), SUM(impressions)) * 100.0 AS thumbstop_rate_3s_pct,
  SAFE_DIVIDE(SUM(spend), SUM(video_plays_3s)) AS cost_per_3s_play,
  SAFE_DIVIDE(SUM(spend), SUM(thruplays_15s)) AS cost_per_thruplay_15s,
  SAFE_DIVIDE(SUM(purchases_conversion_value), SUM(spend)) AS purchase_roas,
  SAFE_DIVIDE(SUM(spend), SUM(purchases)) AS cost_per_purchase
FROM `YOUR_PROJECT_ID.tgm_reporting.unified_ad_performance`
GROUP BY 1, 2, 3, 4, 5, 6;
