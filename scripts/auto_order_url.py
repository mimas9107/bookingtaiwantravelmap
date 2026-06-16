#!/usr/bin/env python3
"""
合歡山松雪樓 - 訂房管線輔助腳本
自動執行 Step 1→Step 2（搜尋→選房型），在瀏覽器開啟 order.aspx。

Usage:
  ./scripts/auto_order_url.py <入住日期> [房型代號]
  ./scripts/auto_order_url.py 2026-07-01              # 景觀兩人房
  ./scripts/auto_order_url.py 2026-07-01 7734         # 精緻兩人房
  ./scripts/auto_order_url.py 2026-07-01 7736         # 四人房

房型代號: 7734=精緻兩人房, 7735=景觀兩人房(預設), 7736=四人房
"""
import sys, os, asyncio, webbrowser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dashboard.scraper import BookingScraper

ROOM_NAMES = {7734: "松雪樓精緻兩人房", 7735: "松雪樓景觀兩人房", 7736: "松雪樓四人房"}


async def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)

    checkin = sys.argv[1]
    room_id = int(sys.argv[2]) if len(sys.argv) >= 3 and sys.argv[2].isdigit() else 7735
    room_name = ROOM_NAMES.get(room_id, "?")

    s = BookingScraper()
    try:
        print(f"🔍 {checkin} | {room_name}")
        print()
        url = await s.order_url(checkin, room_id=room_id)
        print()
        print("👉 訂單頁已準備好，開啟瀏覽器...")
        print()
        print("   在瀏覽器中完成：")
        print("   1. 日曆點選入住日期")
        print("   2. 確認人數，點下一步")
        print("   3. 填姓名、電話、Email")
        print("   4. 選擇付款方式送出")
        print()
        print(f"   {url}")
        webbrowser.open(url)
    finally:
        await s.close()


if __name__ == "__main__":
    asyncio.run(main())
