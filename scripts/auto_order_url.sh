#!/bin/bash
#===============================================================================
# 合歡山松雪樓 - 訂房管線輔助腳本
# 自動執行 Step 1→Step 2（搜尋→選房型），在瀏覽器開啟 order.aspx
#
# 說明：
#   執行後會自動用瀏覽器開啟 order.aspx，
#   後續 Step 3（日曆選日期、填人數）與 Step 4（填個資、第三方金流）
#   皆在瀏覽器中由真人完成。
#
# Usage:
#   ./auto_order_url.sh <入住日期> [退房日期] [房型代號]
#   ./auto_order_url.sh 2026-06-16                    # 1晚，精緻兩人房
#   ./auto_order_url.sh 2026-06-16 2026-06-18         # 2晚
#   ./auto_order_url.sh 2026-06-16 "" 7735            # 景觀兩人房
#
# 房型代號: 7734=精緻兩人房, 7735=景觀兩人房, 7736=四人房
#===============================================================================

CHECKIN="${1:?Usage: $0 <入住日期> [退房日期] [房型代號]}"
CHECKOUT="$2"
ROOM_ID="${3:-7734}"

python3 /dev/stdin << PYEOF
import urllib.request, urllib.parse, re, sys, webbrowser
from http.cookiejar import CookieJar

checkin_arg = "$CHECKIN"
checkout_arg = "$CHECKOUT"
room_id = "$ROOM_ID"

room_names = {'7734': '松雪樓精緻兩人房', '7735': '松雪樓景觀兩人房', '7736': '松雪樓四人房'}
btn_map = {'7734': 0, '7735': 1, '7736': 2}

from datetime import datetime, timedelta
dt = datetime.strptime(checkin_arg, '%Y-%m-%d')
checkin_fmt = dt.strftime('%Y/%m/%d')
if checkout_arg:
    checkout_fmt = datetime.strptime(checkout_arg, '%Y-%m-%d').strftime('%Y/%m/%d')
else:
    checkout_fmt = (dt + timedelta(days=1)).strftime('%Y/%m/%d')

room_name = room_names.get(room_id, '?')
btn_idx = btn_map.get(room_id, 0)
btn_name = f'RoomListView\$ctl0{btn_idx}\$btGoOrderCalendar'

print(f'🔍 {checkin_fmt} → {checkout_fmt} | {room_name}')
print()

cj = CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPRedirectHandler()
)

search_url = (f'https://booking.taiwantravelmap.com/user/searchbooking.aspx'
              f'?m=1156&checkin={checkin_fmt}&checkout={checkout_fmt}'
              f'&count=1&people=2&unit=room&lg=ch')

print('Step 1: GET 搜尋頁...', end=' ', flush=True)
resp = opener.open(search_url)
html = resp.read().decode('utf-8', errors='replace')
if 'btGoOrderCalendar' not in html:
    print('❌ 無空房')
    sys.exit(1)
print('✅')

def gf(name):
    m = re.search(rf'{name}" value="([^"]*)"', html)
    return m.group(1) if m else ''

print('Step 2: POST 選房型...', end=' ', flush=True)
form = {
    '_TSM_HiddenField_': gf('_TSM_HiddenField_'),
    '__VIEWSTATE': gf('__VIEWSTATE'),
    '__VIEWSTATEGENERATOR': gf('__VIEWSTATEGENERATOR'),
    '__VIEWSTATEENCRYPTED': '',
    '__EVENTVALIDATION': gf('__EVENTVALIDATION'),
    '__EVENTTARGET': '', '__EVENTARGUMENT': '', '__LASTFOCUS': '',
    'PageHeader\$SourceURL': '?', 'PageHeader\$hf_lg': 'ch',
    'PageHeader\$hd_ticket_fixdays': 'false', 'PageHeader\$hd_ticket_staydays': '0',
    'PageHeader\$EndMessage': '?', 'PageHeader\$OutsideEndMessage': '?',
    'PageHeader\$EndNextPage': '?', 'PageHeader\$OutsideEndNextPage': '?',
    btn_name: '一般訂房',
}
data = urllib.parse.urlencode(form).encode()
req = urllib.request.Request(search_url, data=data,
    headers={'Content-Type': 'application/x-www-form-urlencoded'})
resp2 = opener.open(req)
_ = resp2.read()

# 取得最終 order.aspx URL
# urllib 會跟 redirect，但 ASP.NET Server.Transfer 不會改變瀏覽器 URL
# 所以直接用 resp2.url（urllib 會追到最終 response 的 URL）
order_url = resp2.url
if 'order.aspx' not in order_url:
    # 從 form action 抓
    order_url = None
    # 重發請求但只取 response body
    resp3 = opener.open(req)
    body = resp3.read().decode('utf-8', errors='replace')
    m = re.search(r'action="([^"]*order\.aspx[^"]*)"', body)
    if m:
        order_url = m.group(1)
    else:
        print('❌ 無法取得訂單頁')
        sys.exit(1)

if order_url.startswith('./'):
    order_url = 'https://booking.taiwantravelmap.com/user/' + order_url[2:]

print('✅')
print()
print('👉 訂單頁已準備好，開啟瀏覽器...')
print()
print('   在瀏覽器中完成：')
print('   1. 日曆點選入住日期')
print('   2. 確認人數，點下一步')
print('   3. 填姓名、電話、Email')
print('   4. 選擇付款方式送出')
print()
print(f'   {order_url}')
webbrowser.open(order_url)
PYEOF
