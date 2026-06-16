---
name:          "SPEC.md"
description:   "合歡山松雪樓空房查詢工具 — 專案規格書"
created_date:  "2026/06/15 16:55:00"
modified_date: "2026/06/16 10:00:00"
project_version: "2.1.4"
document_version: "1.1.0"
agent_sign: ['human/name','opencode/big-pickle','opencode/deepseek-v4-flash-free']
---

# 專案規格書

## 1. 專案概述

合歡山松雪樓空房查詢工具 — 自動化查詢並視覺化松雪樓（booking.taiwantravelmap.com）空房狀況，免去手動逐一檢查。

## 2. 目標使用者

- 需要頻繁查詢松雪樓空房的人
- 需要視覺化瀏覽一段日期範圍內空房狀況的人

## 3. 功能需求

### 3.1 空房查詢（CLI）

| 功能 | 腳本 | 說明 |
|------|------|------|
| 批次範圍檢查 | `check_availability.sh` | 掃描起訖日期之間的所有入住日，輸出是否有空房 |
| 單日快速查詢 | `search_booking.sh` | 查詢特定入住日空房 + 列出房型 |
| Step 1→2 導引 | `auto_order_url.sh` | 自動帶入搜尋條件 → 選擇房型 → 開啟 order.aspx |

### 3.2 一鍵預填（Playwright 自動化）

`prefill_booking.py` — 從 `.env` 讀取個資，使用 Playwright 控制瀏覽器：

1. 搜尋空房（指定日期、人數）
2. 選擇房型
3. 確認入住日期
4. 填寫 confirm.aspx 所有欄位（姓名、身分證、Email、電話…）
5. 自動勾選同意條款
6. 停在驗證碼前，由使用者手動輸入驗證碼並完成付款

### 3.3 儀表板（FastAPI + 前端）

| 功能 | 說明 |
|------|------|
| 月曆顯示 | 以月曆格狀呈現 30 天可訂範圍，顏色標示空房狀態 |
| 即時串流 | SSE 逐日傳送掃描結果，月曆即時更新 + 進度條 |
| 房型明細 | 點選日期查看該日各房型可訂狀態 |
| 快取載入 | 頁面初次載入時自動讀取 SQLite 快取資料 |
| 排程更新 | 外部 cron-job.org 觸發 `/api/cron/scan` 背景更新快取 |

## 4. 非功能需求

### 4.1 反爬蟲策略

| 項目 | 設定 |
|------|------|
| 請求間隔 | 1.5s ± 0.5s 隨機抖動 |
| 併發數 | 1（完全序列化） |
| User-Agent | Chrome 125 完整字串 |
| Accept-Language | zh-TW 優先 |
| Referer | 模擬真實瀏覽流程 |
| Session TTL | 每 4 分鐘重新暖機 |

### 4.2 資料持久化

| 項目 | 說明 |
|------|------|
| 資料庫 | SQLite（內建模組，零第三方依賴） |
| 儲存位置 | `dashboard/data/scans.db` |
| 表格 | `scans`（date, available, room_count, scanned_at） |
| 更新策略 | 即時查詢或排程查詢時 INSERT OR REPLACE |
| 生命週期 | Render 實例存活期間持久；重啟後可能清空；支援下載備份與上傳還原 |

### 4.3 前端狀態覆蓋

| 狀態 | 處理 |
|------|------|
| Loading | 進度條 + 按鈕 disabled |
| Empty | 「尚未查詢」提示（無快取時） |
| Error | 連線中斷提示 |
| Partial | 部分完成提示（error 事件但已有部分資料） |
| Success | 摘要 + 月曆完整顯示 |

## 5. API 規格

### `GET /`
回傳 index.html 儀表板。

### `GET /api/ping`
Keepalive。回傳 `{"status": "ok"}`。

### `GET /api/scan-stream?start=YYYY-MM-DD&end=YYYY-MM-DD`
SSE 串流。事件：
- `meta` — `{"total": N}`
- `progress` — `{"scanned": N, "total": N, "date": "...", "available": bool, "room_count": N}`
- `done` — `{"total": N, "scanned": N, "elapsed": float}`

### `GET /api/cron/scan`
掃描明天起 30 天，寫入 SQLite。回傳 `{"status": "ok", "scanned": 30, "available_days": N}`。

### `GET /api/latest`
回傳 `{"data": [{"date": "...", "available": bool, "room_count": N, "scanned_at": "..."}]}`。

### `GET /api/latest-meta`
回傳 `{"meta": {"scanned_at": "...", "total_days": N, "available_days": N}}`。

### `GET /api/rooms?date=YYYY-MM-DD`
即時查詢特定日期的房型明細。不回存快取。

### `GET /api/scan?start=...&end=...`
（相容）同 scan-stream 但回傳完整 JSON array。

### `GET /api/db/export`
下載 SQLite 資料庫。回傳 `application/octet-stream`，檔名 `songxuelou_scans_YYYYMMDD.db`。

### `POST /bot/telegram`
Telegram Bot webhook（需設定 `TELEGRAM_TOKEN` + `PUBLIC_URL`）。接收 Telegram Update JSON，背景執行查詢並發送回覆。支援指令：

| 指令 | 動作 | 範例 |
|------|------|------|
| `查 <M/D>` | 單日房型明細 | `查 7/1` |
| `查 <M/D>~<M/D>` | 範圍掃描 + 存 DB | `查 7/1~7/5` |
| `快取` / `最近` | 讀取 SQLite 快取 | `最近` |
| `help` / `說明` | 顯示指令列表 | `/help` |

### `POST /api/db/import`
上傳 `.db` 檔案取代目前資料庫。需滿足：
- 有效的 SQLite 格式（magic header 驗證）
- 包含 `scans` 資料表

成功時回傳 `{"status": "ok", "rows": N, "message": "..."}`。
格式錯誤或缺少資料表時回傳 `400`。

## 6. 部署架構

```
cron-job.org                    Browser
  ├─ /api/ping (每 10分)          │
  ├─ /api/cron/scan (08,20)      ├─ /
  │                               ├─ /api/latest-meta
  │                               ├─ /api/latest
  │                               ├─ /api/scan-stream?start=..&end=..
  ▼                               └─ /api/rooms?date=..
────────────────────────────────────────────
            Render.com (Free Tier)
            uvicorn → FastAPI
              ├─ BookingScraper (httpx → booking.taiwantravelmap.com)
              └─ Database (sqlite3 → data/scans.db)
```

## 7. 房型對照

| r= | 房型 | 床型 | 原價 | 特價起 |
|----|------|------|------|--------|
| 7734 | 松雪樓精緻兩人房 | 一大床 | NT$3,800 | NT$2,900 |
| 7735 | 松雪樓景觀兩人房 | 一大床 | NT$4,100 | NT$3,200 |
| 7736 | 松雪樓四人房 | 兩大床 | NT$6,800 | NT$5,400 |

## 8. 入住規則摘要

- 可訂範圍：第 2 天～第 30 天（今日起算）
- 線上可操作時間：08:00～23:00
- Check-in：15:00～17:00
- 付款時限：10 分鐘內完成
- 滑雪山莊（背包床位）：整修中暫不開放
