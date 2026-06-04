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

PRODUCTS = [
    ("P0001", "ペン", "文房具", "棚A", 10, 5, "2026-05-25", "2026-06-02", "店頭用の黒インクペン"),
    ("P0002", "ノート", "文房具", "棚B", 2, 5, "2026-05-20", "2026-05-01", "A5サイズ、50枚"),
    ("P0003", "消しゴム", "文房具", "棚A", 0, 3, "2026-05-10", "2026-04-01", "特売品"),
    ("P0004", "プリンター用紙", "事務用品", "倉庫", 25, 10, "2026-06-01", "2026-05-15", "A4 500枚"),
    ("P0005", "付箋", "文房具", "棚C", 6, 5, "2026-05-30", "2026-04-20", "3色セット"),
]

LOGS = [
    (1, "inbound", 20, "山田", "補充在庫", "2026-06-01 10:15:00"),
    (2, "outbound", 3, "佐藤", "販売", "2026-06-02 14:20:00"),
    (3, "adjustment", -2, "田中", "棚卸調整", "2026-05-30 11:00:00"),
    (4, "outbound", 5, "山田", "販売", "2026-05-15 09:30:00"),
    (5, "inbound", 10, "佐藤", "入荷", "2026-05-20 16:45:00"),
]


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
