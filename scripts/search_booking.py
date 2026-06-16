#!/usr/bin/env python3
"""
合歡山松雪樓 - 查詢特定入住日的空房狀態與房型。

Usage:
  ./scripts/search_booking.py <入住日期> [退房日期]
  ./scripts/search_booking.py 2026-07-01              # 1 晚
  ./scripts/search_booking.py 2026-07-01 2026-07-03   # 2 晚
"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from dashboard.scraper import BookingScraper

ROOM_IDS = {7734: "松雪樓精緻兩人房", 7735: "松雪樓景觀兩人房", 7736: "松雪樓四人房"}


async def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)

    checkin = sys.argv[1]
    checkout = sys.argv[2] if len(sys.argv) >= 3 else ""

    s = BookingScraper()
    try:
        data = await s.rooms(checkin)
        print(f"🔍 查詢: {checkin} → {checkout or '(隔日)'}")
        print()

        if not data["available"]:
            print("❌ 已售完或無符合條件房間")
            return

        print("✅ 有空房！\n")
        for rm in data["rooms"]:
            status = "✅ 可訂" if rm["available"] else "❌ 已售完"
            print(f"  {rm['name']}: {status}")

        print()
        # show quick-order hints
        print("⚡ 快速訂房:")
        for rid, rname in ROOM_IDS.items():
            print(f"   ./auto_order_url.py {checkin} {rid}  # {rname}")
    finally:
        await s.close()


if __name__ == "__main__":
    asyncio.run(main())
