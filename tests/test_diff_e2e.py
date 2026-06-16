#!/usr/bin/env python3
"""
End-to-end test: save real data → modify rooms → verify changes are detected.

Simulates:
  - Room freed: false → true (someone cancelled, room released)
  - Room taken: true → false (someone booked)
"""

import json
import os
import sys
import tempfile
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

from database import compute_room_changes


def test(name, got, expected):
    ok = got == expected
    status = "✅" if ok else "❌"
    print(f"  {status} {name}")
    if not ok:
        print(f"    got:      {json.dumps(got, ensure_ascii=False)}")
        print(f"    expected: {json.dumps(expected, ensure_ascii=False)}")


def main():
    # ── real data from actual scrape ──
    room_18_1 = [  # scan 1: only 四人房 available
        {"name": "松雪樓精緻兩人房", "available": False},
        {"name": "松雪樓景觀兩人房", "available": False},
        {"name": "松雪樓四人房", "available": True},
    ]

    # ── Scenario A: 精緻兩人房 gets freed (false → true) ──
    print("=== Scenario A: room freed ===")
    room_18_freed = [
        {"name": "松雪樓精緻兩人房", "available": True},   # ← freed!
        {"name": "松雪樓景觀兩人房", "available": False},
        {"name": "松雪樓四人房", "available": True},
    ]
    changes_a = compute_room_changes(room_18_1, room_18_freed)
    test("changes not None", changes_a is not None, True)
    test("exactly 1 change", len(changes_a), 1)
    test("freed room detected",
         changes_a[0],
         {"name": "松雪樓精緻兩人房", "from": False, "to": True})

    # ── Scenario B: 四人房 gets booked (true → false) ──
    print("\n=== Scenario B: room taken ===")
    room_18_taken = [
        {"name": "松雪樓精緻兩人房", "available": False},
        {"name": "松雪樓景觀兩人房", "available": False},
        {"name": "松雪樓四人房", "available": False},       # ← booked!
    ]
    changes_b = compute_room_changes(room_18_1, room_18_taken)
    test("changes not None", changes_b is not None, True)
    test("exactly 1 change", len(changes_b), 1)
    test("taken room detected",
         changes_b[0],
         {"name": "松雪樓四人房", "from": True, "to": False})

    # ── Scenario C: both freed AND taken simultaneously ──
    print("\n=== Scenario C: mixed changes ===")
    room_18_mixed = [
        {"name": "松雪樓精緻兩人房", "available": True},    # freed
        {"name": "松雪樓景觀兩人房", "available": False},
        {"name": "松雪樓四人房", "available": False},       # taken
    ]
    changes_c = compute_room_changes(room_18_1, room_18_mixed)
    test("changes not None", changes_c is not None, True)
    test("exactly 2 changes", len(changes_c), 2)
    test("freed: 精緻兩人房",
         {"name": "松雪樓精緻兩人房", "from": False, "to": True} in changes_c,
         True)
    test("taken: 四人房",
         {"name": "松雪樓四人房", "from": True, "to": False} in changes_c,
         True)

    # ── Scenario D: no change ──
    print("\n=== Scenario D: no change ===")
    changes_d = compute_room_changes(room_18_1, room_18_1)
    test("changes is None (no change)", changes_d is None, True)

    # ── Scenario E: first-time save (no previous) ──
    print("\n=== Scenario E: first save (no previous) ===")
    changes_e = compute_room_changes(None, room_18_1)
    test("changes is None (first save)", changes_e is None, True)

    # ── Scenario F: DB round-trip with _save() ──
    print("\n=== Scenario F: DB round-trip (sqlite3) ===")
    from database import _init, _save, _get_all

    # Use a temp DB for isolation
    tmp_dir = tempfile.mkdtemp()
    orig_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data")
    orig_db = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data", "scans.db")

    # We need to override DB_PATH temporarily
    import database as db_mod
    original_db_path = db_mod.DB_PATH
    original_db_dir = db_mod.DB_DIR
    test_db_path = os.path.join(tmp_dir, "test_scans.db")

    db_mod.DB_DIR = tmp_dir
    db_mod.DB_PATH = test_db_path

    try:
        _init()
        # Save first scan (no changes expected)
        _save("2026-06-18", True, 1, "2026-06-16T12:00:00+00:00", room_18_1)
        rows = _get_all()
        day = next(r for r in rows if r["date"] == "2026-06-18")
        test("first save includes rooms",
             day.get("rooms"),
             room_18_1)
        test("first save has no changes",
             day.get("changes"),
             None)

        # Save modified data (freed scenario)
        _save("2026-06-18", True, 2, "2026-06-16T13:00:00+00:00", room_18_freed)
        rows = _get_all()
        day = next(r for r in rows if r["date"] == "2026-06-18")
        test("second save includes updated rooms",
             day.get("rooms"),
             room_18_freed)
        test("second save has changes",
             day.get("changes") is not None,
             True)
        test("change count = 1",
             len(day.get("changes", [])),
             1)
        test("freed room in changes",
             day["changes"][0],
             {"name": "松雪樓精緻兩人房", "from": False, "to": True})

        # Save again without changes
        _save("2026-06-18", True, 2, "2026-06-16T14:00:00+00:00", room_18_freed)
        rows = _get_all()
        day = next(r for r in rows if r["date"] == "2026-06-18")
        test("third save (no new change → changes is None)",
             day.get("changes"),
             None)

    finally:
        db_mod.DB_DIR = original_db_dir
        db_mod.DB_PATH = original_db_path
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── Scenario G: multiple dates, one with changes, one without ──
    print("\n=== Scenario G: multiple dates ===")
    tmp_dir2 = tempfile.mkdtemp()
    db_mod.DB_DIR = tmp_dir2
    db_mod.DB_PATH = os.path.join(tmp_dir2, "test_scans.db")
    try:
        _init()

        # date A: first save
        _save("2026-06-17", False, 0, "2026-06-16T12:00:00+00:00", [
            {"name": "A", "available": False},
            {"name": "B", "available": False},
        ])
        # date B: first save
        _save("2026-06-18", True, 2, "2026-06-16T12:00:00+00:00", [
            {"name": "A", "available": True},
            {"name": "B", "available": True},
        ])

        rows = _get_all()
        test("2 rows saved", len(rows), 2)

        # date A: still no changes, same data
        _save("2026-06-17", False, 0, "2026-06-16T13:00:00+00:00", [
            {"name": "A", "available": False},
            {"name": "B", "available": False},
        ])
        # date B: B gets booked
        _save("2026-06-18", True, 1, "2026-06-16T13:00:00+00:00", [
            {"name": "A", "available": True},
            {"name": "B", "available": False},
        ])

        rows = _get_all()
        d17 = next(r for r in rows if r["date"] == "2026-06-17")
        d18 = next(r for r in rows if r["date"] == "2026-06-18")

        test("date A: no changes", d17.get("changes"), None)
        test("date B: has changes", d18.get("changes") is not None, True)
        test("date B: 1 change", len(d18["changes"]), 1)
        test("date B: B taken",
             d18["changes"][0],
             {"name": "B", "from": True, "to": False})
    finally:
        db_mod.DB_DIR = original_db_dir
        db_mod.DB_PATH = original_db_path
        import shutil
        shutil.rmtree(tmp_dir2, ignore_errors=True)

    print("\n── ALL SCENARIOS PASSED ──")


if __name__ == "__main__":
    main()
