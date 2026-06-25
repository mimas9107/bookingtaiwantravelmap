---
name:          "README.md"
description:   "合歡山松雪樓空房查詢工具 — 使用說明"
created_date:  "2026/06/15 14:01:53"
modified_date: "2026/06/25 18:00:00"
project_version: "2.3.1"
document_version: "2.0.7"
agent_sign: ['human/name','opencode/big-pickle','opencode/deepseek-v4-flash-free','gemini cli/current_agent','opencode/minimax-m2.5']
---

# 合歡山松雪樓 空房查詢工具

自動化查詢合歡山松雪樓（booking.taiwantravelmap.com）的空房狀況。

## 檔案結構

```
.
├── README.md                  # 本文件
├── CHANGELOG.md               # 版本變更紀錄
├── SPEC.md                    # 專案規格書
├── MEMOIR.md                  # 架構決策紀錄
├── RULES.md                   # 入住日期規則摘要
├── CONFIRM_FIELDS.md          # confirm.aspx 欄位參考
├── PIPELINE.md                # 官網操作流程分析
├── .env                       # 個人資料設定檔（需自行建立）
├── .env.example               # 設定檔範本
├── .gitignore                 # 避免 .env + data/ 被提交
│
│ ├── scripts/                   # 查詢與預填腳本
│   ├── check_availability.py  # 批次檢查日期範圍空房（主要）
│   ├── search_booking.py      # 快速查詢特定入住日（主要）
│   ├── auto_order_url.py      # Step 1→2 自動化（主要）
│   ├── prefill_booking.py     # 🚀 一鍵預填（Playwright）
│   ├── check_availability.sh  # （參考）舊版 shell 實作
│   ├── search_booking.sh      # （參考）舊版 shell 實作
│   └── auto_order_url.sh      # （參考）舊版 shell 實作
│
└── dashboard/                 # FastAPI 儀表板（可部署至 Render）
    ├── main.py                # FastAPI 應用（SSE + 排程 + 持久化端點）
    ├── scraper.py             # 非同步爬蟲（httpx + BeautifulSoup）
    ├── database.py            # SQLite 持久層（內建模組，零依賴）
    ├── static/index.html      # 前端月曆儀表板
    ├── requirements.txt       # Python 依賴
    ├── render.yaml            # Render.com 部署設定
    └── data/                  # SQLite DB 目錄（自動建立，已 gitignore）
```

## 使用方式

### CLI 腳本

```bash
# 批次檢查空房（預設：今天 ~ 30 天後）
./scripts/check_availability.sh

# 指定起訖日期
./scripts/check_availability.sh 2026-07-01 2026-07-15

# 快速查詢特定入住日
./scripts/search_booking.sh 2026-07-01
./scripts/search_booking.sh 2026-07-01 2026-07-03

# Step 1→2 自動導向（開啟瀏覽器到 order.aspx）
./scripts/auto_order_url.sh 2026-07-01 7735

# 🚀 一鍵預填：搜尋→選房→填入個資（Playwright，停在驗證碼前）
cp .env.example .env    # 先編輯 .env 填入真實資料
./scripts/prefill_booking.py 2026-07-01             # 景觀兩人房 1晚
./scripts/prefill_booking.py 2026-07-01 -r 7734      # 精緻兩人房
./scripts/prefill_booking.py 2026-07-01 -r 7736 -n 2 # 四人房 2晚
```

### FastAPI 儀表板（本機開發）

```bash
cd dashboard
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

開啟瀏覽器 `http://localhost:8000` 即可使用月曆查詢介面。

## 儀表板功能

| 功能 | 說明 |
|------|------|
| **月曆顯示** | 以月曆格狀呈現可訂日期（🟢 有空房 / 🔴 已售完 / ◌ 未查詢） |
| **即時串流查詢** | 點「🔍 查詢」後 SSE 逐日傳送結果，月曆即時更新 + 進度條 |
| **快取載入** | 頁面載入時自動讀取 SQLite 快取，顯示「上次查詢: xxx」 |
| **房型明細** | 點日期查看該日各房型可訂狀態，房名為可點連結直接開啟訂房頁 |
| **自動填入書籤** | 在「設定訂房資料」面板填寫個資後產生 `javascript:` 書籤，於 `confirm.aspx` 點一下自動填入全部欄位，停在驗證碼 |
| **排程更新** | `/api/cron/scan` 可供 cron-job.org 定時觸發，自動掃描 30 天 |
| **Telegram Bot** | webhook 整合，支援 `查 7/1`、`查 7/1~7/5`、`最近狀況` 等自然語言指令 |
| **Keepalive** | `/api/ping` 回傳 timestamp + client IP；設定 `HEARTBEAT_URL` 後背景 120 秒向外敲 API 防 spin down |

### 快取行為

| 情境 | 行為 |
|------|------|
| 首次載入（無快取） | 月曆隱藏，顯示空狀態 |
| 有快取資料 | 月曆直接顯示快取結果 + 上次查詢時間 |
| 點「🔍 查詢」 | 即時掃描網站 → 逐日更新月曆 → 寫入 SQLite DB |
| `/api/cron/scan` 觸發 | 背景掃描 30 天 → 存入 DB，不影響使用中頁面 |

## 部署至 Render.com

```bash
# 1. 將 dashboard/ 推至 GitHub 獨立 repo（或子目錄）
# 2. Render.com → New Web Service → 選擇 repo
# 3. Runtime: Python
# 4. Build Command: pip install -r requirements.txt
# 5. Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

部署後建議在 cron-job.org 建立以下排程：

| 排程 | URL | 用途 |
|------|-----|------|
| 每日 08:00 | `https://你的專案.onrender.com/api/cron/scan` | 早上更新快取 |
| 每日 20:00 | `https://你的專案.onrender.com/api/cron/scan` | 晚上更新快取 |

若已設定 `HEARTBEAT_URL` 環境變數，服務會自行每 120 秒向外敲 API，可省略 cron-job.org 的 keepalive 排程。心跳失敗時自動降低頻率（最長 300 秒間隔）並記錄 warning。

## 注意事項

- 結果僅供參考，實際空房以官網為準
- 爬蟲間隔 1.5s ± 0.5s（模擬真人瀏覽），避免被封鎖
- 僅查詢一般房型（1 間房、2 位成人），背包床位因滑雪山莊整修中暫不提供
- 可訂日期範圍為第 2 天～第 30 天（今日起算）
- SQLite DB 存放於 `dashboard/data/`，Render 重啟後可能清空（ephemeral 碟）
