import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from werkzeug.security import generate_password_hash

try:
    from .db import column_names, get_database_url, get_db_connection, sql_type
except ImportError:
    from db import column_names, get_database_url, get_db_connection, sql_type

PRODUCT_COLUMNS = {
    "source_sheet": "TEXT",
    "source_row": "INTEGER",
    "big_category": "TEXT",
    "maker_or_product": "TEXT",
    "overview": "TEXT",
    "supplier": "TEXT",
    "amount": "TEXT",
    "stock_status": "TEXT",
    "display_flag": "TEXT",
    "available_stock": "INTEGER NOT NULL DEFAULT 0",
    "total_stock": "INTEGER NOT NULL DEFAULT 0",
    "staff_stock_json": "TEXT",
    "imported_at": "TEXT",
}

STOCK_LOG_COLUMNS = {
    "metadata_json": "TEXT",
}

USER_COLUMNS = {
    "is_active": "INTEGER NOT NULL DEFAULT 1",
    "admin_requested": "INTEGER NOT NULL DEFAULT 0",
}

APP_TIMEZONE = ZoneInfo(os.getenv("APP_TIMEZONE", "Asia/Tokyo"))


def now_jst_string():
    return datetime.now(APP_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


def ensure_product_columns(cursor):
    existing = column_names("products")
    for name, definition in PRODUCT_COLUMNS.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE products ADD COLUMN {name} {definition}")


def ensure_stock_log_columns(cursor):
    existing = column_names("stock_logs")
    for name, definition in STOCK_LOG_COLUMNS.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE stock_logs ADD COLUMN {name} {definition}")


def ensure_user_columns(cursor):
    existing = column_names("users")
    for name, definition in USER_COLUMNS.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")


def ensure_user(username, password, role):
    if not username or not password:
        return False
    conn = get_db_connection()
    try:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            return False
        now = now_jst_string()
        conn.execute(
            "INSERT INTO users (username, password_hash, role, is_active, admin_requested, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (username, generate_password_hash(password), role, 1, 0, now),
        )
        conn.commit()
        return True
    finally:
        conn.close()

PRODUCTS = []

LOGS = []


def create_db(reset=False):
    conn = get_db_connection()
    cursor = conn

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS products (
            id {sql_type("pk")},
            source_sheet TEXT,
            source_row INTEGER,
            big_category TEXT,
            maker_or_product TEXT,
            overview TEXT,
            sku TEXT NOT NULL,
            stock_status TEXT,
            display_flag TEXT,
            available_stock INTEGER NOT NULL DEFAULT 0,
            total_stock INTEGER NOT NULL DEFAULT 0,
            reorder_point INTEGER NOT NULL DEFAULT 0,
            staff_stock_json TEXT,
            notes TEXT,
            imported_at TEXT,
            current_stock INTEGER NOT NULL DEFAULT 0,
            name TEXT NOT NULL,
            category TEXT,
            location TEXT,
            last_in_date TEXT,
            last_out_date TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_products_source ON products(source_sheet, source_row);"
    )
    conn.commit()
    ensure_product_columns(cursor)

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS stock_logs (
            id {sql_type("pk")},
            product_id INTEGER NOT NULL,
            operation_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            staff_name TEXT,
            note TEXT,
            metadata_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
        """
    )
    conn.commit()
    ensure_stock_log_columns(cursor)

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS low_stock_alerts (
            id {sql_type("pk")},
            product_id INTEGER NOT NULL UNIQUE,
            threshold INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS zero_stock_alerts (
            id {sql_type("pk")},
            product_id INTEGER NOT NULL UNIQUE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS stagnant_stock_alerts (
            id {sql_type("pk")},
            product_id INTEGER NOT NULL UNIQUE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id {sql_type("pk")},
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            is_active INTEGER NOT NULL DEFAULT 1,
            admin_requested INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    ensure_user_columns(cursor)

    now = now_jst_string()

    if reset:
        cursor.execute("DELETE FROM low_stock_alerts")
        cursor.execute("DELETE FROM zero_stock_alerts")
        cursor.execute("DELETE FROM stagnant_stock_alerts")
        cursor.execute("DELETE FROM stock_logs")
        cursor.execute("DELETE FROM products")

    if reset or not cursor.execute("SELECT 1 FROM products LIMIT 1").fetchone():
        for row_number, (sku, name, category, location, current_stock, reorder_point, last_in_date, last_out_date, notes) in enumerate(PRODUCTS, start=1):
            cursor.execute(
                "INSERT INTO products (source_sheet, source_row, big_category, maker_or_product, overview, supplier, amount, sku, stock_status, display_flag, available_stock, total_stock, reorder_point, staff_stock_json, notes, imported_at, current_stock, name, category, location, last_in_date, last_out_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("sample", row_number, category or "", name, "", "", "", sku, "", "", current_stock, current_stock, reorder_point, "{}", notes, now, current_stock, name, category, location, last_in_date, last_out_date, now, now),
            )

        for product_id, operation_type, quantity, staff_name, note, created_at in LOGS:
            cursor.execute(
                "INSERT INTO stock_logs (product_id, operation_type, quantity, staff_name, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (product_id, operation_type, quantity, staff_name, note, created_at),
            )

    conn.commit()
    conn.close()
    ensure_user(os.getenv("ADMIN_USERNAME"), os.getenv("ADMIN_PASSWORD"), "admin")
    ensure_user(os.getenv("USER_USERNAME"), os.getenv("USER_PASSWORD"), "user")
    if reset:
        print(f"データベースをリセットしました: {get_database_url()}")
    else:
        print(f"データベースを確認しました: {get_database_url()}")


if __name__ == "__main__":
    create_db(reset="--reset" in sys.argv)
