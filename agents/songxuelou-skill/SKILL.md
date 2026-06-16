---
name: songxuelou-skill
version: 1.1.0
description: 查詢松雪樓空房資訊 — 讀取快取、單日查詢、健康檢查。
tools:
  - name: songxuelou_query
    description: 對松雪樓空房查詢儀表板 API 執行 ping、讀取快取、或單日查詢。
---

# 松雪樓空房查詢 Skill

對已部署的 FastAPI 儀表板發起查詢。支援三種操作：

- **ping**：健康檢查，確認服務在線
- **cache**：讀取最近一次掃描的快取空房資料
- **query**：查詢特定日期的空房狀況

## 📖 使用指南

### 行為規範

1. **優先讀快取**：先問 cache，確認資料新鮮度後再決定是否要即時掃描。
2. **環境變數**：`SONGXUELOU_URL` 為必要欄位，指向儀表板根網址（不含尾部斜線）。
3. **路徑動態偵測**：嚴禁憑記憶編造路徑，必須執行以下步驟。

### 步驟 0：偵測 Skill 實際位置

```bash
find -L ~ -maxdepth 4 -name "songxuelou-skill" -type d 2>/dev/null | head -n 1
```

記結果為 `[SKILL_ROOT]`。

### 步驟 1：確認服務 URL

確認 `SONGXUELOU_URL` 已設定，例如：

```bash
echo "SONGXUELOU_URL=${SONGXUELOU_URL}"
```

若未設定則提示使用者提供，或從部署記錄查詢。

### 步驟 2：執行查詢

```bash
# 健康檢查
python3 [SKILL_ROOT]/scripts/query.py ping

# 讀取完整快取
python3 [SKILL_ROOT]/scripts/query.py cache

# 僅讀取快取中繼資料（掃描時間、空房天數等）
python3 [SKILL_ROOT]/scripts/query.py cache --meta

# 查詢特定日期（例如 2026-06-20）
python3 [SKILL_ROOT]/scripts/query.py query 2026-06-20

# 查詢並包含房型明細
python3 [SKILL_ROOT]/scripts/query.py query 2026-06-20 --rooms
```

## 🛠 參數說明

| 子命令 | 參數 | 說明 |
|--------|------|------|
| `ping` | — | `GET /api/ping`，回傳 `status`, `timestamp`, `client_ip` |
| `cache` | — | `GET /api/latest`，完整掃描資料 |
| `cache` | `--meta` | `GET /api/latest-meta`，僅回傳中繼資料 |
| `query` | `<DATE>` | `GET /api/query?date=YYYY-MM-DD`，單日空房查詢 |
| `query` | `<DATE> --rooms` | 加上 `&rooms=1` 取得房型明細 |

## 環境變數

- `SONGXUELOU_URL`：**必要**，服務根網址，例如 `https://songxuelou.onrender.com`

## 快速範例

```bash
export SONGXUELOU_URL="https://songxuelou.onrender.com"
SKILL_ROOT=~/.agents/skills/songxuelou-skill

python3 "$SKILL_ROOT/scripts/query.py" ping
python3 "$SKILL_ROOT/scripts/query.py" cache --meta
python3 "$SKILL_ROOT/scripts/query.py" cache
python3 "$SKILL_ROOT/scripts/query.py" query 2026-06-20
python3 "$SKILL_ROOT/scripts/query.py" query 2026-06-20 --rooms
```
