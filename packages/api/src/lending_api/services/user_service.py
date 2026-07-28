"""利用者に関するユースケース。"""

from lending_core.errors import ValidationError
from lending_core.models import User
from lending_core.schemas import UserCreate, UserRead
from sqlalchemy.orm import Session

from lending_api.repositories.user_repo import UserRepository


class UserService:
    """利用者に関するユースケースを組み立てる。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._users = UserRepository(db)

    def list_users(self, limit: int, offset: int) -> list[UserRead]:
        """利用者を一覧取得する。"""
        return [UserRead.model_validate(user) for user in self._users.list_all(limit, offset)]

    def create_user(self, payload: UserCreate) -> UserRead:
        """利用者を登録する。メールアドレスが重複する場合は ValidationError。"""
        if self._users.get_by_email(payload.email) is not None:
            raise ValidationError("このメールアドレスはすでに登録されています")
        user = self._users.add(
            User(email=payload.email, name=payload.name, role=payload.role, is_active=True)
        )
        self._db.commit()
        return UserRead.model_validate(user)
