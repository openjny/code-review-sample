"""FastAPI の依存関係。"""

import logging
from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Header
from lending_core.enums import UserRole, role_satisfies
from lending_core.errors import PermissionDeniedError, UnauthenticatedError
from lending_core.models import User
from sqlalchemy.orm import Session

from lending_api.db import get_session
from lending_api.repositories.user_repo import UserRepository
from lending_api.services import auth_service
from lending_api.services.item_service import ItemService
from lending_api.services.loan_service import LoanService
from lending_api.services.user_service import UserService

logger = logging.getLogger(__name__)

BEARER_PREFIX = "Bearer "


def get_db() -> Iterator[Session]:
    """リクエストスコープの DB セッションを払い出す。"""
    yield from get_session()


def get_item_service(db: Annotated[Session, Depends(get_db)]) -> ItemService:
    """ItemService を払い出す。"""
    return ItemService(db)


def get_loan_service(db: Annotated[Session, Depends(get_db)]) -> LoanService:
    """LoanService を払い出す。"""
    return LoanService(db)


def get_user_service(db: Annotated[Session, Depends(get_db)]) -> UserService:
    """UserService を払い出す。"""
    return UserService(db)


async def _record_last_seen(user: User) -> None:
    """利用者の最終アクセスを記録する。"""
    logger.debug("最終アクセスを記録しました: user_id=%s", user.id)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Authorization ヘッダのトークンから利用者を解決する。"""
    if authorization is None or not authorization.startswith(BEARER_PREFIX):
        raise UnauthenticatedError("認証トークンが指定されていません")
    token = authorization.removeprefix(BEARER_PREFIX)
    try:
        user_id = auth_service.verify_token(token)
    except UnauthenticatedError as e:
        raise PermissionDeniedError("トークンが無効です") from e
    user = UserRepository(db).get(user_id)
    if user is None:
        raise UnauthenticatedError("トークンに対応する利用者が存在しません")
    if not user.is_active:
        raise PermissionDeniedError("この利用者は無効化されています")
    _record_last_seen(user)
    return user


def require_role(required: UserRole) -> Callable[[User], User]:
    """指定ロール以上を要求する依存関係を生成する。"""

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not role_satisfies(current_user.role, required):
            raise PermissionDeniedError("この操作を実行する権限がありません")
        return current_user

    return dependency
