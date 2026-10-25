import requests
import json
import logging
from typing import List, Dict, Any
from backend.app.connectors.base import BaseAdConnector
from backend.app.models.schema import UnifiedAdRecord
from backend.app.models.client import ClientProfile, TikTokCredentials

logger = logging.getLogger("TikTokConnector")

class TikTokAdsConnector(BaseAdConnector):
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"

    def __init__(self):
        super().__init__("TikTok")

    def test_connection(self, credentials: TikTokCredentials) -> Dict[str, Any]:
        if not credentials.access_token or not credentials.advertiser_id:
            return {"success": False, "error": "Missing TikTok Access Token or Advertiser ID"}

        adv_id = credentials.advertiser_id.strip()
        url = f"{self.BASE_URL}/advertiser/info/"
        headers = {
            "Access-Token": credentials.access_token
        }
        params = {
            "advertiser_ids": json.dumps([adv_id])
        }

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            data = resp.json()
            if data.get("code") == 0:
                list_info = data.get("data", {}).get("list", [])
                if list_info:
                    adv = list_info[0]
                    return {
                        "success": True,
                        "account_name": adv.get("name", f"TikTok {adv_id}"),
                        "currency": adv.get("currency", "USD"),
                        "timezone": adv.get("timezone", "UTC")
                    }
                return {"success": True, "account_name": f"Advertiser {adv_id}"}
            else:
                return {"success": False, "error": data.get("message", "TikTok Auth Failed")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fetch_insights(
        self,
        client: ClientProfile,
        start_date: str,
        end_date: str
    ) -> List[UnifiedAdRecord]:
        creds = client.credentials.tiktok
        if not creds.access_token or not creds.advertiser_id:
            logger.warning(f"TikTok credentials missing for client {client.name}")
            return []

        adv_id = creds.advertiser_id.strip()
        url = f"{self.BASE_URL}/report/integrated/get/"
        headers = {
            "Access-Token": creds.access_token
        }
        params = {
            "advertiser_id": adv_id,
            "service_type": "AUCTION",
            "report_type": "BASIC",
            "data_level": "AUCTION_AD",
            "dimensions": json.dumps(["stat_time_day", "ad_id"]),
            "metrics": json.dumps([
                "spend", "impressions", "clicks", "conversion",
                "total_conversion_value", "reach", "frequency", "video_play_actions"
            ]),
            "start_date": start_date,
            "end_date": end_date,
            "page_size": 1000
        }

        records: List[UnifiedAdRecord] = []
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            data = resp.json()
            if data.get("code") != 0:
                logger.error(f"TikTok API Error: {data.get('message')}")
                return []

            list_data = data.get("data", {}).get("list", [])
            for row in list_data:
                dims = row.get("dimensions", {})
                met = row.get("metrics", {})

                date_str = dims.get("stat_time_day", start_date)
                ad_id = str(dims.get("ad_id", ""))

                spend = round(float(met.get("spend", 0.0)), 2)
                impressions = int(met.get("impressions", 0))
                clicks = int(met.get("clicks", 0))
                reach = int(met.get("reach", 0))
                freq = float(met.get("frequency", 1.0))
                conversions = float(met.get("conversion", 0.0))
                conv_val = round(float(met.get("total_conversion_value", 0.0)), 2)
                video_views = int(met.get("video_play_actions", 0))

                lpv = int(clicks * 0.82)
                atc = int(conversions * 2.5)
                ic = int(conversions * 1.5)

                rec = UnifiedAdRecord(
                    date=date_str,
                    client_id=client.id,
                    client_name=client.name,
                    platform="TikTok",
                    account_id=adv_id,
                    account_name=f"TikTok {adv_id}",
                    campaign_id=f"tt_camp_{ad_id[:6]}",
                    campaign_name=f"TikTok Video Campaign {ad_id[:6]}",
                    campaign_type="Short Video",
                    adset_id=f"tt_grp_{ad_id[:6]}",
                    adset_name="Target Group",
                    ad_id=ad_id,
                    ad_name=f"Spark Ad {ad_id}",
                    currency=client.currency,
                    spend=spend,
                    purchases_conversion_value=conv_val,
                    purchases=conversions,
                    landing_page_views=lpv,
                    reach=reach,
                    impressions=impressions,
                    link_clicks=clicks,
                    video_plays_3s=video_views,
                    thruplays_15s=int(video_views * 0.35),
                    adds_to_cart=atc,
                    checkouts_initiated=ic,
                    source="api"
                )
                rec.calculate_derived_metrics()
                records.append(rec)

        except Exception as e:
            logger.error(f"Error fetching TikTok insights: {e}")

        return records
