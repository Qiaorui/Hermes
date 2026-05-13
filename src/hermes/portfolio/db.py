"""SQLite database for portfolio, watchlist, triggers, and reports."""

import sqlite3
from pathlib import Path
from hermes.portfolio.models import Holding, WatchItem, TriggerCondition, Report, Transaction

from hermes.config import CONFIG_DIR

DB_PATH = CONFIG_DIR / "hermes.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    name TEXT,
    cost_price REAL NOT NULL,
    shares INTEGER NOT NULL,
    buy_date TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    name TEXT,
    type TEXT NOT NULL,
    value REAL,
    description TEXT,
    active INTEGER DEFAULT 1,
    source TEXT DEFAULT 'auto',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    content TEXT NOT NULL,
    score INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    name TEXT,
    action TEXT NOT NULL,
    price REAL NOT NULL,
    shares INTEGER NOT NULL,
    amount REAL NOT NULL,
    note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def _get_conn() -> sqlite3.Connection:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    # Migration: add source column if missing (existing databases)
    try:
        conn.execute("SELECT source FROM triggers LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE triggers ADD COLUMN source TEXT DEFAULT 'auto'")
        conn.commit()
    return conn


def add_holding(code: str, name: str, cost_price: float, shares: int, buy_date: str) -> Holding:
    conn = _get_conn()
    cur = conn.execute("INSERT INTO holdings (code, name, cost_price, shares, buy_date) VALUES (?, ?, ?, ?, ?)",
                 (code, name, cost_price, shares, buy_date))
    conn.commit()
    row = conn.execute("SELECT * FROM holdings WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return Holding(**dict(row))


def get_holding(id: int) -> Holding | None:
    """Get a single holding by id."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM holdings WHERE id=?", (id,)).fetchone()
    conn.close()
    return Holding(**dict(row)) if row else None


def remove_holding(id: int) -> bool:
    """Remove a holding by id."""
    conn = _get_conn()
    cur = conn.execute("DELETE FROM holdings WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def list_holdings() -> list[Holding]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM holdings ORDER BY id").fetchall()
    conn.close()
    return [Holding(**dict(r)) for r in rows]


def update_holding(id: int, cost_price: float | None = None, shares: int | None = None, buy_date: str | None = None) -> Holding | None:
    """Update holding fields by id. Only updates fields that are not None."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM holdings WHERE id=?", (id,)).fetchone()
    if not row:
        conn.close()
        return None

    updates = []
    values = []
    if cost_price is not None:
        updates.append("cost_price=?")
        values.append(cost_price)
    if shares is not None:
        updates.append("shares=?")
        values.append(shares)
    if buy_date is not None:
        updates.append("buy_date=?")
        values.append(buy_date)

    if not updates:
        conn.close()
        return Holding(**dict(row))

    values.append(id)
    conn.execute(f"UPDATE holdings SET {', '.join(updates)} WHERE id=?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM holdings WHERE id=?", (id,)).fetchone()
    conn.close()
    return Holding(**dict(row))


def add_watch(code: str, name: str) -> WatchItem:
    conn = _get_conn()
    conn.execute("INSERT OR IGNORE INTO watchlist (code, name) VALUES (?, ?)", (code, name))
    conn.commit()
    row = conn.execute("SELECT * FROM watchlist WHERE code=?", (code,)).fetchone()
    conn.close()
    return WatchItem(**dict(row))


def remove_watch(code: str) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM watchlist WHERE code=?", (code,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def list_watchlist() -> list[WatchItem]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM watchlist ORDER BY id").fetchall()
    conn.close()
    return [WatchItem(**dict(r)) for r in rows]


def add_trigger(code: str, name: str, type: str, value: float, description: str = "") -> TriggerCondition:
    conn = _get_conn()
    cur = conn.execute("INSERT INTO triggers (code, name, type, value, description, source) VALUES (?, ?, ?, ?, ?, 'manual')",
                 (code, name, type, value, description))
    conn.commit()
    row = conn.execute("SELECT * FROM triggers WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return TriggerCondition(**dict(row))


def remove_trigger(id: int) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM triggers WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def list_triggers(code: str = "") -> list[TriggerCondition]:
    conn = _get_conn()
    if code:
        rows = conn.execute("SELECT * FROM triggers WHERE code=? AND active=1 ORDER BY id", (code,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM triggers WHERE active=1 ORDER BY id").fetchall()
    conn.close()
    return [TriggerCondition(**dict(r)) for r in rows]


def save_triggers(triggers: list[TriggerCondition]) -> None:
    """Save a batch of auto-generated triggers, replacing only existing auto triggers for same code.
    Manual triggers (source='manual') are preserved.
    """
    if not triggers:
        return
    code = triggers[0].code
    conn = _get_conn()
    conn.execute("UPDATE triggers SET active=0 WHERE code=? AND source='auto'", (code,))
    for t in triggers:
        conn.execute("INSERT INTO triggers (code, name, type, value, description, source) VALUES (?, ?, ?, ?, ?, ?)",
                     (t.code, t.name, t.type, t.value, t.description, t.source or "auto"))
    conn.commit()
    conn.close()


def save_report(code: str, content: str, score: int = 0) -> Report:
    conn = _get_conn()
    cur = conn.execute("INSERT INTO reports (code, content, score) VALUES (?, ?, ?)", (code, content, score))
    conn.commit()
    row = conn.execute("SELECT * FROM reports WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return Report(**dict(row))


def get_report(code: str) -> Report | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM reports WHERE code=? ORDER BY id DESC LIMIT 1", (code,)).fetchone()
    conn.close()
    return Report(**dict(row)) if row else None


def add_transaction(code: str, name: str, action: str, price: float, shares: int, note: str = "") -> Transaction:
    conn = _get_conn()
    amount = round(price * shares, 2)
    cur = conn.execute("INSERT INTO transactions (code, name, action, price, shares, amount, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (code, name, action, price, shares, amount, note))
    conn.commit()
    row = conn.execute("SELECT * FROM transactions WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return Transaction(**dict(row))


def list_transactions(code: str = "", limit: int = 50) -> list[Transaction]:
    conn = _get_conn()
    if code:
        rows = conn.execute("SELECT * FROM transactions WHERE code=? ORDER BY id DESC LIMIT ?", (code, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [Transaction(**dict(r)) for r in rows]