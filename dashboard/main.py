import os
import json
import time
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, Request, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from httpx import AsyncClient
from dashboard.scraper import BookingScraper
from dashboard.database import Database, DB_PATH
from dashboard.bot import telegram as bot

logger = logging.getLogger("uvicorn")

scraper: BookingScraper | None = None
db: Database | None = None
BOT_ENABLED = bool(os.environ.get("TELEGRAM_TOKEN"))
_heartbeat_task: asyncio.Task | None = None

HB_BASE = (os.environ.get("HEARTBEAT_URL") or "").rstrip("/")
HB_OK_INTERVAL = 120
HB_MIN_INTERVAL = 30
HB_MAX_INTERVAL = 300
HB_CONSECUTIVE_WARN = 3


async def _heartbeat_loop():
    if not HB_BASE:
        logger.info("heartbeat disabled (no HEARTBEAT_URL)")
        return
    url = f"{HB_BASE}/api/ping"
    interval = HB_OK_INTERVAL
    failures = 0
    async with AsyncClient() as c:
        while True:
            await asyncio.sleep(interval)
            try:
                r = await c.get(url, timeout=10.0)
                r.raise_for_status()
                if failures > 0:
                    logger.info(f"heartbeat recovered after {failures} failures")
                failures = 0
                interval = HB_OK_INTERVAL
            except Exception as exc:
                failures += 1
                interval = min(HB_MAX_INTERVAL, interval * 2)
                interval = max(interval, HB_MIN_INTERVAL)
                if failures == 1 or failures % HB_CONSECUTIVE_WARN == 0:
                    logger.warning(
                        f"heartbeat failed ({failures}x): {exc.__class__.__name__}; "
                        f"next in {interval}s"
                    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scraper, db, _heartbeat_task
    scraper = BookingScraper()
    db = Database()
    await db.init()
    _heartbeat_task = asyncio.create_task(_heartbeat_loop())
    if BOT_ENABLED:
        public_url = os.environ.get("PUBLIC_URL", "")
        if public_url:
            ok = await bot.set_webhook(public_url)
            logger.info(f"Telegram webhook set: {ok}")
    yield
    if _heartbeat_task:
        _heartbeat_task.cancel()
    if BOT_ENABLED:
        await bot.delete_webhook()
    await scraper.close()


app = FastAPI(title="松雪樓空房查詢", lifespan=lifespan)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open(os.path.join(STATIC_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()


# ── keepalive （避免 Render free tier spin down） ──

@app.get("/api/ping")
async def api_ping(request: Request):
    forwarded = request.headers.get("X-Forwarded-For", "")
    client_ip = forwarded.split(",")[0].strip() if forwarded else request.client.host
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "client_ip": client_ip,
    }


# ── 快取讀取 ──

@app.get("/api/latest")
async def api_latest():
    data = await db.get_all()
    return {"data": data}


@app.get("/api/latest-meta")
async def api_latest_meta():
    meta = await db.get_meta()
    if meta is None:
        return {"meta": None}
    return {"meta": {
        "scanned_at": meta["scanned_at"],
        "total_days": meta["total"],
        "available_days": meta["avail_count"],
    }}


# ── 單日空房查詢（供 bot / agent 使用） ──

@app.get("/api/query")
async def api_query(date: str = Query(...), rooms: int = Query(0)):
    data = await db.get_all()
    day = next((r for r in data if r["date"] == date), None)
    result = {
        "date": date,
        "in_cache": day is not None,
    }
    if day:
        result["available"] = day["available"]
        result["room_count"] = day["room_count"]
        result["scanned_at"] = day["scanned_at"]
        if "changes" in day and day["changes"]:
            result["changes"] = day["changes"]
    if rooms:
        if day and day.get("rooms"):
            result["rooms"] = day["rooms"]
        elif day and day["available"]:
            try:
                detail = await scraper.rooms(date)
                result["rooms"] = detail.get("rooms", [])
            except Exception:
                pass
    return result


# ── 即時查詢（SSE 串流 + 自動存 DB） ──

@app.get("/api/scan-stream")
async def api_scan_stream(request: Request, start: str = Query(...), end: str = Query(...)):
    if start > end:
        raise HTTPException(400, "start 不能晚於 end")

    async def event_stream():
        sd = datetime.strptime(start, "%Y-%m-%d")
        ed = datetime.strptime(end, "%Y-%m-%d")
        total = (ed - sd).days + 1

        yield f"event: meta\ndata: {json.dumps({'total': total})}\n\n"

        t0 = time.time()
        scanned = 0
        async for result in scraper.scan_stream(start, end):
            if await request.is_disconnected():
                break
            scanned += 1
            # persist each result
            try:
                await db.save(result["date"], result.get("available", False), result.get("room_count", 0), result.get("rooms"))
            except Exception:
                pass  # non-critical
            payload = {"scanned": scanned, "total": total, **result}
            yield f"event: progress\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        elapsed = round(time.time() - t0, 1)
        yield f"event: done\ndata: {json.dumps({'total': total, 'scanned': scanned, 'elapsed': elapsed})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── 排程掃描（給外部 cron-job.org 調用） ──

async def run_full_scan():
    """背景執行完整掃描並儲存至 DB"""
    today = datetime.now()
    # 掃描明天起算 30 天
    start = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    end = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    logger.info(f"[Cron] Starting background scan from {start} to {end}")
    try:
        results = await scraper.scan(start, end)
        for r in results:
            await db.save(
                r["date"], 
                r.get("available", False), 
                r.get("room_count", 0), 
                r.get("rooms")
            )
        logger.info(f"[Cron] Background scan completed: {len(results)} days processed")
    except Exception as e:
        logger.error(f"[Cron] Background scan failed: {e}")


@app.get("/api/cron/scan")
async def api_cron_scan(background_tasks: BackgroundTasks):
    # 立即觸發背景任務
    background_tasks.add_task(run_full_scan)
    return {
        "status": "accepted",
        "message": "Scan task started in background",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ── 單日房型（即時查詢，不存 DB） ──

@app.get("/api/rooms")
async def api_rooms(date: str = Query(...)):
    try:
        data = await scraper.rooms(date)
        return {"data": data}
    except Exception as e:
        raise HTTPException(503, f"查詢失敗: {e}")


# ── 保留舊的 scan endpoint（相容） ──

@app.get("/api/scan")
async def api_scan(start: str = Query(...), end: str = Query(...)):
    if start > end:
        raise HTTPException(400, "start 不能晚於 end")
    try:
        data = await scraper.scan(start, end)
        return {"data": data}
    except Exception as e:
        raise HTTPException(503, f"查詢失敗: {e}")


# ── 資料庫匯出/匯入（online 抽換） ──

@app.get("/api/db/export")
async def api_db_export():
    backup_path = await db.export_backup()
    if backup_path is None:
        raise HTTPException(404, "資料庫不存在")
    today = datetime.now().strftime("%Y%m%d")
    filename = f"songxuelou_scans_{today}.db"
    try:
        with open(backup_path, "rb") as f:
            content = f.read()
    finally:
        if os.path.exists(backup_path):
            os.unlink(backup_path)
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/db/import")
async def api_db_import(file: UploadFile = File(...)):
    data = await file.read()
    try:
        count = await db.import_db(data)
        return {"status": "ok", "rows": count, "message": f"已匯入 {count} 筆資料"}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Telegram Bot Webhook ──

@app.post("/bot/telegram")
async def bot_webhook(request: Request):
    if not BOT_ENABLED:
        raise HTTPException(501, "Telegram bot 未啟用 (需設定 TELEGRAM_TOKEN)")
    body = await request.json()
    asyncio.create_task(bot.handle_update(body, scraper, db))
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
