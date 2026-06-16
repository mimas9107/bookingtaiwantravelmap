"""Tests for room change detection algorithm."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

from database import compute_room_changes

# ── fixtures ──

ROOMS_FULL = [
    {"name": "松雪樓精緻兩人房", "available": True},
    {"name": "松雪樓景觀兩人房", "available": True},
    {"name": "松雪樓四人房", "available": True},
]

ROOMS_HALF = [
    {"name": "松雪樓精緻兩人房", "available": True},
    {"name": "松雪樓景觀兩人房", "available": False},
    {"name": "松雪樓四人房", "available": True},
]

ROOMS_NONE = [
    {"name": "松雪樓精緻兩人房", "available": False},
    {"name": "松雪樓景觀兩人房", "available": False},
    {"name": "松雪樓四人房", "available": False},
]


def test_no_prev_returns_none():
    """首次掃描，無前次資料 → 不回傳 changes"""
    assert compute_room_changes(None, ROOMS_FULL) is None


def test_no_change_returns_none():
    """前後一致 → None"""
    assert compute_room_changes(ROOMS_FULL, ROOMS_FULL) is None


def test_room_freed():
    """釋出：false → true"""
    prev = [{"name": "A", "available": False}]
    cur = [{"name": "A", "available": True}]
    assert compute_room_changes(prev, cur) == [
        {"name": "A", "from": False, "to": True},
    ]


def test_room_taken():
    """被訂：true → false"""
    prev = [{"name": "A", "available": True}]
    cur = [{"name": "A", "available": False}]
    assert compute_room_changes(prev, cur) == [
        {"name": "A", "from": True, "to": False},
    ]


def test_mixed_changes():
    """混合變動"""
    prev = [
        {"name": "精緻兩人房", "available": False},
        {"name": "景觀兩人房", "available": True},
    ]
    cur = [
        {"name": "精緻兩人房", "available": True},
        {"name": "景觀兩人房", "available": False},
    ]
    changes = compute_room_changes(prev, cur)
    assert len(changes) == 2
    assert {"name": "精緻兩人房", "from": False, "to": True} in changes
    assert {"name": "景觀兩人房", "from": True, "to": False} in changes


def test_partial_change():
    """只有部分房型變動"""
    prev = ROOMS_HALF
    cur = [
        {"name": "松雪樓精緻兩人房", "available": True},
        {"name": "松雪樓景觀兩人房", "available": True},
        {"name": "松雪樓四人房", "available": False},
    ]
    changes = compute_room_changes(prev, cur)
    assert len(changes) == 2
    assert {"name": "松雪樓景觀兩人房", "from": False, "to": True} in changes
    assert {"name": "松雪樓四人房", "from": True, "to": False} in changes


def test_full_to_none():
    """全滿→全無"""
    changes = compute_room_changes(ROOMS_FULL, ROOMS_NONE)
    assert len(changes) == 3
    assert all(c["from"] is True and c["to"] is False for c in changes)


def test_new_room_appears():
    """新房型出現（不在前次資料中）→ 不視為變動"""
    prev = [{"name": "A", "available": True}]
    cur = [{"name": "A", "available": True}, {"name": "B", "available": True}]
    assert compute_room_changes(prev, cur) is None


if __name__ == "__main__":
    tests = [n for n in dir() if n.startswith("test_")]
    passed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
    total = len(tests)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
