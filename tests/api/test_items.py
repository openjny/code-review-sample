"""備品エンドポイントの検証。"""

import pytest
from fastapi.testclient import TestClient
from lending_api import API_PREFIX
from lending_core.enums import ItemCategory, ItemStatus
from lending_core.models import Item
from sqlalchemy.orm import Session

ITEMS_URL = f"{API_PREFIX}/items"


@pytest.fixture
def items(db: Session) -> list[Item]:
    """検索・取得テスト用の備品を登録する。"""
    created = [
        Item(
            asset_code="TOOL-001",
            name="電動ドライバ",
            category=ItemCategory.TOOL,
            status=ItemStatus.AVAILABLE,
            daily_fee_yen=300,
        ),
        Item(
            asset_code="EQ-001",
            name="プロジェクタ",
            category=ItemCategory.EQUIPMENT,
            status=ItemStatus.LOANED,
            daily_fee_yen=500,
        ),
        Item(
            asset_code="HD-001",
            name="騒音計",
            category=ItemCategory.HIGH_DEMAND,
            status=ItemStatus.AVAILABLE,
            daily_fee_yen=1000,
        ),
    ]
    db.add_all(created)
    db.commit()
    return created


def test_list_items_returns_all_registered_items(
    member_client: TestClient, items: list[Item]
) -> None:
    response = member_client.get(ITEMS_URL)

    assert response.status_code == 200
    assert [item["asset_code"] for item in response.json()] == [
        "TOOL-001",
        "EQ-001",
        "HD-001",
    ]


def test_list_items_filters_by_status(member_client: TestClient, items: list[Item]) -> None:
    response = member_client.get(ITEMS_URL, params={"status": ItemStatus.AVAILABLE.value})

    assert response.status_code == 200
    assert [item["asset_code"] for item in response.json()] == ["TOOL-001", "HD-001"]


def test_list_items_filters_by_category(member_client: TestClient, items: list[Item]) -> None:
    response = member_client.get(ITEMS_URL, params={"category": ItemCategory.HIGH_DEMAND.value})

    assert response.status_code == 200
    assert [item["asset_code"] for item in response.json()] == ["HD-001"]


def test_get_item_returns_the_requested_item(member_client: TestClient, items: list[Item]) -> None:
    response = member_client.get(f"{ITEMS_URL}/{items[0].id}")

    assert response.status_code == 200
    body = response.json()
    assert body["asset_code"] == "TOOL-001"
    assert body["category"] == ItemCategory.TOOL.value
    assert body["status"] == ItemStatus.AVAILABLE.value


def test_get_item_with_unknown_id_returns_404(member_client: TestClient) -> None:
    response = member_client.get(f"{ITEMS_URL}/9999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_staff_can_create_item(staff_client: TestClient) -> None:
    response = staff_client.post(
        ITEMS_URL,
        json={
            "asset_code": "TOOL-100",
            "name": "インパクトレンチ",
            "category": ItemCategory.TOOL.value,
            "daily_fee_yen": 400,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["asset_code"] == "TOOL-100"
    assert body["status"] == ItemStatus.AVAILABLE.value
    assert body["daily_fee_yen"] == 400


def test_member_cannot_create_item(member_client: TestClient) -> None:
    response = member_client.post(
        ITEMS_URL,
        json={"asset_code": "TOOL-200", "name": "スパナ"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_create_item_with_duplicate_asset_code_returns_400(
    staff_client: TestClient, items: list[Item]
) -> None:
    response = staff_client.post(
        ITEMS_URL,
        json={"asset_code": "TOOL-001", "name": "別の電動ドライバ"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_staff_can_update_item(staff_client: TestClient, items: list[Item]) -> None:
    response = staff_client.patch(
        f"{ITEMS_URL}/{items[0].id}",
        json={"name": "電動ドライバ (更新)", "daily_fee_yen": 350},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "電動ドライバ (更新)"
    assert body["daily_fee_yen"] == 350
    assert body["asset_code"] == "TOOL-001"


def test_update_item_can_change_status(staff_client: TestClient, items: list[Item]) -> None:
    response = staff_client.patch(
        f"{ITEMS_URL}/{items[0].id}",
        json={"status": ItemStatus.MAINTENANCE.value},
    )

    assert response.status_code == 200
    assert response.json()["status"] == ItemStatus.MAINTENANCE.value


def test_update_item_with_unknown_id_returns_404(staff_client: TestClient) -> None:
    response = staff_client.patch(f"{ITEMS_URL}/9999", json={"name": "存在しない備品"})

    assert response.status_code == 404


def test_member_cannot_update_item(member_client: TestClient, items: list[Item]) -> None:
    response = member_client.patch(f"{ITEMS_URL}/{items[0].id}", json={"name": "勝手に変更"})

    assert response.status_code == 403


def test_admin_can_retire_item(admin_client: TestClient, items: list[Item]) -> None:
    response = admin_client.delete(f"{ITEMS_URL}/{items[0].id}")

    assert response.status_code == 200
    assert response.json()["status"] == ItemStatus.RETIRED.value


def test_staff_cannot_retire_item(staff_client: TestClient, items: list[Item]) -> None:
    response = staff_client.delete(f"{ITEMS_URL}/{items[0].id}")

    assert response.status_code == 403


def test_retire_loaned_item_returns_409(admin_client: TestClient, items: list[Item]) -> None:
    response = admin_client.delete(f"{ITEMS_URL}/{items[1].id}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ITEM_NOT_AVAILABLE"
