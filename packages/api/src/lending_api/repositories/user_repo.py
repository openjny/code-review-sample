"""利用者の永続化。"""

from lending_core.models import User
from sqlalchemy import select
from sqlalchemy.orm import Session


class UserRepository:
    """``users`` テーブルへのアクセスを提供する。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_id: int) -> User | None:
        """ID で利用者を取得する。"""
        return self._db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """メールアドレスで利用者を取得する。"""
        return self._db.scalars(select(User).where(User.email == email)).first()

    def list_all(self, limit: int, offset: int) -> list[User]:
        """利用者を ID 昇順で一覧取得する。"""
        stmt = select(User).order_by(User.id).limit(limit).offset(offset)
        return list(self._db.scalars(stmt))

    def add(self, user: User) -> User:
        """利用者をセッションに追加する。"""
        self._db.add(user)
        return user
