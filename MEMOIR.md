---
name:          "MEMOIR.md"
description:   "架構決策紀錄與經驗教訓"
created_date:  "2026/06/15 16:55:00"
modified_date: "2026/06/16 10:00:00"
project_version: "2.2.1"
document_version: "1.1.0"
agent_sign: ['human/name','opencode/big-pickle','opencode/deepseek-v4-flash-free']
---

# 架構決策紀錄 (MEMOIR)

## 技術選擇

### Python 爬蟲 vs Shell 腳本

**問題：** 查空房需要解析 HTML，shell script 力有未逮。

**決策：** 混合使用。
- 簡單 GET + grep：Shell（`check_availability.sh`, `search_booking.sh`）
- 需 viewstate POST 處理：Python urllib（`auto_order_url.sh`）
- 瀏覽器自動化：Python Playwright（`prefill_booking.py`）
- 非同步爬蟲 + 解析：Python httpx + BeautifulSoup（`dashboard/scraper.py`）

**教訓：** 工具選擇應依任務需求，而非統一使用單一語言。

### SQLite 內建模組 vs SQLAlchemy

**問題：** FastAPI 非同步架構下需要資料庫存取，但不想增加依賴複雜度。

**決策：** `sqlite3` 內建模組 + `asyncio.get_event_loop().run_in_executor()`。
- 零額外依賴
- 不需 asyncpg/aiosqlite 等第三方套件
- 適合低流量個人工具
- 缺點：thread pool executor 有微量 overhead，但對本專案可忽略

**教訓：** 對於非高併發場景，內建模組 + executor 比大型 ORM 更輕量。

### SSE 串流 vs 傳統 REST

**問題：** 掃描 30 天約需 60 秒，使用者不應等待完整結果才能看到月曆。

**決策：** SSE (Server-Sent Events)。
- `/api/scan-stream` 逐日推送結果
- 前端 `EventSource` 監聽 `progress` 事件，即時更新個別日期格
- 進度條同步更新
- 自動斷線重連（瀏覽器原生支援）

**教訓：** SSE 比 WebSocket 更適合單向資料串流，且不需額外程式庫。

## 過程教訓

### 1. 網站路徑發現
首次實作假設路徑為 `/booking.aspx`，但實際為 `/user/booking.aspx`。直接觀察瀏覽器 network tab 才發現正確路徑。**應在開發初期先手動探索一次目標網站結構。**

### 2. ASP.NET WebForms viewstate
Step 2（選房型）是 POST 請求，需攜帶 `__VIEWSTATE`、`__EVENTVALIDATION` 等隱藏欄位。單純 GET 無法觸發。使用 `urllib` + `BeautifulSoup` 解析 form 欄位再 POST 解決。

### 3. 按鈕命名不一致
`booking.aspx` 的按鈕為 `RoomList$ctlXX$btGoRoomCalendar`，但 `searchbooking.aspx` 為 `RoomListView$ctlXX$btGoOrderCalendar`。**每個頁面的控制項命名不同，不能混用。**

### 4. timezone 陷阱
前端 `toISOString()` 會轉 UTC，在 UTC+8 環境會導致日期偏移一天。使用 `getFullYear()/getMonth()/getDate()` 本地格式化解決。

### 5. 反爬蟲調校
初始 `MIN_DELAY=0.3`（300ms）太激進。調為 `1.5s ± 0.5s` + 完整瀏覽器 headers 後正常。**目標是「像真人」，不是「越快越好」。**

### 6. Shell 背景程序存活
在 CLI tool 中啟動背景 server 很容易被 shell session 結束信號殺死。解法：用 `subprocess.Popen(start_new_session=True)` 完整脫離 session。

### 7. Render free tier spin down
15 分鐘無流量就停機，冷啟動需 30-60 秒。使用 cron-job.org 每 10 分鐘打 `/api/ping` 保持活躍。SQLite 在 spin down 期間資料會保留（同 container 暫存碟）。

## 已知限制

- SQLite 非網絡資料庫，不支援多實例（Render 免費方案僅單實例，無影響）
- Render 重啟或搬遷時 SQLite 資料清空（ephemeral filesystem）；解決方式：透過 `/api/db/export` 下載備份，重啟後再 `/api/db/import` 還原
- 掃描 30 天約需 60 秒（受限於反爬蟲間隔），無法加速
- 金流付款需真人操作（第三方頁面 3D 驗證）
