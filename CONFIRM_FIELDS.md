---
name:          "CONFIRM_FIELDS.md"
description:   "confirm.aspx page field reference for fast booking"
created_date:  "2026/06/15 14:01:53"
modified_date: "2026/06/15 16:30:00"
project_version: "1.2.0"
document_version: "1.0.2"
agent_sign: ['human/name','opencode/big-pickle']
---

# 合歡山松雪樓 - confirm.aspx 預填欄位一覽

> 填入順序建議從上到下，一氣呵成。

---

## 1️⃣ 入住時間（可略過，預設 15:00）

| 欄位 | name | 選項 |
|------|------|------|
| 入住時間 | `ddlCheckInHour` | 15:00 / 15:30 / 16:00 / 16:30 / 17:00 |

---

## 2️⃣ 付款方式

| 選項 | name | 預設 |
|------|------|------|
| 線上信用卡 | `RepeaterPaymentList$ctl00$radioPaymentItem` | ✅ |
| LINE Pay | `RepeaterPaymentList$ctl01$radioPaymentItem` | |

---

## 3️⃣ 發票（可略過，預設不用改）

| 欄位 | type | value | 說明 |
|------|------|-------|------|
| 代收轉付電子收據 | radio | `rb_exact` → value=`5` | ✅ 預設 |
| 不開立公司抬頭統編 | radio | `rb_Invoice` → value=`3` | ✅ 預設 |
| 要開立公司抬頭統編 | radio | `rb_Invoice` → value=`2` | 選此會 postback 載入統編欄位 |

---

## 4️⃣ 訂購人資料 ⭐（最重要，先填這裡）

| 順序 | 欄位 | name/id | type | 必填 |
|------|------|---------|------|------|
| ① | **姓** | `txt_LastName` | text | ✅ |
| ② | **名** | `txt_FirstName` | text | ✅ |
| ③ | 性別 | `rb_sex1` | radio `0`=男 `1`=女 | |
| ④ | 生日年 | `ddl_year1` | select 西元 | |
| ⑤ | 生日月 | `ddl_month1` | select 01~12 | |
| ⑥ | 生日日 | `ddl_day1` | select 01~31 | |
| ⑦ | 證件類別 | `rb_14` | radio `0`=身分證 `1`=護照 | |
| ⑧ | **身分證字號/護照號碼** | `txt_Id` | text | ✅ |
| ⑨ | 國籍 | `ddl_Country` | select `TW`=台灣 | |
| ⑩ | **Email** | `txt_Mail` | text | ✅ |
| ⑪ | **手機** | `txt_tel_1` | text | ✅ |
| ⑫ | 地址 | `txt_MFC05` | text | |
| ⑬ | **查詢密碼** | `txt_MF25` | password | ✅ |
| ⑭ | **密碼確認** | `txt_cpw` | password | ✅ |
| ⑮ | 備註 | `txt_Note` | textarea | |
| ⑯ | 國民旅遊卡 | `chk_MF39` | checkbox | |

---

## 5️⃣ 驗證碼（需手動）

| 欄位 | name | 說明 |
|------|------|------|
| 驗證碼 | `txt_check` | 手動辨識圖片中的文字 |

---

## 6️⃣ 送出

| 按鈕 | name | 說明 |
|------|------|------|
| 我已同意 | `chk_Order` | checkbox（在彈窗中） |
| 送出 | `SendBooking` | 提交訂單 |

---

## 🚀 一鍵預填（Playwright 自動化腳本）

使用 `scripts/prefill_booking.py`：

```bash
cp .env.example .env
vim .env
./scripts/prefill_booking.py 2026-07-01
```

腳本會自動操作瀏覽器完成 Step 1～Step 4 的填入，停在驗證碼前。

> ⚠️ 不再使用 bookmarklet 方式（需將個資嵌入書籤 URL 不安全）
>
> **自動處理**：腳本會幫你勾選同意條款（`chk_Order`）、關閉所有 lightbox、恢復頁面滾動。
> 你只需要：輸入驗證碼 → 送出。
