import re
import time
import random
import asyncio
import urllib.parse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import httpx

BASE = "https://booking.taiwantravelmap.com"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

# human-like pacing
MIN_DELAY = 1.5    # base seconds between requests
JITTER = 0.5       # ±0.5s random jitter
MAX_CONCURRENT = 1  # sequential like a real user
SESSION_TTL = 240   # refresh session every 4 min


class BookingScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            },
            follow_redirects=True,
            timeout=30.0,
        )
        self._warmed = False
        self._session_at = 0.0
        self._last_req = 0.0
        self._sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def close(self):
        await self.client.aclose()

    async def _pace(self):
        elapsed = time.time() - self._last_req
        delay = MIN_DELAY + random.uniform(-JITTER, JITTER)
        wait = max(0, delay - elapsed)
        if wait > 0:
            await asyncio.sleep(wait)

    async def _request(self, url: str, referer: str = "") -> str:
        await self._pace()
        self._last_req = time.time()
        headers = {}
        if referer:
            headers["Referer"] = referer
        r = await self.client.get(url, headers=headers)
        r.raise_for_status()
        return r.text

    async def _warmup(self):
        now = time.time()
        if self._warmed and (now - self._session_at) < SESSION_TTL:
            return
        await self._request(f"{BASE}/user/booking.aspx?m=1156")
        self._warmed = True
        self._session_at = time.time()

    def _search_url(self, ds: str) -> str:
        d = datetime.strptime(ds, "%Y-%m-%d")
        ci = d.strftime("%Y/%m/%d")
        co = (d + timedelta(days=1)).strftime("%Y/%m/%d")
        return (f"{BASE}/user/searchbooking.aspx?m=1156"
                f"&checkin={ci}&checkout={co}"
                f"&count=1&people=2&unit=room&lg=ch")

    # ── public API ──

    async def scan(self, start: str, end: str) -> list:
        sd = datetime.strptime(start, "%Y-%m-%d")
        ed = datetime.strptime(end, "%Y-%m-%d")
        days = [(sd + timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range((ed - sd).days + 1)]
        await self._warmup()

        async def check_one(ds: str) -> dict:
            async with self._sem:
                try:
                    html = await self._request(
                        self._search_url(ds),
                        referer=f"{BASE}/user/booking.aspx?m=1156",
                    )
                    parsed = self._parse_rooms(html, ds)
                    rooms = parsed.get("rooms", [])
                    parsed["room_count"] = sum(1 for r in rooms if r["available"])
                    return parsed
                except Exception as e:
                    return {"date": ds, "available": False, "room_count": 0, "error": str(e)}

        return await asyncio.gather(*[check_one(d) for d in days])

    async def scan_stream(self, start: str, end: str):
        sd = datetime.strptime(start, "%Y-%m-%d")
        ed = datetime.strptime(end, "%Y-%m-%d")
        days = [(sd + timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range((ed - sd).days + 1)]
        await self._warmup()

        for ds in days:
            async with self._sem:
                try:
                    html = await self._request(
                        self._search_url(ds),
                        referer=f"{BASE}/user/booking.aspx?m=1156",
                    )
                    parsed = self._parse_rooms(html, ds)
                    rooms = parsed.get("rooms", [])
                    parsed["room_count"] = sum(1 for r in rooms if r["available"])
                    yield parsed
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    yield {"date": ds, "available": False, "room_count": 0, "error": str(e)}

    async def rooms(self, ds: str) -> dict:
        await self._warmup()
        html = await self._request(
            self._search_url(ds),
            referer=f"{BASE}/user/booking.aspx?m=1156",
        )
        return self._parse_rooms(html, ds)

    def _parse_rooms(self, html: str, ds: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        title_divs = soup.find_all("div", class_="room_type_title")
        names = []
        for d in title_divs:
            raw = d.get_text("\n", strip=True)
            lines = [l.strip() for l in raw.split("\n") if l.strip()]
            name = lines[0] if lines else raw
            names.append(name)

        buttons = soup.find_all("input", attrs={
            "type": "submit",
            "name": re.compile(r"btGoOrderCalendar"),
        })
        avail = set()
        for b in buttons:
            m = re.search(r"ctl0(\d)", b.get("name", ""))
            if m:
                avail.add(m.group(1))

        rooms = [
            {"name": n, "available": str(i) in avail}
            for i, n in enumerate(names)
        ]
        return {
            "date": ds,
            "available": any(r["available"] for r in rooms),
            "rooms": rooms,
        }

    async def _post(self, url: str, data: dict, referer: str = ""):
        await self._pace()
        self._last_req = time.time()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if referer:
            headers["Referer"] = referer
        r = await self.client.post(url, data=data, headers=headers)
        r.raise_for_status()
        return r

    def _grep_field(self, html: str, name: str) -> str:
        m = re.search(rf'{re.escape(name)}"\s+value="([^"]*)"', html)
        return m.group(1) if m else ""

    NAME_TO_ID = {
        "松雪樓精緻兩人房": 7734,
        "松雪樓景觀兩人房": 7735,
        "松雪樓四人房": 7736,
    }

    async def order_url(self, checkin: str, checkout: str | None = None,
                        room_id: int = 7735) -> str:
        """Step 1→2: search → select room → return final order.aspx URL."""
        await self._warmup()

        dt = datetime.strptime(checkin, "%Y-%m-%d")
        ci = dt.strftime("%Y/%m/%d")
        co = (datetime.strptime(checkout, "%Y-%m-%d") if checkout
              else dt + timedelta(days=1)).strftime("%Y/%m/%d")

        search_url = (f"{BASE}/user/searchbooking.aspx?m=1156"
                      f"&checkin={ci}&checkout={co}"
                      f"&count=1&people=2&unit=room&lg=ch")

        print("Step 1: GET 搜尋頁...", end=" ", flush=True)
        html = await self._request(search_url, referer=f"{BASE}/user/booking.aspx?m=1156")

        # parse room order from page to map room_id → ctl index
        soup = BeautifulSoup(html, "html.parser")
        title_divs = soup.find_all("div", class_="room_type_title")
        room_names = []
        for d in title_divs:
            raw = d.get_text("\n", strip=True)
            lines = [l.strip() for l in raw.split("\n") if l.strip()]
            room_names.append(lines[0] if lines else raw)

        target_idx = None
        for i, name in enumerate(room_names):
            if self.NAME_TO_ID.get(name) == room_id:
                target_idx = i
                break

        if target_idx is None:
            raise RuntimeError(f"找不到房型 ID {room_id}（頁面顯示: {room_names}）")

        btn_name = f"RoomListView$ctl{target_idx:02d}$btGoOrderCalendar"
        if btn_name not in html:
            raise RuntimeError(f"房型 {room_id}（{room_names[target_idx]}）無空房或頁面異常")
        print("✅")

        print("Step 2: POST 選房型...", end=" ", flush=True)
        data = {
            "_TSM_HiddenField_": self._grep_field(html, "_TSM_HiddenField_"),
            "__VIEWSTATE": self._grep_field(html, "__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": self._grep_field(html, "__VIEWSTATEGENERATOR"),
            "__VIEWSTATEENCRYPTED": self._grep_field(html, "__VIEWSTATEENCRYPTED"),
            "__EVENTVALIDATION": self._grep_field(html, "__EVENTVALIDATION"),
            "__EVENTTARGET": "", "__EVENTARGUMENT": "", "__LASTFOCUS": "",
            "PageHeader$SourceURL": "?",
            "PageHeader$hf_lg": "ch",
            "PageHeader$hd_ticket_fixdays": "false",
            "PageHeader$hd_ticket_staydays": "0",
            "PageHeader$EndMessage": "?",
            "PageHeader$OutsideEndMessage": "?",
            "PageHeader$EndNextPage": "?",
            "PageHeader$OutsideEndNextPage": "?",
            btn_name: "一般訂房",
        }
        resp = await self._post(search_url, data, referer=search_url)
        body = resp.text
        order_url = str(resp.url)

        # httpx may not always reflect Server.Transfer redirect →
        # fall back to form action
        if "order.aspx" not in order_url:
            m = re.search(r'action="([^"]*order\.aspx[^"]*)"', body)
            if m:
                order_url = m.group(1)
            else:
                raise RuntimeError("無法取得 order.aspx URL")

        if order_url.startswith("./"):
            order_url = f"{BASE}/user/{order_url[2:]}"
        elif order_url.startswith("/"):
            order_url = f"{BASE}{order_url}"

        print("✅")
        return order_url
