#!/usr/bin/env python3
"""
Smoke test: two sequential scans → compare per-day room data.
Outputs {previous, current, changed} per date.
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dashboard"))

from scraper import BookingScraper
from datetime import datetime, timedelta

NAME_LABEL = {
    "松雪樓精緻兩人房": "精雙",
    "松雪樓景觀兩人房": "景雙",
    "松雪樓四人房": "四",
}


def short_name(name: str) -> str:
    return NAME_LABEL.get(name, name)


def compare_rooms(prev_rooms, curr_rooms):
    """Compare two room lists, return changes list and overall changed flag."""
    if not prev_rooms or not curr_rooms:
        return [], prev_rooms != curr_rooms
    prev_map = {r["name"]: r["available"] for r in prev_rooms}
    changes = []
    for r in curr_rooms:
        old = prev_map.get(r["name"])
        if old is not None and old != r["available"]:
            changes.append({"name": r["name"], "from": old, "to": r["available"]})
    return changes, len(changes) > 0


async def main():
    scraper = BookingScraper()

    today = datetime.now()
    start = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    end = (today + timedelta(days=3)).strftime("%Y-%m-%d")
    print(f"Smoke test range: {start} ~ {end} ({3} days)\n", flush=True)

    # ── scan 1 ──
    print("=== Scan 1 ===", flush=True)
    t0 = datetime.now()
    scan1 = await scraper.scan(start, end)
    t1 = datetime.now()
    print(f"  elapsed: {(t1 - t0).total_seconds():.1f}s", flush=True)

    # ── scan 2 ──
    print("\n=== Scan 2 ===", flush=True)
    scan2 = await scraper.scan(start, end)
    t2 = datetime.now()
    print(f"  elapsed: {(t2 - t1).total_seconds():.1f}s\n", flush=True)

    await scraper.close()

    # ── per-day comparison ──
    date_map1 = {r["date"]: r for r in scan1}
    date_map2 = {r["date"]: r for r in scan2}
    all_dates = sorted(set(date_map1.keys()) | set(date_map2.keys()))

    total = len(all_dates)
    changed_count = 0

    for ds in all_dates:
        r1 = date_map1.get(ds)
        r2 = date_map2.get(ds)

        prev_data = {
            "available": r1.get("available", False) if r1 else None,
            "room_count": r1.get("room_count", 0) if r1 else None,
            "rooms": r1.get("rooms", []) if r1 else [],
        } if r1 else None

        curr_data = {
            "available": r2.get("available", False) if r2 else None,
            "room_count": r2.get("room_count", 0) if r2 else None,
            "rooms": r2.get("rooms", []) if r2 else [],
        } if r2 else None

        # room-level diff
        changes, changed = compare_rooms(
            r1.get("rooms") if r1 else None,
            r2.get("rooms") if r2 else None,
        )

        if changed:
            changed_count += 1

        # pretty-print summary
        label = "🔄 CHANGED" if changed else "   same"
        avail1 = "✅" if prev_data["available"] else "❌" if prev_data else "?"
        avail2 = "✅" if curr_data["available"] else "❌" if curr_data else "?"

        def fmt_rooms(rooms):
            if not rooms:
                return "—"
            return ", ".join(
                f"{'✅' if r['available'] else '❌'}{short_name(r['name'])}"
                for r in rooms
            )

        def fmt_changes(changes):
            if not changes:
                return ""
            return " | " + ", ".join(
                f"{'🟢' if c['to'] else '🔴'}{short_name(c['name'])}"
                for c in changes
            )

        print(
            f"{label} {ds}  "
            f"{avail1} → {avail2}  "
            f"({prev_data['room_count']} → {curr_data['room_count']})  "
            f"[{fmt_rooms(prev_data['rooms'])}] → [{fmt_rooms(curr_data['rooms'])}]"
            f"{fmt_changes(changes)}"
        )

    print(f"\n── Summary ──")
    print(f"  total days:  {total}")
    print(f"  changed:     {changed_count}")
    print(f"  unchanged:   {total - changed_count}")

    # JSON output for machine consumption
    result = {
        "range": {"start": start, "end": end},
        "scans": {
            "first": {"finished_at": t1.isoformat()},
            "second": {"finished_at": t2.isoformat()},
        },
        "days": [],
    }
    for ds in all_dates:
        r1 = date_map1.get(ds)
        r2 = date_map2.get(ds)
        _, changed = compare_rooms(
            r1.get("rooms") if r1 else None,
            r2.get("rooms") if r2 else None,
        )
        result["days"].append({
            "date": ds,
            "previous": {
                "available": r1.get("available", False) if r1 else None,
                "room_count": r1.get("room_count", 0) if r1 else None,
                "rooms": r1.get("rooms", []) if r1 else [],
            } if r1 else None,
            "current": {
                "available": r2.get("available", False) if r2 else None,
                "room_count": r2.get("room_count", 0) if r2 else None,
                "rooms": r2.get("rooms", []) if r2 else [],
            } if r2 else None,
            "changed": changed,
        })

    print(f"\n── JSON ──")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if changed_count == 0 else 0  # always exit 0 for this test


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
