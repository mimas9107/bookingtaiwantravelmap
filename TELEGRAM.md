---
name:          "TELEGRAM.md"
description:   "松雪樓空房查詢 Telegram Bot — 設定與使用說明"
created_date:  "2026/06/16 11:00:00"
modified_date: "2026/06/16 11:00:00"
project_version: "2.1.0"
document_version: "1.0.0"
agent_sign: ['human/name','opencode/big-pickle','opencode/deepseek-v4-flash-free']
---

# 松雪樓 Telegram Bot

整合於 FastAPI 儀表板中的 Telegram Bot，可在對話中直接查詢空房。

## 運作流程

```
使用者 ──傳送訊息──→ Telegram ──webhook POST──→ /bot/telegram
                                                    │
                                          asyncio.create_task()
                                                    │
                                          intent.parse(text)
                                          ┌─────┼─────┐
                                          │     │     │
                                       rooms  scan  latest
                                          │     │     │
                                     scraper  scraper  db
                                          │     │     │
                                     formatter formatter formatter
                                          └─────┼─────┘
                                               │
                                        sendMessage API
                                               │
使用者 ←──收到回覆─── Telegram ←──────────────┘
```

## API Endpoint

### `POST /bot/telegram`

Telegram webhook 接收端點。接收 Telegram Update JSON，立即回傳 `200`，實際處理在背景進行。

- 無需認證（由 Telegram IP 白名單隱含保護）
- 需設定環境變數 `TELEGRAM_TOKEN` 才啟用，否則回傳 `501`
- 回應時間 < 1ms（僅確認收到），長查詢（30 天掃描 ~90s）完成後透過 `sendMessage` 發送回覆

## 環境變數

| 變數 | 必要 | 說明 |
|------|------|------|
| `TELEGRAM_TOKEN` | 是 | 向 [@BotFather](https://t.me/BotFather) 申請的 Bot Token |
| `PUBLIC_URL` | 是 | 部署後的公開網址（如 `https://你的專案.onrender.com`），用於啟動時自動註冊 webhook |

變數設於 Render Dashboard 的 **Environment Variables** 頁面，或 `.env` 檔案（本機開發）。

## 部署流程

### 1. 建立 Bot

1. 在 Telegram 中搜尋 [@BotFather](https://t.me/BotFather)
2. 傳送 `/newbot`，依指示輸入名稱（如 `松雪樓查房`）與 username（如 `songxuelou_bot`）
3. BotFather 回覆中包含 `HTTP API Token`，格式如 `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`
4. 複製此 Token

### 2. 設定環境變數

在 Render Dashboard → Environment Variables 新增：

| Key | Value |
|-----|-------|
| `TELEGRAM_TOKEN` | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `PUBLIC_URL` | `https://songxuelou-dashboard.onrender.com` |

### 3. 重新部署

Render 會自動重啟。啟動日誌應出現：

```
Telegram webhook set: True
```

### 4. 測試

在 Telegram 中向你的 Bot 傳送 `/start`，應收到 help 回覆。

## 支援指令

| 使用者訊息 | 動作 | 範例 |
|-----------|------|------|
| `查 M/D` | 單日房型明細（即時） | `查 7/1` |
| `查 M/D~M/D` | 範圍掃描（即時，自動存 DB） | `查 7/1~7/5` |
| `快取` / `最近` / `現狀` | 讀取 SQLite 快取 | `最近` |
| `help` / `/help` / `/start` | 顯示指令列表 | `/start` |

日期格式支援 `M/D`、`M-D`。年份自動推算。

## 本機開發

使用 ngrok 暴露本機埠供 Telegram webhook 測試：

```bash
# 終端 1：啟動儀表板
cd dashboard
TELEGRAM_TOKEN=xxx PUBLIC_URL=https://xxx.ngrok-free.app uvicorn main:app --reload

# 終端 2：啟動 ngrok
ngrok http 8000
```

啟動後 ngrok 顯示的 `Forwarding` 網址即為 `PUBLIC_URL`。

## 注意事項

1. **掃描時間較長**：30 天掃描需 ~90 秒（受反爬蟲間隔 1.5s/day 限制）。Bot 會先回覆 200，查完後才透過 `sendMessage` 送出結果，對話框不會顯示「打字中」狀態。
2. **無權限控制**：任何知道 Bot username 的人皆可查詢。建議 Bot username 設為非公開名稱。
3. **webhook 生命週期**：應用啟動時自動向 Telegram 註冊 webhook，關閉時自動清除（`deleteWebhook`）。若需手動管理，使用 curl：

   ```bash
   # 設定 webhook
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -d "url=https://你的專案.onrender.com/bot/telegram"

   # 查詢 webhook 狀態
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

   # 刪除 webhook
   curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
   ```

4. **錯誤不回傳 500**：查詢失敗時 Bot 會回覆錯誤訊息，webhook 端點仍回 200，避免 Telegram 重送請求。
5. **範圍掃描結果會寫入 SQLite**：與儀表板共用同一資料庫，儀表板月曆會同步更新。
6. **Telegram 訊息長度限制**：40 天以內的掃描結果皆在 4096 字元限制內。超過時 Bot 會自動截斷 HTML tag 避免格式錯誤。
