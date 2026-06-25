---
name:          "LINEBOT_REV-implement-for-songxuelou-booking.md"
description:   "合歡山松雪樓空房查詢 — LINEBOT_REV 整合開發文件 (AI Tool-use 版本)"
created_date:  "2026/06/16 11:40:00"
modified_date: "2026/06/16 15:45:00"
project_version: "2.3.3"
document_version: "2.0.0"
agent_sign: ['opencode/deepseek-v4-flash-free', 'gemini cli/current_agent']
---

# LINEBOT_REV × 松雪樓空房查詢 整合開發文件 (AI Tool-use 版)

## 1. 概述

本方案捨棄傳統的「關鍵字攔截」寫法，改用 **Gemini SDK 的 Automatic Function Calling (AFC)** 技術。
將松雪樓查詢功能封裝為 AI 的一個「工具技能 (Tool)」，讓 AI 能根據對話情境、自然語言（如：下週三、這個週末）主動判定是否呼叫 API。

**使用者體驗優點**：
- **無需精確關鍵字**：使用者問「幫我看看最近松雪樓有沒有房」也能觸發。
- **日期智能解析**：AI 會自動將「下週五」轉換為正確的 `YYYY-MM-DD` 格式。
- **架構極簡**：`line_handler.py` 無需新增任何 `if/else` 邏輯。

## 2. 前提條件

### 2.1 服務端（松雪樓儀表板）
- 已部署至 Render，獲得 `SONGXUELOU_URL`。
- `/api/query` 端點運作正常（支援 `date` 與 `rooms` 參數）。

### 2.2 LINEBOT_REV 端
- 使用 `google-genai` SDK (rev3.1 已導入)。
- 需新增環境變數 `SONGXUELOU_URL`。

## 3. 實作步驟

### 3.1 建立技能函式 (New File)
在 `LINEBOT_REV` 專案中建立 `services/tools/songxuelou.py`：

```python
import requests
import os

def query_songxuelou_availability(date: str) -> str:
    """
    查詢合歡山松雪樓在特定日期的空房剩餘狀況。
    
    Args:
        date: 要查詢的日期，格式必須為 'YYYY-MM-DD' (例如 '2026-06-20')。
              請根據使用者提到的時間點推算正確日期。
    """
    api_url = os.environ.get("SONGXUELOU_URL", "").rstrip("/")
    if not api_url:
        return "錯誤：尚未設定 SONGXUELOU_URL 環境變數。"

    try:
        # 呼叫爬蟲 API
        resp = requests.get(
            f"{api_url}/api/query", 
            params={"date": date, "rooms": 1}, 
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("in_cache"):
            return f"抱歉，系統目前沒有 {date} 的預約資料，可能日期太遠或尚未自動掃描。"
        
        # 回傳結構化資料，AI 會自行閱讀並轉化為自然語言回覆使用者
        return str(data)
    except Exception as e:
        return f"呼叫查詢服務時發生錯誤：{str(e)}"
```

### 3.2 注入技能至 AI Service
修改 `LINEBOT_REV/services/ai_text.py` 中的 `_chat_with_history` 方法：

```python
from google.genai import types
from services.tools.songxuelou import query_songxuelou_availability # 1. 引入技能

# ... 在 AITextService 類別中 ...

    def _chat_with_history(self, client: genai.Client, prompt: str, history: list[dict]) -> str:
        chat_history = self._convert_history_to_contents(history)
        
        # 2. 建立包含工具的 Config
        config_obj = types.GenerateContentConfig(
            tools=[query_songxuelou_availability], # 注入工具
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=False # 啟用自動函式呼叫
            ),
            temperature=0.7,
            system_instruction=(
                "你是一個親切的合歡山旅遊助手。當使用者詢問松雪樓房況時，請調用工具查詢。\n"
                "特別注意：若查詢結果包含 'changes' 資訊，代表房位有最新變動（如釋出或被訂走），"
                "請在回覆中主動提醒使用者這些變化。回覆時請使用繁體中文，並將房間資訊整理成易讀的列表。"
            )
        )
        
        # 3. 建立對話 Session
        chat = client.chats.create(
            model=config.GEMINI_MODEL,
            history=chat_history,
            config=config_obj
        )
        
        # 4. 發送訊息（SDK 會自動處理 Tool Call 循環）
        response = chat.send_message(prompt)
        return response.text
```

### 3.3 保持 `LineHandler` 的簡潔
確保 `handlers/line_handler.py` 的 `_handle_text_message` 不再需要手動攔截關鍵字：

```python
    def _handle_text_message(self, event: MessageEvent, user_id: str) -> str:
        text = event.message.text
        
        # AI 對話模式：現在 AI 具備「主動查房」的技能
        if text.lower().startswith("ai:"):
            prompt = text[3:].strip()
            save_user_message(user_id, prompt, 'text')
            
            # 取得歷史紀錄並呼叫 AI
            history = get_chat_history(user_id)
            result = chat_with_ai(prompt, history)
            
            save_model_response(user_id, result, 'text')
            return result
```

## 4. 環境變數設定

在 Render 平台上為 `LINEBOT_REV` 服務新增：

| 變數名稱 | 值 | 說明 |
|---------|-----|------|
| `SONGXUELOU_URL` | `https://your-dashboard.onrender.com` | 松雪樓儀表板網址 |

## 5. 測試案例 (驗證 AI 智能)

| 使用者輸入 | AI 預期行為 |
|-----------|------------|
| `ai: 幫我看看下週六松雪樓有房嗎？` | AI 算出日期 -> 呼叫工具 -> 回傳房況摘要 |
| `ai: 那 6/20 呢？` | AI 根據上下文呼叫工具查詢 2026-06-20 |
| `ai: 查詢 6/20 房況並告訴我那天的天氣` | AI 呼叫房況工具（若有天氣工具則併呼叫），最後綜合回覆 |

## 6. 優點與後續擴展

1. **無痛擴展**：未來新增「天氣」、「路況」查詢，只需寫好 Python Function 並加入 `tools` 清單。
2. **參數容錯**：AI 會處理「6月20日」、「6/20」、「下週三」等各種日期表達方式。
3. **對話感強**：AI 會根據查詢結果給予人性化的建議（例如：剩最後兩間喔，要趕快訂！）。

---
文件結束
�感強**：AI 會根據查詢結果給予人性化的建議（例如：剩最後兩間喔，要趕快訂！）。

---
文件結束
