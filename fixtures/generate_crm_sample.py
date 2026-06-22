"""Generate fixtures/crm_sample.csv — a fake CRM batch export.

Mirrors the real CRM contract (see CLAUDE_wip_report.md §2):
  - Tab separated, exactly 72 columns.
  - Headers are SIMPLIFIED Chinese.
  - Cell values are mostly TRADITIONAL Chinese, but not 100% (row R6 is
    deliberately simplified to test OpenCC normalization).
  - 8 data rows matching the ground-truth table in §8.

This is fake data only. Run:  python3 fixtures/generate_crm_sample.py
"""
import csv
import os

# --- the 16 passthrough output columns, simplified names, fixed order (§3) ---
OUTPUT_COLUMNS = [
    "模组", "课别", "料号", "批号", "当前数量", "工序描述",
    "wip当前回圈数", "wip当前层别", "LOTTYPE", "移进时间",
    "工站停留时间", "过账状态", "HOLD原因代码", "HOLD原因描述",
    "下站工序名称", "下站工序课别",
]

# --- 56 filler columns (simplified) so the batch totals 72 columns ---
FILLER_NAMED = [
    "客户代码", "客户名称", "客户简称", "业务员", "业务部门",
    "厂区代码", "厂区名称", "产线代码", "产线名称", "机台编号",
    "工单号", "生产订单", "优先级", "计划开始", "计划完成",
    "实际开始", "实际完成", "投入数量", "产出数量", "良品数量",
    "不良数量", "不良率", "工时", "标准工时", "建立人员",
    "建立时间", "更新人员", "更新时间", "班别", "班长", "备注",
]
FILLER = FILLER_NAMED + [f"备用字段{i:02d}" for i in range(1, 26)]  # 31 + 25 = 56

# header: 8 fillers, then the 16 meaningful columns, then the remaining 48 fillers.
# (Deliberately NOT putting the output columns first, so name-based selection is
#  actually exercised rather than positional slicing.)
HEADER = FILLER[:8] + OUTPUT_COLUMNS + FILLER[8:]
assert len(HEADER) == 72, len(HEADER)

# --- per-row meaningful values. Key columns come straight from §8. ---
# (课别 / 工站停留时间 / LOTTYPE drive the business logic.)
ROWS = [
    # 批号 acts as a stable row id (B001..B008 == R1..R8) for tests.
    dict(批号="B001", 课别="BGA線路課", 工站停留时间="12.5", LOTTYPE="ES-樣品先行批"),
    dict(批号="B002", 课别="BGA線路課", 工站停留时间="8.0",  LOTTYPE="QC-量產急料"),
    dict(批号="B003", 课别="BGA線路課", 工站停留时间="25.3", LOTTYPE="P0-量產正式批"),
    dict(批号="B004", 课别="BGA線路課", 工站停留时间="3.2",  LOTTYPE="QS-樣品急料"),
    dict(批号="B005", 课别="BGA線路課", 工站停留时间="10.0", LOTTYPE="S1-一般樣品"),
    dict(批号="B006", 课别="BGA线路课", 工站停留时间="15",   LOTTYPE="ES-样品先行批"),  # 简体
    dict(批号="B007", 课别="外層線路課", 工站停留时间="50",   LOTTYPE="ES-樣品先行批"),
    dict(批号="B008", 课别="SMT課",     工站停留时间="2",    LOTTYPE="S1-一般樣品"),
]

# Shared, traditional-Chinese defaults for the remaining meaningful columns.
def meaningful_defaults(i, row):
    return {
        "模组": "BGA",
        "料号": f"MAT-10{i:02d}",
        "当前数量": str(100 + i),
        "工序描述": "迴流焊接",
        "wip当前回圈数": str(i % 3 + 1),
        "wip当前层别": f"L{i % 4 + 1}",
        "移进时间": f"2026-06-2{i % 9} 08:30",
        "过账状态": "已過帳",
        "HOLD原因代码": "",
        "HOLD原因描述": "",
        "下站工序名称": "電性測試",
        "下站工序课别": "測試課",
    }


def build_record(i, row):
    rec = {col: "備用" for col in HEADER}          # filler default value (traditional)
    rec.update(meaningful_defaults(i, row))
    rec.update(row)                                  # key columns last (win)
    return rec


def main():
    out_path = os.path.join(os.path.dirname(__file__), "crm_sample.csv")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, delimiter="\t")
        w.writeheader()
        for i, row in enumerate(ROWS, start=1):
            w.writerow(build_record(i, row))
    print(f"wrote {out_path}: {len(ROWS)} rows x {len(HEADER)} cols")


if __name__ == "__main__":
    main()
