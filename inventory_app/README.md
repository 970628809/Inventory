# 店舗用在庫管理ツール

日本の小売店向けに設計された、ローカル実行の在庫管理 Web ツールです。

## 目的
- Excel 在庫表の補助として使う
- ローカルのパソコンで動作させる
- ログインや権限管理は不要
- 売上・利益計算や複雑なグラフは含まない

## ファイル構成
- `app.py` - Flask アプリ本体
- `init_db.py` - SQLite データベース初期化スクリプト
- `inventory.db` - SQLite データベースファイル（初期化後に中身が作成されます）
- `requirements.txt` - 必要な Python パッケージ
- `templates/` - HTML テンプレート
- `static/` - CSS
- `data/sample_products.csv` - サンプル CSV データ

## インストール
1. Python 3 を用意します
2. 仮想環境を作成します

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r inventory_app/requirements.txt
```

## データベース確認
```bash
python inventory_app/init_db.py
```

このコマンドは既存データを残したままテーブルを確認します。
データを全部消して作り直す場合だけ、次を使います。

```bash
python inventory_app/init_db.py --reset
```

## アプリ起動
```bash
python inventory_app/app.py
```

## ブラウザ確認
- ダッシュボード: http://127.0.0.1:5001/
- 在庫一覧: http://127.0.0.1:5001/inventory

## 5001 ポートが使えない場合
`APP_PORT=5002 python inventory_app/app.py` のように、`APP_PORT` を指定して別ポートで起動できます。

## メモ
- 在庫 0、低在庫、30 日以上出庫なしの不動在庫をダッシュボードで確認できます
- 商品検索は商品名・SKU・カテゴリー・保管場所に対応しています
