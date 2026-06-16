---
name:          "CHANGELOG.md"
description:   "合歡山松雪樓訂房工具 — 版本變更紀錄"
created_date:  "2026/06/15 16:30:00"
modified_date: "2026/06/16 10:00:00"
project_version: "2.1.0"
document_version: "2.0.2"
agent_sign: ['human/name','opencode/big-pickle','opencode/deepseek-v4-flash-free']
---

# 版本變更紀錄

## v2.1.0 (2026-06-16)

### 🚀 新增 — Telegram Bot 整合
- `dashboard/bot/` 模組：intent 解析 / formatter 排版 / telegram API 封裝
- `POST /bot/telegram` — Telegram webhook 端點（背景處理，即時回應）
- intent 支援：單日查詢 `查 7/1`、範圍掃描 `查 7/1~7/5`、快取讀取、help
- 啟動時自動向 Telegram 註冊 webhook（需設定 `TELEGRAM_TOKEN` + `PUBLIC_URL`）
- `.env.example` 新增 Telegram Bot 設定區段

---

## v2.0.2 (2026-06-16)

### 🔧 修正 — 資料庫 concurrent 安全與 CLI 工具
- `database.py`: 新增 `threading.Lock` 保護匯入時檔案置換區段，防止與 `_save()` 競搶
- `database.py`: 匯出改為 `src.backup(dst)` API，確保 WAL 資料一併寫入快照
- `main.py`: 匯出端點讀取 temp backup → 記憶體 → 清除，無殘留
- `scripts/db_tool.py` 新增：純 `urllib` 零依賴，支援 `download`/`upload`/`info` 子命令

---

## v2.0.1 (2026-06-16)

### 🚀 新增 — 資料庫線上抽換
- `GET /api/db/export` — 下載 SQLite 資料庫檔案
- `POST /api/db/import` — 上傳 `.db` 檔案取代目前資料庫（含格式驗證）
- 前端底部「資料庫」工具列：下載 / 上傳按鈕 + 狀態提示
- `database.py` 新增 `export_path()` / `import_db()` 方法（synchronous 執行緒安全）

### 🔧 修正
- Render 重啟後資料遺失問題緩解：使用者可手動下載備份 DB

---

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
