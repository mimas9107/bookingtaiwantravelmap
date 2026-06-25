---
name:          "CHANGELOG.md"
description:   "合歡山松雪樓空房查詢工具 — 版本變更紀錄"
created_date:  "2026/06/15 16:30:00"
modified_date: "2026/06/25 18:00:00"
project_version: "2.3.3"
document_version: "2.2.3"
agent_sign: ['human/name','opencode/big-pickle','opencode/deepseek-v4-flash-free','gemini cli/current_agent','opencode/minimax-m2.5','opencode/deepseek-v4-flash-free']
---

# 版本變更紀錄

## v2.3.2 (2026-06-25)

### 🐛 修復 — 查詢起始日期行為

- `app.js`: 修正 `loadCache()` 不再覆蓋日期輸入框為快取日期，改為固定帶入明天起算、退房 +7 天；月曆仍顯示快取資料

## v2.3.1 (2026-06-25)

### ✨ 新增 — 前端 Footer 顯示 Git Commit

- `main.py`: 新增 `/api/version` 端點，啟動時取得 git commit 前 8 碼
- `index.html`: 新增 `<footer>` 元素，顯示 commit hash
- `app.js`: 頁面載入時 fetch `/api/version` 顯示於 footer
- `style.css`: 新增 `footer` 樣式（灰色小字、居中、分隔線）

## v2.3.0 (2026-06-22)

### ✨ 新增 — 瀏覽器書籤自動填入訂房表單

- `index.html` / `style.css` / `app.js`: 新增「設定訂房資料」面板，使用者在 dashboard 填寫一次個資後自動存入 `localStorage`
- 產出 `javascript:` 書籤 （bookmarklet），在 `confirm.aspx` 點一下即可填入所有欄位
- 三層安全檢查：網域 + 路徑 + 表單元素存在才執行填入
- 停在驗證碼欄位，由使用者手動輸入 + 點擊送出（不下 Auto Submit）
- 自動勾選「我已同意訂購須知」checkbox（位於 lightbox 內）

### ⚡ 優化 — 掃描時預先抓取訂房網址（實驗 C）

- `scraper.py`: 萃取 `_complete_order_url()` 從 `order_url()` 分離 POST 邏輯，新增 `_enrich_rooms_with_urls()` 在掃描中為可訂房型補上 `url` 欄位
- `scan()` / `scan_stream()` / `rooms()` 三個入口皆會自動帶入訂房網址
- `app.js`: 前端直接使用房間資料的 `r.url`，不再額外呼叫 `/api/booking-url`

## v2.2.4 (2026-06-22)

### ✨ 新增 — 可訂房型一鍵連結至訂房頁
- `scraper.py`: `order_url()` 新增 `verbose` 參數，支援無聲 API 呼叫
- `main.py`: 新增 `GET /api/booking-url?date=...&room_name=...`，複用既有 `order_url()` 邏輯
- `app.js`: 點擊有空的日期後，自動為每間可訂房型抓取訂房網址，房名改為 `<a>` 可點連結
- `style.css`: 新增 `.rname-link`（藍色底線）樣式
- 點擊房名在新分頁開啟 `confirm.aspx`，直接進入該房型訂單填寫頁

## v2.2.3 (2026-06-16)

### 🐛 修復 — /api/cron/scan 422 錯誤
- 修正 `dashboard/main.py` 缺少 `BackgroundTasks` 匯入導致的參數驗證失敗

## v2.2.2 (2026-06-16)

### 🚀 優化 — /api/cron/scan 非同步化
- 修正外部 Cron-job 呼叫超時問題（Render/Cron-job.org 30s 限制）
- 引入 FastAPI `BackgroundTasks`：接收請求後立即回傳 `200 Accepted`，並於背景執行 30 天完整掃描
- 維護爬蟲禮貌延遲（1.5s/day）的同時，確保排程任務不因等待而失敗

## v2.2.1 (2026-06-16)

### 🛠 工具 — db_tool.py 新增 csv 子命令
- `csv` 子命令：呼叫 `/api/latest`，輸出 CSV 至 stdout 或 `-o FILE`
- 欄位：`date`, `available`, `room_count`, `rooms`(JSON), `changes`(JSON), `scanned_at`
- `rooms` 與 `changes` 以 JSON 字串嵌入 CSV，保留完整結構資訊

---

## v2.2.0 (2026-06-16)

### ✨ 新增 — 房況變動偵測（diff）
- 每次掃描時自動比對前次資料，標記有變動的房型（釋出 / 被訂走）
- DB schema 新增 `rooms_json` + `changes_json` 欄位
- `scraper.scan()` / `scan_stream()` 改用 `_parse_rooms()` 回傳各房型明細
- `_save()` 自動計算 diff：讀取前次 rooms → 比對 → 寫入 changes
- `Database._get_all()` 自動解析 JSON 欄位，前端可直接取用
- `tests/test_diff.py` — `compute_room_changes()` 8 項單元測試

### 🎨 前端 — 變動視覺化
- 日曆格子：有變動的日期右上角顯示紫色圓點（CSS `::after`）
- 房型詳情 panel：變動房型顯示「⬇ 釋出」「⬆ 被訂走」標籤

### 🤖 Bot — 變動提示
- Telegram 查詢結果中，有變動的日期後方顯示 `🔄`
- 單日房型詳情顯示「⬇釋出／⬆被訂」註記

---

## v2.1.4 (2026-06-16)

### ✨ 新增 — `/api/query` 單日空房查詢端點
- `GET /api/query?date=2026-06-20`：從快取回傳單日空房摘要（`available`, `room_count`, `scanned_at`）
- `GET /api/query?date=2026-06-20&rooms=1`：若該日有空房，額外回傳各房型明細
- 專為 bot / AI agent 設計的輕量端點，避免解析整份快取列表

---

## v2.1.3 (2026-06-16)

### 📦 維護 — 將 songxuelou-skill 遷入專案
- skill 從 `~/.agents/skills/songxuelou-skill/` 遷入 `agents/songxuelou-skill/`，納入版控
- `~/.agents/skills/` 以 symlink 指向專案內路徑

---

## v2.1.2 (2026-06-16)

### 🔧 強化 — 心跳改為外部路由 + 退避機制
- 心跳改由 `HEARTBEAT_URL` 環境變數指定服務公開網址，經外部路由繞回戳 `/api/ping`（避免 localhost 繞過 Render 閒置偵測）
- 失敗時指數退避：30s → 60s → 120s → 300s 上限，連續 3 次失敗發 warning 日誌
- 未設定 `HEARTBEAT_URL` 時心跳停用（不影響舊有行為）

---

## v2.1.1 (2026-06-16)

### 🔧 強化 — ping 端點與自動心跳
- `/api/ping` 回傳擴充：`timestamp`（UTC ISO8601）+ `client_ip`（支援 `X-Forwarded-For` proxy 環境）
- 新增背景心跳任務：透過 `HEARTBEAT_URL` 環境變數指定服務公開網址，每 120 秒向外敲 `/api/ping`
- 心跳失敗時指數退避（30s → 60s → 120s → 300s 上限），連續 3 次失敗發 warning 日誌，不影響主程序
- 心跳任務在 lifespan shutdown 時正確取消

---

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
