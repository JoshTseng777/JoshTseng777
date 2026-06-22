"""§8 斷言驗證 — 把藍圖 §8 的三條彙總斷言寫成可執行檢查,並印出實際數字。

用法:
    PYTHONPATH=src python tests/verify_section8.py

這支同時:
  1. 印出「篩選後列數 / 紅A 列數 / 紅B 列數」的實際數字。
  2. 跑 §8 的三條 assert(任何一條不符就 raise,exit code != 0)。
  3. 單獨列出 R5(邊界=10)與 R6(简体值)兩列的處理結果。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wip_transform.ingest import read_crm_batch  # noqa: E402
from wip_transform.transform import (  # noqa: E402
    FLAG_LOTTYPE,
    FLAG_STAYTIME,
    transform,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures", "crm_sample.csv")


def main() -> int:
    df_in = read_crm_batch(FIXTURE)
    df_out = transform(df_in)

    filtered = len(df_out)
    red_a = int(df_out[FLAG_STAYTIME].sum())
    red_b = int(df_out[FLAG_LOTTYPE].sum())

    print("=" * 56)
    print("§8 彙總斷言 — 實際數字")
    print("=" * 56)
    print(f"  原始輸入列數          : {len(df_in)}")
    print(f"  篩選後列數 (期望 6)   : {filtered}")
    print(f"  紅A 停留>=10 (期望 4) : {red_a}")
    print(f"  紅B 急料     (期望 5) : {red_b}")
    print(f"  保留的批号            : {list(df_out['批号'])}")
    print()

    # 三條 §8 斷言
    assert filtered == 6, f"篩選後列數應為 6,實得 {filtered}"
    assert red_a == 4, f"紅A 應為 4,實得 {red_a}"
    assert red_b == 5, f"紅B 應為 5,實得 {red_b}"
    print("  ✅ 三條 §8 斷言全部通過")
    print()

    print("=" * 56)
    print("R5 / R6 單列處理結果")
    print("=" * 56)
    for label, batch in (("R5 (邊界 停留=10)", "LOT0005"), ("R6 (简体值)", "LOT0006")):
        row = df_out.loc[df_out["批号"] == batch].iloc[0]
        print(f"[{label}]  批号={batch}")
        print(f"    课别        = {row['课别']!r}")
        print(f"    工站停留时间 = {row['工站停留时间']!r}")
        print(f"    LOTTYPE     = {row['LOTTYPE']!r}")
        print(f"    紅A 停留旗標 = {bool(row[FLAG_STAYTIME])}")
        print(f"    紅B 急料旗標 = {bool(row[FLAG_LOTTYPE])}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
