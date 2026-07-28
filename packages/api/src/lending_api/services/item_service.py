"""備品に関するユースケース。"""

from lending_core.cache import aggregate_cache
from lending_core.enums import ItemCategory, ItemStatus
from lending_core.errors import ItemNotAvailableError, NotFoundError, ValidationError
from lending_core.models import Item
from lending_core.schemas import ItemCreate, ItemRead, ItemUpdate
from sqlalchemy.orm import Session

from lending_api.config import DEFAULT_PAGE_LIMIT
from lending_api.repositories.item_repo import ItemRepository


class ItemService:
    """備品の参照・登録・更新・廃棄を提供する。"""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._items = ItemRepository(db)

    def list_items(
        self,
        status: ItemStatus | None = None,
        category: ItemCategory | None = None,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> list[ItemRead]:
        """条件に一致する備品を一覧取得する。"""
        items = self._items.list_items(status, category, limit, offset)
        return [ItemRead.model_validate(item) for item in items]

    def get_item(self, item_id: int) -> ItemRead:
        """備品を 1 件取得する。存在しなければ NotFoundError。"""
        return ItemRead.model_validate(self._get_or_raise(item_id))

    def create_item(self, payload: ItemCreate) -> ItemRead:
        """備品を登録する。資産コードが重複する場合は ValidationError。"""
        if self._items.get_by_asset_code(payload.asset_code) is not None:
            raise ValidationError(f"資産コードがすでに登録されています: {payload.asset_code}")
        item = self._items.add(
            Item(
                asset_code=payload.asset_code,
                name=payload.name,
                category=payload.category,
                status=ItemStatus.AVAILABLE,
                daily_fee_yen=payload.daily_fee_yen,
            )
        )
        self._db.commit()
        return ItemRead.model_validate(item)

    def update_item(self, item_id: int, payload: ItemUpdate) -> ItemRead:
        """備品の属性を部分更新する。"""
        item = self._get_or_raise(item_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        self._db.commit()
        aggregate_cache.invalidate_prefix("aggregate:")
        return ItemRead.model_validate(item)

    def retire_item(self, item_id: int) -> ItemRead:
        """備品を廃棄済みにする（論理削除）。貸出中なら ItemNotAvailableError。"""
        item = self._get_or_raise(item_id)
        if item.status == ItemStatus.LOANED:
            raise ItemNotAvailableError("貸出中の備品は廃棄できません")
        item.status = ItemStatus.RETIRED
        self._db.commit()
        aggregate_cache.invalidate_prefix("aggregate:")
        return ItemRead.model_validate(item)

    def _get_or_raise(self, item_id: int) -> Item:
        item = self._items.get(item_id)
        if item is None:
            raise NotFoundError(f"備品が見つかりません: id={item_id}")
        return item
