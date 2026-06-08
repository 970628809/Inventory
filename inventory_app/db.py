import os
import re
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_URL = f"sqlite:///{BASE_DIR / 'inventory.db'}"


def get_database_url():
    return normalize_database_url(os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))


def normalize_database_url(url):
    if url and url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


engine = create_engine(get_database_url(), future=True, pool_pre_ping=True)


def is_postgres():
    return engine.dialect.name == "postgresql"


def is_sqlite():
    return engine.dialect.name == "sqlite"


def sql_type(base_type):
    if base_type == "pk":
        return "SERIAL PRIMARY KEY" if is_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    if base_type == "datetime":
        return "TIMESTAMP" if is_postgres() else "TEXT"
    return base_type


def convert_sql(sql, params):
    if isinstance(params, dict):
        return normalize_sql(sql), params
    params = tuple(params or ())
    index = 0
    values = {}

    def repl(_match):
        nonlocal index
        key = f"p{index}"
        values[key] = params[index]
        index += 1
        return f":{key}"

    return normalize_sql(re.sub(r"\?", repl, sql)), values


def normalize_sql(sql):
    if is_postgres():
        sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO")
        sql = re.sub(
            r"INSERT INTO (zero_stock_alerts|stagnant_stock_alerts) \(product_id\) VALUES \((:[^)]+)\)",
            r"INSERT INTO \1 (product_id) VALUES (\2) ON CONFLICT (product_id) DO NOTHING",
            sql,
        )
        sql = re.sub(
            r"INSERT OR REPLACE INTO low_stock_alerts \(product_id, threshold\) VALUES \((:[^,]+), (:[^)]+)\)",
            r"INSERT INTO low_stock_alerts (product_id, threshold) VALUES (\1, \2) ON CONFLICT (product_id) DO UPDATE SET threshold = EXCLUDED.threshold",
            sql,
        )
        sql = re.sub(r"\bdate\(([^)]+)\)", r"CAST(\1 AS DATE)", sql)
    return sql


class DbRow:
    def __init__(self, mapping, values):
        self._mapping = dict(mapping)
        self._values = tuple(values)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._mapping[key]

    def __getattr__(self, key):
        try:
            return self._mapping[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def keys(self):
        return self._mapping.keys()

    def get(self, key, default=None):
        return self._mapping.get(key, default)

    def __iter__(self):
        return iter(self._values)


class DbResult:
    def __init__(self, result, fetch_lastrowid=False):
        self._result = result
        self.rowcount = result.rowcount
        self.lastrowid = getattr(result, "lastrowid", None)
        if fetch_lastrowid and self.lastrowid is None and result.returns_rows:
            row = result.fetchone()
            self.lastrowid = row[0] if row else None

    def fetchone(self):
        row = self._result.fetchone()
        return wrap_row(row)

    def fetchall(self):
        return [wrap_row(row) for row in self._result.fetchall()]

    def scalar(self):
        return self._result.scalar()


class DbConnection:
    def __init__(self):
        self._conn = engine.connect()
        self._tx = self._conn.begin()

    def execute(self, sql, params=None):
        statement_sql, values = convert_sql(sql, params)
        fetch_lastrowid = False
        if is_postgres() and statement_sql.lstrip().upper().startswith("INSERT INTO PRODUCTS") and "RETURNING" not in statement_sql.upper():
            statement_sql = statement_sql.rstrip() + " RETURNING id"
            fetch_lastrowid = True
        result = self._conn.execute(text(statement_sql), values)
        return DbResult(result, fetch_lastrowid=fetch_lastrowid)

    def commit(self):
        self._tx.commit()
        self._tx = self._conn.begin()

    def rollback(self):
        self._tx.rollback()
        self._tx = self._conn.begin()

    def close(self):
        if self._tx.is_active:
            self._tx.rollback()
        self._conn.close()


def wrap_row(row):
    if row is None:
        return None
    return DbRow(row._mapping, row)


def get_db_connection():
    return DbConnection()


def table_exists(table_name):
    return inspect(engine).has_table(table_name)


def column_names(table_name):
    if not table_exists(table_name):
        return set()
    return {column["name"] for column in inspect(engine).get_columns(table_name)}
