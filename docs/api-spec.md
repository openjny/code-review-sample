# API 仕様

ベース URL: `/api/v1`

すべてのレスポンスは JSON。日時は ISO 8601 の UTC（例 `2026-07-28T01:23:45Z`）。

## 認証・認可

`Authorization: Bearer <token>` ヘッダで認証する。ロールは 3 種類。

| ロール | 説明 |
|--------|------|
| `member` | 一般利用者。自分の貸出のみ操作可 |
| `staff` | 備品管理担当。備品と全貸出を操作可 |
| `admin` | 管理者。すべて操作可 |

**すべての `/api/v1` 配下のエンドポイントは、ルータのハンドラに `require_role(...)` 依存を宣言すること。** 認可不要なエンドポイントは `/health` のみ。

### エラーレスポンス

```json
{ "error": { "code": "ITEM_NOT_AVAILABLE", "message": "..." } }
```

| HTTP | code の例 |
|------|-----------|
| 400 | `VALIDATION_ERROR` |
| 401 | `UNAUTHENTICATED` |
| 403 | `FORBIDDEN` |
| 404 | `NOT_FOUND` |
| 409 | `ITEM_NOT_AVAILABLE`, `EXTENSION_LIMIT_EXCEEDED` |

## エンドポイント

### `GET /health`

認可不要。`{ "status": "ok" }` を返す。

### 備品 `/items`

| メソッド | パス | 必要ロール | 説明 |
|---------|------|-----------|------|
| GET | `/items` | member | 一覧。`?status=` `?category=` `?limit=` `?offset=` |
| GET | `/items/{item_id}` | member | 単体取得 |
| POST | `/items` | staff | 登録 |
| PATCH | `/items/{item_id}` | staff | 更新 |
| DELETE | `/items/{item_id}` | admin | 廃棄（status を `retired` に変更する論理削除） |

`ItemRead`:

```json
{
  "id": 1,
  "asset_code": "TOOL-0001",
  "name": "トルクレンチ",
  "category": "tool",
  "status": "available",
  "daily_fee_yen": 300,
  "created_at": "2026-07-01T00:00:00Z"
}
```

### 貸出 `/loans`

| メソッド | パス | 必要ロール | 説明 |
|---------|------|-----------|------|
| GET | `/loans` | member | 一覧。member は自分の貸出のみ返す |
| GET | `/loans/{loan_id}` | member | 単体取得 |
| POST | `/loans` | member | 貸出。`{ "item_id": 1 }` |
| POST | `/loans/{loan_id}/extend` | member | 延長。最大 2 回、1 回あたり 7 日 |
| POST | `/loans/{loan_id}/return` | member | 返却。延滞していれば違約金を計上する |

`LoanRead`:

```json
{
  "id": 10,
  "item_id": 1,
  "user_id": 5,
  "loaned_at": "2026-07-01T00:00:00Z",
  "due_at": "2026-07-15T00:00:00Z",
  "returned_at": null,
  "extension_count": 0,
  "status": "active",
  "is_overdue": false
}
```

### 利用者 `/users`

| メソッド | パス | 必要ロール | 説明 |
|---------|------|-----------|------|
| GET | `/users/me` | member | 自分の情報 |
| GET | `/users` | admin | 一覧 |
| POST | `/users` | admin | 登録 |

`UserRead`:

```json
{
  "id": 5,
  "email": "user@example.com",
  "name": "山田",
  "role": "member",
  "is_active": true
}
```

### レポート `/reports`

| メソッド | パス | 必要ロール | 説明 |
|---------|------|-----------|------|
| GET | `/reports/summary` | staff | 期間集計 |
| GET | `/reports/categories` | staff | カテゴリ別件数 |
| GET | `/reports/penalties` | admin | 違約金明細 |

いずれも `?start=` `?end=`（ISO 8601）を必須で受け取る。`/reports/summary` は追加で `?category=` `?sort_by=` `?order=` を受け取る。

`ReportSummary`:

```json
{
  "start": "2026-07-01T00:00:00Z",
  "end": "2026-08-01T00:00:00Z",
  "rows": [
    { "category": "tool", "loan_count": 12, "return_count": 10, "total_penalty_yen": 1500 }
  ],
  "total_penalty_yen": 1500
}
```

## 業務ルール

- 貸出期間はカテゴリ別（`docs/architecture.md` の依存ルール 5 に従い `lending_core.rules` に集約）。
  - `tool` / `equipment`: 14 日
  - `high_demand`: 7 日
- 延長は最大 2 回、1 回 7 日。延滞中の貸出は延長できない。
- 違約金 = 延滞日数 × 日額 × 係数 0.5（整数円に四捨五入）。
- `status = available` でない備品は貸出できない（409 `ITEM_NOT_AVAILABLE`）。
