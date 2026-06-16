import sqlite3
import asyncio
import json
import os
from datetime import datetime, timezone
from functools import partial

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "scans.db")


def _conn():
    os.makedirs(DB_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


def _init():
    c = _conn()
    c.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            date TEXT PRIMARY KEY,
            available INTEGER NOT NULL DEFAULT 0,
            room_count INTEGER NOT NULL DEFAULT 0,
            scanned_at TEXT NOT NULL
        )
    """)
    c.commit()
    c.close()

def _save(date, available, room_count, scanned_at):
    c = _conn()
    c.execute("""
        INSERT OR REPLACE INTO scans (date, available, room_count, scanned_at)
        VALUES (?, ?, ?, ?)
    """, (date, int(available), room_count, scanned_at))
    c.commit()
    c.close()

def _get_all():
    c = _conn()
    rows = c.execute("SELECT * FROM scans ORDER BY date").fetchall()
    c.close()
    return [dict(r) for r in rows]

def _get_meta():
    c = _conn()
    row = c.execute("""
        SELECT scanned_at, COUNT(*) as total,
               SUM(available) as avail_count
        FROM scans
    """).fetchone()
    c.close()
    return dict(row) if row and row["total"] else None


class Database:
    def __init__(self):
        self._loop = asyncio.get_event_loop()

    async def init(self):
        await self._loop.run_in_executor(None, _init)

    async def save(self, date: str, available: bool, room_count: int):
        scanned_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        await self._loop.run_in_executor(
            None, partial(_save, date, available, room_count, scanned_at)
        )

    async def get_all(self) -> list:
        rows = await self._loop.run_in_executor(None, _get_all)
        for r in rows:
            r["available"] = bool(r["available"])
        return rows

    async def get_meta(self) -> dict | None:
        return await self._loop.run_in_executor(None, _get_meta)
