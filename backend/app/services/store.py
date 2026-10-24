"""Transaction store — in-memory for the demo, optional SQLite persistence.

Set BORDERLESS_MONEY_DB_PATH=/path/file.sqlite to persist receipts across restarts.
Production store is PostgreSQL (see app/db/schema.sql); this keeps the demo
zero-setup for judges.
"""
import json
import os
import sqlite3
import threading

from app import config

_LOCK = threading.Lock()
_MEMORY: dict[str, dict] = {}
_DB_PATH = config.DB_PATH


def _ensure_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS transactions ("
        " id TEXT PRIMARY KEY, status TEXT, created_at TEXT, payload TEXT)"
    )


def _conn() -> sqlite3.Connection | None:
    if not _DB_PATH:
        return None
    conn = sqlite3.connect(_DB_PATH)
    _ensure_db(conn)
    return conn


def save_transaction(tx: dict) -> dict:
    with _LOCK:
        _MEMORY[tx["transaction_id"]] = tx
        conn = _conn()
        if conn is not None:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO transactions (id, status, created_at, payload) "
                    "VALUES (?, ?, ?, ?)",
                    (tx["transaction_id"], tx["status"], tx["created_at"], json.dumps(tx)),
                )
                conn.commit()
            finally:
                conn.close()
    return tx


def get_transaction(transaction_id: str) -> dict | None:
    with _LOCK:
        tx = _MEMORY.get(transaction_id)
    if tx is not None:
        return tx
    conn = _conn()
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT payload FROM transactions WHERE id = ?", (transaction_id,)
        ).fetchone()
    finally:
        conn.close()
    return json.loads(row[0]) if row else None
