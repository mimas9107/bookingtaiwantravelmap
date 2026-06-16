import os
import asyncio
import httpx
from . import intent, formatter

API_BASE = "https://api.telegram.org/bot{token}"


def _token() -> str | None:
    return os.environ.get("TELEGRAM_TOKEN") or None


async def send_message(chat_id: int, text: str):
    token = _token()
    if not token:
        return
    url = f"{API_BASE.format(token=token)}/sendMessage"
    async with httpx.AsyncClient() as c:
        try:
            await c.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            }, timeout=10.0)
        except Exception:
            pass


async def set_webhook(public_url: str) -> bool:
    token = _token()
    if not token:
        return False
    url = f"{API_BASE.format(token=token)}/setWebhook"
    webhook_url = f"{public_url.rstrip('/')}/bot/telegram"
    async with httpx.AsyncClient() as c:
        try:
            r = await c.post(url, json={"url": webhook_url}, timeout=10.0)
            data = r.json()
            return data.get("ok", False)
        except Exception:
            return False


async def delete_webhook() -> bool:
    token = _token()
    if not token:
        return False
    url = f"{API_BASE.format(token=token)}/deleteWebhook"
    async with httpx.AsyncClient() as c:
        try:
            await c.post(url, timeout=10.0)
            return True
        except Exception:
            return False


async def handle_update(data: dict, scraper, db):
    token = _token()
    if not token:
        return

    msg = data.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text = (msg.get("text") or "").strip()
    if not chat_id or not text:
        return

    parsed = intent.parse(text)
    if not parsed or parsed["action"] == "help":
        await send_message(chat_id, formatter.help_text())
        return

    try:
        if parsed["action"] == "rooms":
            result = await scraper.rooms(parsed["date"])
            data = await db.get_all()
            day = next((r for r in data if r["date"] == result["date"]), None)
            changes = day.get("changes") if day else None
            await send_message(chat_id, formatter.rooms(result, changes))

        elif parsed["action"] == "scan":
            results = await scraper.scan(parsed["start"], parsed["end"])
            for r in results:
                try:
                    await db.save(
                        r["date"], r.get("available", False), r.get("room_count", 0), r.get("rooms")
                    )
                except Exception:
                    pass
            await send_message(chat_id, formatter.scan(results))

        elif parsed["action"] == "latest":
            data = await db.get_all()
            meta = await db.get_meta()
            await send_message(chat_id, formatter.latest(data, meta))

    except Exception as e:
        await send_message(chat_id, formatter.error(str(e)))
