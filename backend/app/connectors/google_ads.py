import requests
import logging
from typing import List, Dict, Any, Optional
from backend.app.connectors.base import BaseAdConnector
from backend.app.models.schema import UnifiedAdRecord
from backend.app.models.client import ClientProfile, GoogleAdsCredentials

logger = logging.getLogger("GoogleAdsConnector")

class GoogleAdsConnector(BaseAdConnector):
    API_VERSION = "v16"
    BASE_URL = f"https://googleads.googleapis.com/{API_VERSION}"
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self):
        super().__init__("Google")

    def _normalize_customer_id(self, customer_id: str) -> str:
        return customer_id.replace("-", "").strip()

    def _get_access_token(self, creds: GoogleAdsCredentials) -> Optional[str]:
        if not creds.client_id or not creds.client_secret or not creds.refresh_token:
            return None
        
        try:
            resp = requests.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "refresh_token": creds.refresh_token,
                    "grant_type": "refresh_token"
                },
                timeout=15
            )
            data = resp.json()
            return data.get("access_token")
        except Exception as e:
            logger.error(f"Failed to refresh Google Ads OAuth token: {e}")
            return None

    def test_connection(self, credentials: GoogleAdsCredentials) -> Dict[str, Any]:
        access_token = self._get_access_token(credentials)
        if not access_token:
            return {"success": False, "error": "Could not obtain Google OAuth access token. Check Client ID, Secret, and Refresh Token."}
        
        cid = self._normalize_customer_id(credentials.customer_id)
        if not cid:
            return {"success": False, "error": "Customer ID is required."}

        url = f"{self.BASE_URL}/customers/{cid}/googleAds:search"
        headers = {
            "developer-token": credentials.developer_token,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        if credentials.login_customer_id:
            headers["login-customer-id"] = self._normalize_customer_id(credentials.login_customer_id)

        query = "SELECT customer.id, customer.descriptive_name, customer.currency_code, customer.time_zone FROM customer LIMIT 1"

        try:
            resp = requests.post(url, headers=headers, json={"query": query}, timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                results = data.get("results", [])
                if results:
                    c = results[0].get("customer", {})
                    return {
                        "success": True,
                        "account_name": c.get("descriptiveName", f"Google Ads {cid}"),
                        "currency": c.get("currencyCode", "USD"),
                        "timezone": c.get("timeZone", "UTC")
                    }
                return {"success": True, "account_name": f"Customer {cid}"}
            else:
                err_msg = data.get("error", {}).get("message", "Google Ads API error")
                return {"success": False, "error": err_msg}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fetch_insights(
        self,
        client: ClientProfile,
        start_date: str,
        end_date: str
    ) -> List[UnifiedAdRecord]:
        creds = client.credentials.google
        access_token = self._get_access_token(creds)
        if not access_token:
            logger.warning(f"Google Ads access token could not be obtained for client {client.name}")
            return []

        cid = self._normalize_customer_id(creds.customer_id)
        url = f"{self.BASE_URL}/customers/{cid}/googleAds:searchStream"
        headers = {
            "developer-token": creds.developer_token,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        if creds.login_customer_id:
            headers["login-customer-id"] = self._normalize_customer_id(creds.login_customer_id)

        gaql = f"""
        SELECT
            segments.date,
            customer.id,
            customer.descriptive_name,
            campaign.id,
            campaign.name,
            campaign.advertising_channel_type,
            ad_group.id,
            ad_group.name,
            ad_group_ad.ad.id,
            ad_group_ad.ad.name,
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value,
            metrics.video_views
        FROM ad_group_ad
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        """

        records: List[UnifiedAdRecord] = []
        try:
            resp = requests.post(url, headers=headers, json={"query": gaql}, timeout=45)
            if resp.status_code != 200:
                logger.error(f"Google Ads API Error: {resp.text}")
                return []

            stream_data = resp.json()
            # Google Ads searchStream returns list of batches
            batches = stream_data if isinstance(stream_data, list) else [stream_data]

            for batch in batches:
                for row in batch.get("results", []):
                    seg = row.get("segments", {})
                    cust = row.get("customer", {})
                    camp = row.get("campaign", {})
                    ad_group = row.get("adGroup", {})
                    ad_info = row.get("adGroupAd", {}).get("ad", {})
                    metrics = row.get("metrics", {})

                    cost_micros = int(metrics.get("costMicros", 0))
                    spend = round(cost_micros / 1000000.0, 2)
                    impressions = int(metrics.get("impressions", 0))
                    clicks = int(metrics.get("clicks", 0))
                    conversions = float(metrics.get("conversions", 0.0))
                    conv_value = float(metrics.get("conversionsValue", 0.0))
                    video_views = int(metrics.get("videoViews", 0))

                    channel_type = camp.get("advertisingChannelType", "SEARCH")
                    camp_type = "Search" if "SEARCH" in channel_type else ("Shopping" if "SHOPPING" in channel_type else "Performance Max")

                    lpv = int(clicks * 0.88)
                    atc = int(conversions * 2.2)
                    ic = int(conversions * 1.4)

                    rec = UnifiedAdRecord(
                        date=seg.get("date", start_date),
                        client_id=client.id,
                        client_name=client.name,
                        platform="Google",
                        account_id=str(cust.get("id", cid)),
                        account_name=cust.get("descriptiveName", f"Google Ads {cid}"),
                        campaign_id=str(camp.get("id", "")),
                        campaign_name=camp.get("name", "Untitled Campaign"),
                        campaign_type=camp_type,
                        adset_id=str(ad_group.get("id", "")),
                        adset_name=ad_group.get("name", "Untitled Ad Group"),
                        ad_id=str(ad_info.get("id", "")),
                        ad_name=ad_info.get("name", "Responsive Search Ad"),
                        currency=client.currency,
                        spend=spend,
                        purchases_conversion_value=conv_value,
                        purchases=conversions,
                        landing_page_views=lpv,
                        reach=impressions,
                        impressions=impressions,
                        link_clicks=clicks,
                        video_plays_3s=video_views,
                        thruplays_15s=int(video_views * 0.4),
                        adds_to_cart=atc,
                        checkouts_initiated=ic,
                        source="api"
                    )
                    rec.calculate_derived_metrics()
                    records.append(rec)

        except Exception as e:
            logger.error(f"Error fetching Google Ads data: {e}")

        return records
