"""site.db 資料庫初始化與種子資料。"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).with_name("site.db")


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    contact TEXT NOT NULL,
    phone TEXT NOT NULL,
    tax_id TEXT NOT NULL UNIQUE,
    rating INTEGER NOT NULL DEFAULT 3 CHECK (rating BETWEEN 1 AND 5),
    note TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_date TEXT NOT NULL,
    material_name TEXT NOT NULL,
    vendor_id INTEGER NOT NULL,
    inbound_qty REAL NOT NULL DEFAULT 0,
    used_qty REAL NOT NULL DEFAULT 0,
    current_stock REAL NOT NULL DEFAULT 0,
    safety_stock REAL NOT NULL DEFAULT 0,
    unit TEXT NOT NULL DEFAULT '噸',
    unit_price REAL NOT NULL DEFAULT 0,
    invoice_no TEXT DEFAULT '',
    paid INTEGER NOT NULL DEFAULT 0 CHECK (paid IN (0, 1)),
    note TEXT DEFAULT '',
    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_date TEXT NOT NULL,
    category TEXT NOT NULL,
    item TEXT NOT NULL,
    amount REAL NOT NULL,
    handler TEXT NOT NULL,
    note TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS equipment_rentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_name TEXT NOT NULL,
    borrower TEXT NOT NULL,
    borrow_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    return_date TEXT,
    status TEXT NOT NULL DEFAULT '借出中' CHECK (status IN ('借出中', '已歸還')),
    note TEXT DEFAULT ''
);
"""

VENDORS = [
    ("台灣水泥股份有限公司", "水泥", "陳明宏", "0912-345-678", "03512578", 5, "北部長期配合，供貨穩定"),
    ("唐榮鐵工廠股份有限公司", "鋼構", "林志豪", "0923-456-789", "07821345", 4, "鋼筋加工與配送"),
    ("大甲砂石行", "砂石", "王阿水", "0933-567-890", "04567890", 4, "粒料品質良好"),
    ("東昇模板工程行", "模板", "李東昇", "0955-888-777", "26783456", 3, "模板系統暫緩付款"),
    ("宏遠機電工程有限公司", "水電", "張宏遠", "0966-777-888", "16823456", 5, "機電與臨時用水電"),
]

MATERIALS = [
    ("2026-11-18", "水泥", 1, 25.0, 8.0, 17.0, 10.0, "噸", 380.0, "INV-20261118-001", 0, "台中捷運周邊工程"),
    ("2026-11-17", "鋼筋", 2, 12.0, 9.5, 2.5, 5.0, "噸", 17500.0, "INV-20261117-002", 1, "已請款，待對帳"),
    ("2026-11-16", "砂石", 3, 40.0, 22.0, 18.0, 15.0, "立方公尺", 650.0, "INV-20261116-003", 1, "級配砂石"),
    ("2026-11-15", "模板", 4, 180.0, 165.0, 15.0, 30.0, "片", 220.0, "INV-20261115-004", 0, "庫存偏低需補貨"),
    ("2026-11-14", "水泥", 1, 20.0, 18.0, 2.0, 10.0, "噸", 380.0, "INV-20261114-005", 1, "已對帳完成"),
]

EXPENSES = [
    ("2026-11-18", "膳食費", "工地便當 25 份", 2500, "黃秘書", "中午加班便當"),
    ("2026-11-17", "五金耗材", "鐵釘、砂輪片", 1280, "王工頭", "現場修補用"),
    ("2026-11-16", "交通費", "材料送貨車資", 900, "黃秘書", "砂石進場"),
    ("2026-11-15", "清潔費", "工務所清潔用品", 650, "林小姐", ""),
    ("2026-11-14", "雜支", "安全帽 5 頂", 1500, "王工頭", "新進人員"),
]

EQUIPMENT = [
    ("夯實機", "陳明宏", "2026-11-18", "2026-11-20", None, "借出中", "B區回填"),
    ("發電機", "林志豪", "2026-11-17", "2026-11-19", None, "借出中", "夜間施工"),
    ("夯實機", "王阿水", "2026-11-10", "2026-11-12", "2026-11-12", "已歸還", ""),
    ("發電機", "李東昇", "2026-11-05", "2026-11-08", "2026-11-08", "已歸還", ""),
    ("夯實機", "張宏遠", "2026-11-18", "2026-11-21", None, "借出中", "C區整地"),
]


def init_db() -> None:
    """建立資料表．若無資料則寫入 5 筆模擬資料。"""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO vendors (name, category, contact, phone, tax_id, rating, note) VALUES (?,?,?,?,?,?,?)",
                VENDORS,
            )
        if conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0] == 0:
            conn.executemany(
                """INSERT INTO materials
                (record_date, material_name, vendor_id, inbound_qty, used_qty, current_stock,
                 safety_stock, unit, unit_price, invoice_no, paid, note)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                MATERIALS,
            )
        if conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO expenses (expense_date, category, item, amount, handler, note) VALUES (?,?,?,?,?,?)",
                EXPENSES,
            )
        if conn.execute("SELECT COUNT(*) FROM equipment_rentals").fetchone()[0] == 0:
            conn.executemany(
                """INSERT INTO equipment_rentals
                (equipment_name, borrower, borrow_date, due_date, return_date, status, note)
                VALUES (?,?,?,?,?,?,?)""",
                EQUIPMENT,
            )


if __name__ == "__main__":
    init_db()
    print(f"資料庫已建立：{DB_PATH}")
