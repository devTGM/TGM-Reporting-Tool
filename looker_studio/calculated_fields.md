# Looker Studio Calculated Fields Dictionary

This document details the exact Calculated Field formulas required to build the Looker Studio dashboard matching the client specification spreadsheet ([Google Sheet Reference](https://docs.google.com/spreadsheets/d/1yulDW_Xm-pmawzXSqBtRmg1WojiP74FpuyN1T6sp-yQ/edit?usp=sharing)).

> **IMPORTANT LOOKER STUDIO RULE:**
> Always use aggregated expressions (e.g. `SUM(...) / NULLIF(SUM(...), 0)`) rather than raw row metrics. This ensures that when dashboard users apply date filters (Day, Week, Month), channel filters, or nomenclature filters, all ratios recalculate with mathematical correctness rather than averaging row-level averages.

---

## 1. Raw Input Metrics (11 Fields)

These fields are ingested directly from advertising platforms (Meta, Google, LinkedIn, TikTok, Snapchat) and stored as columns in the BigQuery base table:

| Field Name in BigQuery | Looker Studio Display Name | Type | Aggregation |
| :--- | :--- | :--- | :--- |
| `spend` | Amount spent | Currency ($) | SUM |
| `purchases_conversion_value`| Purchases conversion value | Currency ($) | SUM |
| `purchases` | Purchases | Number (Numeric) | SUM |
| `landing_page_views` | Landing page views (LPV) | Number (Numeric) | SUM |
| `reach` | Reach | Number (Numeric) | SUM |
| `impressions` | Impressions | Number (Numeric) | SUM |
| `link_clicks` | Link clicks | Number (Numeric) | SUM |
| `video_plays_3s` | 3-second video plays | Number (Numeric) | SUM |
| `thruplays_15s` | 15-second ThruPlays | Number (Numeric) | SUM |
| `adds_to_cart` | Adds to cart (ATC) | Number (Numeric) | SUM |
| `checkouts_initiated` | Checkouts initiated (IC) | Number (Numeric) | SUM |

---

## 2. Formulated / Calculated Metrics (17 Formulas)

### 1. Purchase ROAS
* **Spreadsheet Definition**: `Purchases conversion value ÷ Amount spent`
* **Looker Studio Formula**:
  ```sql
  SUM(purchases_conversion_value) / NULLIF(SUM(spend), 0)
  ```
* **Data Type**: Number &rarr; Numeric (2 decimal places)

### 2. Cost per purchase (CPA)
* **Spreadsheet Definition**: `Amount spent ÷ Purchases`
* **Looker Studio Formula**:
  ```sql
  SUM(spend) / NULLIF(SUM(purchases), 0)
  ```
* **Data Type**: Currency &rarr; USD ($)

### 3. Average purchases conversion value (AOV)
* **Spreadsheet Definition**: `Purchases conversion value ÷ Purchases`
* **Looker Studio Formula**:
  ```sql
  SUM(purchases_conversion_value) / NULLIF(SUM(purchases), 0)
  ```
* **Data Type**: Currency &rarr; USD ($)

### 4. Purchases rate per LPV
* **Spreadsheet Definition**: `(Purchases ÷ Landing page views) × 100`
* **Looker Studio Formula**:
  ```sql
  SUM(purchases) / NULLIF(SUM(landing_page_views), 0)
  ```
* **Data Type**: Number &rarr; Percent (%)

### 5. Cost per LPV
* **Spreadsheet Definition**: `Amount spent ÷ Landing page views`
* **Looker Studio Formula**:
  ```sql
  SUM(spend) / NULLIF(SUM(landing_page_views), 0)
  ```
* **Data Type**: Currency &rarr; USD ($)

### 6. LPV rate per link clicks
* **Spreadsheet Definition**: `(Landing page views ÷ Link clicks) × 100`
* **Looker Studio Formula**:
  ```sql
  SUM(landing_page_views) / NULLIF(SUM(link_clicks), 0)
  ```
* **Data Type**: Number &rarr; Percent (%)

### 7. Frequency
* **Spreadsheet Definition**: `Impressions ÷ Reach`
* **Looker Studio Formula**:
  ```sql
  SUM(impressions) / NULLIF(SUM(reach), 0)
  ```
* **Data Type**: Number &rarr; Numeric (2 decimal places)

### 8. CPM (Cost Per Mille)
* **Spreadsheet Definition**: `(Amount spent ÷ Impressions) × 1000`
* **Looker Studio Formula**:
  ```sql
  (SUM(spend) / NULLIF(SUM(impressions), 0)) * 1000
  ```
* **Data Type**: Currency &rarr; USD ($)

### 9. CPC (Cost Per Click)
* **Spreadsheet Definition**: `Amount spent ÷ Link clicks`
* **Looker Studio Formula**:
  ```sql
  SUM(spend) / NULLIF(SUM(link_clicks), 0)
  ```
* **Data Type**: Currency &rarr; USD ($)

### 10. CTR (Click-Through Rate)
* **Spreadsheet Definition**: `(Link clicks ÷ Impressions) × 100`
* **Looker Studio Formula**:
  ```sql
  SUM(link_clicks) / NULLIF(SUM(impressions), 0)
  ```
* **Data Type**: Number &rarr; Percent (%)

### 11. 3-second video plays rate per impressions (Thumbstop Rate)
* **Spreadsheet Definition**: `(3-second video plays ÷ Impressions) × 100`
* **Looker Studio Formula**:
  ```sql
  SUM(video_plays_3s) / NULLIF(SUM(impressions), 0)
  ```
* **Data Type**: Number &rarr; Percent (%)

### 12. Cost per 3-second video play
* **Spreadsheet Definition**: `Amount spent ÷ 3-second video plays`
* **Looker Studio Formula**:
  ```sql
  SUM(spend) / NULLIF(SUM(video_plays_3s), 0)
  ```
* **Data Type**: Currency &rarr; USD ($)

### 13. Cost per 15-second ThruPlay
* **Spreadsheet Definition**: `Amount spent ÷ 15-second ThruPlays`
* **Looker Studio Formula**:
  ```sql
  SUM(spend) / NULLIF(SUM(thruplays_15s), 0)
  ```
* **Data Type**: Currency &rarr; USD ($)

### 14. Cost per add to cart
* **Spreadsheet Definition**: `Amount spent ÷ Adds to cart`
* **Looker Studio Formula**:
  ```sql
  SUM(spend) / NULLIF(SUM(adds_to_cart), 0)
  ```
* **Data Type**: Currency &rarr; USD ($)

### 15. Add to cart %
* **Spreadsheet Definition**: `(Adds to cart ÷ Landing page views) × 100`
* **Looker Studio Formula**:
  ```sql
  SUM(adds_to_cart) / NULLIF(SUM(landing_page_views), 0)
  ```
* **Data Type**: Number &rarr; Percent (%)

### 16. Cost per checkout initiated
* **Spreadsheet Definition**: `Amount spent ÷ Checkouts initiated`
* **Looker Studio Formula**:
  ```sql
  SUM(spend) / NULLIF(SUM(checkouts_initiated), 0)
  ```
* **Data Type**: Currency &rarr; USD ($)

### 17. Checkout initiated %
* **Spreadsheet Definition**: `(Checkouts initiated ÷ Landing page views) × 100`
* **Looker Studio Formula**:
  ```sql
  SUM(checkouts_initiated) / NULLIF(SUM(landing_page_views), 0)
  ```
* **Data Type**: Number &rarr; Percent (%)

---

## 3. Weekly Nomenclature Tables (8 Taxonomy Dimensions)

The pipeline automatically parses campaign and ad naming conventions into 8 normalized dimension fields:

1. **`category_collection`**: `CATEGORY/COLLECTION` (e.g. Polo, T-Shirts, Shirts, Hoodies & Sweatshirts, Storewide)
2. **`product_name`**: `PRODUCTNAME` (e.g. Leaf Print Polo - Slate Color, Classic Polo - Solid Black, Royal Blue Solid Polo, Multiple Products / Bundle)
3. **`funnel`**: `FUNNEL` (e.g. Top of Funnel, Middle of Funnel, Bottom of Funnel, Advantage+ Shopping Campaign)
4. **`sale_offer`**: `(SALENAME+OFFER)` (e.g. Black Friday / 20% Off, End of Season / Buy 2 Get 1, Spring Sale / Flat ₹500 Off, Evergreen / BAU)
5. **`audience_type`**: `AUDIENCETYPE` (e.g. Broad, Lookalike Audience, Interest-Based Targeting, Retargeting, Dynamic Retargeting)
6. **`concept_angle_hook`**: `CONCEPT/ANGLE-HOOK` (e.g. Customer Video Review / Unboxing, Price Anchor, Comparison Chart, Problem-Agitation, Product Feature)
7. **`format`**: `FORMAT` (e.g. Single Image, Reel/Video, Carousel, Short Animated GIF)
8. **`landing_page`**: `LANDINGPAGE` (e.g. Collection Landing Page, Product Detail Page, Homepage, Custom Bundle Offer Page)

---

## 4. Connecting BigQuery to Looker Studio

1. In **Looker Studio** ([lookerstudio.google.com](https://lookerstudio.google.com)), click **Create &rarr; Data Source**.
2. Select the **BigQuery** connector.
3. Select your Project ID, then choose dataset `tgm_reporting`.
4. Connect to View:
   * For Full Exploration: `v_looker_studio_daily_overview`
   * For Weekly Nomenclature Tables: `v_looker_studio_weekly_nomenclature`
   * For Creative & Video Breakdown: `v_looker_studio_creative_performance`
5. The view comes pre-packaged with all safe-divided metrics, or you can add the formulas above directly as custom calculated fields.
