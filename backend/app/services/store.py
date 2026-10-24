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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS quotes ("
        " id TEXT PRIMARY KEY, status TEXT, created_at TEXT, payload TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS idempotency ("
        " key TEXT PRIMARY KEY, created_at TEXT, response TEXT)"
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


_QUOTES_MEMORY: dict[str, dict] = {}


def save_quote(quote: dict) -> dict:
    with _LOCK:
        _QUOTES_MEMORY[quote["quote_id"]] = quote
        conn = _conn()
        if conn is not None:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO quotes (id, status, created_at, payload) "
                    "VALUES (?, ?, ?, ?)",
                    (quote["quote_id"], quote["status"], quote["created_at"], json.dumps(quote)),
                )
                conn.commit()
            finally:
                conn.close()
    return quote


def get_quote(quote_id: str) -> dict | None:
    with _LOCK:
        quote = _QUOTES_MEMORY.get(quote_id)
    if quote is not None:
        return quote
    conn = _conn()
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT payload FROM quotes WHERE id = ?", (quote_id,)
        ).fetchone()
    finally:
        conn.close()
    return json.loads(row[0]) if row else None


_IDEMPOTENCY_MEMORY: dict[str, dict] = {}


def save_idempotent_response(key: str, response: dict) -> dict:
    """First response for an idempotency key wins; replays return it verbatim."""
    with _LOCK:
        if key not in _IDEMPOTENCY_MEMORY:
            _IDEMPOTENCY_MEMORY[key] = response
            conn = _conn()
            if conn is not None:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO idempotency (key, created_at, response) "
                        "VALUES (?, ?, ?)",
                        (key, response.get("transaction", {}).get("created_at", ""),
                         json.dumps(response)),
                    )
                    conn.commit()
                finally:
                    conn.close()
        return _IDEMPOTENCY_MEMORY[key]


def get_idempotent_response(key: str) -> dict | None:
    with _LOCK:
        return _IDEMPOTENCY_MEMORY.get(key)
