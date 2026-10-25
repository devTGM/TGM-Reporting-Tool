import time
import uuid
import logging
from typing import List, Dict, Any
from datetime import datetime

from backend.app.models.client import ClientProfile, SyncJobRequest, SyncJobLog
from backend.app.models.schema import UnifiedAdRecord
from backend.app.database import (
    get_all_clients, get_client_by_id, upsert_cleaned_records,
    log_sync_job, get_bigquery_config
)
from backend.app.connectors.meta import MetaAdsConnector
from backend.app.connectors.google_ads import GoogleAdsConnector
from backend.app.connectors.linkedin import LinkedInAdsConnector
from backend.app.connectors.tiktok import TikTokAdsConnector
from backend.app.connectors.snapchat import SnapchatAdsConnector
from backend.app.connectors.mock_data import generate_mock_ad_data
from backend.app.pipeline.cleaner import clean_and_normalize_records
from backend.app.pipeline.validator import audit_and_validate_records
from backend.app.pipeline.bigquery_exporter import BigQueryExporter

logger = logging.getLogger("SyncService")

class SyncService:
    def __init__(self):
        self.connectors = {
            "meta": MetaAdsConnector(),
            "google": GoogleAdsConnector(),
            "linkedin": LinkedInAdsConnector(),
            "tiktok": TikTokAdsConnector(),
            "snapchat": SnapchatAdsConnector()
        }

    def execute_sync_job(self, req: SyncJobRequest) -> Dict[str, Any]:
        """
        Executes end-to-end sync job:
        1. Select clients (all active or requested IDs).
        2. For each client and platform:
           - Fetch raw insights (via official API or Sandbox Mock).
        3. Clean and normalize data (standard schema, date formats, casing, currency, zero division).
        4. Validate data health (quality scoring).
        5. Upsert to local SQLite lake.
        6. Stream to Google BigQuery if requested/configured.
        7. Record audit logs.
        """
        job_id = f"sync_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        # 1. Resolve clients
        if req.client_ids:
            clients = [c for c in (get_client_by_id(cid) for cid in req.client_ids) if c and c.is_active]
        else:
            clients = [c for c in get_all_clients() if c.is_active]

        if not clients:
            return {
                "success": False,
                "error": "No active clients found to sync. Please add a client first.",
                "job_id": job_id
            }

        all_extracted_records: List[UnifiedAdRecord] = []
        platform_logs: List[Dict[str, Any]] = []
        bq_config = get_bigquery_config()
        bq_exporter = BigQueryExporter(bq_config) if (req.push_to_bigquery or bq_config.auto_push) else None

        for client in clients:
            for platform in req.platforms:
                plat_lower = platform.lower()
                connector = self.connectors.get(plat_lower)
                plat_start = time.time()
                
                rows_from_plat: List[UnifiedAdRecord] = []
                status = "success"
                error_msg = None

                # Check if credentials exist and are enabled
                creds_obj = getattr(client.credentials, plat_lower, None)
                is_enabled = getattr(creds_obj, "enabled", False) if creds_obj else False

                try:
                    if req.use_mock or not is_enabled:
                        # Use mock sandbox generator
                        rows_from_plat = generate_mock_ad_data(
                            client=client,
                            platforms=[plat_lower],
                            start_date=req.start_date,
                            end_date=req.end_date
                        )
                    else:
                        # Call live API connector
                        rows_from_plat = connector.fetch_insights(
                            client=client,
                            start_date=req.start_date,
                            end_date=req.end_date
                        )
                except Exception as e:
                    status = "failed"
                    error_msg = str(e)
                    logger.error(f"Error syncing {platform} for {client.name}: {e}")

                all_extracted_records.extend(rows_from_plat)
                plat_duration = round(time.time() - plat_start, 2)

                log_entry = SyncJobLog(
                    job_id=job_id,
                    client_id=client.id,
                    client_name=client.name,
                    platform=platform.capitalize(),
                    status=status,
                    rows_extracted=len(rows_from_plat),
                    rows_cleaned=len(rows_from_plat),
                    rows_exported_bq=0,
                    started_at=datetime.utcnow().isoformat(),
                    completed_at=datetime.utcnow().isoformat(),
                    duration_seconds=plat_duration,
                    error_message=error_msg,
                    details={"mode": "mock" if (req.use_mock or not is_enabled) else "api"}
                )
                log_sync_job(log_entry)
                platform_logs.append(log_entry.dict())

        # 2. Automated Data Cleaning & Normalization Pipeline
        cleaned_records, clean_stats = clean_and_normalize_records(all_extracted_records)

        # 3. Validation and Health Audit
        audit_report = audit_and_validate_records(cleaned_records)

        # 4. Upsert into local SQLite cache
        rows_saved_local = upsert_cleaned_records(cleaned_records)

        # 5. Push to BigQuery if requested
        bq_result = None
        rows_pushed_bq = 0
        if bq_exporter and cleaned_records:
            bq_result = bq_exporter.upsert_records(cleaned_records)
            if bq_result.get("success"):
                rows_pushed_bq = bq_result.get("rows_inserted", 0)

        total_duration = round(time.time() - start_time, 2)

        return {
            "success": True,
            "job_id": job_id,
            "duration_seconds": total_duration,
            "clients_synced": len(clients),
            "rows_extracted": len(all_extracted_records),
            "rows_cleaned": len(cleaned_records),
            "rows_saved_local": rows_saved_local,
            "rows_exported_bq": rows_pushed_bq,
            "cleaning_stats": clean_stats,
            "data_health_audit": audit_report,
            "bigquery_export": bq_result,
            "platform_logs": platform_logs
        }

sync_service = SyncService()
