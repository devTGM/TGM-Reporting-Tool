import os
import csv
import io
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from backend.app.config import BASE_DIR
from backend.app.models.client import (
    ClientProfile, BigQueryConfig, SyncJobRequest, MetaCredentials,
    GoogleAdsCredentials, LinkedInCredentials, TikTokCredentials, SnapchatCredentials
)
from backend.app.database import (
    get_all_clients, get_client_by_id, save_client, delete_client,
    get_bigquery_config, save_bigquery_config, get_setting, save_setting,
    get_cleaned_records, get_performance_summary, get_recent_sync_logs,
    authenticate_user, create_session, get_user_by_session_token, delete_session,
    get_all_users, get_user_by_id, create_user, update_user_permissions, delete_user,
    get_or_create_share_link, regenerate_share_link, get_client_by_share_token
)
from backend.app.services.sync_service import sync_service
from backend.app.services.looker_service import LookerStudioService
from backend.app.pipeline.bigquery_exporter import BigQueryExporter

app = FastAPI(
    title="TGM Reporting Studio",
    description="Cross-Channel Ad Reporting Pipeline & Agency Portal for Looker Studio",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed sample agency clients if none exist
def seed_initial_clients():
    existing = get_all_clients()
    if not existing:
        sample_clients = [
            ClientProfile(
                id="client_apex_01",
                name="Apex Global Direct",
                website="https://apexglobal.example.com",
                industry="eCommerce & Apparel",
                currency="INR",
                is_active=True
            ),
            ClientProfile(
                id="client_nexus_02",
                name="Nexus Enterprise Cloud",
                website="https://nexuscloud.example.com",
                industry="B2B SaaS",
                currency="INR",
                is_active=True
            ),
            ClientProfile(
                id="client_zenith_03",
                name="Zenith Health & Wellness",
                website="https://zenithwellness.example.com",
                industry="D2C Consumer Brands",
                currency="INR",
                is_active=True
            )
        ]
        for c in sample_clients:
            save_client(c)

    # Check if cleaned_records_v2 has rows
    records_data = get_cleaned_records(limit=1)
    if records_data.get("total", 0) == 0:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        two_weeks_ago = (datetime.utcnow() - timedelta(days=21)).strftime("%Y-%m-%d")
        sync_service.execute_sync_job(
            SyncJobRequest(
                client_ids=["client_apex_01", "client_nexus_02"],
                platforms=["meta", "google", "linkedin", "tiktok", "snapchat"],
                start_date=two_weeks_ago,
                end_date=today,
                use_mock=True,
                push_to_bigquery=False
            )
        )

seed_initial_clients()

# ----------------- Health Check ----------------- #
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "TGM Reporting Studio",
        "timestamp": datetime.utcnow().isoformat()
    }

# ----------------- Auth & RBAC Dependencies & Endpoints ----------------- #

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "member"
    assigned_client_ids: List[str] = []

class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    assigned_client_ids: Optional[List[str]] = None
    password: Optional[str] = None

def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif x_session_token:
        token = x_session_token
    if not token:
        return None
    return get_user_by_session_token(token)

def require_auth(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
) -> Dict[str, Any]:
    user = get_current_user_optional(authorization, x_session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required. Please log in.")
    return user

def require_admin(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
) -> Dict[str, Any]:
    user = require_auth(authorization, x_session_token)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Administrator privileges required.")
    return user

def enforce_client_access(user: Optional[Dict[str, Any]], client_id: Optional[str]) -> Optional[str]:
    if not user or user.get("role") == "admin":
        return client_id
    assigned = user.get("assigned_client_ids", [])
    if "*" in assigned:
        return client_id
    if not assigned:
        raise HTTPException(status_code=403, detail="No client access assigned to your user account.")
    if client_id:
        if client_id not in assigned:
            raise HTTPException(status_code=403, detail="You do not have permission to view this client's data.")
        return client_id
    return assigned[0]

@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_session(user["id"])
    return {
        "success": True,
        "token": token,
        "user": user
    }

@app.get("/api/auth/me")
def get_current_user_profile(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    user = require_auth(authorization, x_session_token)
    return user

@app.post("/api/auth/logout")
def logout(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif x_session_token:
        token = x_session_token
    if token:
        delete_session(token)
    return {"success": True, "message": "Logged out successfully."}

# ----------------- Team & Permissions Management (Admin Only) ----------------- #

@app.get("/api/team/users")
def list_team_users(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    return get_all_users()

@app.post("/api/team/users")
def add_team_user(
    req: CreateUserRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    all_u = get_all_users()
    if any(u["email"].lower() == req.email.strip().lower() for u in all_u):
        raise HTTPException(status_code=400, detail="User with this email already exists.")
    user = create_user(
        email=req.email,
        password=req.password,
        name=req.name,
        role=req.role,
        assigned_client_ids=req.assigned_client_ids
    )
    return user

@app.put("/api/team/users/{user_id}")
def update_team_user(
    user_id: str,
    req: UpdateUserRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    updated = update_user_permissions(
        user_id=user_id,
        name=req.name,
        role=req.role,
        assigned_client_ids=req.assigned_client_ids,
        password=req.password
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found.")
    return updated

@app.delete("/api/team/users/{user_id}")
def remove_team_user(
    user_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    current = require_admin(authorization, x_session_token)
    if current["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account.")
    success = delete_user(user_id)
    return {"success": success}

# ----------------- Client Management (With RBAC Filtering) ----------------- #

@app.get("/api/clients", response_model=List[ClientProfile])
def list_clients(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    all_c = get_all_clients()
    user = get_current_user_optional(authorization, x_session_token)
    if user and user.get("role") != "admin":
        assigned = user.get("assigned_client_ids", [])
        if "*" not in assigned:
            return [c for c in all_c if c.id in assigned]
    return all_c

@app.get("/api/clients/{client_id}", response_model=ClientProfile)
def get_client(
    client_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    user = get_current_user_optional(authorization, x_session_token)
    if user and user.get("role") != "admin":
        assigned = user.get("assigned_client_ids", [])
        if "*" not in assigned and client_id not in assigned:
            raise HTTPException(status_code=403, detail="Access denied to this client.")
    c = get_client_by_id(client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    return c

@app.post("/api/clients", response_model=ClientProfile)
def create_or_update_client(
    client: ClientProfile,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    return save_client(client)

@app.put("/api/clients/{client_id}", response_model=ClientProfile)
def update_client_profile(
    client_id: str,
    updated: ClientProfile,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    client = get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    updated.id = client_id
    return save_client(updated)

class ClientSheetConfigRequest(BaseModel):
    google_sheet_url: str
    google_sheet_gid: Optional[str] = "0"

@app.post("/api/clients/{client_id}/sheet-config")
def update_client_sheet_config(
    client_id: str,
    req: ClientSheetConfigRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    client = get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.google_sheet_url = req.google_sheet_url.strip()
    client.google_sheet_gid = (req.google_sheet_gid or "0").strip()
    save_client(client)
    return {
        "success": True,
        "message": f"Google Sheet saved for {client.name}",
        "client": client
    }

@app.post("/api/clients/{client_id}/sync-sheet")
def sync_client_sheet_endpoint(
    client_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    user = require_auth(authorization, x_session_token)
    if user.get("role") != "admin":
        allowed_ids = user.get("assigned_clients", [])
        if client_id not in allowed_ids:
            raise HTTPException(status_code=403, detail="Not authorized to sync this client.")
    from backend.app.pipeline.sheets_importer import import_google_sheet_records
    client = get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if not client.google_sheet_url:
        raise HTTPException(status_code=400, detail=f"No Google Sheet configured for {client.name}. Please configure sheet URL first.")
    res = import_google_sheet_records(
        sheet_url_or_id=client.google_sheet_url,
        client_id=client.id,
        gid=client.google_sheet_gid or "0",
        replace_existing=True
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@app.post("/api/clients/{client_id}/clear-data")
def clear_client_data_endpoint(
    client_id: str,
    source: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    client = get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    from backend.app.database import clear_client_records
    deleted = clear_client_records(client_id, source=source)
    return {
        "success": True,
        "message": f"Cleared {deleted} records for {client.name}",
        "deleted_count": deleted
    }

@app.delete("/api/clients/{client_id}")
def remove_client(
    client_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    success = delete_client(client_id)
    return {"success": success, "message": f"Client {client_id} deleted"}

# ----------------- Client Share Links (For Client Dashboard Access) ----------------- #

@app.get("/api/clients/{client_id}/share-link")
def get_client_share_link(
    client_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    user = get_current_user_optional(authorization, x_session_token)
    if user and user.get("role") != "admin":
        assigned = user.get("assigned_client_ids", [])
        if "*" not in assigned and client_id not in assigned:
            raise HTTPException(status_code=403, detail="Access denied to this client's share link.")
    c = get_client_by_id(client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found.")
    link_info = get_or_create_share_link(client_id, c.name, created_by=user["name"] if user else "admin")
    return {
        "client_id": client_id,
        "client_name": c.name,
        "token": link_info["token"],
        "share_url": f"/portal?token={link_info['token']}"
    }

@app.post("/api/clients/{client_id}/share-link/regenerate")
def regenerate_client_share_link_endpoint(
    client_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    user = require_admin(authorization, x_session_token)
    c = get_client_by_id(client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found.")
    link_info = regenerate_share_link(client_id, c.name, created_by=user["name"])
    return {
        "client_id": client_id,
        "client_name": c.name,
        "token": link_info["token"],
        "share_url": f"/portal?token={link_info['token']}"
    }

# ----------------- Public Client Real-Time Portal (Zero Login) ----------------- #

@app.get("/api/portal/{share_token}/info")
def get_portal_info(share_token: str):
    client_info = get_client_by_share_token(share_token)
    if not client_info:
        raise HTTPException(status_code=404, detail="Invalid, expired, or revoked share link.")
    return client_info

@app.get("/api/portal/{share_token}/summary")
def get_portal_summary(
    share_token: str,
    timeframe: str = "day",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    client_info = get_client_by_share_token(share_token)
    if not client_info:
        raise HTTPException(status_code=404, detail="Invalid, expired, or revoked share link.")
    summary = get_performance_summary(
        client_id=client_info["client_id"],
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date
    )
    return {
        "client": client_info,
        "summary": summary
    }

@app.get("/api/portal/{share_token}/nomenclature")
def get_portal_nomenclature(
    share_token: str,
    dimension: str = Query("category", description="category, product, funnel, offer, audience, hook, format, landing_page"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    from backend.app.database import get_weekly_nomenclature_table
    client_info = get_client_by_share_token(share_token)
    if not client_info:
        raise HTTPException(status_code=404, detail="Invalid, expired, or revoked share link.")
    data = get_weekly_nomenclature_table(
        dimension_name=dimension,
        client_id=client_info["client_id"],
        start_date=start_date,
        end_date=end_date
    )
    return {
        "client": client_info,
        "dimension": dimension,
        "records": data
    }

# ----------------- Connector Testing ----------------- #
class TestConnectorRequest(BaseModel):
    platform: str
    credentials: Dict[str, Any]

@app.post("/api/connectors/test")
def test_platform_connector(req: TestConnectorRequest):
    platform = req.platform.lower()
    connector = sync_service.connectors.get(platform)
    if not connector:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    # Map credentials dictionary to typed model
    creds_data = req.credentials
    if platform == "meta":
        typed_creds = MetaCredentials(**creds_data)
    elif platform == "google":
        typed_creds = GoogleAdsCredentials(**creds_data)
    elif platform == "linkedin":
        typed_creds = LinkedInCredentials(**creds_data)
    elif platform == "tiktok":
        typed_creds = TikTokCredentials(**creds_data)
    elif platform == "snapchat":
        typed_creds = SnapchatCredentials(**creds_data)
    else:
        typed_creds = creds_data

    result = connector.test_connection(typed_creds)
    return result

# ----------------- Sync & Ingestion ----------------- #
@app.post("/api/sync/run")
def trigger_sync(req: SyncJobRequest):
    result = sync_service.execute_sync_job(req)
    return result

@app.get("/api/sync/logs")
def get_sync_logs(limit: int = 25):
    return get_recent_sync_logs(limit)

# ----------------- Google Sheets Sync ----------------- #
class GoogleSheetSyncRequest(BaseModel):
    sheet_url_or_id: Optional[str] = None
    client_id: Optional[str] = None
    gid: Optional[str] = "0"
    replace_existing: bool = True
    push_to_bigquery: bool = False

@app.post("/api/sheets/sync")
def sync_google_sheet(req: GoogleSheetSyncRequest):
    from backend.app.pipeline.sheets_importer import import_google_sheet_records
    res = import_google_sheet_records(
        sheet_url_or_id=req.sheet_url_or_id,
        client_id=req.client_id,
        gid=req.gid or "0",
        replace_existing=req.replace_existing,
        push_to_bigquery=req.push_to_bigquery
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

# ----------------- Performance & Cleaned Data ----------------- #
@app.get("/api/data/records")
def query_records(
    client_id: Optional[str] = None,
    platform: Optional[str] = None,
    category: Optional[str] = None,
    funnel: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    user = get_current_user_optional(authorization, x_session_token)
    scoped_client_id = enforce_client_access(user, client_id)
    return get_cleaned_records(
        client_id=scoped_client_id,
        platform=platform,
        category=category,
        funnel=funnel,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )

@app.get("/api/data/summary")
def get_summary(
    client_id: Optional[str] = None,
    timeframe: str = "day",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    user = get_current_user_optional(authorization, x_session_token)
    scoped_client_id = enforce_client_access(user, client_id)
    return get_performance_summary(
        client_id=scoped_client_id,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date
    )

@app.get("/api/data/nomenclature/weekly")
def get_weekly_nomenclature(
    dimension: str = Query("category", description="category, product, funnel, offer, audience, hook, format, landing_page"),
    client_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    from backend.app.database import get_weekly_nomenclature_table
    user = get_current_user_optional(authorization, x_session_token)
    scoped_client_id = enforce_client_access(user, client_id)
    return get_weekly_nomenclature_table(
        dimension_name=dimension,
        client_id=scoped_client_id,
        start_date=start_date,
        end_date=end_date
    )

@app.get("/api/data/export/csv")
def export_csv(
    client_id: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    user = get_current_user_optional(authorization, x_session_token)
    scoped_client_id = enforce_client_access(user, client_id)
    data = get_cleaned_records(client_id=scoped_client_id, limit=10000, offset=0)
    records = data.get("records", [])
    if not records:
        raise HTTPException(status_code=404, detail="No records to export")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(records[0].keys()))
    writer.writeheader()
    writer.writerows(records)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cleaned_ad_reporting_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )

@app.post("/api/data/clear-demo")
def clear_demo_records_route(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    from backend.app.database import delete_demo_records
    deleted = delete_demo_records()
    return {"success": True, "deleted_count": deleted}

# ----------------- BigQuery Configuration ----------------- #
@app.get("/api/bigquery/config", response_model=BigQueryConfig)
def get_bq_config():
    return get_bigquery_config()

@app.post("/api/bigquery/config", response_model=BigQueryConfig)
def update_bq_config(
    config: BigQueryConfig,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    save_bigquery_config(config)
    return config

@app.post("/api/bigquery/test")
def test_bigquery(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    config = get_bigquery_config()
    exporter = BigQueryExporter(config)
    res = exporter.test_connection()
    if res.get("success"):
        config.connection_status = "connected"
        config.last_connection_test = datetime.utcnow().isoformat()
        save_bigquery_config(config)
    else:
        config.connection_status = "failed"
        save_bigquery_config(config)
    return res

@app.post("/api/bigquery/deploy")
def deploy_bigquery_schema(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    config = get_bigquery_config()
    exporter = BigQueryExporter(config)
    return exporter.ensure_dataset_and_table()

# ----------------- Looker Studio Hub ----------------- #
@app.get("/api/looker/resources")
def get_looker_resources():
    return LookerStudioService.get_dashboard_resources()

@app.get("/api/looker/embed-url")
def get_embed_url():
    url = get_setting("looker_embed_url", "")
    return {"embed_url": url}

class EmbedUrlRequest(BaseModel):
    embed_url: str

@app.post("/api/looker/embed-url")
def set_embed_url(
    req: EmbedUrlRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    require_admin(authorization, x_session_token)
    save_setting("looker_embed_url", req.embed_url)
    return {"success": True, "embed_url": req.embed_url}

# ----------------- Serve Frontend Static UI ----------------- #
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.api_route("/", methods=["GET", "HEAD"])
    def serve_index():
        return FileResponse(frontend_dir / "index.html")

    @app.get("/portal")
    def serve_portal():
        portal_file = frontend_dir / "portal.html"
        if portal_file.exists():
            return FileResponse(portal_file)
        return FileResponse(frontend_dir / "index.html")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        target = frontend_dir / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(frontend_dir / "index.html")
