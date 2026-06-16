---
name:          "CHANGELOG.md"
description:   "合歡山松雪樓訂房工具 — 版本變更紀錄"
created_date:  "2026/06/15 16:30:00"
modified_date: "2026/06/15 16:55:00"
project_version: "2.0.0"
document_version: "2.0.0"
agent_sign: ['human/name','opencode/big-pickle']
---

# 版本變更紀錄

## v2.0.0 (2026-06-15)

### 🚀 新增 — FastAPI 儀表板
- `dashboard/main.py` — FastAPI 應用，含 SSE 串流、SQLite 持久化、排程端點
- `dashboard/scraper.py` — 非同步爬蟲（httpx + BeautifulSoup），平行請求 + 速率限制
- `dashboard/static/index.html` — 月曆儀表板前端（SSE 即時更新、進度條、快取載入）
- `database.py` — SQLite 持久層（內建模組，零依賴）
- `dashboard/requirements.txt` + `render.yaml` — Render.com 部署設定

### 🚀 新增 — 持久化與排程
- `GET /api/ping` — Keepalive 端點（cron-job.org 每 10 分鐘避免 spin down）
- `GET /api/cron/scan` — 排程掃描 30 天 + 寫入 SQLite DB
- `GET /api/latest` / `GET /api/latest-meta` — 快取讀取端點
- SSE `/api/scan-stream` 每筆結果自動寫入 DB

### 🔧 修正
- 前端 `fmt()` timezone 修復：`toISOString()` → 本地日期格式化
- `showCacheBadge()` 時區解析修復：支援 UTC+00:00 ISO 格式
- 爬蟲速率調整：`MIN_DELAY 2.5→1.5s`，`JITTER 0.8→0.5s`
- 防止爬蟲封鎖：增加 Referer、Accept-Language 等瀏覽器 headers

### 📁 文件
- `README.md` — 完整更新：儀表板功能、快取行為、Render 部署步驟
- `CHANGELOG.md` — 新增 v2.0.0 紀錄
- `SPEC.md` — 新增專案規格書
- `MEMOIR.md` — 新增架構決策紀錄
- `RULES.md` / `PIPELINE.md` / `CONFIRM_FIELDS.md` — 維持 v1.2 內容
- `.gitignore` — 新增 `data/` + `__pycache__/`

---

## v1.2.0 (2026-06-15)

### 🚀 新增
- `scripts/prefill_booking.py` — Playwright 一鍵預填腳本
- `CHANGELOG.md` — 版本紀錄

### 🔧 修正
- 所有 scripts 路徑更新：`/booking.aspx` → `/user/booking.aspx`
- 房型按鈕名稱修正：`btGoRoomCalendar` → `btGoOrderCalendar`
- 空房偵測 pattern 更新
- 移除 bookmarklet 方式（個資安全性考量）

### 📁 文件
- `PIPELINE.md` / `CONFIRM_FIELDS.md` / `README.md` / `.env.example` / `.gitignore`

---

## v1.1.0 (2026-06-15)
- `scripts/auto_order_url.sh` — Step 1→2 自動化（urllib + viewstate）
- `.env` + `.env.example` 設定檔系統
- 路徑修正為 `/user/`，按鈕命名發現

---

## v1.0.0 (2026-06-15)
- `RULES.md` / `PIPELINE.md` / `CONFIRM_FIELDS.md` / `README.md`
- `scripts/check_availability.sh` / `search_booking.sh`
- `scripts/prefill_bookmarklet.js` → 後移除
