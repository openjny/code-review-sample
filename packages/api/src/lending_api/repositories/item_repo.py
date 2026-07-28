"""備品の永続化。"""

from lending_core.enums import ItemCategory, ItemStatus
from lending_core.models import Item
from sqlalchemy import select
from sqlalchemy.orm import Session


class ItemRepository:
    """``items`` テーブルへのアクセスを提供する。"""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, item_id: int) -> Item | None:
        """ID で備品を取得する。"""
        return self._db.get(Item, item_id)

    def get_by_asset_code(self, code: str) -> Item | None:
        """資産コードで備品を取得する。"""
        return self._db.scalars(select(Item).where(Item.asset_code == code)).first()

    def list_items(
        self,
        status: ItemStatus | None,
        category: ItemCategory | None,
        limit: int,
        offset: int,
    ) -> list[Item]:
        """条件に一致する備品を ID 昇順で一覧取得する。"""
        stmt = select(Item)
        if status is not None:
            stmt = stmt.where(Item.status == status)
        if category is not None:
            stmt = stmt.where(Item.category == category)
        stmt = stmt.order_by(Item.id).limit(limit).offset(offset)
        return list(self._db.scalars(stmt))

    def add(self, item: Item) -> Item:
        """備品をセッションに追加する。"""
        self._db.add(item)
        return item

    def flush(self) -> None:
        """保留中の変更を DB へ送出する。"""
        self._db.flush()
