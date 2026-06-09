# Render Deployment

## Option A. Blueprint

この repo には `render.yaml` があります。

Render で `New -> Blueprint` を選び、この GitHub repo を指定すると、Web Service と PostgreSQL をまとめて作成できます。

Blueprint 作成時に Render が入力を求める値:

```bash
ADMIN_USERNAME
ADMIN_PASSWORD
USER_USERNAME
USER_PASSWORD
```

普通ユーザーを初回作成しない場合、`USER_USERNAME` と `USER_PASSWORD` は空でも構いません。

`DATABASE_URL` は Render PostgreSQL から自動設定され、`SECRET_KEY` は Render が自動生成します。

## Option B. Manual Setup

### 1. PostgreSQL

Render で PostgreSQL を作成し、Connect メニューから接続 URL を取得します。

アプリには次の環境変数として設定します。

```bash
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
```

Render が `postgres://...` を表示する場合でも、アプリ側で `postgresql://...` に変換します。

### 2. Web Service

Render で `New -> Web Service` を選び、GitHub repo を接続します。

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn app:app
```

### 3. Environment Variables

Web Service の Environment に次を設定します。

```bash
DATABASE_URL=Render PostgreSQL の接続 URL
SECRET_KEY=長いランダム文字列
FLASK_ENV=production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=強いパスワード
```

普通ユーザーも初回に作る場合だけ設定します。

```bash
USER_USERNAME=staff
USER_PASSWORD=強いパスワード
```

## First Deploy

手動コマンドは不要です。

初回起動時にアプリが自動で次を行います。

- 必要な DB テーブルを作成
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` から初期管理者を作成
- sample data は投入しない
- 既存データは削除しない

## Smoke Test

Render の URL が出たら順番に確認します。

1. 未ログインで `/inventory` を開くと `/login` に移動する
2. 管理者でログインできる
3. 普通ユーザーでログインできる
4. 普通ユーザーが在庫一覧を閲覧・検索できる
5. 普通ユーザーが Excel 取込や在庫修正に入れない
6. 管理者が Excel をアップロードできる
7. アップロード後に在庫一覧が表示される
8. 在庫0リマインダーが表示される
9. 低在庫リマインダーが表示される
10. スマホや店外ネットワークからアクセスできる
