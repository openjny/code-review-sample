# code-review-sample

備品貸出管理システムのサンプル実装。コードレビュー機能の検証用リポジトリです。

## 構成

uv workspace による 3 パッケージ構成。

| パッケージ | 役割 |
|-----------|------|
| `packages/core` | ドメイン層。モデル・スキーマ・業務ルール。他パッケージに依存しない |
| `packages/api` | FastAPI アプリケーション。ルータ / サービス / リポジトリの 3 層 |
| `packages/worker` | バッチ処理。延滞通知・日次集計 |

依存方向は `worker → core`、`api → core` の一方向のみ。詳細は [docs/architecture.md](docs/architecture.md)。

## セットアップ

```bash
uv sync
```

## 実行

```bash
# API サーバ
uv run uvicorn lending_api.main:app --reload

# バッチ (延滞通知)
uv run python -m lending_worker.scheduler overdue
```

## テスト

```bash
uv run pytest
uv run ruff check .
```

## ドキュメント

- [docs/architecture.md](docs/architecture.md) — レイヤ構造と依存ルール
- [docs/api-spec.md](docs/api-spec.md) — API 仕様
- [docs/coding-standards.md](docs/coding-standards.md) — コーディング規約
