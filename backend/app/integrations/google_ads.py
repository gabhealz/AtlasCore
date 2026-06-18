"""Google Ads API client — per-client dynamic integration.

Each client has their own OAuth2 refresh token stored encrypted in IntegrationSetting.
The refresh token + the Healz developer token are used to query the Google Ads API.
"""

import logging
from datetime import date, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


def fetch_daily_insights(
    refresh_token: str,
    customer_id: str,
    target_date: date | None = None,
) -> dict:
    """Fetch daily ad insights for a single Google Ads account.

    Args:
        refresh_token: Decrypted OAuth2 refresh token for this client.
        customer_id: The Google Ads Customer ID (digits only, no dashes).
        target_date: The date to fetch insights for. Defaults to yesterday.

    Returns:
        Dict with keys: spend, impressions, clicks, cpc, conversions
    """
    from google.ads.googleads.client import GoogleAdsClient

    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    date_str = target_date.strftime("%Y-%m-%d")

    # Strip dashes from customer ID
    customer_id = customer_id.replace("-", "").replace(" ", "")

    # Build credentials dict for this specific client
    credentials = {
        "developer_token": getattr(settings, "GOOGLE_ADS_DEVELOPER_TOKEN", ""),
        "client_id": getattr(settings, "GOOGLE_ADS_CLIENT_ID", ""),
        "client_secret": getattr(settings, "GOOGLE_ADS_CLIENT_SECRET", ""),
        "refresh_token": refresh_token,
        "use_proto_plus": True,
    }

    # If there's a login_customer_id (MCC), use it
    login_customer_id = getattr(settings, "GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
    if login_customer_id:
        credentials["login_customer_id"] = login_customer_id.replace("-", "")

    try:
        client = GoogleAdsClient.load_from_dict(credentials)
        ga_service = client.get_service("GoogleAdsService")

        query = f"""
            SELECT
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.average_cpc,
                metrics.conversions
            FROM customer
            WHERE segments.date = '{date_str}'
        """

        response = ga_service.search(customer_id=customer_id, query=query)

        total_spend = 0.0
        total_impressions = 0
        total_clicks = 0
        total_conversions = 0.0

        row_count = 0
        for row in response:
            metrics = row.metrics
            total_spend += metrics.cost_micros / 1_000_000
            total_impressions += metrics.impressions
            total_clicks += metrics.clicks
            total_conversions += metrics.conversions
            row_count += 1

        if row_count == 0:
            logger.info(
                "No Google Ads data for customer=%s date=%s",
                customer_id,
                date_str,
            )
            return _empty_result()

        # Weighted average CPC = total spend / total clicks (not arithmetic mean of daily CPCs)
        cpc = round(total_spend / max(total_clicks, 1), 2)

        return {
            "spend": round(total_spend, 2),
            "impressions": total_impressions,
            "clicks": total_clicks,
            "cpc": cpc,
            "conversions": round(total_conversions, 2),
        }

    except Exception as e:
        logger.error(
            "Google Ads fetch failed for customer=%s: %s",
            customer_id,
            str(e),
        )
        raise


def test_connection(refresh_token: str, customer_id: str) -> dict:
    """Test if the refresh token can access this Google Ads account.

    Returns:
        Dict with keys: success (bool), message (str)
    """
    from google.ads.googleads.client import GoogleAdsClient

    customer_id = customer_id.replace("-", "").replace(" ", "")

    credentials = {
        "developer_token": getattr(settings, "GOOGLE_ADS_DEVELOPER_TOKEN", ""),
        "client_id": getattr(settings, "GOOGLE_ADS_CLIENT_ID", ""),
        "client_secret": getattr(settings, "GOOGLE_ADS_CLIENT_SECRET", ""),
        "refresh_token": refresh_token,
        "use_proto_plus": True,
    }

    login_customer_id = getattr(settings, "GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
    if login_customer_id:
        credentials["login_customer_id"] = login_customer_id.replace("-", "")

    try:
        client = GoogleAdsClient.load_from_dict(credentials)
        ga_service = client.get_service("GoogleAdsService")

        query = "SELECT customer.descriptive_name FROM customer LIMIT 1"
        response = ga_service.search(customer_id=customer_id, query=query)

        for row in response:
            name = row.customer.descriptive_name
            return {
                "success": True,
                "message": f"Conectado com sucesso! Conta: {name}",
            }

        return {
            "success": True,
            "message": "Conectado com sucesso! (sem nome disponível)",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Falha na conexão: {str(e)}",
        }


def _empty_result() -> dict:
    return {
        "spend": 0.0,
        "impressions": 0,
        "clicks": 0,
        "cpc": 0.0,
        "conversions": 0.0,
    }
