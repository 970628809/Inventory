import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from openpyxl import load_workbook

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventory.db"

app = Flask(__name__)
app.secret_key = "inventory-secret-key"

OPERATION_LABELS = {
    "inbound": "入庫",
    "outbound": "出庫",
    "adjustment": "棚卸",
    "modification": "修正",
}

PRODUCT_COLUMNS = {
    "source_sheet": "TEXT",
    "source_row": "INTEGER",
    "big_category": "TEXT",
    "maker_or_product": "TEXT",
    "overview": "TEXT",
    "stock_status": "TEXT",
    "display_flag": "TEXT",
    "available_stock": "INTEGER NOT NULL DEFAULT 0",
    "total_stock": "INTEGER NOT NULL DEFAULT 0",
    "staff_stock_json": "TEXT",
    "imported_at": "TEXT",
}


def ensure_product_columns(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(products)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    for name, definition in PRODUCT_COLUMNS.items():
        if name not in existing_columns:
            cursor.execute(f"ALTER TABLE products ADD COLUMN {name} {definition}")
    conn.commit()


def ensure_database():
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
        if cursor.fetchone():
            ensure_product_columns(conn)
        else:
            conn.close()
            conn = None
            from init_db import create_db
            create_db()
            return
    finally:
        if conn:
            conn.close()


ensure_database()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def format_staff_stock_display(staff_stock_json):
    """
    Filter to display staff stock without zero values.
    Input: JSON string like '{"A05": 1, "A06": 0, "H12": 2}'
    Output: "A05: 1 / H12: 2" or "-" if empty or all zeros
    """
    if not staff_stock_json:
        return "-"
    try:
        data = json.loads(staff_stock_json)
        non_zero = {k: v for k, v in data.items() if v != 0}
        if not non_zero:
            return "-"
        return " / ".join([f"{k}: {v}" for k, v in non_zero.items()])
    except Exception:
        return "-"


app.jinja_env.filters['format_staff_stock'] = format_staff_stock_display


def parse_search_args():
    return {
        "q": request.args.get("q", "", type=str).strip(),
        "sku": request.args.get("sku", "", type=str).strip(),
        "big_category": request.args.get("big_category", "", type=str).strip(),
        "location": request.args.get("location", "", type=str).strip(),
    }


def build_product_query(params):
    sql = "SELECT * FROM products WHERE 1=1"
    values = []

    if params["q"]:
        sql += " AND (name LIKE ? OR sku LIKE ? OR big_category LIKE ? OR maker_or_product LIKE ? OR overview LIKE ? OR notes LIKE ? OR source_sheet LIKE ? OR category LIKE ? OR location LIKE ? OR staff_stock_json LIKE ? )"
        term = f"%{params['q']}%"
        values.extend([term] * 10)

    if params["sku"]:
        sql += " AND sku LIKE ?"
        values.append(f"%{params['sku']}%")

    if params["big_category"]:
        sql += " AND big_category = ?"
        values.append(params["big_category"])

    if params["location"]:
        sql += " AND location LIKE ?"
        values.append(f"%{params['location']}%")

    sql += " ORDER BY name ASC"
    return sql, values


def parse_int(value):
    if value is None:
        return 0
    if isinstance(value, str):
        value = value.strip().replace(",", "")
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return 0


def get_cell(sheet, row, col):
    value = sheet.cell(row=row, column=col).value
    return value if value is not None else ""


def parse_staff_stock(sheet, row):
    values = {}
    for col in range(13, 27):
        header = sheet.cell(row=2, column=col).value
        if header is None:
            continue
        header = str(header).strip()
        if not header:
            continue
        cell_value = sheet.cell(row=row, column=col).value
        stock = parse_int(cell_value)
        values[header] = stock
    return values


NORMAL_SHEETS = {
    "エアコン在庫": "エアコン",
    "給湯器在庫": "給湯器",
    "トイレ在庫": "トイレ",
    "その他設備在庫": None,
    "その他家電在庫": None,
}


def parse_inventory_row(sheet, sheet_name, row):
    if sheet_name in NORMAL_SHEETS:
        reorder_point = parse_int(get_cell(sheet, row, 2))
        stock_status = str(get_cell(sheet, row, 3)).strip()
        maker_or_product = str(get_cell(sheet, row, 4)).strip()
        overview = str(get_cell(sheet, row, 5)).strip()
        sku = str(get_cell(sheet, row, 6)).strip()
        display_flag = str(get_cell(sheet, row, 7)).strip()
        available_stock = parse_int(get_cell(sheet, row, 8))
        total_stock = parse_int(get_cell(sheet, row, 12))
        notes = str(get_cell(sheet, row, 27)).strip()
        staff_stock = parse_staff_stock(sheet, row)

        if not sku and not maker_or_product and not overview:
            return None

        if NORMAL_SHEETS[sheet_name] is None:
            big_category = maker_or_product
        else:
            big_category = NORMAL_SHEETS[sheet_name]

        name = maker_or_product or sku or overview or "不明"
        return {
            "source_sheet": sheet_name,
            "source_row": row,
            "big_category": big_category,
            "maker_or_product": maker_or_product,
            "overview": overview,
            "sku": sku,
            "stock_status": stock_status,
            "display_flag": display_flag,
            "available_stock": available_stock,
            "total_stock": total_stock,
            "reorder_point": reorder_point,
            "staff_stock_json": json.dumps(staff_stock, ensure_ascii=False),
            "notes": notes,
            "imported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_stock": available_stock,
            "name": name,
            "category": big_category,
            "location": "",
        }
    if sheet_name == "魚倉庫在庫":
        reorder_point = parse_int(get_cell(sheet, row, 2))
        stock_status = str(get_cell(sheet, row, 3)).strip()
        available_stock = parse_int(get_cell(sheet, row, 4))
        maker_or_product = str(get_cell(sheet, row, 8)).strip()
        overview = str(get_cell(sheet, row, 7)).strip()
        sku = str(get_cell(sheet, row, 9)).strip()
        notes = str(get_cell(sheet, row, 20)).strip()
        big_category = str(get_cell(sheet, row, 6)).strip()

        if not sku and not overview:
            return None

        name = maker_or_product or sku or overview or "不明"
        return {
            "source_sheet": sheet_name,
            "source_row": row,
            "big_category": big_category,
            "maker_or_product": maker_or_product,
            "overview": overview,
            "sku": sku,
            "stock_status": stock_status,
            "display_flag": "",
            "available_stock": available_stock,
            "total_stock": 0,
            "reorder_point": reorder_point,
            "staff_stock_json": json.dumps({}, ensure_ascii=False),
            "notes": notes,
            "imported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_stock": available_stock,
            "name": name,
            "category": big_category,
            "location": "",
        }
    return None


def import_excel_file(file_stream):
    workbook = load_workbook(filename=file_stream, data_only=True)
    sheet_names = [name for name in workbook.sheetnames if workbook[name].sheet_state == "visible"]
    imported = 0
    skipped = 0
    errors = 0
    error_details = []
    deleted_products = 0
    deleted_logs = 0
    
    conn = get_db_connection()
    
    try:
        # Delete old data before importing
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stock_logs")
        deleted_logs = cursor.rowcount
        cursor.execute("DELETE FROM products")
        deleted_products = cursor.rowcount
        conn.commit()
        
        # Now import new data
        for sheet_name in sheet_names:
            if sheet_name not in list(NORMAL_SHEETS.keys()) + ["魚倉庫在庫"]:
                continue
            sheet = workbook[sheet_name]
            for row in range(4, sheet.max_row + 1):
                try:
                    record = parse_inventory_row(sheet, sheet_name, row)
                    if record is None:
                        skipped += 1
                        continue
                    
                    conn.execute(
                        "INSERT INTO products (source_sheet, source_row, big_category, maker_or_product, overview, sku, stock_status, display_flag, available_stock, total_stock, reorder_point, staff_stock_json, notes, imported_at, current_stock, name, category, location, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            record["source_sheet"],
                            record["source_row"],
                            record["big_category"],
                            record["maker_or_product"],
                            record["overview"],
                            record["sku"],
                            record["stock_status"],
                            record["display_flag"],
                            record["available_stock"],
                            record["total_stock"],
                            record["reorder_point"],
                            record["staff_stock_json"],
                            record["notes"],
                            record["imported_at"],
                            record["current_stock"],
                            record["name"],
                            record["category"],
                            record["location"],
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                    imported += 1
                except Exception as exc:
                    errors += 1
                    error_details.append(f"{sheet_name} 行 {row}: {exc}")
        
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise exc
    finally:
        conn.close()
    
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "error_details": error_details,
        "deleted_products": deleted_products,
        "deleted_logs": deleted_logs,
    }


@app.route("/")
def dashboard():
    conn = get_db_connection()
    today = datetime.today().date()
    cutoff = today - timedelta(days=30)

    zero_stock = conn.execute(
        "SELECT * FROM products WHERE available_stock = 0 ORDER BY name"
    ).fetchall()

    low_stock = conn.execute(
        "SELECT * FROM products WHERE reorder_point > 0 AND available_stock > 0 AND available_stock <= reorder_point ORDER BY available_stock ASC"
    ).fetchall()

    stagnant_stock = conn.execute(
        "SELECT * FROM products WHERE current_stock > 0 AND last_out_date IS NOT NULL AND date(last_out_date) < date(?) ORDER BY last_out_date"
    , (cutoff.isoformat(),)).fetchall()

    recent_logs = conn.execute(
        "SELECT stock_logs.*, products.name, products.sku FROM stock_logs JOIN products ON stock_logs.product_id = products.id ORDER BY stock_logs.created_at DESC LIMIT 10"
    ).fetchall()

    conn.close()
    return render_template(
        "dashboard.html",
        zero_stock=zero_stock,
        low_stock=low_stock,
        stagnant_stock=stagnant_stock,
        recent_logs=recent_logs,
        cutoff=cutoff,
        operation_labels=OPERATION_LABELS,
    )


@app.route("/stock/log/edit/<int:log_id>", methods=["GET", "POST"])
def edit_stock_log(log_id):
    conn = get_db_connection()
    log = conn.execute(
        "SELECT stock_logs.*, products.name, products.sku FROM stock_logs JOIN products ON stock_logs.product_id = products.id WHERE stock_logs.id = ?",
        (log_id,),
    ).fetchone()
    if log is None:
        conn.close()
        return "ログが見つかりません。", 404

    error_message = None
    if request.method == "POST":
        staff_name = request.form.get("staff_name", "").strip()
        note = request.form.get("note", "").strip()
        conn.execute(
            "UPDATE stock_logs SET staff_name = ?, note = ? WHERE id = ?",
            (staff_name, note, log_id),
        )
        conn.commit()
        conn.close()
        flash("在庫記録を更新しました。", "success")
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template(
        "edit_stock_log.html",
        log=log,
        operation_label=OPERATION_LABELS.get(log["operation_type"], log["operation_type"]),
        error_message=error_message,
    )


@app.route("/inventory")
def inventory():
    params = parse_search_args()
    sql, values = build_product_query(params)
    conn = get_db_connection()
    products = conn.execute(sql, values).fetchall()
    
    # Get all distinct big_categories
    big_categories_result = conn.execute(
        "SELECT DISTINCT big_category FROM products WHERE big_category IS NOT NULL AND big_category != '' ORDER BY big_category"
    ).fetchall()
    big_categories = [row[0] for row in big_categories_result]
    
    conn.close()
    return render_template(
        "inventory.html",
        products=products,
        params=params,
        big_categories=big_categories,
    )


@app.route("/excel_import", methods=["GET", "POST"])
def excel_import():
    result = None
    if request.method == "POST":
        uploaded_file = request.files.get("excel_file")
        if not uploaded_file or uploaded_file.filename == "":
            flash("Excelファイルを選択してください。", "danger")
        elif not uploaded_file.filename.lower().endswith(".xlsx"):
            flash(".xlsxファイルをアップロードしてください。", "danger")
        else:
            result = import_excel_file(uploaded_file)
            deleted_msg = f"旧データ：{result['deleted_products']}件の商品と{result['deleted_logs']}件のログを削除しました。"
            if result["errors"] == 0:
                flash(f"Excel取込が完了しました。{deleted_msg} 新規登録：{result['imported']}件、スキップ：{result['skipped']}件。", "success")
            else:
                flash(f"Excel取込が完了しました。{deleted_msg} 新規登録：{result['imported']}件、スキップ：{result['skipped']}件、エラー：{result['errors']}件。", "danger")
    return render_template("excel_import.html", result=result)


@app.route("/stock/operate/<int:product_id>", methods=["GET", "POST"])
def stock_operate(product_id):
    operation_type = request.args.get("type", "inbound")
    if operation_type not in ["inbound", "outbound", "adjustment", "modification"]:
        operation_type = "inbound"

    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()

    if product is None:
        conn.close()
        return "商品が見つかりません。", 404

    error_message = None
    if request.method == "POST":
        staff_name = request.form.get("staff_name", "").strip()
        note = request.form.get("note", "").strip()
        today = datetime.today().date().isoformat()
        current_stock = product["current_stock"]
        quantity = None
        change = None
        last_in_date = product["last_in_date"]
        last_out_date = product["last_out_date"]

        if operation_type == "adjustment":
            actual_quantity = request.form.get("actual_quantity", type=int)
            if actual_quantity is None or actual_quantity < 0:
                error_message = "正しい実際在庫数を入力してください。"
            else:
                change = actual_quantity - current_stock
                quantity = change
                new_stock = actual_quantity
        elif operation_type == "modification":
            new_stock = request.form.get("new_stock", type=int)
            if new_stock is None or new_stock < 0:
                error_message = "正しい新在庫数を入力してください。"
            else:
                change = new_stock - current_stock
                quantity = change
        else:
            quantity = request.form.get("quantity", type=int)
            if quantity is None or quantity < 0:
                error_message = "正しい数量を入力してください。"
            else:
                if operation_type == "inbound":
                    change = quantity
                    new_stock = current_stock + quantity
                    last_in_date = today
                elif operation_type == "outbound":
                    if quantity > current_stock:
                        error_message = "在庫が不足しています。"
                    else:
                        change = -quantity
                        new_stock = current_stock - quantity
                        last_out_date = today

        if error_message is None and change is not None:
            conn.execute(
                "UPDATE products SET current_stock = ?, last_in_date = ?, last_out_date = ?, updated_at = ? WHERE id = ?",
                (new_stock, last_in_date, last_out_date, today + " 00:00:00", product_id),
            )
            conn.execute(
                "INSERT INTO stock_logs (product_id, operation_type, quantity, staff_name, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (product_id, operation_type, quantity, staff_name, note, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
            conn.close()
            flash("在庫操作が正常に完了しました。", "success")
            return redirect(url_for("inventory"))

    conn.close()
    return render_template(
        "stock_operation.html",
        product=product,
        operation_type=operation_type,
        operation_label=OPERATION_LABELS.get(operation_type, operation_type),
        error_message=error_message,
    )


if __name__ == "__main__":
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "5001"))
    app.run(debug=True, host=host, port=port)
