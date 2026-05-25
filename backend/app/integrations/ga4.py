"""Google Analytics 4 Data API client — per-client dynamic integration.

Each client's GA4 Property ID is stored in IntegrationSetting.account_id.
The access_token field stores the Service Account JSON (encrypted).
"""

import json
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def fetch_daily_insights(
    service_account_json: str,
    property_id: str,
    target_date: date | None = None,
) -> dict:
    """Fetch daily analytics for a single GA4 property.

    Args:
        service_account_json: Decrypted JSON string of the Google Service Account.
        property_id: The GA4 Property ID (numeric string).
        target_date: The date to fetch. Defaults to yesterday.

    Returns:
        Dict with keys: sessions, conversions, new_users
    """
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Metric,
        RunReportRequest,
    )
    from google.oauth2 import service_account as sa

    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    date_str = target_date.isoformat()

    try:
        # Parse the JSON and create credentials
        sa_info = json.loads(service_account_json)
        credentials = sa.Credentials.from_service_account_info(
            sa_info,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )

        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            metrics=[
                Metric(name="sessions"),
                Metric(name="conversions"),
                Metric(name="newUsers"),
            ],
        )

        response = client.run_report(request)

        if not response.rows:
            logger.info(
                "No GA4 data for property=%s date=%s",
                property_id,
                date_str,
            )
            return _empty_result()

        row = response.rows[0]

        return {
            "sessions": int(row.metric_values[0].value),
            "conversions": int(row.metric_values[1].value),
            "new_users": int(row.metric_values[2].value),
        }

    except Exception as e:
        logger.error(
            "GA4 fetch failed for property=%s: %s",
            property_id,
            str(e),
        )
        raise


def test_connection(service_account_json: str, property_id: str) -> dict:
    """Test if the Service Account JSON can access this GA4 property.

    Returns:
        Dict with keys: success (bool), message (str)
    """
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Metric,
        RunReportRequest,
    )
    from google.oauth2 import service_account as sa

    try:
        sa_info = json.loads(service_account_json)
        credentials = sa.Credentials.from_service_account_info(
            sa_info,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )

        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date="yesterday", end_date="yesterday")],
            metrics=[Metric(name="sessions")],
        )

        response = client.run_report(request)
        sessions = 0
        if response.rows:
            sessions = int(response.rows[0].metric_values[0].value)

        return {
            "success": True,
            "message": f"Conectado com sucesso! Sessões ontem: {sessions}",
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "message": "O JSON da Service Account é inválido.",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Falha na conexão: {str(e)}",
        }


def _empty_result() -> dict:
    return {
        "sessions": 0,
        "conversions": 0,
        "new_users": 0,
    }
