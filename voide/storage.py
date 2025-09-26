"""Persistence helpers for cache/memory/logging chunks."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryStore:
    """SQLite-backed key/value store with optional TTL-aware lookups."""

    _CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS items (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        created_at REAL NOT NULL
    )
    """

    _UPSERT_SQL = """
    INSERT INTO items(key, value, created_at)
    VALUES (?, ?, ?)
    ON CONFLICT(key) DO UPDATE SET
        value = excluded.value,
        created_at = excluded.created_at
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path).expanduser() if path else None
        db_path = str(self._path) if self._path else ":memory:"
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._conn:
            self._conn.execute(self._CREATE_TABLE_SQL)

    def upsert(self, key: str, value: Dict[str, Any]) -> None:
        payload = json.dumps(value, ensure_ascii=False)
        created_at = time.time()
        with self._conn:
            self._conn.execute(self._UPSERT_SQL, (key, payload, created_at))

    def get(self, key: str, ttl: Optional[float] = None) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT value, created_at FROM items WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None

        if ttl is not None and ttl >= 0:
            created_at = float(row["created_at"])
            if time.time() - created_at > ttl:
                with self._conn:
                    self._conn.execute("DELETE FROM items WHERE key = ?", (key,))
                return None

        return json.loads(row["value"])

    def query(
        self, pattern: str = "", k: int = 8, ttl: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        like = f"%{pattern}%"
        params: List[Any] = [like]
        conditions = "value LIKE ?"
        if ttl is not None and ttl >= 0:
            cutoff = time.time() - ttl
            conditions += " AND created_at >= ?"
            params.append(cutoff)

        params.append(k)
        rows = self._conn.execute(
            f"SELECT key, value, created_at FROM items WHERE {conditions} "
            "ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()

        results: List[Dict[str, Any]] = []
        for row in rows:
            record = json.loads(row["value"])
            results.append(record)
        return results


class JSONLog:
    """Append-only JSON lines logger with UTC timestamps."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: Dict[str, Any]) -> None:
        payload = dict(record)
        payload.setdefault(
            "timestamp",
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        line = json.dumps(payload, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

