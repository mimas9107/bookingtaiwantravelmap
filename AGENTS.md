# AI 代理操作守則 (AGENTS.md)

歡迎來到 **合歡山松雪樓空房查詢工具** 專案！為了確保 AI 代理人在開發、維護與擴展本專案時能維持架構一致性、遵守網站禮貌，並確保功能穩定，請嚴格遵守以下特調守則。

---

## 🧭 專案架構概覽

在開始任何修改前，請先理解以下模組的職責分配：

```
.
├── scripts/                   # CLI 腳本與自動化預填
│   ├── check_availability.py  # 批次檢查空房（CLI 入口）
│   ├── search_booking.py      # 單日快速查詢（CLI 入口）
│   ├── auto_order_url.py      # Step 1→2 自動化導航網址產出
│   └── prefill_booking.py     # Playwright 一鍵預填 (依賴 .env)
│
├── dashboard/                 # FastAPI 儀表板與 Web 服務
│   ├── main.py                # 應用主程式（提供 REST API、SSE 串流與排程）
│   ├── scraper.py             # 核心非同步爬蟲（基於 httpx & BeautifulSoup）
│   ├── database.py            # SQLite 持久化層（執行緒安全、WAL 模式）
│   ├── static/                # 前端月曆介面、CSS 與 JS
│   └── bot/                   # Telegram Bot 訊息解析與 Webhook 處理
│
└── agents/
    └── songxuelou-skill/      # 本專案的專屬 Skill，用於對外提供 API 呼叫
```

---

## ⚠️ 核心行為守則 (Critical Rules)

### 1. 防爬蟲政策與禮貌延遲 (Crawling Limits)
* **目標網域**：`booking.taiwantravelmap.com`。
* **延遲限制**：每次請求之間必須引入 **`1.5s ± 0.5s` 的隨機抖動延遲**。
* **併發控制**：必須保持 **單一執行緒 (Concurrency = 1)** 序列化抓取，嚴禁平行發送多個查詢請求。
* **身份偽裝**：必須攜帶完整的瀏覽器 `User-Agent`，以及正確的 `Referer` 與 `Accept-Language: zh-TW`。
* **嚴禁優化**：無論如何都**不得**為了提高效率而將延遲縮短至 1 秒以下，避免導致 IP 被目標伺服器封鎖。

### 2. 非同步與 SQLite 執行緒安全 (Thread Safety)
* **避免阻塞**：FastAPI 為非同步架構，而 Python 內建的 `sqlite3` 是同步模組。
* **執行緒調度**：所有資料庫讀寫操作（如 `Database` 類別內的方法）必須透過 `asyncio.get_event_loop().run_in_executor()` 委託給 Thread Pool 執行，嚴禁阻塞 asyncio 事件循環。
* **檔案置換保護**：在進行資料庫匯出 (`export_backup`) 與線上匯入 (`import_db`) 時，必須使用 `threading.Lock` (`_db_lock`) 保護檔案置換區段，防止 concurrent 請求造成檔案毀損。

### 3. 排程與長時間任務背景化 (Background Tasks)
* **異步處理**：由於反爬蟲禮貌延遲，掃描 30 天空房需要耗時約 60 秒。
* **超時預防**：`/api/cron/scan` 必須使用 FastAPI `BackgroundTasks`。在接收到請求後立即回傳 `200 OK` (或 `202 Accepted`)，並在背景繼續執行掃描。
* **嚴禁同步等待**：不得在主 HTTP 響應中等待 30 天掃描完成，否則會因超過外部 Cron 服務（如 Render/Cron-job.org 的 30 秒限制）而造成連線超時錯誤。

### 4. 時區與前端狀態處理 (Timezone & SSE)
* **時區防偏移**：前端日曆日期必須使用本地時間格式化（例如 `getFullYear()`、`getMonth() + 1`、`getDate()`），**嚴禁**直接呼叫 `toISOString()`（會轉為 UTC 時間，導致台灣時間 UTC+8 的日期在午夜前後發生偏移一天的 Bug）。
* **SSE 串流**：`/api/scan-stream` 採用 Server-Sent Events (SSE) 逐日推送最新掃描進度，讓前端能即時渲染月曆。修改此 API 時須確保 SSE 事件格式 (`event: progress`, `data: ...`) 完整無缺。

### 5. 個資安全與預填防護 (Autofill Security)
* **嚴禁提交憑證**：本機設定檔 `.env` 包含敏感個人資料，已列入 `.gitignore`，開發時**絕對不可**將真實的 `.env` 提交至 Git。
* **書籤安全限制**：前端「自動填入書籤 (Bookmarklet)」產生的 JavaScript 程式碼，必須包含網域驗證 (`location.host === 'booking.taiwantravelmap.com'`) 與路徑驗證 (`location.pathname.includes('confirm.aspx')`)，且必須確認目標 input 欄位存在才可寫入值，防止在錯誤的頁面執行或造成跨網站腳本 (XSS) 風險。

---

## 🔄 文件版本與簽名規範 (Documentation & Versioning)

本專案有一套嚴格的文檔更新與版本同步規範，請務必遵循：

### 1. 文件 Frontmatter 維護
專案中所有的 Markdown 文件（如 `README.md`、`SPEC.md`、`RULES.md`、`MEMOIR.md`、`CHANGELOG.md` 等）皆包含 YAML Frontmatter。當你修改這些文件時，請更新以下欄位：
```yaml
modified_date: "YYYY/MM/DD HH:MM:SS"   # 修改日期（台北時間 UTC+8）
document_version: "X.Y.Z"              # 遞增文件版本
agent_sign: ['gemini cli/current_agent', ...] # 新增你的代理人簽名
```

### 2. 版本一致性同步 (Version Sync)
* 當專案升級、新增重大功能或修復 Bug 時，必須將新版本同步寫入 `CHANGELOG.md`、`SPEC.md`、`MEMOIR.md`、`README.md` 的 `project_version` 標頭以及程式碼中的版本常數。
* **版本遞增原則**：遵循十進位遞增規則，當 `PATCH` 或 `MINOR` 滿 10 時需進位（例如 `v2.2.9` 之後為 `v2.2.10`；若 Minor 滿 10 則進位至 Major）。
* **操作建議**：修改版本時，應優先使用並參考 `version-sync-checker` Skill 以確保無痛同步。

---

## 🛠️ 開發常用命令 (Common Commands)

### 1. 本地開發伺服器
在專案根目錄下啟動 FastAPI 服務：
```bash
# 使用 virtualenv 或系統 python
python3 -m uvicorn dashboard.main:app --reload --port 8000
```
服務啟動後，本地儀表板位於 `http://localhost:8000`。

### 2. 執行單元測試
在進行 Scraping 邏輯、資料庫 Diff 計算修改後，必須執行單元測試以防 Regression：
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

### 3. 一鍵預填自動化測試
若需調試 Playwright 預填邏輯，可先編輯 `.env`，然後執行：
```bash
python3 scripts/prefill_booking.py 2026-07-01
```

---

> [!IMPORTANT]
> **切記**：這是一個極輕量但高穩定性的個人工具。修改程式碼時應維持「零額外第三方依賴」的原則（除非有絕對必要，否則避免引入大型 ORM 或複雜的非同步資料庫套件），讓專案保持精簡、易於維護與快速部署。
