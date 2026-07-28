"""利用者エンドポイント。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from lending_core.enums import UserRole
from lending_core.models import User
from lending_core.schemas import UserCreate, UserRead

from lending_api.config import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from lending_api.deps import get_user_service, require_role
from lending_api.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def get_me(actor: Annotated[User, Depends(require_role(UserRole.MEMBER))]) -> UserRead:
    """認証中の利用者自身の情報を返す。"""
    return UserRead.model_validate(actor)


@router.get("")
def list_users(
    service: Annotated[UserService, Depends(get_user_service)],
    _actor: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[UserRead]:
    """利用者を一覧取得する。"""
    return service.list_users(limit=limit, offset=offset)


@router.post("", status_code=201)
def create_user(
    payload: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
    _actor: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> UserRead:
    """利用者を登録する。"""
    return service.create_user(payload)
