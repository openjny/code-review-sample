# コーディング規約

## 全般

- Python 3.12 以上。型ヒントは必須。
- フォーマット / lint は `ruff` に従う（`line-length = 100`）。
- 公開関数には docstring を付ける。内部ヘルパーは不要。

## 命名

| 対象 | 規約 | 例 |
|------|------|-----|
| モジュール | snake_case | `loan_service.py` |
| クラス | PascalCase | `LoanService` |
| 関数・変数 | snake_case | `calculate_due_date` |
| 定数 | UPPER_SNAKE_CASE | `MAX_EXTENSION_COUNT` |
| 金額を表す変数 | 単位サフィックスを付ける | `fee_yen`, `penalty_yen` |

## 金額計算

- **金額は必ず `Decimal` で計算し、`lending_core.money.to_yen()` で整数円に丸める。**
- **丸めは `ROUND_HALF_UP`（四捨五入）で統一する。** `round()` 組み込み関数は使用禁止（銀行丸めのため規約違反）。
- `float` による金額計算は禁止。

## 例外処理

- 業務エラーは `lending_core.errors` の例外を送出する。汎用の `Exception` / `ValueError` を業務エラーとして使わない。
- **例外の握り潰し（`except: pass` / `except Exception: pass`）は禁止。** 意図的に無視する場合は理由をコメントで明記し、`logger.warning` を出す。
- 例外を再送出する際は `raise ... from e` で元例外を連鎖させる。

## ログ

- `logging.getLogger(__name__)` を使う。`print()` は禁止。
- **認証トークン・パスワード・メールアドレス等の機微情報をログに出力しない。**

## データベースアクセス

- **SQL 文字列の組み立てに f-string / `%` / `+` を使わない。** 必ず SQLAlchemy の式か `text()` + バインドパラメータを使う。
- ループ内でのクエリ発行（N+1）を避ける。

## 非同期処理

- `async def` で定義した関数の呼び出しは必ず `await` する。
- ブロッキング I/O を async 関数内で直接呼ばない。

## その他

- ミュータブルなデフォルト引数（`def f(x: list = [])`）は禁止。
- マジックナンバーは定数化する。設定値は `lending_api.config` / 環境変数から読む。
- 秘密情報（API キー・パスワード）をソースコードにハードコードしない。
