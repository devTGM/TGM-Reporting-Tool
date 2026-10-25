import requests
import json
import logging
from typing import List, Dict, Any
from backend.app.connectors.base import BaseAdConnector
from backend.app.models.schema import UnifiedAdRecord
from backend.app.models.client import ClientProfile, MetaCredentials

logger = logging.getLogger("MetaConnector")

class MetaAdsConnector(BaseAdConnector):
    GRAPH_API_VERSION = "v19.0"
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(self):
        super().__init__("Meta")

    def _normalize_account_id(self, act_id: str) -> str:
        act_id = act_id.strip()
        if not act_id.startswith("act_"):
            return f"act_{act_id}"
        return act_id

    def test_connection(self, credentials: MetaCredentials) -> Dict[str, Any]:
        if not credentials.access_token or not credentials.ad_account_id:
            return {"success": False, "error": "Missing Access Token or Ad Account ID"}
        
        act_id = self._normalize_account_id(credentials.ad_account_id)
        url = f"{self.BASE_URL}/{act_id}"
        params = {
            "fields": "id,name,currency,account_status,timezone_name",
            "access_token": credentials.access_token
        }
        
        try:
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            if resp.status_code == 200 and "id" in data:
                return {
                    "success": True,
                    "account_name": data.get("name", "Meta Account"),
                    "currency": data.get("currency", "USD"),
                    "timezone": data.get("timezone_name", "UTC"),
                    "status": "ACTIVE" if data.get("account_status") == 1 else "DISABLED"
                }
            else:
                err = data.get("error", {}).get("message", "Authentication failed")
                return {"success": False, "error": err}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fetch_insights(
        self,
        client: ClientProfile,
        start_date: str,
        end_date: str
    ) -> List[UnifiedAdRecord]:
        creds = client.credentials.meta
        if not creds.access_token or not creds.ad_account_id:
            logger.warning(f"Meta credentials missing for client {client.name}")
            return []

        act_id = self._normalize_account_id(creds.ad_account_id)
        url = f"{self.BASE_URL}/{act_id}/insights"
        
        fields = [
            "date_start", "date_stop", "account_id", "account_name",
            "campaign_id", "campaign_name", "adset_id", "adset_name",
            "ad_id", "ad_name", "spend", "impressions", "clicks",
            "inline_link_clicks", "reach", "frequency", "actions", "action_values",
            "video_3_sec_watched_actions", "video_thruplay_watched_actions"
        ]
        
        params = {
            "access_token": creds.access_token,
            "fields": ",".join(fields),
            "time_range": json.dumps({"since": start_date, "until": end_date}),
            "time_increment": 1,
            "level": "ad",
            "limit": 500
        }

        records: List[UnifiedAdRecord] = []
        
        try:
            while url:
                resp = requests.get(url, params=params, timeout=30)
                data = resp.json()
                
                if resp.status_code != 200:
                    err = data.get("error", {}).get("message", "Meta API Error")
                    logger.error(f"Meta API error for client {client.name}: {err}")
                    break

                rows = data.get("data", [])
                for row in rows:
                    date_val = row.get("date_start")
                    spend = float(row.get("spend", 0.0))
                    impressions = int(row.get("impressions", 0))
                    link_clicks = int(row.get("inline_link_clicks", row.get("clicks", 0)))
                    reach = int(row.get("reach", impressions))
                    
                    # Parse actions (Purchases, LPV, ATC, IC)
                    actions = row.get("actions", [])
                    action_values = row.get("action_values", [])
                    
                    purchases = 0.0
                    lpv = 0
                    atc = 0
                    ic = 0
                    purchases_conversion_val = 0.0

                    for act in actions:
                        act_type = act.get("action_type", "")
                        val = float(act.get("value", 0))
                        if "purchase" in act_type:
                            purchases += val
                        elif "landing_page_view" in act_type:
                            lpv += int(val)
                        elif "add_to_cart" in act_type:
                            atc += int(val)
                        elif "initiate_checkout" in act_type:
                            ic += int(val)

                    for act_val in action_values:
                        act_type = act_val.get("action_type", "")
                        val = float(act_val.get("value", 0))
                        if "purchase" in act_type:
                            purchases_conversion_val += val

                    # 3-second video plays and ThruPlays
                    video_3s = sum(int(v.get("value", 0)) for v in row.get("video_3_sec_watched_actions", []))
                    thruplay = sum(int(v.get("value", 0)) for v in row.get("video_thruplay_watched_actions", []))

                    record = UnifiedAdRecord(
                        date=date_val,
                        client_id=client.id,
                        client_name=client.name,
                        platform="Meta",
                        account_id=str(row.get("account_id", act_id)),
                        account_name=row.get("account_name", "Meta Ad Account"),
                        campaign_id=str(row.get("campaign_id", "")),
                        campaign_name=row.get("campaign_name", "Untitled Campaign"),
                        campaign_type="Conversion",
                        adset_id=str(row.get("adset_id", "")),
                        adset_name=row.get("adset_name", "Untitled AdSet"),
                        ad_id=str(row.get("ad_id", "")),
                        ad_name=row.get("ad_name", "Untitled Ad"),
                        currency=client.currency,
                        spend=spend,
                        purchases_conversion_value=purchases_conversion_val,
                        purchases=purchases,
                        landing_page_views=lpv,
                        reach=reach,
                        impressions=impressions,
                        link_clicks=link_clicks,
                        video_plays_3s=video_3s,
                        thruplays_15s=thruplay,
                        adds_to_cart=atc,
                        checkouts_initiated=ic,
                        source="api"
                    )
                    record.calculate_derived_metrics()
                    records.append(record)

                # Pagination
                paging = data.get("paging", {})
                url = paging.get("next")
                params = None  # Next URL already includes parameters

        except Exception as e:
            logger.error(f"Error fetching Meta insights: {e}")

        return records
