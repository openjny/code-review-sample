"""集計キャッシュ（``lending_core.cache`` へ移動済み）。"""

from lending_core.cache import TTLCache, aggregate_cache, aggregate_key

__all__ = ["TTLCache", "aggregate_cache", "aggregate_key"]
