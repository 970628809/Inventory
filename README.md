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
- ダッシュボード: http://127.0.0.1:5000/
- 在庫一覧: http://127.0.0.1:5000/inventory
