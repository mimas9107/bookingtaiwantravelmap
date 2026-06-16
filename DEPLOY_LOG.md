---
name:          "DEPLOY_LOG.md"
description:   "合歡山松雪樓空房查詢工具 — 佈署問題紀錄"
created_date:  "2026/06/16 12:45:00"
modified_date: "2026/06/16 12:45:00"
project_version: "2.2.1"
document_version: "1.0.0"
agent_sign: ['opencode/deepseek-v4-flash-free']
---

# 佈署問題紀錄

## 問題 1：`ModuleNotFoundError: No module named 'scraper'`

### 發生時間
2026-06-16 佈署時，commit `3a0fb01` 前。

### 錯誤訊息
```
File "/opt/render/project/src/dashboard/main.py", line 12, in <module>
    from scraper import BookingScraper
ModuleNotFoundError: No module named 'scraper'
```

### 根因
`dashboard/main.py` 使用相對裸 import `from scraper import BookingScraper`。Render 以 `uvicorn dashboard.main:app` 啟動時，CWD 是專案根目錄，Python 只在頂層搜尋 `scraper` 模組，但 `scraper.py` 位於 `dashboard/` 套件內。

### 解決方式
1. 建立 `dashboard/__init__.py`，使 `dashboard` 成為正式 Python package
2. 將 `main.py` 的 import 改為絕對路徑：
   - `from scraper import BookingScraper` → `from dashboard.scraper import BookingScraper`
   - `from database import Database, DB_PATH` → `from dashboard.database import Database, DB_PATH`
   - `from bot import telegram as bot` → `from dashboard.bot import telegram as bot`
3. 同步更新 `dashboard/render.yaml` 的 start command 為 `uvicorn dashboard.main:app --host 0.0.0.0 --port $PORT`

### 本地開發
修改後本地開發需從專案根目錄啟動：
```bash
uvicorn dashboard.main:app --reload
```

---

## 問題 2：`RuntimeError: Form data requires "python-multipart"`

### 發生時間
2026-06-16 佈署時，commit `ffdd5de` 前。

### 錯誤訊息
```
RuntimeError: Form data requires "python-multipart" to be installed.
```

### 根因
`/api/db/import` 使用 FastAPI 的 `UploadFile`，底層依賴 `python-multipart` 解析 multipart/form-data。`requirements.txt` 未包含此套件。

### 解決方式
在 `dashboard/requirements.txt` 新增：
```
python-multipart>=0.0.20
```

---

## Render 佈署重點

### 啟動命令
`uvicorn dashboard.main:app --host 0.0.0.0 --port $PORT`

Render 會自動設定 `$PORT` 環境變數（預設 10000）。

### 環境變數（需在 Render Dashboard 設定）
| 變數 | 必要 | 說明 |
|------|------|------|
| `HEARTBEAT_URL` | 建議 | 服務公開網址根路徑，例如 `https://songxuelou.onrender.com`，每 120 秒向外 ping `/api/ping` 防止 spin down |
| `PUBLIC_URL` | 選擇 | Telegram webhook 用，與 `HEARTBEAT_URL` 通常相同 |
| `TELEGRAM_TOKEN` | 選擇 | Telegram Bot token，設定後啟動 webhook |

### 注意事項
- Render free tier 檔案系統非持久，SQLite 資料 (`data/scans.db`) 在重啟後消失。建議定期使用 `scripts/db_tool.py download` 備份
- 排程掃描可搭配 cron-job.org 定時呼叫 `/api/cron/scan`（建議 08:00、20:00 各一次）
- 若 `HEARTBEAT_URL` 未設定，心跳任務會直接返回，不影響主程序
