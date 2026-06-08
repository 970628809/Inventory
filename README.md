# Inventory App

ローカル実行とクラウド実行の両方を想定した Flask 在庫管理ツールです。

## Local SQLite

```bash
cd /Users/wangyilin/Desktop/Inventory
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export SECRET_KEY="local-dev-secret"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="change-this-password"
python inventory_app/init_db.py

python app.py
```

ブラウザで `http://127.0.0.1:5001/` を開き、管理者アカウントでログインします。

`DATABASE_URL` を設定しない場合、既定で `inventory_app/inventory.db` の SQLite を使います。

## Cloud PostgreSQL Preparation

クラウドでは次の環境変数を設定します。

```bash
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
SECRET_KEY=long-random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong-admin-password
```

初回だけ DB 初期化を実行します。

```bash
python inventory_app/init_db.py
```

アプリ起動例:

```bash
gunicorn inventory_app.app:app
```

一部の環境で `postgres://...` 形式の URL が渡される場合も、アプリ側で `postgresql://...` として扱います。

## Users

`users` テーブルにユーザーを保存します。パスワードは hash 化され、平文では保存されません。

初期管理者は次の環境変数を設定して `python inventory_app/init_db.py` を実行すると作成されます。

```bash
ADMIN_USERNAME=admin
ADMIN_PASSWORD=strong-admin-password
```

普通ユーザーをテスト用に作る場合:

```bash
USER_USERNAME=staff
USER_PASSWORD=staff-password
python inventory_app/init_db.py
```

## Roles

管理者:
- Excel 取込
- Excel 出力
- 在庫修正
- 新品追加
- 入庫 / 出庫
- 棚卸開始、チェック、修正
- 最近の在庫変動の編集 / 削除
- リマインダー追加 / 削除

普通ユーザー:
- ダッシュボード閲覧
- 在庫一覧の閲覧と検索
- 棚卸一覧の閲覧
- リマインダー閲覧

未ログインユーザーは在庫ページにアクセスできません。

## Files Not To Commit

`.gitignore` で次を除外しています。

- `.env`
- `inventory_app/inventory.db`
- `*.xlsx`, `*.xls`, `*.xlsm`
- `uploads/`
- `exports/`

真实会社データや本番 Excel はリポジトリに入れないでください。
