"""Meta Ads API client — per-client dynamic integration.

Each client has their own access token stored encrypted in IntegrationSetting.
The token is decrypted at runtime and used to query the Meta Marketing API.
"""

import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def fetch_daily_insights(
    access_token: str,
    account_id: str,
    target_date: date | None = None,
) -> dict:
    """Fetch daily ad insights for a single Meta Ads account.

    Args:
        access_token: Decrypted access token for this client's ad account.
        account_id: The ad account ID (with or without 'act_' prefix).
        target_date: The date to fetch insights for. Defaults to yesterday.

    Returns:
        Dict with keys: spend, impressions, clicks, cpc, cpm, ctr, leads
    """
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount

    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    date_str = target_date.isoformat()

    # Ensure account_id has the 'act_' prefix
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"

    # Initialize the API with the client's own token
    # We pass empty app_id/secret since we're using a pre-generated token
    FacebookAdsApi.init(
        app_id="",
        app_secret="",
        access_token=access_token,
    )

    account = AdAccount(account_id)

    fields = [
        "spend",
        "impressions",
        "clicks",
        "cpc",
        "cpm",
        "ctr",
        "actions",
    ]

    params = {
        "time_range": {"since": date_str, "until": date_str},
        "level": "account",
    }

    try:
        insights = account.get_insights(fields=fields, params=params)
        if not insights:
            logger.info(
                "No Meta Ads data for account=%s date=%s",
                account_id,
                date_str,
            )
            return _empty_result()

        row = insights[0]

        # Extract lead count from actions array
        leads = 0
        actions = row.get("actions", [])
        if actions:
            for action in actions:
                if action.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead"):
                    leads += int(action.get("value", 0))

        return {
            "spend": float(row.get("spend", 0)),
            "impressions": int(row.get("impressions", 0)),
            "clicks": int(row.get("clicks", 0)),
            "cpc": float(row.get("cpc", 0)),
            "cpm": float(row.get("cpm", 0)),
            "ctr": float(row.get("ctr", 0)),
            "leads": leads,
        }

    except Exception as e:
        logger.error(
            "Meta Ads fetch failed for account=%s: %s",
            account_id,
            str(e),
        )
        raise


def test_connection(access_token: str, account_id: str) -> dict:
    """Test if the access token can read the ad account.

    Returns:
        Dict with keys: success (bool), message (str)
    """
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.adaccount import AdAccount

    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"

    FacebookAdsApi.init(app_id="", app_secret="", access_token=access_token)

    try:
        account = AdAccount(account_id)
        account_info = account.api_get(fields=["name", "account_status"])
        name = account_info.get("name", "Desconhecido")
        return {
            "success": True,
            "message": f"Conectado com sucesso! Conta: {name}",
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
        "cpm": 0.0,
        "ctr": 0.0,
        "leads": 0,
    }
