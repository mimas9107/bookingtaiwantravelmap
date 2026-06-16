#!/usr/bin/env python3
"""
一鍵預填 — 合歡山松雪樓訂房（從搜尋到 confirm.aspx 自動填入個資）

Usage:
  ./scripts/prefill_booking.py 2026-06-17               # 景觀兩人房 1晚
  ./scripts/prefill_booking.py 2026-06-17 -r 7734        # 精緻兩人房
  ./scripts/prefill_booking.py 2026-06-17 -r 7736 -n 2   # 四人房 2晚

流程:
  1. 搜尋空房 → 選擇房型 → 到達 order.aspx
  2. 自動確認日期跳至 confirm.aspx（若無則等你手動）
  3. 從 .env 讀取個資填入所有欄位 + 勾選同意條款
  4. 停在付款前，你只需輸入驗證碼 → 送出
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PTimeout
except ImportError:
    print("❌ pip install playwright && playwright install chromium")
    sys.exit(1)

BASE = "https://booking.taiwantravelmap.com"
ROOM_NAMES = {"7734": "精緻兩人房", "7735": "景觀兩人房", "7736": "四人房"}
# searchbooking.aspx 上房型按鈕的 ctl index 與 room_id 未必對應，會 fallback
ROOM_BTN = {"7734": "ctl00", "7735": "ctl01", "7736": "ctl02"}
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def load_env():
    env = {}
    if not os.path.isfile(ENV_PATH):
        print(f"❌ 找不到 {ENV_PATH}\n   請執行: cp .env.example {ENV_PATH} 後編輯填入資料")
        return None
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    missing = [k for k in ["LAST_NAME", "FIRST_NAME", "ID_NUMBER", "EMAIL", "PHONE", "PASSWORD"] if not env.get(k)]
    if missing:
        print(f"❌ .env 缺少必要欄位: {', '.join(missing)}")
        return None
    return env


def try_fill(page, selector, value):
    if not value:
        return
    try:
        el = page.locator(selector)
        if el.count() > 0:
            el.fill(value)
    except Exception:
        pass


def try_select(page, selector, value):
    if not value:
        return
    try:
        el = page.locator(selector)
        if el.count() > 0:
            el.select_option(value)
    except Exception:
        pass


def try_check(page, selector):
    try:
        el = page.locator(selector)
        if el.count() > 0:
            el.check(force=True)
    except Exception:
        pass


def fill_confirm(page, env):
    fields = [
        ("姓名", [
            ("input[name='txt_LastName']", env.get("LAST_NAME")),
            ("input[name='txt_FirstName']", env.get("FIRST_NAME")),
        ]),
        ("性別", [(f"input[name='rb_sex1'][value='{env.get('SEX', '0')}']", None)]),
        ("生日", [
            ("select[name='ddl_year1']", env.get("BIRTH_YEAR")),
            ("select[name='ddl_month1']", env.get("BIRTH_MONTH")),
            ("select[name='ddl_day1']", env.get("BIRTH_DAY")),
        ]),
        ("證件", [
            (f"input[name='rb_14'][value='{env.get('ID_TYPE', '0')}']", None),
            ("input[name='txt_Id']", env.get("ID_NUMBER")),
        ]),
        ("國籍", [("select[name='ddl_Country']", env.get("COUNTRY", "TW"))]),
        ("聯絡", [
            ("input[name='txt_Mail']", env.get("EMAIL")),
            ("input[name='txt_tel_1']", env.get("PHONE")),
            ("input[name='txt_MFC05']", env.get("ADDRESS")),
        ]),
        ("密碼", [
            ("input[name='txt_MF25']", env.get("PASSWORD", "")),
            ("input[name='txt_cpw']", env.get("PASSWORD", "")),
        ]),
        ("備註", [("textarea[name='txt_Note']", env.get("NOTE"))]),
        ("入住時間", [("select[name='ddlCheckInHour']", env.get("CHECKIN_TIME", "15:00"))]),
        ("付款", [(f"input[name='RepeaterPaymentList${'ctl00' if env.get('PAYMENT', '0') == '0' else 'ctl01'}$radioPaymentItem']", None)]),
        ("發票", [
            (f"input[name='rb_Invoice'][value='{env.get('INVOICE', '3')}']", None),
            (f"input[name='rb_exact'][value='{env.get('RECEIPT', '5')}']", None),
        ]),
    ]
    if env.get("NATIONAL_CARD", "").lower() == "true":
        fields.append(("國旅卡", [("input[name='chk_MF39']", None)]))

    for label, items in fields:
        print(f"  ─ {label}...")
        for sel, val in items:
            if val is not None:
                try_fill(page, sel, val)
            else:
                try_check(page, sel)

    # 勾選「我已同意」條款 & 關閉 lightbox
    print("  ─ 同意條款...")
    page.evaluate("""() => {
        var cb = document.getElementById('chk_Order') || document.querySelector('[name="chk_Order"]');
        if (cb) { cb.checked = true; cb.dispatchEvent(new Event('change', {bubbles: true})); }
        document.querySelectorAll('.w3-modal,.modal,.lightbox,.modal-backdrop,div[id^="id0"]')
            .forEach(m => { m.style.display = 'none'; });
        document.body.style.overflow = 'auto';
        document.documentElement.style.overflow = 'auto';
    }""")
    page.wait_for_timeout(300)
    page.evaluate("window.scrollTo(0,0)")

    print("✅ 資料已全部填入")


def main():
    ap = argparse.ArgumentParser(description="合歡山松雪樓 — 一鍵預填訂房")
    ap.add_argument("date", help="入住日期 YYYY-MM-DD")
    ap.add_argument("-r", "--room", default="7735", choices=ROOM_NAMES.keys(),
                    help=f"房型代碼 (預設 7735=景觀兩人房)")
    ap.add_argument("-n", "--nights", type=int, default=1, help="入住晚數 (預設 1)")
    ap.add_argument("--url", help="直接填入指定 confirm.aspx URL (跳過搜尋流程)")
    args = ap.parse_args()

    env = load_env()
    if not env:
        sys.exit(1)

    def close_modals(page):
        page.evaluate("""() => {
            document.querySelectorAll('.w3-modal,.modal,.lightbox,.modal-backdrop,div[id^="id0"]')
                .forEach(m => m.style.display = 'none');
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
        }""")
        page.wait_for_timeout(300)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="zh-TW")
        page = ctx.new_page()

        if args.url:
            page.goto(args.url)
            page.wait_for_load_state("networkidle")
            if "confirm.aspx" in page.url:
                fill_confirm(page, env)
            else:
                print(f"❌ 不是 confirm.aspx: {page.url}")
                browser.close()
                sys.exit(1)
        else:
            d = datetime.strptime(args.date, "%Y-%m-%d")
            checkin_str = d.strftime("%Y/%m/%d")
            checkout_str = (d + timedelta(days=args.nights)).strftime("%Y/%m/%d")
            room_name = ROOM_NAMES[args.room]
            btn_id = ROOM_BTN[args.room]

            # Step 1: 直接從 searchbooking.aspx 搜尋（日期用 URL query，不透過 booking.aspx 表單）
            print(f"🔍 Step 1: 搜尋 {args.date} {room_name} {args.nights}晚 ...")
            search_url = (f"{BASE}/user/searchbooking.aspx?m=1156"
                          f"&checkin={checkin_str}&checkout={checkout_str}"
                          f"&count=1&people=2&unit=room&lg=ch")
            # 先到 booking.aspx 建立 session，再到 searchbooking.aspx
            page.goto(f"{BASE}/user/booking.aspx?m=1156")
            page.wait_for_load_state("networkidle")
            close_modals(page)
            page.goto(search_url)
            page.wait_for_load_state("networkidle")
            close_modals(page)

            # Step 2: 選擇房型
            all_btns = page.locator("input[name*='btGoOrderCalendar']")
            print(f"🏠 Step 2: 選擇 {room_name} ... (可訂 {all_btns.count()} 間)")
            if all_btns.count() == 0:
                print("❌ 沒有可訂房型")
                page.screenshot(path="/tmp/opencode/booking_no_rooms.png")
                browser.close()
                sys.exit(1)
            btn = page.locator(f"input[name='RoomListView${btn_id}$btGoOrderCalendar']")
            if btn.count() == 0:
                print(f"   {room_name} 已滿，改選第一間可訂房型")
                btn = all_btns.first
            btn.wait_for(state="visible", timeout=10000)
            with page.expect_navigation(timeout=15000):
                btn.click(force=True)
            page.wait_for_load_state("networkidle")

            # Step 3: order.aspx 點「確認人數，前往下一步」→ confirm.aspx
            print(f"📅 Step 3: 前往 confirm.aspx ...")
            next_link = page.locator("a:has-text('確認人數')")
            if next_link.count() > 0:
                print("   點擊「確認人數，前往下一步」...")
                with page.expect_navigation(timeout=10000):
                    next_link.click(force=True)
                page.wait_for_load_state("networkidle")

            # 檢查是否已到 confirm.aspx，未到則等使用者手動操作
            if "confirm.aspx" in page.url:
                fill_confirm(page, env)
                print("=" * 50)
                print("✋ 已在 confirm.aspx 填入所有個人資料")
                print("   已幫您勾選「同意條款」")
                print("   只需: 1️⃣ 驗證碼  2️⃣ 送出")
                print("=" * 50)
            else:
                print(f"📍 目前在: {page.url}")
                print("⏳ 請在瀏覽器中選擇入住/退房日期 → 點「確認人數，前往下一步」")
                # 輪詢等待 confirm.aspx，最久 10 分鐘
                for _ in range(600):
                    page.wait_for_timeout(1000)
                    if "confirm.aspx" in page.url:
                        fill_confirm(page, env)
                        print("=" * 50)
                        print("✋ 已在 confirm.aspx 填入所有個人資料")
                        print("   已幫您勾選「同意條款」")
                        print("   只需: 1️⃣ 驗證碼  2️⃣ 送出")
                        print("=" * 50)
                        break
                else:
                    print("\n⚠️ 等待超時（10分鐘）")

        print("=" * 60)
        print("🟢 瀏覽器保持開啟中 — 送出後會跳到金流付款頁")
        print("   完成付款後，回此終端機按 Enter 關閉瀏覽器")
        print("=" * 60)
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
        except Exception:
            pass
        finally:
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
