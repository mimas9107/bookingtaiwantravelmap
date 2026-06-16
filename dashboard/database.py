import sqlite3
import asyncio
import json
import os
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from functools import partial

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "scans.db")
_db_lock = threading.Lock()


def compute_room_changes(old_rooms, new_rooms):
    """Compare two room lists and return changes (flipped status only).

    old_rooms / new_rooms: list of {"name": str, "available": bool} or None.
    Returns list of {"name": str, "from": bool, "to": bool} or None if no change.
    """
    if not old_rooms or not new_rooms:
        return None
    old_map = {r["name"]: r["available"] for r in old_rooms}
    changes = []
    for r in new_rooms:
        prev = old_map.get(r["name"])
        if prev is not None and prev != r["available"]:
            changes.append({"name": r["name"], "from": prev, "to": r["available"]})
    return changes or None


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
            scanned_at TEXT NOT NULL,
            rooms_json TEXT,
            changes_json TEXT
        )
    """)
    for col in ("rooms_json", "changes_json"):
        try:
            c.execute(f"ALTER TABLE scans ADD COLUMN {col} TEXT")
        except Exception:
            pass
    c.commit()
    c.close()

def _save(date, available, room_count, scanned_at, rooms=None):
    c = _conn()
    rooms_json = json.dumps(rooms, ensure_ascii=False) if rooms else None
    changes_json = None
    if rooms:
        prev = c.execute("SELECT rooms_json FROM scans WHERE date=?", (date,)).fetchone()
        old_rooms = json.loads(prev["rooms_json"]) if prev and prev["rooms_json"] else None
        changes = compute_room_changes(old_rooms, rooms)
        changes_json = json.dumps(changes, ensure_ascii=False) if changes else None
    c.execute("""
        INSERT OR REPLACE INTO scans (date, available, room_count, scanned_at, rooms_json, changes_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (date, int(available), room_count, scanned_at, rooms_json, changes_json))
    c.commit()
    c.close()

def _get_all():
    c = _conn()
    rows = c.execute("SELECT * FROM scans ORDER BY date").fetchall()
    c.close()
    result = []
    for r in rows:
        d = dict(r)
        d["available"] = bool(d["available"])
        if d.get("rooms_json"):
            d["rooms"] = json.loads(d["rooms_json"])
        if d.get("changes_json"):
            d["changes"] = json.loads(d["changes_json"])
        d.pop("rooms_json", None)
        d.pop("changes_json", None)
        result.append(d)
    return result

def _get_meta():
    c = _conn()
    row = c.execute("""
        SELECT scanned_at, COUNT(*) as total,
               SUM(available) as avail_count
        FROM scans
    """).fetchone()
    c.close()
    return dict(row) if row and row["total"] else None

def _export_backup() -> str | None:
    """Create a consistent snapshot via SQLite backup API (includes WAL data)."""
    with _db_lock:
        if not os.path.exists(DB_PATH):
            return None
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        dst_path = tmp.name
        tmp.close()
        try:
            src = sqlite3.connect(DB_PATH)
            dst = sqlite3.connect(dst_path)
            src.backup(dst)
            dst.close()
            src.close()
            return dst_path
        except Exception:
            if os.path.exists(dst_path):
                os.unlink(dst_path)
            raise

def _import_from_bytes(data: bytes) -> int:
    if not data.startswith(b'SQLite format 3\x00'):
        raise ValueError("不是有效的 SQLite 檔案 (missing magic header)")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        c = sqlite3.connect(tmp_path)
        tables = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='scans'"
        ).fetchall()
        c.close()
        if not tables:
            raise ValueError("上傳的資料庫缺少 scans 資料表")
        # lock: 禁止 concurrent _save / _export_backup 與檔案置換競搶
        with _db_lock:
            os.makedirs(DB_DIR, exist_ok=True)
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
            shutil.move(tmp_path, DB_PATH)
            tmp_path = None
            c = sqlite3.connect(DB_PATH)
            count = c.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
            c.close()
            return count
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


class Database:
    def __init__(self):
        self._loop = asyncio.get_event_loop()

    async def init(self):
        await self._loop.run_in_executor(None, _init)

    async def save(self, date: str, available: bool, room_count: int, rooms: list = None):
        scanned_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        await self._loop.run_in_executor(
            None, partial(_save, date, available, room_count, scanned_at, rooms)
        )

    async def get_all(self) -> list:
        rows = await self._loop.run_in_executor(None, _get_all)
        return rows

    async def get_meta(self) -> dict | None:
        return await self._loop.run_in_executor(None, _get_meta)

    async def export_backup(self) -> str | None:
        return await self._loop.run_in_executor(None, _export_backup)

    async def import_db(self, data: bytes) -> int:
        return await self._loop.run_in_executor(None, _import_from_bytes, data)
