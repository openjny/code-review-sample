"""貸出実績レポートエンドポイントの検証。"""

from fastapi.testclient import TestClient
from lending_api import API_PREFIX

REPORTS_URL = f"{API_PREFIX}/reports"
PERIOD = {"start": "2026-07-01T00:00:00Z", "end": "2026-08-01T00:00:00Z"}


def test_get_summary_returns_rows(client: TestClient) -> None:
    response = client.get(f"{REPORTS_URL}/summary", params=PERIOD)

    assert response.status_code == 200
    assert "rows" in response.json()


def test_list_categories_is_available_for_member(member_client: TestClient) -> None:
    response = member_client.get(f"{REPORTS_URL}/categories", params=PERIOD)

    assert response.status_code == 200


def test_list_penalties_is_available_for_member(member_client: TestClient) -> None:
    response = member_client.get(f"{REPORTS_URL}/penalties", params=PERIOD)

    assert response.status_code == 200
