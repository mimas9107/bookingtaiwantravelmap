#!/bin/bash
#===============================================================================
# 合歡山松雪樓 - 空房查詢腳本
# 檢查指定日期範圍內每天是否有空房
#
# Usage:
#   ./check_availability.sh [start_date] [end_date]
#   ./check_availability.sh                     # 預設：今天 ~ 30天後
#   ./check_availability.sh 2026-06-15 2026-07-15
#
# 注意：
#   - 僅檢查一般房型（1間房、2位成人）
#   - 可訂日期範圍為第2天~第30天
#   - 回傳結果僅供參考，實際以官網為準
#===============================================================================

BASE_URL="https://booking.taiwantravelmap.com/user/searchbooking.aspx?m=1156"

# 日期預設值
START_DATE="${1:-$(date +%Y-%m-%d)}"
END_DATE="${2:-$(date -d '+30 days' +%Y-%m-%d)}"

START_TS=$(date -d "$START_DATE" +%s)
END_TS=$(date -d "$END_DATE" +%s)
CURRENT_TS=$START_TS

echo "=== 合歡山松雪樓 空房查詢 ==="
echo "查詢範圍: $(date -d @$START_TS +%Y/%m/%d) ~ $(date -d @$END_TS +%Y/%m/%d) (入住日期)"
echo ""

AVAILABLE=()
SOLD_OUT=()

while [ $CURRENT_TS -le $END_TS ]; do
    CHECKIN=$(date -d "@$CURRENT_TS" +%Y/%m/%d)
    NEXT_TS=$((CURRENT_TS + 86400))
    NEXT=$(date -d "@$NEXT_TS" +%Y/%m/%d)

    URL="${BASE_URL}&checkin=${CHECKIN}&checkout=${NEXT}&count=1&people=2&unit=room&lg=ch"
    RESULT=$(curl -s --connect-timeout 10 --max-time 20 "$URL")

    if echo "$RESULT" | grep -q "btGoOrderCalendar\|一般訂房"; then
        echo "✅ $CHECKIN - 有空房"
        AVAILABLE+=("$CHECKIN")
    elif echo "$RESULT" | grep -q "松雪樓"; then
        echo "✅ $CHECKIN - 有空房"
        AVAILABLE+=("$CHECKIN")
    else
        echo "❌ $CHECKIN - 已售完"
        SOLD_OUT+=("$CHECKIN")
    fi

    CURRENT_TS=$NEXT_TS
    sleep 0.5
done

# 摘要
echo ""
echo "=== 查詢完畢 ==="
echo "✅ 有空房: ${#AVAILABLE[@]} 天"
for d in "${AVAILABLE[@]}"; do
    echo "   $d"
done
echo "❌ 已售完: ${#SOLD_OUT[@]} 天"
