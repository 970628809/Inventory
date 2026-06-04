import os
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventory.db"

app = Flask(__name__)
app.secret_key = "inventory-secret-key"

OPERATION_LABELS = {
    "inbound": "入庫",
    "outbound": "出庫",
    "adjustment": "棚卸",
}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_search_args():
    return {
        "q": request.args.get("q", "", type=str).strip(),
        "sku": request.args.get("sku", "", type=str).strip(),
        "category": request.args.get("category", "", type=str).strip(),
        "location": request.args.get("location", "", type=str).strip(),
    }


def build_product_query(params):
    sql = "SELECT * FROM products WHERE 1=1"
    values = []

    if params["q"]:
        sql += " AND (name LIKE ? OR sku LIKE ?)"
        term = f"%{params['q']}%"
        values.extend([term, term])

    if params["sku"]:
        sql += " AND sku LIKE ?"
        values.append(f"%{params['sku']}%")

    if params["category"]:
        sql += " AND category LIKE ?"
        values.append(f"%{params['category']}%")

    if params["location"]:
        sql += " AND location LIKE ?"
        values.append(f"%{params['location']}%")

    sql += " ORDER BY name ASC"
    return sql, values


@app.route("/")
def dashboard():
    conn = get_db_connection()
    today = datetime.today().date()
    cutoff = today - timedelta(days=30)

    zero_stock = conn.execute(
        "SELECT * FROM products WHERE current_stock = 0 ORDER BY name"
    ).fetchall()

    low_stock = conn.execute(
        "SELECT * FROM products WHERE current_stock > 0 AND current_stock <= reorder_point ORDER BY current_stock ASC"
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


@app.route("/inventory")
def inventory():
    params = parse_search_args()
    sql, values = build_product_query(params)
    conn = get_db_connection()
    products = conn.execute(sql, values).fetchall()
    conn.close()
    return render_template(
        "inventory.html",
        products=products,
        params=params,
    )


@app.route("/stock/operate/<int:product_id>", methods=["GET", "POST"])
def stock_operate(product_id):
    operation_type = request.args.get("type", "inbound")
    if operation_type not in ["inbound", "outbound", "adjustment"]:
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
