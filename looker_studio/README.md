# Looker Studio Agency Dashboard Guide

This guide walks you through connecting your BigQuery marketing warehouse to **Google Looker Studio**, building an executive cross-channel dashboard, and embedding it inside your agency portal.

---

## 1. Connecting BigQuery to Looker Studio

1. Open [Google Looker Studio](https://lookerstudio.google.com/).
2. Click **Create** &rarr; **Data Source**.
3. In the Google Connectors search bar, select **BigQuery**.
4. In the left panel:
   * Select **My Projects**.
   * Choose your Google Cloud Project ID.
   * Dataset: `tgm_reporting`.
   * Table or View: Select `v_looker_studio_daily_overview` (recommended) or `unified_ad_performance`.
5. In the top right corner, click **Connect**.

---

## 2. Field Types & Semantic Role Verification

Ensure the following field definitions match in Looker Studio:

| Field Name | Type | Aggregation |
| :--- | :--- | :--- |
| `date` | Date (YYYYMMDD) | None |
| `platform` | Text | None |
| `client_name` | Text | None |
| `campaign_name` | Text | None |
| `spend` | Currency (USD / Local) | SUM |
| `impressions` | Number | SUM |
| `clicks` | Number | SUM |
| `conversions` | Number | SUM |
| `conversion_value`| Currency (USD) | SUM |

---

## 3. Recommended Visualizations & Layout

### Top Scorecard Bar
* **Total Ad Spend**: `SUM(spend)` (Comparison to previous period).
* **Attributed Revenue**: `SUM(conversion_value)`.
* **Blended ROAS**: Calculated Field `SUM(conversion_value) / NULLIF(SUM(spend), 0)`.
* **Total Conversions**: `SUM(conversions)`.
* **Blended CPA**: Calculated Field `SUM(spend) / NULLIF(SUM(conversions), 0)`.

### Charts & Breakdowns
1. **Time-Series Combo Chart**:
   * Dimension: `date`
   * Metrics: `SUM(spend)` (Bars) and `Blended ROAS` or `Attributed Revenue` (Line on secondary Y-axis).
2. **Platform Share Donut Chart**:
   * Dimension: `platform`
   * Metric: `SUM(spend)`
3. **Cross-Channel Performance Matrix Table**:
   * Dimensions: `platform`, `campaign_name`, `campaign_type`
   * Metrics: `SUM(spend)`, `SUM(impressions)`, `SUM(clicks)`, `Blended CTR`, `Blended CPC`, `SUM(conversions)`, `Attributed Revenue`, `Blended ROAS`.
   * Apply heatmap formatting to `Blended ROAS` and `SUM(spend)`.

### Controls & Dropdowns
* **Date Range Control**: Fixed to top right (Default: Last 30 Days).
* **Client Dropdown Filter**: Dimension `client_name`.
* **Platform Dropdown Filter**: Dimension `platform` (Meta, Google, LinkedIn, TikTok, Snapchat).

---

## 4. Embedding Looker Studio in the Agency Portal

1. In your Looker Studio report, click **File &rarr; Embed report**.
2. Check **Enable embedding**.
3. Choose **Embed URL** (or copy the iframe `src`).
4. Copy the URL (format: `https://lookerstudio.google.com/embed/reporting/XXXXXXXX-XXXX...`).
5. In **TGM Reporting Studio**, navigate to the **Looker Studio** tab.
6. Paste the URL into the **Looker Studio Embedded Dashboard** input field and click **Save & Load**.
7. Your agency team and clients can now view and interact with the live Looker Studio dashboard directly from the agency portal!
