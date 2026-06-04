from flask import Flask, render_template, request
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventory.db"

app = Flask(__name__)


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


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
