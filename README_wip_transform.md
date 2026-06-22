# WIP 報表轉換 (Phase 1–4)

把 CRM batch 匯出(72 欄, Tab 分隔)轉成精簡 WIP 報表(16 欄)Excel,只保留
BGA 線路課,並對「停留逾時 (≥10h)」與「急料 LOTTYPE」兩種列做反紅標示。

施工藍圖 / 規則:見 [`CLAUDE_wip_report.md`](CLAUDE_wip_report.md)。

## 安裝

```bash
pip install -r requirements.txt
```

## 執行 (run-time:純確定性 Python,無模型呼叫)

```bash
python -m wip_transform <input.tsv> <output.xlsx>
# 例:對著 fixture 跑
PYTHONPATH=src python -m wip_transform fixtures/crm_sample.csv out.xlsx
```

## 架構 (讀寫與轉換分離)

| 檔案 | Phase | 職責 |
| --- | --- | --- |
| `src/wip_transform/ingest.py` | 1 | 讀檔、編碼自動偵測 (utf-8→gbk→big5)、列數/欄數 VERIFY |
| `src/wip_transform/normalize.py` | 2 | OpenCC 簡繁正規化(所有中文值比對的唯一入口) |
| `src/wip_transform/transform.py` | 2+3 | **pure** `transform(df) -> df`:篩 BGA 線路課 + 兩個反紅旗標 |
| `src/wip_transform/render.py` | 4 | 寫 16 欄 Excel,反紅列套紅色格式 + VERIFY 反紅列數 |
| `src/wip_transform/pipeline.py` | glue | read → transform → write |

核心轉換 `transform(df)` 不讀檔、不寫檔、不呼叫模型,可單獨測試 (L6)。

## 測試 (fixture 標準答案,見藍圖 §8)

```bash
PYTHONPATH=src python -m pytest tests/ -q
```

關鍵案例:R6(简体值仍須命中,證明 OpenCC 正規化有效)、R5(停留 =10.0 邊界須反紅)。

## 範圍

本層只做**資料轉換**。排程 (L1) 與 Ding+ 推送 (L5) 不在此 repo 範圍。
真實 CRM 資料不可進入任何模型 context;開發只對著 `fixtures/` 假資料。
