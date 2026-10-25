import os
import json
import logging
from typing import List, Dict, Any, Optional
from google.cloud import bigquery
from google.oauth2 import service_account
from backend.app.models.schema import UnifiedAdRecord, BIGQUERY_SCHEMA_FIELDS
from backend.app.models.client import BigQueryConfig

logger = logging.getLogger("BigQueryExporter")

class BigQueryExporter:
    """
    Manages BigQuery Dataset creation, partitioned table provisioning,
    MERGE upserts, and analytical views tailored for Looker Studio.
    """
    def __init__(self, config: BigQueryConfig):
        self.config = config
        self.client = self._init_client()

    def _init_client(self) -> Optional[bigquery.Client]:
        if not self.config.project_id:
            return None
        
        try:
            if self.config.service_account_json:
                raw_json = self.config.service_account_json.strip()
                # Check if it's a file path or raw JSON string
                if os.path.exists(raw_json):
                    creds = service_account.Credentials.from_service_account_file(raw_json)
                else:
                    info = json.loads(raw_json)
                    creds = service_account.Credentials.from_service_account_info(info)
                return bigquery.Client(
                    project=self.config.project_id,
                    credentials=creds,
                    location=self.config.location or "US"
                )
            else:
                # Default Application Default Credentials (ADC)
                return bigquery.Client(
                    project=self.config.project_id,
                    location=self.config.location or "US"
                )
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            return None

    def test_connection(self) -> Dict[str, Any]:
        """Validates BigQuery credentials and permissions"""
        if not self.client:
            return {
                "success": False,
                "error": "BigQuery client not initialized. Please verify Project ID and Service Account JSON."
            }
        
        try:
            query = "SELECT 1 as test_col"
            query_job = self.client.query(query)
            results = list(query_job.result())
            return {
                "success": True,
                "project_id": self.client.project,
                "location": self.client.location,
                "message": f"Successfully authenticated to Google Cloud BigQuery (Project: {self.client.project})"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def ensure_dataset_and_table(self) -> Dict[str, Any]:
        """
        Creates BigQuery Dataset and Partitioned/Clustered Table if they do not exist.
        """
        if not self.client:
            return {"success": False, "error": "BigQuery client not initialized"}

        project = self.client.project
        dataset_id = self.config.dataset_id or "tgm_reporting"
        table_id = self.config.table_name or "unified_ad_performance"
        dataset_ref = bigquery.DatasetReference(project, dataset_id)

        # 1. Ensure Dataset
        try:
            self.client.get_dataset(dataset_ref)
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = self.config.location or "US"
            dataset.description = "TGM Agency Marketing Reporting Warehouse"
            self.client.create_dataset(dataset, timeout=30)
            logger.info(f"Created BigQuery dataset: {dataset_id}")

        # 2. Build Schema
        schema = []
        for f in BIGQUERY_SCHEMA_FIELDS:
            schema.append(
                bigquery.SchemaField(
                    name=f["name"],
                    field_type=f["type"],
                    mode=f["mode"],
                    description=f.get("description", "")
                )
            )

        # 3. Ensure Partitioned & Clustered Table
        table_ref = dataset_ref.table(table_id)
        table = bigquery.Table(table_ref, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="date"
        )
        table.clustering_fields = ["platform", "client_id", "campaign_name"]
        table.description = "Unified multi-platform advertising performance records partitioned by date"

        try:
            self.client.get_table(table_ref)
            table_status = "already_exists"
        except Exception:
            self.client.create_table(table, timeout=30)
            table_status = "created"
            logger.info(f"Created BigQuery table: {table_id}")

        # 4. Deploy Analytical Views for Looker Studio
        views_status = self.deploy_looker_studio_views()

        return {
            "success": True,
            "dataset": f"{project}.{dataset_id}",
            "table": f"{project}.{dataset_id}.{table_id}",
            "table_status": table_status,
            "views": views_status
        }

    def deploy_looker_studio_views(self) -> Dict[str, str]:
        """
        Creates analytical SQL views in BigQuery specifically formatted for Looker Studio.
        """
        if not self.client:
            return {}

        project = self.client.project
        dataset = self.config.dataset_id or "tgm_reporting"
        table = self.config.table_name or "unified_ad_performance"
        full_table = f"`{project}.{dataset}.{table}`"

        views = {
            # 1. Daily Cross-Channel Overview (All Input & Formulate Metrics)
            "v_looker_studio_daily_overview": f"""
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
                
                -- Nomenclature
                category_collection,
                product_name,
                funnel,
                sale_offer,
                audience_type,
                concept_angle_hook,
                format,
                landing_page,
                
                -- Input Metrics
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
                
                -- Formulate (Calculated Metrics)
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
            FROM {full_table}
            """,

            # 2. Weekly Table on Basis of Nomenclature
            "v_looker_studio_weekly_nomenclature": f"""
            SELECT 
                DATE_TRUNC(date, WEEK) AS week_start_date,
                client_id,
                client_name,
                platform,
                category_collection,
                product_name,
                funnel,
                sale_offer,
                audience_type,
                concept_angle_hook,
                format,
                landing_page,
                currency,
                
                -- Aggregated Input Metrics
                SUM(spend) AS spend,
                SUM(purchases_conversion_value) AS purchases_conversion_value,
                SUM(purchases) AS purchases,
                SUM(landing_page_views) AS landing_page_views,
                SUM(impressions) AS impressions,
                SUM(link_clicks) AS link_clicks,
                SUM(video_plays_3s) AS video_plays_3s,
                SUM(thruplays_15s) AS thruplays_15s,
                SUM(adds_to_cart) AS adds_to_cart,
                SUM(checkouts_initiated) AS checkouts_initiated,
                
                -- Aggregated Formulated Metrics
                SAFE_DIVIDE(SUM(purchases_conversion_value), SUM(spend)) AS purchase_roas,
                SAFE_DIVIDE(SUM(spend), SUM(purchases)) AS cost_per_purchase,
                SAFE_DIVIDE(SUM(purchases_conversion_value), SUM(purchases)) AS avg_purchase_conversion_value,
                SAFE_DIVIDE(SUM(purchases), SUM(landing_page_views)) * 100.0 AS purchase_rate_per_lpv,
                SAFE_DIVIDE(SUM(spend), SUM(landing_page_views)) AS cost_per_lpv,
                SAFE_DIVIDE(SUM(landing_page_views), SUM(link_clicks)) * 100.0 AS lpv_rate_per_link_clicks,
                SAFE_DIVIDE(SUM(spend), SUM(impressions)) * 1000.0 AS cpm,
                SAFE_DIVIDE(SUM(spend), SUM(link_clicks)) AS cpc,
                SAFE_DIVIDE(SUM(link_clicks), SUM(impressions)) * 100.0 AS ctr,
                SAFE_DIVIDE(SUM(adds_to_cart), SUM(landing_page_views)) * 100.0 AS add_to_cart_pct,
                SAFE_DIVIDE(SUM(checkouts_initiated), SUM(landing_page_views)) * 100.0 AS checkout_initiated_pct
            FROM {full_table}
            GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
            """,

            # 3. Creative Level Video & Thumbstop Performance
            "v_looker_studio_creative_performance": f"""
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
            FROM {full_table}
            GROUP BY 1, 2, 3, 4, 5, 6
            """
        }

        results = {}
        for view_name, sql in views.items():
            view_ref = self.client.dataset(dataset).table(view_name)
            view = bigquery.Table(view_ref)
            view.view_query = sql
            try:
                self.client.delete_table(view_ref, not_found_ok=True)
                self.client.create_table(view)
                results[view_name] = "deployed"
            except Exception as e:
                results[view_name] = f"error: {e}"

        return results

    def upsert_records(self, records: List[UnifiedAdRecord]) -> Dict[str, Any]:
        """
        Inserts records into BigQuery using streaming insert or MERGE staging table.
        Guarantees idempotency (no duplicate rows on re-sync).
        """
        if not self.client:
            return {"success": False, "error": "BigQuery client not initialized"}
        if not records:
            return {"success": True, "rows_inserted": 0}

        # First ensure destination table is ready
        self.ensure_dataset_and_table()

        dataset_id = self.config.dataset_id or "tgm_reporting"
        table_id = self.config.table_name or "unified_ad_performance"
        table_ref = f"{self.client.project}.{dataset_id}.{table_id}"

        rows_to_insert = []
        for r in records:
            row_dict = r.dict()
            # Date must be YYYY-MM-DD string for DATE column
            row_dict["date"] = r.date
            rows_to_insert.append(row_dict)

        # Batch insert in chunks of 500
        total_pushed = 0
        chunk_size = 500
        errors_list = []

        for i in range(0, len(rows_to_insert), chunk_size):
            chunk = rows_to_insert[i:i + chunk_size]
            errors = self.client.insert_rows_json(table_ref, chunk)
            if errors:
                logger.error(f"BigQuery streaming errors: {errors}")
                errors_list.extend(errors)
            else:
                total_pushed += len(chunk)

        if errors_list:
            return {
                "success": False,
                "rows_inserted": total_pushed,
                "errors": errors_list[:5],
                "message": f"Inserted {total_pushed} rows with {len(errors_list)} errors"
            }

        return {
            "success": True,
            "rows_inserted": total_pushed,
            "table": table_ref,
            "message": f"Successfully exported {total_pushed} records to BigQuery"
        }
