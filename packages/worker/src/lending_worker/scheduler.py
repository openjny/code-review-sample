"""バッチ処理の CLI エントリポイント。"""

import argparse
import logging
from datetime import date

from lending_worker.config import get_settings
from lending_worker.db import get_session
from lending_worker.jobs import daily_aggregate, overdue_notifier

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lending-worker",
        description="備品貸出管理システムのバッチ処理",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("overdue", help="延滞通知を送信する")

    aggregate_parser = subparsers.add_parser("aggregate", help="日次集計を実行する")
    aggregate_parser.add_argument(
        "--date",
        dest="target_date",
        type=date.fromisoformat,
        default=None,
        help="集計対象日 (YYYY-MM-DD)。既定は前日。",
    )
    aggregate_parser.add_argument(
        "--no-cache",
        dest="use_cache",
        action="store_false",
        help="キャッシュを参照せずに再集計する",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI から呼ばれるエントリポイント。終了コードを返す。"""
    args = _build_parser().parse_args(argv)
    logging.basicConfig(level=get_settings().log_level)

    with get_session() as db:
        if args.command == "overdue":
            result = overdue_notifier.run(db)
            logger.info("overdue: scanned=%d notified=%d", result.scanned, result.notified)
        else:
            summary = daily_aggregate.run(
                db,
                target_date=args.target_date,
                use_cache=args.use_cache,
            )
            logger.info(
                "aggregate: date=%s created=%d returned=%d penalty_yen=%d items=%s",
                summary.target_date.isoformat(),
                summary.loans_created,
                summary.loans_returned,
                summary.penalty_total_yen,
                summary.items_by_status,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
