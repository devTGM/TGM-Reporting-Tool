import sqlite3
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from backend.app.config import DB_PATH
from backend.app.models.client import ClientProfile, BigQueryConfig, SyncJobLog
from backend.app.models.schema import UnifiedAdRecord

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000)
    return f"{salt}${key.hex()}"

def verify_password(stored_hash: str, password: str) -> bool:
    try:
        salt, key_hex = stored_hash.split('$')
        new_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000)
        return secrets.compare_digest(new_key.hex(), key_hex)
    except Exception:
        return False

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Clients Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        website TEXT,
        industry TEXT,
        currency TEXT DEFAULT 'USD',
        is_active INTEGER DEFAULT 1,
        google_sheet_url TEXT DEFAULT '',
        google_sheet_gid TEXT DEFAULT '0',
        last_sheet_synced_at TEXT,
        credentials_json TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)
    
    # Auto-migration for existing database schemas
    cursor.execute("PRAGMA table_info(clients)")
    existing_client_cols = [c[1] for c in cursor.fetchall()]
    if "google_sheet_url" not in existing_client_cols:
        cursor.execute("ALTER TABLE clients ADD COLUMN google_sheet_url TEXT DEFAULT ''")
    if "google_sheet_gid" not in existing_client_cols:
        cursor.execute("ALTER TABLE clients ADD COLUMN google_sheet_gid TEXT DEFAULT '0'")
    if "last_sheet_synced_at" not in existing_client_cols:
        cursor.execute("ALTER TABLE clients ADD COLUMN last_sheet_synced_at TEXT")

    # Seed The Sunya's designated sheet if unset
    cursor.execute("""
    UPDATE clients 
    SET google_sheet_url = 'https://docs.google.com/spreadsheets/d/1yulDW_Xm-pmawzXSqBtRmg1WojiP74FpuyN1T6sp-yQ/edit#gid=886192859',
        google_sheet_gid = '886192859'
    WHERE name = 'The Sunya' AND (google_sheet_url IS NULL OR google_sheet_url = '')
    """)
    
    # Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value_json TEXT,
        updated_at TEXT
    )
    """)
    
    # Cleaned Records Table (Full Schema matching requirements)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cleaned_records_v2 (
        record_id TEXT PRIMARY KEY,
        date TEXT NOT NULL,
        client_id TEXT NOT NULL,
        client_name TEXT,
        platform TEXT NOT NULL,
        account_id TEXT,
        account_name TEXT,
        campaign_id TEXT,
        campaign_name TEXT,
        campaign_type TEXT,
        adset_id TEXT,
        adset_name TEXT,
        ad_id TEXT,
        ad_name TEXT,
        audience_segment TEXT,
        currency TEXT,
        
        -- Nomenclature Tags
        category_collection TEXT,
        product_name TEXT,
        funnel TEXT,
        sale_offer TEXT,
        audience_type TEXT,
        concept_angle_hook TEXT,
        format TEXT,
        landing_page TEXT,
        
        -- Fetch Numbers (Input Metrics)
        spend REAL,
        purchases_conversion_value REAL,
        purchases REAL,
        landing_page_views INTEGER,
        reach INTEGER,
        impressions INTEGER,
        link_clicks INTEGER,
        video_plays_3s INTEGER,
        thruplays_15s INTEGER,
        adds_to_cart INTEGER,
        checkouts_initiated INTEGER,
        
        -- Formulate (Calculated Metrics)
        purchase_roas REAL,
        cost_per_purchase REAL,
        avg_purchase_conversion_value REAL,
        purchase_rate_per_lpv REAL,
        cost_per_lpv REAL,
        lpv_rate_per_link_clicks REAL,
        frequency REAL,
        cpm REAL,
        cpc REAL,
        ctr REAL,
        video_plays_3s_rate_per_impressions REAL,
        cost_per_video_play_3s REAL,
        cost_per_thruplay_15s REAL,
        cost_per_add_to_cart REAL,
        add_to_cart_pct REAL,
        cost_per_checkout_initiated REAL,
        checkout_initiated_pct REAL,
        
        synced_at TEXT,
        source TEXT,
        exported_to_bq INTEGER DEFAULT 0
    )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records2_date ON cleaned_records_v2(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records2_client ON cleaned_records_v2(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records2_platform ON cleaned_records_v2(platform)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records2_category ON cleaned_records_v2(category_collection)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records2_funnel ON cleaned_records_v2(funnel)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records2_format ON cleaned_records_v2(format)")
    
    # Sync Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT,
        client_id TEXT,
        client_name TEXT,
        platform TEXT,
        status TEXT,
        rows_extracted INTEGER,
        rows_cleaned INTEGER,
        rows_exported_bq INTEGER,
        started_at TEXT,
        completed_at TEXT,
        duration_seconds REAL,
        error_message TEXT,
        details_json TEXT
    )
    """)

    # Users Table for Role-Based Access Control (Admin / Team Member)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'member', -- 'admin' or 'member'
        assigned_client_ids TEXT NOT NULL DEFAULT '[]', -- JSON array of client IDs, or '["*"]' for all
        is_active INTEGER DEFAULT 1,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    # Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Client Share Links (Public tokenized real-time access for individual clients)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS client_share_links (
        token TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        client_name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_by TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
    )
    """)

    # Seed default Admin and Team Member if users table is empty
    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()["count"]
    if user_count == 0:
        now = datetime.utcnow().isoformat()
        admin_pwd = hash_password("admin")
        member_pwd = hash_password("alex123")
        
        # 1. Agency Super Admin (Full access to all clients)
        cursor.execute("""
        INSERT INTO users (id, email, password_hash, name, role, assigned_client_ids, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            "user_admin_surya",
            "surya@thinkgrowmedia.com",
            hash_password("ThinkGrow2311@$"),
            "Surya Kumar (Admin)",
            "admin",
            json.dumps(["*"]),
            now,
            now
        ))

    # Migration: Ensure surya@thinkgrowmedia.com exists and has ThinkGrow2311@$
    cursor.execute("SELECT id FROM users WHERE email = 'surya@thinkgrowmedia.com'")
    surya_row = cursor.fetchone()
    surya_hash = hash_password("ThinkGrow2311@$")
    if surya_row:
        cursor.execute("""
        UPDATE users 
        SET password_hash = ?, role = 'admin', assigned_client_ids = ?, updated_at = ?
        WHERE email = 'surya@thinkgrowmedia.com'
        """, (surya_hash, json.dumps(["*"]), datetime.utcnow().isoformat()))
    else:
        cursor.execute("""
        INSERT INTO users (id, email, password_hash, name, role, assigned_client_ids, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            "user_admin_surya",
            "surya@thinkgrowmedia.com",
            surya_hash,
            "Surya Kumar (Admin)",
            "admin",
            json.dumps(["*"]),
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))

    # Remove demo profiles and demo users
    cursor.execute("DELETE FROM clients WHERE id IN ('client_apex_01', 'client_nexus_02', 'client_zenith_03')")
    cursor.execute("DELETE FROM cleaned_records_v2 WHERE client_id IN ('client_apex_01', 'client_nexus_02', 'client_zenith_03')")
    cursor.execute("DELETE FROM client_share_links WHERE client_id IN ('client_apex_01', 'client_nexus_02', 'client_zenith_03')")
    cursor.execute("DELETE FROM users WHERE email = 'alex@thinkgrowmedia.com'")

    # Ensure each client has an active share link
    cursor.execute("SELECT id, name FROM clients")
    all_c = cursor.fetchall()
    now_ts = datetime.utcnow().isoformat()
    for c in all_c:
        cid = c["id"]
        cname = c["name"]
        cursor.execute("SELECT token FROM client_share_links WHERE client_id = ? AND is_active = 1", (cid,))
        if not cursor.fetchone():
            token = f"share_{secrets.token_urlsafe(16)}"
            cursor.execute("""
            INSERT INTO client_share_links (token, client_id, client_name, created_at, is_active, created_by)
            VALUES (?, ?, ?, ?, 1, 'admin')
            """, (token, cid, cname, now_ts))

    conn.commit()
    conn.close()

# ----------------- Client Management ----------------- #

def get_all_clients() -> List[ClientProfile]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients ORDER BY name ASC")
    rows = cursor.fetchall()

    # Aggregate performance metrics per client
    cursor.execute("""
    SELECT 
        client_id, 
        COUNT(*) as total_records, 
        COALESCE(SUM(spend), 0) as total_spend, 
        COALESCE(SUM(purchases_conversion_value), 0) as total_revenue
    FROM cleaned_records_v2 
    GROUP BY client_id
    """)
    stats_map = {r["client_id"]: dict(r) for r in cursor.fetchall()}
    conn.close()
    
    clients = []
    for r in rows:
        data = dict(r)
        cid = data["id"]
        creds = json.loads(data.pop("credentials_json") or "{}")
        c_stats = stats_map.get(cid, {})
        clients.append(ClientProfile(
            **data, 
            credentials=creds,
            total_spend=round(c_stats.get("total_spend", 0.0), 2),
            total_revenue=round(c_stats.get("total_revenue", 0.0), 2),
            total_records=c_stats.get("total_records", 0)
        ))
    return clients

def get_client_by_id(client_id: str) -> Optional[ClientProfile]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    creds = json.loads(data.pop("credentials_json") or "{}")
    return ClientProfile(**data, credentials=creds)

def save_client(client: ClientProfile) -> ClientProfile:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
    INSERT INTO clients (
        id, name, website, industry, currency, is_active, 
        google_sheet_url, google_sheet_gid, last_sheet_synced_at,
        credentials_json, created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        name=excluded.name,
        website=excluded.website,
        industry=excluded.industry,
        currency=excluded.currency,
        is_active=excluded.is_active,
        google_sheet_url=excluded.google_sheet_url,
        google_sheet_gid=excluded.google_sheet_gid,
        last_sheet_synced_at=COALESCE(excluded.last_sheet_synced_at, clients.last_sheet_synced_at),
        credentials_json=excluded.credentials_json,
        updated_at=excluded.updated_at
    """, (
        client.id,
        client.name,
        client.website,
        client.industry,
        client.currency,
        1 if client.is_active else 0,
        client.google_sheet_url or "",
        client.google_sheet_gid or "0",
        client.last_sheet_synced_at,
        json.dumps(client.credentials.dict()),
        client.created_at or now,
        now
    ))
    conn.commit()
    conn.close()
    return client

def clear_client_records(client_id: str, source: Optional[str] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    if source:
        cursor.execute("DELETE FROM cleaned_records_v2 WHERE client_id = ? AND source = ?", (client_id, source))
    else:
        cursor.execute("DELETE FROM cleaned_records_v2 WHERE client_id = ?", (client_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted

def delete_client(client_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    cursor.execute("DELETE FROM cleaned_records_v2 WHERE client_id = ?", (client_id,))
    conn.commit()
    conn.close()
    return True

def delete_demo_records() -> int:
    """Removes all synthetic/mock demo records, preserving only imported Google Sheet records."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM cleaned_records_v2 
        WHERE campaign_name LIKE '[Top]%' 
           OR campaign_name LIKE '[Middle]%' 
           OR campaign_name LIKE '[Bottom]%' 
           OR campaign_name LIKE '[Advantage+]%'
    """)
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted

# ----------------- Settings & BigQuery Config ----------------- #

def get_setting(key: str, default: Any = None) -> Any:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value_json FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row and row["value_json"]:
        return json.loads(row["value_json"])
    return default

def save_setting(key: str, value: Any) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO settings (key, value_json, updated_at)
    VALUES (?, ?, ?)
    ON CONFLICT(key) DO UPDATE SET
        value_json=excluded.value_json,
        updated_at=excluded.updated_at
    """, (key, json.dumps(value), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_bigquery_config() -> BigQueryConfig:
    data = get_setting("bigquery_config")
    if data:
        return BigQueryConfig(**data)
    return BigQueryConfig()

def save_bigquery_config(config: BigQueryConfig) -> None:
    save_setting("bigquery_config", config.dict())

# ----------------- Cleaned Records Storage ----------------- #

def upsert_cleaned_records(records: List[UnifiedAdRecord], exported_to_bq: bool = False) -> int:
    if not records:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    
    inserted_or_updated = 0
    for rec in records:
        rec.calculate_derived_metrics()
        cursor.execute("""
        INSERT INTO cleaned_records_v2 (
            record_id, date, client_id, client_name, platform, account_id, account_name,
            campaign_id, campaign_name, campaign_type, adset_id, adset_name, ad_id, ad_name,
            audience_segment, currency,
            category_collection, product_name, funnel, sale_offer, audience_type, concept_angle_hook, format, landing_page,
            spend, purchases_conversion_value, purchases, landing_page_views, reach, impressions, link_clicks,
            video_plays_3s, thruplays_15s, adds_to_cart, checkouts_initiated,
            purchase_roas, cost_per_purchase, avg_purchase_conversion_value, purchase_rate_per_lpv, cost_per_lpv,
            lpv_rate_per_link_clicks, frequency, cpm, cpc, ctr, video_plays_3s_rate_per_impressions,
            cost_per_video_play_3s, cost_per_thruplay_15s, cost_per_add_to_cart, add_to_cart_pct,
            cost_per_checkout_initiated, checkout_initiated_pct,
            synced_at, source, exported_to_bq
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?
        )
        ON CONFLICT(record_id) DO UPDATE SET
            spend=excluded.spend,
            purchases_conversion_value=excluded.purchases_conversion_value,
            purchases=excluded.purchases,
            landing_page_views=excluded.landing_page_views,
            reach=excluded.reach,
            impressions=excluded.impressions,
            link_clicks=excluded.link_clicks,
            video_plays_3s=excluded.video_plays_3s,
            thruplays_15s=excluded.thruplays_15s,
            adds_to_cart=excluded.adds_to_cart,
            checkouts_initiated=excluded.checkouts_initiated,
            purchase_roas=excluded.purchase_roas,
            cost_per_purchase=excluded.cost_per_purchase,
            avg_purchase_conversion_value=excluded.avg_purchase_conversion_value,
            purchase_rate_per_lpv=excluded.purchase_rate_per_lpv,
            cost_per_lpv=excluded.cost_per_lpv,
            lpv_rate_per_link_clicks=excluded.lpv_rate_per_link_clicks,
            frequency=excluded.frequency,
            cpm=excluded.cpm,
            cpc=excluded.cpc,
            ctr=excluded.ctr,
            video_plays_3s_rate_per_impressions=excluded.video_plays_3s_rate_per_impressions,
            cost_per_video_play_3s=excluded.cost_per_video_play_3s,
            cost_per_thruplay_15s=excluded.cost_per_thruplay_15s,
            cost_per_add_to_cart=excluded.cost_per_add_to_cart,
            add_to_cart_pct=excluded.add_to_cart_pct,
            cost_per_checkout_initiated=excluded.cost_per_checkout_initiated,
            checkout_initiated_pct=excluded.checkout_initiated_pct,
            synced_at=excluded.synced_at,
            exported_to_bq=MAX(cleaned_records_v2.exported_to_bq, excluded.exported_to_bq)
        """, (
            rec.record_id, rec.date, rec.client_id, rec.client_name, rec.platform, rec.account_id, rec.account_name,
            rec.campaign_id, rec.campaign_name, rec.campaign_type, rec.adset_id, rec.adset_name, rec.ad_id, rec.ad_name,
            rec.audience_segment, rec.currency,
            rec.category_collection, rec.product_name, rec.funnel, rec.sale_offer, rec.audience_type, rec.concept_angle_hook, rec.format, rec.landing_page,
            rec.spend, rec.purchases_conversion_value, rec.purchases, rec.landing_page_views, rec.reach, rec.impressions, rec.link_clicks,
            rec.video_plays_3s, rec.thruplays_15s, rec.adds_to_cart, rec.checkouts_initiated,
            rec.purchase_roas, rec.cost_per_purchase, rec.avg_purchase_conversion_value, rec.purchase_rate_per_lpv, rec.cost_per_lpv,
            rec.lpv_rate_per_link_clicks, rec.frequency, rec.cpm, rec.cpc, rec.ctr, rec.video_plays_3s_rate_per_impressions,
            rec.cost_per_video_play_3s, rec.cost_per_thruplay_15s, rec.cost_per_add_to_cart, rec.add_to_cart_pct,
            rec.cost_per_checkout_initiated, rec.checkout_initiated_pct,
            rec.synced_at, rec.source, 1 if exported_to_bq else 0
        ))
        inserted_or_updated += 1
        
    conn.commit()
    conn.close()
    return inserted_or_updated

def get_cleaned_records(
    client_id: Optional[str] = None,
    platform: Optional[str] = None,
    category: Optional[str] = None,
    funnel: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM cleaned_records_v2 WHERE 1=1"
    params = []
    
    if client_id:
        query += " AND client_id = ?"
        params.append(client_id)
    if platform:
        query += " AND LOWER(platform) = ?"
        params.append(platform.lower())
    if category:
        query += " AND category_collection = ?"
        params.append(category)
    if funnel:
        query += " AND funnel = ?"
        params.append(funnel)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
        
    count_query = f"SELECT COUNT(*) as total FROM ({query})"
    cursor.execute(count_query, params)
    total = cursor.fetchone()["total"]
    
    query += " ORDER BY date DESC, spend DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    conn.close()
    return {
        "total": total,
        "records": [dict(r) for r in rows]
    }

def get_performance_summary(
    client_id: Optional[str] = None,
    timeframe: str = "day",  # 'day', 'week', 'month'
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    where_clause = "WHERE 1=1"
    params = []
    if client_id:
        where_clause += " AND client_id = ?"
        params.append(client_id)
    if start_date:
        where_clause += " AND date >= ?"
        params.append(start_date)
    if end_date:
        where_clause += " AND date <= ?"
        params.append(end_date)
        
    cursor.execute(f"""
    SELECT 
        COUNT(DISTINCT record_id) as total_rows,
        COALESCE(SUM(spend), 0) as total_spend,
        COALESCE(SUM(purchases_conversion_value), 0) as total_conversion_value,
        COALESCE(SUM(purchases), 0) as total_purchases,
        COALESCE(SUM(landing_page_views), 0) as total_lpv,
        COALESCE(SUM(reach), 0) as total_reach,
        COALESCE(SUM(impressions), 0) as total_impressions,
        COALESCE(SUM(link_clicks), 0) as total_link_clicks,
        COALESCE(SUM(video_plays_3s), 0) as total_video_plays_3s,
        COALESCE(SUM(thruplays_15s), 0) as total_thruplays_15s,
        COALESCE(SUM(adds_to_cart), 0) as total_adds_to_cart,
        COALESCE(SUM(checkouts_initiated), 0) as total_checkouts_initiated,
        COUNT(DISTINCT client_id) as active_clients_count,
        COUNT(DISTINCT platform) as active_platforms_count
    FROM cleaned_records_v2
    {where_clause}
    """, params)
    totals = dict(cursor.fetchone() or {})
    
    spend = totals.get("total_spend", 0.0)
    rev = totals.get("total_conversion_value", 0.0)
    purchases = totals.get("total_purchases", 0.0)
    lpv = totals.get("total_lpv", 0)
    clicks = totals.get("total_link_clicks", 0)
    impr = totals.get("total_impressions", 0)
    reach = totals.get("total_reach", 0)
    v3s = totals.get("total_video_plays_3s", 0)
    v15s = totals.get("total_thruplays_15s", 0)
    atc = totals.get("total_adds_to_cart", 0)
    ic = totals.get("total_checkouts_initiated", 0)
    
    # Formulated Metrics Calculation
    totals["purchase_roas"] = round(rev / spend, 2) if spend > 0 else 0.0
    totals["cost_per_purchase"] = round(spend / purchases, 2) if purchases > 0 else 0.0
    totals["avg_purchase_conversion_value"] = round(rev / purchases, 2) if purchases > 0 else 0.0
    totals["purchase_rate_per_lpv"] = round((purchases / lpv) * 100, 2) if lpv > 0 else 0.0
    totals["cost_per_lpv"] = round(spend / lpv, 2) if lpv > 0 else 0.0
    totals["lpv_rate_per_link_clicks"] = round((lpv / clicks) * 100, 2) if clicks > 0 else 0.0
    totals["frequency"] = round(impr / reach, 2) if reach > 0 else 1.0
    totals["cpm"] = round((spend / impr) * 1000, 2) if impr > 0 else 0.0
    totals["cpc"] = round(spend / clicks, 2) if clicks > 0 else 0.0
    totals["ctr"] = round((clicks / impr) * 100, 2) if impr > 0 else 0.0
    totals["video_plays_3s_rate_per_impressions"] = round((v3s / impr) * 100, 2) if impr > 0 else 0.0
    totals["cost_per_video_play_3s"] = round(spend / v3s, 3) if v3s > 0 else 0.0
    totals["cost_per_thruplay_15s"] = round(spend / v15s, 3) if v15s > 0 else 0.0
    totals["cost_per_add_to_cart"] = round(spend / atc, 2) if atc > 0 else 0.0
    totals["add_to_cart_pct"] = round((atc / lpv) * 100, 2) if lpv > 0 else 0.0
    totals["cost_per_checkout_initiated"] = round(spend / ic, 2) if ic > 0 else 0.0
    totals["checkout_initiated_pct"] = round((ic / lpv) * 100, 2) if lpv > 0 else 0.0
    
    # Platform Breakdown
    cursor.execute(f"""
    SELECT 
        platform,
        COALESCE(SUM(spend), 0) as spend,
        COALESCE(SUM(purchases_conversion_value), 0) as conversion_value,
        COALESCE(SUM(purchases), 0) as purchases,
        COALESCE(SUM(landing_page_views), 0) as landing_page_views,
        COALESCE(SUM(reach), 0) as reach,
        COALESCE(SUM(impressions), 0) as impressions,
        COALESCE(SUM(link_clicks), 0) as link_clicks,
        COALESCE(SUM(adds_to_cart), 0) as adds_to_cart,
        COALESCE(SUM(checkouts_initiated), 0) as checkouts_initiated
    FROM cleaned_records_v2
    {where_clause}
    GROUP BY platform
    ORDER BY spend DESC, impressions DESC
    """, params)
    by_platform = [dict(r) for r in cursor.fetchall()]
    for p in by_platform:
        s = p.get("spend", 0)
        cv = p.get("conversion_value", 0)
        pu = p.get("purchases", 0)
        im = p.get("impressions", 0)
        cl = p.get("link_clicks", 0)
        lp = p.get("landing_page_views", 0)
        p["purchase_roas"] = round(cv / s, 2) if s > 0 else 0.0
        p["cpa"] = round(s / pu, 2) if pu > 0 else 0.0
        p["cpc"] = round(s / cl, 2) if cl > 0 else 0.0
        p["cpm"] = round((s / im) * 1000, 2) if im > 0 else 0.0
        p["ctr"] = round((cl / im) * 100, 2) if im > 0 else 0.0
        p["purchase_rate_lpv"] = round((pu / lp) * 100, 2) if lp > 0 else 0.0

    # Trend grouped by Day, Week, or Month
    date_group = "date"
    if timeframe == "week":
        date_group = "strftime('%Y-W%W', date)"
    elif timeframe == "month":
        date_group = "strftime('%Y-%m', date)"

    cursor.execute(f"""
    SELECT 
        {date_group} as time_bucket,
        COALESCE(SUM(spend), 0) as spend,
        COALESCE(SUM(purchases_conversion_value), 0) as conversion_value,
        COALESCE(SUM(purchases), 0) as purchases,
        COALESCE(SUM(reach), 0) as reach,
        COALESCE(SUM(link_clicks), 0) as clicks,
        COALESCE(SUM(impressions), 0) as impressions
    FROM cleaned_records_v2
    {where_clause}
    GROUP BY 1
    ORDER BY 1 ASC
    LIMIT 60
    """, params)
    time_trend = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "totals": totals,
        "by_platform": by_platform,
        "time_trend": time_trend
    }

def get_weekly_nomenclature_table(
    dimension_name: str,
    client_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Computes Weekly Performance on basis of nomenclature:
    - CATEGORY/COLLECTION
    - PRODUCTNAME
    - FUNNEL
    - (SALENAME+OFFER)
    - AUDIENCETYPE
    - CONCEPT/ANGLE-HOOK
    - FORMAT
    - LANDINGPAGE
    """
    valid_dims = {
        "category": "category_collection",
        "category_collection": "category_collection",
        "category/collection": "category_collection",
        "product": "product_name",
        "product_name": "product_name",
        "productname": "product_name",
        "funnel": "funnel",
        "offer": "sale_offer",
        "sale_offer": "sale_offer",
        "salename+offer": "sale_offer",
        "(salename+offer)": "sale_offer",
        "sale": "sale_offer",
        "audience": "audience_type",
        "audience_type": "audience_type",
        "audiencetype": "audience_type",
        "hook": "concept_angle_hook",
        "concept": "concept_angle_hook",
        "concept_angle_hook": "concept_angle_hook",
        "concept/angle-hook": "concept_angle_hook",
        "format": "format",
        "landing_page": "landing_page",
        "landingpage": "landing_page"
    }
    col = valid_dims.get(dimension_name.lower().strip(), "category_collection")

    conn = get_connection()
    cursor = conn.cursor()
    
    where = f"WHERE {col} IS NOT NULL AND {col} != ''"
    params = []
    if client_id:
        where += " AND client_id = ?"
        params.append(client_id)
    if start_date:
        where += " AND date >= ?"
        params.append(start_date)
    if end_date:
        where += " AND date <= ?"
        params.append(end_date)

    cursor.execute(f"""
    SELECT 
        strftime('%Y-W%W', date) as week_period,
        {col} as nomenclature_value,
        COALESCE(SUM(spend), 0) as spend,
        COALESCE(SUM(purchases_conversion_value), 0) as purchases_conversion_value,
        COALESCE(SUM(purchases), 0) as purchases,
        COALESCE(SUM(landing_page_views), 0) as landing_page_views,
        COALESCE(SUM(impressions), 0) as impressions,
        COALESCE(SUM(link_clicks), 0) as link_clicks,
        COALESCE(SUM(adds_to_cart), 0) as adds_to_cart,
        COALESCE(SUM(checkouts_initiated), 0) as checkouts_initiated
    FROM cleaned_records_v2
    {where}
    GROUP BY 1, 2
    ORDER BY week_period DESC, spend DESC
    LIMIT 100
    """, params)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        s = d.get("spend", 0)
        cv = d.get("purchases_conversion_value", 0)
        pu = d.get("purchases", 0)
        lp = d.get("landing_page_views", 0)
        cl = d.get("link_clicks", 0)
        im = d.get("impressions", 0)
        atc = d.get("adds_to_cart", 0)
        ic = d.get("checkouts_initiated", 0)

        d["purchase_roas"] = round(cv / s, 2) if s > 0 else 0.0
        d["cost_per_purchase"] = round(s / pu, 2) if pu > 0 else 0.0
        d["avg_purchase_conversion_value"] = round(cv / pu, 2) if pu > 0 else 0.0
        d["purchase_rate_per_lpv"] = round((pu / lp) * 100, 2) if lp > 0 else 0.0
        d["cost_per_lpv"] = round(s / lp, 2) if lp > 0 else 0.0
        d["add_to_cart_pct"] = round((atc / lp) * 100, 2) if lp > 0 else 0.0
        d["checkout_initiated_pct"] = round((ic / lp) * 100, 2) if lp > 0 else 0.0
        d["cpc"] = round(s / cl, 2) if cl > 0 else 0.0
        d["ctr"] = round((cl / im) * 100, 2) if im > 0 else 0.0
        result.append(d)

    return result

# ----------------- Sync Logs ----------------- #

def log_sync_job(log: SyncJobLog) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO sync_logs (
        job_id, client_id, client_name, platform, status,
        rows_extracted, rows_cleaned, rows_exported_bq,
        started_at, completed_at, duration_seconds, error_message, details_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log.job_id, log.client_id, log.client_name, log.platform, log.status,
        log.rows_extracted, log.rows_cleaned, log.rows_exported_bq,
        log.started_at, log.completed_at, log.duration_seconds, log.error_message,
        json.dumps(log.details or {})
    ))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id

def get_recent_sync_logs(limit: int = 25) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sync_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("details_json"):
            try:
                d["details"] = json.loads(d["details_json"])
            except:
                d["details"] = {}
        result.append(d)
    return result

# ----------------- User Auth & RBAC Management ----------------- #

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?) AND is_active = 1", (email.strip(),))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    user_dict = dict(row)
    if verify_password(user_dict["password_hash"], password):
        user_dict.pop("password_hash", None)
        try:
            user_dict["assigned_client_ids"] = json.loads(user_dict["assigned_client_ids"])
        except Exception:
            user_dict["assigned_client_ids"] = []
        return user_dict
    return None

def create_session(user_id: str, days_valid: int = 7) -> str:
    token = secrets.token_urlsafe(32)
    created_at = datetime.utcnow().isoformat()
    expires_at = (datetime.utcnow() + timedelta(days=days_valid)).isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO sessions (token, user_id, created_at, expires_at)
    VALUES (?, ?, ?, ?)
    """, (token, user_id, created_at, expires_at))
    conn.commit()
    conn.close()
    return token

def get_user_by_session_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
    SELECT u.id, u.email, u.name, u.role, u.assigned_client_ids, u.is_active, s.expires_at
    FROM sessions s
    JOIN users u ON s.user_id = u.id
    WHERE s.token = ? AND s.expires_at > ? AND u.is_active = 1
    """, (token, now))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    user = dict(row)
    try:
        user["assigned_client_ids"] = json.loads(user["assigned_client_ids"])
    except Exception:
        user["assigned_client_ids"] = []
    return user

def delete_session(token: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def get_all_users() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, role, assigned_client_ids, is_active, created_at, updated_at FROM users ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    users = []
    for r in rows:
        d = dict(r)
        try:
            d["assigned_client_ids"] = json.loads(d["assigned_client_ids"])
        except Exception:
            d["assigned_client_ids"] = []
        users.append(d)
    return users

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, role, assigned_client_ids, is_active, created_at, updated_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["assigned_client_ids"] = json.loads(d["assigned_client_ids"])
    except Exception:
        d["assigned_client_ids"] = []
    return d

def create_user(email: str, password: str, name: str, role: str = "member", assigned_client_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    uid = f"user_{int(datetime.utcnow().timestamp()*1000)}"
    pwd_hash = hash_password(password)
    assigned_json = json.dumps(assigned_client_ids if assigned_client_ids is not None else ([] if role != 'admin' else ["*"]))
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO users (id, email, password_hash, name, role, assigned_client_ids, is_active, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
    """, (uid, email.strip().lower(), pwd_hash, name.strip(), role, assigned_json, now, now))
    conn.commit()
    conn.close()
    return {
        "id": uid,
        "email": email.strip().lower(),
        "name": name.strip(),
        "role": role,
        "assigned_client_ids": json.loads(assigned_json),
        "is_active": 1,
        "created_at": now
    }

def update_user_permissions(user_id: str, name: Optional[str] = None, role: Optional[str] = None, assigned_client_ids: Optional[List[str]] = None, password: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    now = datetime.utcnow().isoformat()
    updates = ["updated_at = ?"]
    params = [now]
    if name is not None:
        updates.append("name = ?")
        params.append(name.strip())
    if role is not None:
        updates.append("role = ?")
        params.append(role)
    if assigned_client_ids is not None:
        updates.append("assigned_client_ids = ?")
        params.append(json.dumps(assigned_client_ids))
    if password:
        updates.append("password_hash = ?")
        params.append(hash_password(password))
    params.append(user_id)
    cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)

def delete_user(user_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    affected = cursor.rowcount > 0
    cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return affected

# ----------------- Client Share Links & Public Portal ----------------- #

def get_or_create_share_link(client_id: str, client_name: str, created_by: str = "admin") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM client_share_links WHERE client_id = ? AND is_active = 1", (client_id,))
    row = cursor.fetchone()
    if row:
        res = dict(row)
        conn.close()
        return res
    token = f"share_{secrets.token_urlsafe(16)}"
    now = datetime.utcnow().isoformat()
    cursor.execute("""
    INSERT INTO client_share_links (token, client_id, client_name, created_at, is_active, created_by)
    VALUES (?, ?, ?, ?, 1, ?)
    """, (token, client_id, client_name, now, created_by))
    conn.commit()
    conn.close()
    return {
        "token": token,
        "client_id": client_id,
        "client_name": client_name,
        "created_at": now,
        "is_active": 1,
        "created_by": created_by
    }

def regenerate_share_link(client_id: str, client_name: str, created_by: str = "admin") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE client_share_links SET is_active = 0 WHERE client_id = ?", (client_id,))
    token = f"share_{secrets.token_urlsafe(16)}"
    now = datetime.utcnow().isoformat()
    cursor.execute("""
    INSERT INTO client_share_links (token, client_id, client_name, created_at, is_active, created_by)
    VALUES (?, ?, ?, ?, 1, ?)
    """, (token, client_id, client_name, now, created_by))
    conn.commit()
    conn.close()
    return {
        "token": token,
        "client_id": client_id,
        "client_name": client_name,
        "created_at": now,
        "is_active": 1,
        "created_by": created_by
    }

def get_client_by_share_token(token: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT sl.token, sl.client_id, sl.client_name, sl.created_at, sl.is_active,
           c.name as client_full_name, c.currency, c.industry, c.website
    FROM client_share_links sl
    JOIN clients c ON sl.client_id = c.id
    WHERE sl.token = ? AND sl.is_active = 1
    """, (token,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

init_db()

