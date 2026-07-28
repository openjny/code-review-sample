"""貸出エンドポイントの検証。"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from lending_api import API_PREFIX
from lending_core.enums import ItemCategory, ItemStatus, LoanStatus
from lending_core.models import Item, Penalty
from sqlalchemy import select
from sqlalchemy.orm import Session

LOANS_URL = f"{API_PREFIX}/loans"
DAILY_FEE_YEN = 300
TOOL_LOAN_DAYS = 14


def _create_item(
    db: Session,
    *,
    asset_code: str,
    category: ItemCategory = ItemCategory.TOOL,
    daily_fee_yen: int = DAILY_FEE_YEN,
) -> Item:
    item = Item(
        asset_code=asset_code,
        name=f"備品 {asset_code}",
        category=category,
        status=ItemStatus.AVAILABLE,
        daily_fee_yen=daily_fee_yen,
    )
    db.add(item)
    db.commit()
    return item


@pytest.fixture
def tool_item(db: Session) -> Item:
    """貸出可能な tool カテゴリの備品。"""
    return _create_item(db, asset_code="TOOL-001")


@pytest.mark.parametrize(
    ("category", "expected_days"),
    [
        (ItemCategory.TOOL, 14),
        (ItemCategory.EQUIPMENT, 14),
        (ItemCategory.HIGH_DEMAND, 7),
    ],
)
def test_create_loan_sets_due_at_from_category(
    member_client: TestClient,
    db: Session,
    frozen_clock,
    category: ItemCategory,
    expected_days: int,
) -> None:
    item = _create_item(db, asset_code=f"ASSET-{category.value}", category=category)

    response = member_client.post(LOANS_URL, json={"item_id": item.id})

    assert response.status_code == 201
    body = response.json()
    assert datetime.fromisoformat(body["loaned_at"]) == frozen_clock.current
    assert datetime.fromisoformat(body["due_at"]) == frozen_clock.current + timedelta(
        days=expected_days
    )
    assert body["status"] == LoanStatus.ACTIVE.value
    assert body["extension_count"] == 0
    assert body["is_overdue"] is False


def test_create_loan_marks_item_as_loaned(
    member_client: TestClient, db: Session, frozen_clock, tool_item: Item
) -> None:
    response = member_client.post(LOANS_URL, json={"item_id": tool_item.id})

    assert response.status_code == 201
    db.expire_all()
    assert tool_item.status is ItemStatus.LOANED


def test_create_loan_for_unknown_item_returns_404(member_client: TestClient, frozen_clock) -> None:
    response = member_client.post(LOANS_URL, json={"item_id": 9999})

    assert response.status_code == 404


def test_create_loan_for_already_loaned_item_returns_409(
    member_client: TestClient, frozen_clock, tool_item: Item
) -> None:
    assert member_client.post(LOANS_URL, json={"item_id": tool_item.id}).status_code == 201

    response = member_client.post(LOANS_URL, json={"item_id": tool_item.id})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ITEM_NOT_AVAILABLE"


def test_extend_loan_is_allowed_up_to_two_times(
    member_client: TestClient, frozen_clock, tool_item: Item
) -> None:
    created = member_client.post(LOANS_URL, json={"item_id": tool_item.id}).json()
    loan_id = created["id"]
    original_due_at = datetime.fromisoformat(created["due_at"])

    first = member_client.post(f"{LOANS_URL}/{loan_id}/extend")
    assert first.status_code == 200
    assert first.json()["extension_count"] == 1
    assert datetime.fromisoformat(first.json()["due_at"]) == original_due_at + timedelta(days=7)

    second = member_client.post(f"{LOANS_URL}/{loan_id}/extend")
    assert second.status_code == 200
    assert second.json()["extension_count"] == 2
    assert datetime.fromisoformat(second.json()["due_at"]) == original_due_at + timedelta(days=14)


def test_third_extend_returns_409(member_client: TestClient, frozen_clock, tool_item: Item) -> None:
    loan_id = member_client.post(LOANS_URL, json={"item_id": tool_item.id}).json()["id"]
    member_client.post(f"{LOANS_URL}/{loan_id}/extend")
    member_client.post(f"{LOANS_URL}/{loan_id}/extend")

    response = member_client.post(f"{LOANS_URL}/{loan_id}/extend")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EXTENSION_LIMIT_EXCEEDED"


def test_extend_overdue_loan_returns_409(
    member_client: TestClient, frozen_clock, tool_item: Item
) -> None:
    loan_id = member_client.post(LOANS_URL, json={"item_id": tool_item.id}).json()["id"]
    frozen_clock.advance(timedelta(days=TOOL_LOAN_DAYS + 1, seconds=1))

    response = member_client.post(f"{LOANS_URL}/{loan_id}/extend")

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "延滞中の貸出は延長できません"


def test_return_loan_makes_item_available_again(
    member_client: TestClient, db: Session, frozen_clock, tool_item: Item
) -> None:
    loan_id = member_client.post(LOANS_URL, json={"item_id": tool_item.id}).json()["id"]

    response = member_client.post(f"{LOANS_URL}/{loan_id}/return")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == LoanStatus.RETURNED.value
    assert datetime.fromisoformat(body["returned_at"]) == frozen_clock.current
    db.expire_all()
    assert tool_item.status is ItemStatus.AVAILABLE


def test_return_loan_twice_returns_409(
    member_client: TestClient, frozen_clock, tool_item: Item
) -> None:
    loan_id = member_client.post(LOANS_URL, json={"item_id": tool_item.id}).json()["id"]
    member_client.post(f"{LOANS_URL}/{loan_id}/return")

    response = member_client.post(f"{LOANS_URL}/{loan_id}/return")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LOAN_ALREADY_RETURNED"


def test_return_on_time_records_no_penalty(
    member_client: TestClient, db: Session, frozen_clock, tool_item: Item
) -> None:
    loan_id = member_client.post(LOANS_URL, json={"item_id": tool_item.id}).json()["id"]
    frozen_clock.advance(timedelta(days=TOOL_LOAN_DAYS))

    assert member_client.post(f"{LOANS_URL}/{loan_id}/return").status_code == 200
    assert db.scalars(select(Penalty)).all() == []


def test_overdue_return_records_penalty(
    member_client: TestClient, db: Session, frozen_clock, tool_item: Item
) -> None:
    loan_id = member_client.post(LOANS_URL, json={"item_id": tool_item.id}).json()["id"]
    frozen_clock.advance(timedelta(days=TOOL_LOAN_DAYS + 3))

    response = member_client.post(f"{LOANS_URL}/{loan_id}/return")

    assert response.status_code == 200
    penalties = db.scalars(select(Penalty)).all()
    assert len(penalties) == 1
    # 日額 300 円 × 2 日 × 違約金率 0.5 = 300 円
    assert penalties[0].amount_yen == 300
    assert penalties[0].loan_id == loan_id


def test_get_loan_reports_overdue_flag(
    member_client: TestClient, frozen_clock, tool_item: Item
) -> None:
    loan_id = member_client.post(LOANS_URL, json={"item_id": tool_item.id}).json()["id"]
    frozen_clock.advance(timedelta(days=TOOL_LOAN_DAYS + 1, seconds=1))

    response = member_client.get(f"{LOANS_URL}/{loan_id}")

    assert response.status_code == 200
    assert response.json()["is_overdue"] is True


def test_member_cannot_read_another_users_loan(
    member_client: TestClient, staff_client: TestClient, db: Session, frozen_clock
) -> None:
    staff_item = _create_item(db, asset_code="TOOL-STAFF")
    staff_loan_id = staff_client.post(LOANS_URL, json={"item_id": staff_item.id}).json()["id"]

    response = member_client.get(f"{LOANS_URL}/{staff_loan_id}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_staff_can_read_another_users_loan(
    member_client: TestClient, staff_client: TestClient, frozen_clock, tool_item: Item
) -> None:
    member_loan_id = member_client.post(LOANS_URL, json={"item_id": tool_item.id}).json()["id"]

    response = staff_client.get(f"{LOANS_URL}/{member_loan_id}")

    assert response.status_code == 200
    assert response.json()["id"] == member_loan_id


def test_member_list_excludes_other_users_loans(
    member_client: TestClient, staff_client: TestClient, db: Session, frozen_clock
) -> None:
    member_item = _create_item(db, asset_code="TOOL-MEMBER")
    staff_item = _create_item(db, asset_code="TOOL-STAFF")
    member_loan_id = member_client.post(LOANS_URL, json={"item_id": member_item.id}).json()["id"]
    staff_loan_id = staff_client.post(LOANS_URL, json={"item_id": staff_item.id}).json()["id"]

    response = member_client.get(LOANS_URL)

    assert response.status_code == 200
    loan_ids = [loan["id"] for loan in response.json()]
    assert loan_ids == [member_loan_id]
    assert staff_loan_id not in loan_ids


def test_staff_list_includes_all_loans(
    member_client: TestClient, staff_client: TestClient, db: Session, frozen_clock
) -> None:
    member_item = _create_item(db, asset_code="TOOL-MEMBER")
    staff_item = _create_item(db, asset_code="TOOL-STAFF")
    member_loan_id = member_client.post(LOANS_URL, json={"item_id": member_item.id}).json()["id"]
    staff_loan_id = staff_client.post(LOANS_URL, json={"item_id": staff_item.id}).json()["id"]

    response = staff_client.get(LOANS_URL)

    assert response.status_code == 200
    assert {loan["id"] for loan in response.json()} == {member_loan_id, staff_loan_id}
