# Implementation Notes — Mini-Foundry (Session 1: schema + simulator + pytest)

## 本次範圍
只完成 `CLAUDE_mini_foundry.md` 中的資料模型（schema）、simulator（v1 批次模式）、
以及驗收標準中的 pytest。**不含** FastAPI、Streamlit、docker-compose。

## 目錄結構
```
mini_foundry/
  schema/schema.sql          -- 三表 DDL（lots / route_steps / events）
  simulator/
    routes.py                -- 固定 demo route 樣板（product PA / PB）
    core.py                  -- 純函式：seed 決定性模擬，不依賴 DB / 系統時間
    db.py                    -- 讀環境變數建立連線、套用 schema、批次寫入
    run.py                   -- CLI 入口：python -m simulator.run --seed 42
  tests/
    conftest.py              -- session-scoped fixtures：模擬資料 + DB 載入
    helpers.py                -- 測試專用「當前狀態推導」輔助函式
    test_data_integrity.py   -- 驗收標準：4 條資料完整性規則 + DB constraint 驗證
    test_seed_assertions.py  -- 驗收標準：seed=42 決定性 + 固定 lot 位置斷言
  requirements.txt
  pyproject.toml             -- pytest pythonpath 設定
  .env.example
```

## 環境變數
DB 連線資訊一律由環境變數提供，禁止 hardcode：
- 優先讀取 `DATABASE_URL`
- 否則由 `PGHOST` / `PGPORT` / `PGUSER` / `PGPASSWORD` / `PGDATABASE` 組成

執行測試前需先 `export` 或提供 `.env.test`（已加入 `.gitignore`，不會被提交）。
本機驗證使用的是直接安裝的 PostgreSQL 16（非 docker-compose，見下方 Deviations）。

## Deviations（偏離規格之處，均採保守方案）

1. **`lots.product_id` 未設實體外鍵約束**
   `route_steps` 的主鍵是複合鍵 `(product_id, seq)`，`product_id` 單獨並非唯一鍵，
   PostgreSQL 無法直接對非唯一欄位建立 FK。規格明確要求「三表正規化」（不新增第 4
   張 products 表），因此保留邏輯對應關係，改由 simulator 產生資料時保證一致、並由
   pytest（`test_row_counts_match_simulated_data` 等）交叉驗證，而非資料庫層級強制。

2. **本階段不建立 docker-compose**
   規格中的三個 service（db / api / dashboard）本階段只完成資料與 simulator，
   API 和 dashboard 尚不存在，此時寫 docker-compose 沒有實質內容可編排。改為直接
   使用本機 PostgreSQL 進行開發與測試驗證，docker-compose 將於下一個 session
   （API 層）與 API/dashboard 一併補上。

3. **hold / release 語意的具體實作**
   規格只定義了 ENUM 值，未規定 hold 發生的時機與對「停留時間」的影響。本次實作
   選擇：hold 發生在單一站點 track_in 之後、track_out 之前（機率 15%），hold 期間
   會延長該站的總停留時間，release 之後才會有 track_out。此為對「急件 vs 一般件
   停留時間分佈」最保守、最直覺的解讀。

4. **Route 樣板為 demo 用固定資料**
   規格未提供實際載板廠 route 清單，`simulator/routes.py` 中的 PA（4 層）/ PB
   （6 層）僅為代表性 demo 樣板（Core LTH LDI曝光 / DES / AOI 迴圈 + 前後製程），
   非真實產品資料。之後若有真實 route 清單，可直接替換此模組而不影響其他層。

5. **「API 回傳值與 DB 推導值一致」驗收標準的先行驗證**
   本階段沒有 API，故 `tests/helpers.py` 提供一個「當前狀態推導」的測試專用函式，
   分別套用在 in-memory 模擬結果與 DB 查詢結果上並互相比對，作為此驗收標準的先行
   版本。此函式刻意只放在 `tests/` 下，不放進 `simulator/` 或建立新的 `api/`
   模組，避免逾越本次「不碰 API」的範圍；下一個 session 建 API 時預期會參考此邏輯
   重寫為正式的查詢邏輯。

6. **`simulate()` 的 `end_date` 必須由呼叫端明確傳入**
   為確保「同 seed 必產出相同結果」在測試環境下永遠成立，`simulate()` 不讀取
   `datetime.now()`；pytest 固定傳入 `end_date=date(2026, 1, 1)`。真實批次執行時
   （`simulator/run.py`）由 CLI 呼叫端傳入 `date.today()`。

## Seed 斷言基準值（seed=42, months=3, end_date=2026-01-01）
- `LOT000001`（product PA）：已完整跑完 route，最後事件為 seq=18 track_out，qty=288
- `LOT000371`（product PB）：模擬結束時仍在製程中，停在 seq=23（外觀檢查 Final AOI），
  qty=377，狀態 in_process
- `LOT000399`（product PB）：模擬結束時卡在 seq=19 的 hold（尚未 release），qty=232

以上數值皆直接寫死於 `tests/test_seed_assertions.py`，作為之後任何 simulator 核心邏輯
變動的回歸警示。

## 驗證結果
`pytest` 全數 15 項測試通過（4 條資料完整性規則、4 項 DB constraint 驗證、
determinism 驗證、3 個固定 lot 位置斷言、DB vs in-memory 推導一致性驗證）。

## 下一步（下一個 session）
- FastAPI：`/wip/current`、`/wip/hotlots`、`/lots/{lot_id}/history`
- docker-compose：db / api / dashboard 三個 service
- Streamlit 兩頁 dashboard
