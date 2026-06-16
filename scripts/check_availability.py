#!/usr/bin/env python3
"""
合歡山松雪樓 - 空房查詢腳本
檢查指定日期範圍內每天是否有空房。

Usage:
  ./scripts/check_availability.py [start_date] [end_date]
  ./scripts/check_availability.py                     # 預設：明天 ~ 30 天後
  ./scripts/check_availability.py 2026-07-01 2026-07-15
"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from dashboard.scraper import BookingScraper


async def main():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if len(sys.argv) >= 3:
        start, end = sys.argv[1], sys.argv[2]
    elif len(sys.argv) == 2:
        start, end = sys.argv[1], (today + timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        start = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end = (today + timedelta(days=31)).strftime("%Y-%m-%d")

    s = BookingScraper()
    try:
        print(f"=== 合歡山松雪樓 空房查詢 ===")
        print(f"查詢範圍: {start} ~ {end} (入住日期)\n")

        results = await s.scan(start, end)
        avail = [r for r in results if r.get("available")]
        sold = [r for r in results if not r.get("available")]

        for r in results:
            icon = "✅" if r.get("available") else "❌"
            err = f" ({r['error']})" if r.get("error") else ""
            rooms = f" ({r['room_count']} 間)" if r.get("room_count") else ""
            print(f"  {icon} {r['date']}{rooms}{err}")

        print(f"\n=== 查詢完畢 ===")
        print(f"✅ 有空房: {len(avail)} 天")
        for r in avail:
            print(f"   {r['date']}")
        print(f"❌ 已售完: {len(sold)} 天")
    finally:
        await s.close()


if __name__ == "__main__":
    asyncio.run(main())
