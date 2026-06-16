#!/bin/bash
#===============================================================================
# 合歡山松雪樓 - 快速訂房搜尋腳本
# 直接查詢指定入住/退房日期的空房狀態與價格
#
# Usage:
#   ./search_booking.sh <入住日期> [退房日期]
#   ./search_booking.sh 2026-06-16           # 1晚
#   ./search_booking.sh 2026-06-16 2026-06-18 # 2晚
#===============================================================================

BASE_URL="https://booking.taiwantravelmap.com/user/searchbooking.aspx?m=1156"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <入住日期 YYYY-MM-DD> [退房日期 YYYY-MM-DD]"
    echo "  例: $0 2026-06-16"
    echo "  例: $0 2026-06-16 2026-06-18"
    exit 1
fi

CHECKIN=$(date -d "$1" +%Y/%m/%d 2>/dev/null)
if [ -z "$CHECKIN" ]; then
    echo "❌ 日期格式錯誤"
    exit 1
fi

if [ -n "$2" ]; then
    CHECKOUT=$(date -d "$2" +%Y/%m/%d 2>/dev/null)
else
    NEXT=$(date -d "$1 +1 day" +%s)
    CHECKOUT=$(date -d "@$NEXT" +%Y/%m/%d)
fi

echo "🔍 查詢: $CHECKIN → $CHECKOUT"
echo ""

URL="${BASE_URL}&checkin=${CHECKIN}&checkout=${CHECKOUT}&count=1&people=2&unit=room&lg=ch"
RESULT=$(curl -s --connect-timeout 10 --max-time 20 "$URL")

if echo "$RESULT" | grep -q "btGoOrderCalendar"; then
    echo "✅ 有空房！"
    echo ""
    python3 -c "
import re, html
content = open('/dev/stdin').read()
content = html.unescape(content)

titles = re.findall(r'room_type_title[^>]*>(.*?)</div>', content, re.DOTALL)
prices = re.findall(r'原價[^<]*<[^>]*>([^<]*)</span>', content)
discounts = re.findall(r'破盤價[^<]*<[^>]*>([^<]*)</span>', content)

for i, t in enumerate(titles):
    t_clean = re.sub(r'<[^>]+>', '', t).strip()
    price = prices[i].strip() if i < len(prices) else '?'
    disc = discounts[i].strip() if i < len(discounts) else '?'
    if t_clean:
        print(f'  [{i+1}] {t_clean} 原價{price} 特價{disc}')

# Show room IDs for order URL construction
ids = re.findall(r'RoomListView_ctl0(\d).*?btGoOrderCalendar', content)
if ids:
    room_idx = {'0': '精緻兩人房', '1': '景觀兩人房', '2': '四人房'}
    print()
    for rid in sorted(set(ids)):
        name = room_idx.get(rid, '?')
        print(f'  ⚡ 快速訂房 → https://booking.taiwantravelmap.com/user/searchbooking.aspx?m=1156 (選{name})')
" <<< "$RESULT"
else
    echo "❌ 已售完或無符合條件房間"
fi

echo ""
echo "---"
echo "官網搜尋結果:"
echo "$URL"
