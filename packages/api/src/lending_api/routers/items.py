"""備品エンドポイント。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from lending_core.enums import ItemCategory, ItemStatus, UserRole
from lending_core.models import User
from lending_core.schemas import ItemCreate, ItemRead, ItemUpdate

from lending_api.config import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from lending_api.deps import get_item_service, require_role
from lending_api.services.item_service import ItemService

router = APIRouter(prefix="/items", tags=["items"])


@router.get("")
def list_items(
    service: Annotated[ItemService, Depends(get_item_service)],
    _actor: Annotated[User, Depends(require_role(UserRole.MEMBER))],
    status: ItemStatus | None = None,
    category: ItemCategory | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ItemRead]:
    """備品を一覧取得する。"""
    return service.list_items(status=status, category=category, limit=limit, offset=offset)


@router.get("/{item_id}")
def get_item(
    item_id: int,
    service: Annotated[ItemService, Depends(get_item_service)],
    _actor: Annotated[User, Depends(require_role(UserRole.MEMBER))],
) -> ItemRead:
    """備品を 1 件取得する。"""
    return service.get_item(item_id)


@router.post("", status_code=201)
def create_item(
    payload: ItemCreate,
    service: Annotated[ItemService, Depends(get_item_service)],
    _actor: Annotated[User, Depends(require_role(UserRole.STAFF))],
) -> ItemRead:
    """備品を登録する。"""
    return service.create_item(payload)


@router.patch("/{item_id}")
def update_item(
    item_id: int,
    payload: ItemUpdate,
    service: Annotated[ItemService, Depends(get_item_service)],
    _actor: Annotated[User, Depends(require_role(UserRole.STAFF))],
) -> ItemRead:
    """備品を部分更新する。"""
    return service.update_item(item_id, payload)


@router.delete("/{item_id}")
def retire_item(
    item_id: int,
    service: Annotated[ItemService, Depends(get_item_service)],
    _actor: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> ItemRead:
    """備品を廃棄済みにする（論理削除）。"""
    return service.retire_item(item_id)
