from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class MetaCredentials(BaseModel):
    enabled: bool = False
    access_token: str = ""
    ad_account_id: str = ""  # act_XXXXXXXX
    app_id: Optional[str] = ""
    app_secret: Optional[str] = ""

class GoogleAdsCredentials(BaseModel):
    enabled: bool = False
    developer_token: str = ""
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    customer_id: str = ""  # XXX-XXX-XXXX without hyphens
    login_customer_id: Optional[str] = ""

class LinkedInCredentials(BaseModel):
    enabled: bool = False
    access_token: str = ""
    ad_account_id: str = ""  # numeric account ID or URN

class TikTokCredentials(BaseModel):
    enabled: bool = False
    access_token: str = ""
    advertiser_id: str = ""

class SnapchatCredentials(BaseModel):
    enabled: bool = False
    access_token: str = ""
    ad_account_id: str = ""

class ClientPlatformCredentials(BaseModel):
    meta: MetaCredentials = Field(default_factory=MetaCredentials)
    google: GoogleAdsCredentials = Field(default_factory=GoogleAdsCredentials)
    linkedin: LinkedInCredentials = Field(default_factory=LinkedInCredentials)
    tiktok: TikTokCredentials = Field(default_factory=TikTokCredentials)
    snapchat: SnapchatCredentials = Field(default_factory=SnapchatCredentials)

class ClientProfile(BaseModel):
    id: str
    name: str
    website: Optional[str] = ""
    industry: Optional[str] = "E-Commerce"
    currency: str = "USD"
    is_active: bool = True
    google_sheet_url: Optional[str] = ""
    google_sheet_gid: Optional[str] = "0"
    last_sheet_synced_at: Optional[str] = None
    total_spend: float = 0.0
    total_revenue: float = 0.0
    total_records: int = 0
    credentials: ClientPlatformCredentials = Field(default_factory=ClientPlatformCredentials)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class BigQueryConfig(BaseModel):
    project_id: str = ""
    dataset_id: str = "tgm_reporting"
    table_name: str = "unified_ad_performance"
    service_account_json: Optional[str] = ""
    location: str = "US"
    auto_push: bool = False
    last_connection_test: Optional[str] = None
    connection_status: str = "unconfigured"  # unconfigured, connected, failed

class SyncJobRequest(BaseModel):
    client_ids: List[str] = Field(default_factory=list, description="List of client IDs or empty for all active")
    platforms: List[str] = Field(default_factory=lambda: ["meta", "google", "linkedin", "tiktok", "snapchat"])
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    use_mock: bool = Field(False, description="Use sandbox mock generator if true or if platform credentials missing")
    push_to_bigquery: bool = Field(False, description="Whether to stream cleaned rows directly into BigQuery")

class SyncJobLog(BaseModel):
    id: Optional[int] = None
    job_id: str
    client_id: str
    client_name: str
    platform: str
    status: str  # pending, running, success, warning, failed
    rows_extracted: int = 0
    rows_cleaned: int = 0
    rows_exported_bq: int = 0
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
