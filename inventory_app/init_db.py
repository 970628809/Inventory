import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventory.db"

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


def ensure_product_columns(cursor):
    cursor.execute("PRAGMA table_info(products)")
    existing = {row[1] for row in cursor.fetchall()}
    for name, definition in PRODUCT_COLUMNS.items():
        if name not in existing:
            cursor.execute(f"ALTER TABLE products ADD COLUMN {name} {definition}")

PRODUCTS = []

LOGS = []


def create_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    ensure_product_columns(cursor)

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            operation_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            staff_name TEXT,
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
        """
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("DELETE FROM stock_logs")
    cursor.execute("DELETE FROM products")

    for row_number, (sku, name, category, location, current_stock, reorder_point, last_in_date, last_out_date, notes) in enumerate(PRODUCTS, start=1):
        cursor.execute(
            "INSERT INTO products (source_sheet, source_row, big_category, maker_or_product, overview, sku, stock_status, display_flag, available_stock, total_stock, reorder_point, staff_stock_json, notes, imported_at, current_stock, name, category, location, last_in_date, last_out_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("sample", row_number, category or "", name, "", sku, "", "", current_stock, current_stock, reorder_point, "{}", notes, now, current_stock, name, category, location, last_in_date, last_out_date, now, now),
        )

    for product_id, operation_type, quantity, staff_name, note, created_at in LOGS:
        cursor.execute(
            "INSERT INTO stock_logs (product_id, operation_type, quantity, staff_name, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (product_id, operation_type, quantity, staff_name, note, created_at),
        )

    conn.commit()
    conn.close()
    print(f"データベースを初期化しました: {DB_PATH}")


if __name__ == "__main__":
    create_db()
