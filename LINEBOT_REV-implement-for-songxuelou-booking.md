---
name:          "LINEBOT_REV-implement-for-songxuelou-booking.md"
description:   "合歡山松雪樓空房查詢 — LINEBOT_REV 整合開發文件"
created_date:  "2026/06/16 11:40:00"
modified_date: "2026/06/16 11:40:00"
project_version: "2.1.4"
document_version: "1.0.0"
agent_sign: ['opencode/deepseek-v4-flash-free']
---

# LINEBOT_REV × 松雪樓空房查詢 整合開發文件

## 1. 概述

讓 LINEBOT_REV 的使用者可在 LINE 對話中直接查詢松雪樓空房狀況。

**使用者體驗**：
```
使用者: 松雪樓 6/20
LINE bot: 📅 2026-06-20 ✅ 有空房（可訂 2 間）
          ✅ 松雪樓景觀兩人房
          ✅ 松雪樓四人房
          ❌ 松雪樓精緻兩人房
          （資料時間: 2026-06-16 08:00:00+00:00）
```

## 2. 前提條件

### 2.1 服務端（松雪樓儀表板）

- 已部署至 Render，獲得公開網址（以下稱 `SONGXUELOU_URL`）
- `/api/query` 端點正常運作
- 每日定時掃描（08:00、20:00）確保快取新鮮

### 2.2 LINEBOT_REV 端

- `requests` 套件已存在（`requirements.txt` 已有，用於 `bookmark.py`、`keepalive.py`）
- 無需新增任何 Python 依賴
- 需新增環境變數 `SONGXUELOU_URL`

## 3. API 規格 — `/api/query`

### 請求

```http
GET {SONGXUELOU_URL}/api/query?date=2026-06-20
GET {SONGXUELOU_URL}/api/query?date=2026-06-20&rooms=1
```

| 參數 | 型態 | 必要 | 說明 |
|------|------|------|------|
| `date` | string | 是 | 日期，格式 `YYYY-MM-DD` |
| `rooms` | int | 否 | `1` 時回傳各房型明細 |

### 回應（`rooms=0`）

```json
{
  "date": "2026-06-20",
  "in_cache": true,
  "available": true,
  "room_count": 2,
  "scanned_at": "2026-06-16T08:00:00+00:00"
}
```

### 回應（`rooms=1`）

```json
{
  "date": "2026-06-20",
  "in_cache": true,
  "available": true,
  "room_count": 2,
  "scanned_at": "2026-06-16T08:00:00+00:00",
  "rooms": [
    {"name": "松雪樓精緻兩人房", "available": false},
    {"name": "松雪樓景觀兩人房", "available": true},
    {"name": "松雪樓四人房", "available": true}
  ]
}
```

### edge cases

| 情境 | `in_cache` | 說明 |
|------|-----------|------|
| 該日不在快取中 | `false` | 快取過期或尚未掃描，建議引導使用者稍後再查或主動觸發掃描 |
| 該日無空房 | `true`, `available: false` | 所有房型均已售罄 |

### 錯誤處理

| HTTP 狀態 | 情境 |
|-----------|------|
| `422` | `date` 參數缺失或格式錯誤 |
| `200` + `in_cache: false` | 該日未掃描（非錯誤，正常回應） |

## 4. LINEBOT_REV 實作指引

### 4.1 修改檔案

**唯一需要修改的檔案**：`handlers/line_handler.py`

在 `_handle_text_message` 方法中，於 `ai:` 判斷**之前**插入松雪樓查詢區塊。

### 4.2 建議程式碼

```python
# ── 松雪樓空房查詢（在 ai: 判斷之前插入） ──
SONGXUELOU_URL = os.environ.get("SONGXUELOU_URL", "").rstrip("/")

# 鬆散比對：包含「松雪樓」「合歡山」「空房」任一關鍵字即觸發
keywords = ["松雪樓", "合歡山", "空房", "songxuelou"]
if any(kw in text for kw in keywords):
    # 從訊息中嘗試提取日期
    date_match = re.search(r"(\d{1,2})/(\d{1,2})", text)
    if not date_match:
        return "請提供日期，例如：松雪樓 6/20"

    month, day = date_match.groups()
    this_year = datetime.now().year
    date_str = f"{this_year}-{int(month):02d}-{int(day):02d}"

    if not SONGXUELOU_URL:
        return "松雪樓查詢服務未設定（SONGXUELOU_URL）"

    try:
        resp = requests.get(
            f"{SONGXUELOU_URL}/api/query",
            params={"date": date_str, "rooms": 1},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"查詢失敗: {e}"

    if not data.get("in_cache"):
        return f"⚠️ {month}/{day} 的資料尚未掃描，請稍後再查。"

    lines = [f"📅 {month}/{day}"]
    if data["available"]:
        lines.append(f"✅ 有空房（可訂 {data['room_count']} 間）")
        for r in data.get("rooms", []):
            icon = "✅" if r["available"] else "❌"
            lines.append(f"{icon} {r['name']}")
    else:
        lines.append("❌ 無空房")

    scanned = data.get("scanned_at", "")
    if scanned:
        lines.append(f"（資料時間: {scanned}）")

    return "\n".join(lines)
```

### 4.3 完整的 `_handle_text_message` 方法結構（變更示意）

```python
def _handle_text_message(self, event, user_id):
    text = event.message.text

    # [新增] 松雪樓空房查詢
    if any(kw in text for kw in ["松雪樓", "合歡山", "空房", "songxuelou"]):
        ...  # 上述程式碼
        return result

    # 原有 AI 對話
    if text.lower().startswith("ai:"):
        ...

    # 原有複製模式
    elif text.lower().startswith("c:"):
        ...

    return ""
```

## 5. 環境變數

在 Render dashboard 的 LINEBOT_REV 服務中新增：

| 變數名稱 | 值 | 說明 |
|---------|-----|------|
| `SONGXUELOU_URL` | `https://你的松雪樓儀表板.onrender.com` | 不加尾部斜線 |

## 6. 測試

### 6.1 手動測試（curl）

部署完成後，透過 LINE 傳以下訊息驗證：

| 輸入 | 預期行為 |
|------|---------|
| `松雪樓 6/20` | 回傳該日空房摘要 |
| `合歡山 7/1` | 同上（關鍵字觸發） |
| `6/20 松雪樓有空房嗎` | 應被觸發（關鍵字鬆散比對） |
| `松雪樓` | 提示「請提供日期」 |
| `ai: 你好` | 不應觸發，正常走 Gemini AI |

### 6.2 邊界情境

- **日期格式容錯**：`6/20`、`06/20`、`6/5` 皆應正常解析
- **跨年處理**：年底時（如 `12/30`）需注意年份邏輯 — 若月份小於當前月份 + 一個閾值，可能需跳至明年（目前固定用今年，使用者在年底前使用無問題）

## 7. LINE 訊息格式限制

- LINE 訊息單則最多 5000 字元（本功能遠低於此限制）
- 支援純文字，使用一般文字 + 換行即可
- 若需跳脫「松雪樓」觸發，用戶可前綴 `c:`（`c: 松雪樓`）觸發 echo 繞過

## 8. 整合後架構

```
使用者 ──LINE──→ LINE Platform ──webhook──→ LINEBOT_REV (/callback)
                                                   │
                                          ┌────────┴────────┐
                                          │ line_handler.py  │
                                          │  松雪樓關鍵字攔截   │
                                          └────────┬────────┘
                                                   │ GET /api/query
                                                   ▼
                                          ┌─────────────────┐
                                          │ 松雪樓儀表板      │
                                          │ (FastAPI / Render)│
                                          │ 快取 / 即時掃描   │
                                          └─────────────────┘
```

## 9. 往後優化方向（非必要）

| 項目 | 說明 |
|------|------|
| 日期範圍查詢 | 一次問「松雪樓 6/20~6/25」列出多日 |
| 排序顯示 | 僅顯示有空房日期，狀態一目瞭然 |
| 房型價格 | 若官網有價格資料可一併呈現 |
| 預約連結 | 回傳 `order_url` 產生的預約捷徑 |
