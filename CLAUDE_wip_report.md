# CLAUDE WIP Report — 施工藍圖 (Skill)

> 這份文件是 Claude 在這個專案中的「施工藍圖」。它描述要做什麼、用哪份資料、
> 以及每個分析任務的**標準答案**,讓任何人(或自動化測試)都能驗證結果是否正確。

## 1. 專案目標 (Goal)

針對 `fixtures/crm_sample.csv` 這份 CRM 假資料,建立一套可重複執行的分析流程,
並用本文件記錄的標準答案來驗證輸出是否正確。這是一個資料分析的練習腳手架
(data analytics practice scaffold)。

## 2. 資料來源 (Data Source)

- 路徑:`fixtures/crm_sample.csv`
- 筆數:15 位客戶 (`C001`–`C015`)
- 欄位:

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| `customer_id` | string | 客戶唯一編號 |
| `name` | string | 客戶姓名(假資料) |
| `region` | enum | `North` / `South` / `East` / `West` |
| `signup_date` | date (YYYY-MM-DD) | 註冊日期 |
| `plan` | enum | `Basic` (50) / `Pro` (200) / `Enterprise` (500) |
| `monthly_revenue` | int | 每月經常性收入 (USD),與 `plan` 對應 |
| `status` | enum | `active` / `churned` |
| `last_active_date` | date (YYYY-MM-DD) | 最後活躍日期 |

## 3. 施工步驟 (Work Plan)

1. 載入 `fixtures/crm_sample.csv`。
2. 計算第 4 節列出的各項指標。
3. 將計算結果對照第 4 節的**標準答案**,全部相符才算通過。

## 4. 標準答案 (Ground Truth)

> 以下數字由 `fixtures/crm_sample.csv` 直接計算而得,作為驗收基準。

### 4.1 客戶總覽
- 客戶總數:**15**
- 活躍 (active):**12**
- 流失 (churned):**3**
- 流失率 (churn rate):**20.0%**

### 4.2 收入指標
- 全部客戶 MRR 總和:**3000**
- 活躍客戶 MRR 總和:**2700**
- 活躍客戶 ARPU(平均每用戶收入):**225.0**

### 4.3 區域分布(客戶數)
| Region | Customers |
| --- | --- |
| North | 5 |
| South | 4 |
| East | 3 |
| West | 3 |

### 4.4 各區域活躍 MRR
| Region | Active MRR |
| --- | --- |
| East | 1000 |
| North | 900 |
| West | 450 |
| South | 350 |

- 活躍 MRR 最高的區域:**East (1000)**

### 4.5 方案分布(客戶數)
| Plan | Customers |
| --- | --- |
| Basic | 6 |
| Pro | 6 |
| Enterprise | 3 |

## 5. 驗證方式 (How to Verify)

任何分析腳本只要讀入同一份 CSV,計算結果應與第 4 節完全一致。範例(Python):

```python
import csv
from collections import defaultdict

rows = list(csv.DictReader(open("fixtures/crm_sample.csv")))
active = [r for r in rows if r["status"] == "active"]

assert len(rows) == 15
assert len(active) == 12
assert sum(int(r["monthly_revenue"]) for r in active) == 2700  # active MRR
assert round(len([r for r in rows if r["status"] == "churned"]) / len(rows) * 100, 1) == 20.0
print("OK — all ground-truth checks passed")
```

## 6. 狀態 (Status)

- [x] 建立 `fixtures/crm_sample.csv` 假資料
- [x] 記錄標準答案 (ground truth)
- [ ] 實作分析腳本(後續工作)
