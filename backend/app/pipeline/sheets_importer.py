import re
import csv
import io
import urllib.request
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from backend.app.models.schema import UnifiedAdRecord
from backend.app.models.client import ClientProfile
from backend.app.database import (
    get_client_by_id, get_all_clients, save_client, clear_client_records,
    upsert_cleaned_records, get_bigquery_config, log_sync_job
)
from backend.app.pipeline.cleaner import clean_and_normalize_records
from backend.app.pipeline.validator import audit_and_validate_records
from backend.app.pipeline.bigquery_exporter import BigQueryExporter

logger = logging.getLogger("GoogleSheetsImporter")

# Column alias dictionary for resilient header detection
COLUMN_ALIASES = {
    "date": ["date", "day", "time", "reporting date", "date_start", "start date"],
    "platform": ["platform", "channel", "network", "source", "ad platform", "ad network"],
    "campaign_name": ["campaign name", "campaign", "campaign_name", "campaigns", "utm_campaign"],
    "adset_name": ["ad set name", "adset name", "adset", "ad set", "ad group", "adgroup name", "target group"],
    "ad_name": ["ad name", "creative name", "ad_name", "creative"],
    "audience_segment": ["audience segments", "audience", "audiences", "audience segment", "targeting"],
    
    # 11 Raw Input Metrics (Supports Coefficient & Coupler field headers)
    "spend": ["amount spent", "spend", "cost", "cost ($)", "spend (usd)", "amount_spent", "ad spend", "total cost"],
    "purchases_conversion_value": ["purchases conversion value", "conversion value", "conversion value ($)", "revenue", "purchase value", "sales", "website purchase conversion value", "total conversion value", "conv. value"],
    "purchases": ["purchases", "purchase", "conversions", "orders", "transactions", "leads", "website purchases", "conv."],
    "landing_page_views": ["landing page views", "landing page view", "lpv", "landing_page_views", "landing page visits", "landing page views (all)"],
    "reach": ["reach", "unique users", "unique impressions"],
    "impressions": ["impressions", "impr", "impressions count", "views", "impr."],
    "link_clicks": ["link clicks", "inline link clicks", "link click"],
    "clicks_all": ["clicks (all)", "clicks", "total clicks", "click count"],
    "video_plays_3s": ["3s video plays", "3-second video plays", "3s plays", "3s video", "video plays 3s", "3-second continuous video plays", "video 3-second views"],
    "thruplays_15s": ["15s thruplays", "thruplays", "15-second thruplays", "thruplay", "thru plays"],
    "adds_to_cart": ["adds to cart", "add to cart", "atc", "cart additions", "adds_to_cart", "website adds to cart"],
    "checkouts_initiated": ["checkouts initiated", "initiate checkout", "checkouts", "checkout initiated", "initiations", "website checkouts initiated"]
}

def extract_spreadsheet_and_gid(sheet_url_or_id: str, default_gid: str = "0"):
    """Extracts raw spreadsheet ID and gid from URL or bare string."""
    cleaned = sheet_url_or_id.strip()
    sheet_id = cleaned
    gid = default_gid
    
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", cleaned)
    if match:
        sheet_id = match.group(1)

    gid_match = re.search(r"[#&?]gid=([0-9]+)", cleaned)
    if gid_match:
        gid = gid_match.group(1)

    return sheet_id, gid

def extract_spreadsheet_id(sheet_url_or_id: str) -> str:
    """Extracts raw spreadsheet ID from URL or bare string."""
    s_id, _ = extract_spreadsheet_and_gid(sheet_url_or_id)
    return s_id

def fetch_sheet_csv(spreadsheet_id: str, gid: str = "0") -> str:
    """Downloads public/shared Google Sheet as CSV."""
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status != 200:
            raise ValueError(f"Google Sheet returned HTTP status {resp.status}")
        return resp.read().decode("utf-8")

def map_column_headers(raw_headers: List[str]) -> Dict[str, int]:
    """Matches raw CSV headers to internal canonical fields, prioritizing exact matches."""
    mapping = {}
    normalized = [h.strip().lower().replace("_", " ") for h in raw_headers]
    
    # Pass 1: Exact matches
    for canon_field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            for idx, raw_h in enumerate(normalized):
                if alias == raw_h and canon_field not in mapping:
                    mapping[canon_field] = idx
                    break
            if canon_field in mapping:
                break
                
    # Pass 2: Word-boundary substring matches (ignoring derivative fields like 'cpm', 'cost per', 'ctr', 'rate')
    for canon_field, aliases in COLUMN_ALIASES.items():
        if canon_field in mapping:
            continue
        for alias in aliases:
            for idx, raw_h in enumerate(normalized):
                if any(deriv in raw_h for deriv in ["cpm", "ctr", "cpc", "cost per", "rate", "percent", "%"]):
                    continue
                pattern = r'\b' + re.escape(alias) + r'\b'
                if re.search(pattern, raw_h) and idx not in mapping.values():
                    mapping[canon_field] = idx
                    break
            if canon_field in mapping:
                break
            
    return mapping

def safe_float(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    s = str(val).replace("$", "").replace(",", "").replace("₹", "").replace("%", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0

def safe_int(val: Any) -> int:
    return int(safe_float(val))

def find_header_and_data_rows(rows: List[List[str]]) -> Tuple[List[str], List[List[str]], Dict[str, int]]:
    """Scans the first 5 rows to locate the real header row (handles Coefficient/Supermetrics title banners)."""
    best_row_idx = 0
    best_mapping = {}

    for idx in range(min(5, len(rows))):
        mapping = map_column_headers(rows[idx])
        if len(mapping) > len(best_mapping):
            best_mapping = mapping
            best_row_idx = idx

    header_row = rows[best_row_idx]
    data_rows = rows[best_row_idx + 1:]
    return header_row, data_rows, best_mapping

def import_google_sheet_records(
    sheet_url_or_id: Optional[str] = None,
    client_id: Optional[str] = None,
    gid: Optional[str] = None,
    replace_existing: bool = True,
    push_to_bigquery: bool = False
) -> Dict[str, Any]:
    """
    Downloads Google Sheet for a designated client, maps headers to 11 raw metrics,
    cleans through pipeline (17 calculated metrics + 8 taxonomies),
    replaces existing sheet records for clean isolation, and saves to database.
    """
    # 1. Resolve client
    if client_id:
        client = get_client_by_id(client_id)
    else:
        clients = get_all_clients()
        client = clients[0] if clients else None

    if not client:
        return {"success": False, "error": f"No valid agency client found for ID '{client_id}'."}

    client_name = client.name
    active_client_id = client.id

    # 2. Resolve Sheet URL and GID
    active_sheet_input = (sheet_url_or_id or "").strip()
    if not active_sheet_input:
        if client.google_sheet_url:
            active_sheet_input = client.google_sheet_url.strip()
            if not gid or gid == "0":
                gid = client.google_sheet_gid or "0"
        else:
            return {
                "success": False,
                "error": f"No Google Sheet configured for client '{client_name}'. Please enter a Google Sheet URL."
            }

    spreadsheet_id, resolved_gid = extract_spreadsheet_and_gid(active_sheet_input, default_gid=gid or "0")
    if not spreadsheet_id:
        return {"success": False, "error": "Invalid Google Sheet URL or Spreadsheet ID format."}

    # Automatically save and update this sheet URL & GID for the client
    client.google_sheet_url = active_sheet_input
    client.google_sheet_gid = resolved_gid
    client.last_sheet_synced_at = datetime.utcnow().isoformat()
    save_client(client)

    try:
        csv_text = fetch_sheet_csv(spreadsheet_id, resolved_gid)
    except Exception as e:
        logger.error(f"Failed to download Google Sheet: {e}")
        return {
            "success": False,
            "error": f"Failed to download Google Sheet. Ensure sheet is shared ('Anyone with link can view'): {str(e)}"
        }

    reader = csv.reader(io.StringIO(csv_text))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    
    if len(rows) < 2:
        return {"success": False, "error": "Google Sheet contains no data rows or is empty."}

    header_row, data_rows, col_map = find_header_and_data_rows(rows)

    if not col_map:
        return {
            "success": False,
            "error": f"Could not match headers. Detected headers: {header_row[:8]}..."
        }

    extracted_records: List[UnifiedAdRecord] = []
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    for row_idx, r in enumerate(data_rows):
        def get_val(canon_key: str, default=None):
            idx = col_map.get(canon_key)
            if idx is not None and idx < len(r):
                val = r[idx].strip()
                return val if val else default
            return default

        # Basic Fields
        row_date = get_val("date", today_str)
        # Standardize date format YYYY-MM-DD
        if "/" in row_date:
            parts = row_date.split("/")
            if len(parts) == 3:
                # MM/DD/YYYY or DD/MM/YYYY
                try:
                    if len(parts[2]) == 4:
                        row_date = f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                except Exception:
                    pass

        row_platform = get_val("platform", "Meta").capitalize()
        camp_name = get_val("campaign_name", f"Campaign {row_idx + 1}")
        adset_name = get_val("adset_name", "General AdSet")
        ad_name = get_val("ad_name", "Main Creative")
        aud_seg = get_val("audience_segment", "All Audiences")

        spend = safe_float(get_val("spend", 0.0))
        rev = safe_float(get_val("purchases_conversion_value", 0.0))
        purchases = safe_float(get_val("purchases", 0.0))
        lpv = safe_int(get_val("landing_page_views", 0))
        reach = safe_int(get_val("reach", 0))
        impr = safe_int(get_val("impressions", 0))
        clicks = safe_int(get_val("link_clicks", 0))
        if clicks == 0:
            clicks = safe_int(get_val("clicks_all", 0))
        v3s = safe_int(get_val("video_plays_3s", 0))
        thru = safe_int(get_val("thruplays_15s", 0))
        atc = safe_int(get_val("adds_to_cart", 0))
        chk = safe_int(get_val("checkouts_initiated", 0))

        # Explicitly scope IDs to this client to guarantee zero overlap across clients
        record = UnifiedAdRecord(
            date=row_date,
            client_id=active_client_id,
            client_name=client_name,
            platform=row_platform,
            account_id=f"act_{active_client_id}",
            account_name=client_name,
            campaign_id=f"cmp_{active_client_id}_{row_idx + 1}",
            campaign_name=camp_name,
            adset_id=f"adset_{active_client_id}_{row_idx + 1}",
            adset_name=adset_name,
            ad_id=f"ad_{active_client_id}_{row_idx + 1}",
            ad_name=ad_name,
            audience_segment=aud_seg,
            currency=(client.currency if client and client.currency else "INR"),
            spend=spend,
            purchases_conversion_value=rev,
            purchases=purchases,
            landing_page_views=lpv,
            reach=reach,
            impressions=impr,
            link_clicks=clicks,
            video_plays_3s=v3s,
            thruplays_15s=thru,
            adds_to_cart=atc,
            checkouts_initiated=chk,
            source="sheet"
        )
        extracted_records.append(record)

    # Clean & normalize all 17 calculated metrics + 8 taxonomies
    cleaned, clean_stats = clean_and_normalize_records(extracted_records)
    audit = audit_and_validate_records(cleaned)

    # Replace existing records for this client to completely avoid overlapping/double-counting
    if replace_existing:
        clear_client_records(active_client_id, source="sheet")
        clear_client_records(active_client_id, source="api")

    upsert_cleaned_records(cleaned)

    # Optional BigQuery export
    bq_res = None
    bq_config = get_bigquery_config()
    if push_to_bigquery or bq_config.auto_push:
        try:
            exporter = BigQueryExporter(bq_config)
            bq_res = exporter.stream_records(cleaned)
        except Exception as bq_err:
            bq_res = {"success": False, "error": str(bq_err)}

    total_spend = sum(r.spend for r in cleaned)
    total_rev = sum(r.purchases_conversion_value for r in cleaned)
    overall_roas = round(total_rev / total_spend, 2) if total_spend > 0 else 0.0

    return {
        "success": True,
        "client_id": active_client_id,
        "client_name": client_name,
        "spreadsheet_id": spreadsheet_id,
        "gid": resolved_gid,
        "rows_imported": len(cleaned),
        "total_spend": round(total_spend, 2),
        "total_revenue": round(total_rev, 2),
        "overall_roas": overall_roas,
        "quality_score": audit.get("quality_score", 100.0),
        "bigquery_export": bq_res
    }
