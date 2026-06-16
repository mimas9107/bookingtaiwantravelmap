---
name:          "PIPELINE.md"
description:   "Complete booking pipeline analysis for 合歡山松雪樓"
created_date:  "2026/06/15 14:01:53"
modified_date: "2026/06/15 16:30:00"
project_version: "1.2.0"
document_version: "1.0.2"
agent_sign: ['human/name','opencode/big-pickle']
---

# 合歡山松雪樓 訂房管線分析

## 完整流程（4 步驟）

```
booking.aspx  ──[ 查詢 ]──→  searchbooking.aspx  ──[ 一般訂房 ]──→  order.aspx
                                                                        │
                                                                  [ 確認人數 ]
                                                                        │
                                                                        ▼
                                                                  confirm.aspx
                                                                        │
                                                                  [ 送出訂單 ]
                                                                        │
                                                                        ▼
                                                             第三方金流付款頁
                                                         (LINE Pay / 信用卡)
```

---

## Step 1：搜尋（/user/booking.aspx）

| 項目 | 說明 |
|------|------|
| **URL** | `/user/booking.aspx?m=1156` |
| **觸發** | 點擊「查詢」按鈕 |
| **提交按鈕** | `SearchView$btn_search` |
| **目標** | `searchbooking.aspx?m=1156&checkin=...&checkout=...&count=1&people=2&unit=room&lg=ch` |
| **搜尋結果（直接 GET）** | `/user/searchbooking.aspx?m=1156&checkin=...&checkout=...&count=1&people=2&unit=room&lg=ch` |
| **查詢按鈕（搜尋頁）** | `PageHeader$btn_search` |
| **相關欄位** | 入住/退房日期、房間數、成人/兒童人數 |

---

## Step 2：選擇房型（/user/searchbooking.aspx → /user/order.aspx）

| 項目 | 說明 |
|------|------|
| **URL** | `/user/searchbooking.aspx?m=1156&checkin=...&checkout=...` |
| **觸發** | 點擊房型的「一般訂房」按鈕 |
| **提交方式** | POST（一般 submit button，非 __doPostBack） |
| **按鈕對照（搜尋結果頁）** | |
| | `RoomListView$ctl00$btGoOrderCalendar` → 松雪樓四⫿房（注意：ctl index 未必對應房型 ID） |
| | `RoomListView$ctl01$btGoOrderCalendar` → 松雪樓景觀兩人房 |
| | `RoomListView$ctl02$btGoOrderCalendar` → 松雪樓四人房 |
| **按鈕對照（主頁 booking.aspx）** | |
| | `RoomList$ctl00$btGoRoomCalendar` → 一般訂房（不同命名！） |
| | `RoomList$ctl01$btGoRoomCalendar` → 一般訂房 |
| | `RoomList$ctl02$btGoRoomCalendar` → 一般訂房 |
| **必要欄位** | 所有 ASP.NET 隱藏欄位（__VIEWSTATE, __EVENTVALIDATION 等）+ 按鈕 name/value |
| **目標 URL** | `/user/order.aspx?m=1156&r={ROOM_ID}&checkin=...&checkout=...&count=1&people=2` |

**房型 ID 對照：**
| r= | 房型 |
|----|------|
| 7734 | 松雪樓精緻兩人房 |
| 7735 | 松雪樓景觀兩人房 |
| 7736 | 松雪樓四人房 |

---

## Step 3：日曆選日期 + 人數（/user/order.aspx）

| 項目 | 說明 |
|------|------|
| **URL** | `/user/order.aspx?m=1156&r={ROOM_ID}&checkin=...&checkout=...` |
| **功能** | 顯示該房型的可訂日曆，選擇入住日與人數 |

**頁面主要欄位：**
| 欄位名稱 | 說明 |
|----------|------|
| `calendar1$ddl_SelectRooms` | 可切換房型（同系列可互換） |
| `calendar1$ddl_count` | 房間數量 |
| `calendar1$txt_In` | 入住日期（唯讀） |
| `calendar1$txt_Out` | 退房日期（唯讀） |
| `calendar1$repeaterPeopleView$ctl00$ddlPeopleViewAdultCount` | 成人人數 |
| `calendar1$repeaterPeopleView$ctl00$ddlPeopleViewChildrenCount` | 兒童人數 |

**日曆日期按鈕：**
| 按鈕類型 | class | 意義 |
|----------|-------|------|
| `Button1` | `check_btn` | 特殊狀態 |
| `Button3` | `check_btn` | 特殊狀態 |
| `Button4` | `check_btn` | 可選擇（有空房） |
| `Button5` | `date_btn` | 特殊狀態 |

**下一步按鈕：**
- `calendar1$btn_PeopleNext` — `__doPostBack('calendar1$btn_PeopleNext','')`
- 顯示文字：「確認人數，前往下一步」
- 目標：`confirm.aspx?m=1156&r=7734&count=1&people=2`

---

## Step 4：填寫資料 + 付款（/user/confirm.aspx）

| 項目 | 說明 |
|------|------|
| **URL** | `/user/confirm.aspx?m=1156&r={ROOM_ID}&count=1&people=2` |
| **提交按鈕** | `SendBooking`（value="送出"） |

### 訂購人資訊

| 欄位名稱 | 說明 |
|----------|------|
| `txt_LastName` | 姓氏 |
| `txt_FirstName` | 名字 |
| `txt_Id` | 身分證字號 |
| `txt_Mail` | 電子信箱 |
| `txt_tel_1` | 聯絡電話 |
| `ddl_Country` | 國家 |
| `txt_Note` | 備註 |
| `rb_sex1` | 性別 |

### 入住時間

| 欄位名稱 | 選項 |
|----------|------|
| `ddlCheckInHour` | 15:00 / 15:30 / 16:00 / 16:30 / 17:00 |

### 付款方式

| 欄位名稱 | 說明 |
|----------|------|
| `RepeaterPaymentList$ctl00$radioPaymentItem` | 線上信用卡 / 國民旅遊卡 |
| `RepeaterPaymentList$ctl01$radioPaymentItem` | LINE Pay |

### 發票選項

| 欄位名稱 | 說明 |
|----------|------|
| `rb_14` | 個人：身分證字號 |
| `rb_exact` | 代收轉付電子收據（預設） |
| `rb_Invoice` | 不開立公司抬頭統編 |

### 其他

| 欄位名稱 | 說明 |
|----------|------|
| `chk_Order` | 同意訂購須知及交易規則（checkbox） |
| `chk_MF39` | 其他勾選項目 |
| `hidNextPage` | 隱藏導航欄位 |

### 送出後

- 表單 submit 到 `confirm.aspx`（自身）
- 成功後導向第三方金流頁面
- 金流選項：LINE Pay / 台新金流 / 藍新金流
- 須在 **10 分鐘內** 完成刷卡

---

## 腳本化可行性分析

| 步驟 | 可腳本化 | 難度 | 說明 |
|------|---------|------|------|
| Step 1 搜尋 | ✅ 簡單 | 低 | 直接 GET，URL 參數即可 |
| Step 2 選房型 | ✅ 可行 | 中 | 需 POST + 完整 viewstate，Cookie 需維持 session |
| Step 3 日曆 + 人數 | ⚠️ 中等 | 高 | 需解析日曆按鈕與日期對應關係，viewstate 重 |
| Step 4 填資料送出 | ⚠️ 可行 | 高 | 欄位多，需處理第三方金流跳轉 |
| 金流付款 | ❌ 不可能 | — | 第三方頁面，需真人操作 |

**結論：** Step 1～3 可以腳本化輔助查詢與自動填入，但 **Step 4 的金流付款** 因涉及第三方支付（LINE Pay / 銀行 3D 驗證），需真人操作。

房型 ID 可透過 `ddl_SelectRooms` 的 `<option value="...">` 解析動態取得，不需寫死。

---

## URL 參數速查

```
/user/booking.aspx        ?m=1156
/user/searchbooking.aspx  ?m=1156&checkin=YYYY/MM/DD&checkout=YYYY/MM/DD&count=N&people=N&unit=room&lg=ch
/user/order.aspx          ?m=1156&r=ROOM_ID&checkin=YYYY/MM/DD&checkout=YYYY/MM/DD&count=N&people=N&unit=room&lg=ch
/user/confirm.aspx        ?m=1156&r=ROOM_ID&count=N&people=N&lg=ch
```
