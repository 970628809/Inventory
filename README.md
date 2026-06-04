# Inventory App

このプロジェクトは `inventory_app/` フォルダ内に Flask アプリ本体を含みます。

## 使い方

```bash
cd /Users/wangyilin/Desktop/Inventory
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python init_db.py
python app.py
```

## 起動後の確認
- ダッシュボード: http://127.0.0.1:5001/
- 在庫一覧: http://127.0.0.1:5001/inventory

## ポートが 5001 で使えない場合
`5001` が他のシステムサービスに使われている場合は、次のように別ポートで起動できます。

```bash
cd /Users/wangyilin/Desktop/Inventory
source venv/bin/activate
APP_PORT=5002 python app.py
```

その場合はブラウザで `http://127.0.0.1:5002/` を開いてください。
