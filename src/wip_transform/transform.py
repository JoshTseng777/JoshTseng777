"""Phase 2 + 3 — 清洗/正規化 + 業務邏輯 (filter + flag).

核心轉換是 pure function `transform(df_in) -> df_out`:不讀檔、不寫檔、不呼叫模型。
冪等 / 確定性:同一份輸入跑幾次結果都一致。
"""
from __future__ import annotations

import pandas as pd

from .normalize import normalize

# §3 — the 16 passthrough output columns, in their fixed order.
OUTPUT_COLUMNS = [
    "模组", "课别", "料号", "批号", "当前数量", "工序描述",
    "wip当前回圈数", "wip当前层别", "LOTTYPE", "移进时间",
    "工站停留时间", "过账状态", "HOLD原因代码", "HOLD原因描述",
    "下站工序名称", "下站工序课别",
]

# Internal boolean flag columns added by Phase 3 (consumed by Phase 4 render).
FLAG_STAYTIME = "_red_staytime"
FLAG_LOTTYPE = "_red_lottype"

# §4.1 — keep only rows whose 课别 normalises to this.
KEBIE_COLUMN = "课别"
TARGET_KEBIE = normalize("BGA线路课")

# §4.2 — 停留逾時 (>= 10 hours, boundary inclusive).
STAYTIME_COLUMN = "工站停留时间"
STAYTIME_THRESHOLD = 10.0

# §4.3 — 急料 LOTTYPE, exact match after normalisation (NOT prefix).
LOTTYPE_COLUMN = "LOTTYPE"
URGENT_LOTTYPES = frozenset(
    normalize(v) for v in (
        "ES-样品先行批",
        "QC-量产急料",
        "QS-样品急料",
        "S1-一般样品",
    )
)


class TransformError(RuntimeError):
    """Raised on schema / type VERIFY failures (§ Phase 2)."""


def _assert_schema(df: pd.DataFrame) -> None:
    """VERIFY: all 16 output columns must exist (§ Phase 2)."""
    missing = [c for c in OUTPUT_COLUMNS if c not in df.columns]
    if missing:
        raise TransformError(f"缺少輸出欄位:{missing}")


def _to_staytime_float(df: pd.DataFrame) -> pd.Series:
    """Coerce 工站停留时间 to float, reporting any uncovertible rows (no silent drop)."""
    coerced = pd.to_numeric(df[STAYTIME_COLUMN], errors="coerce")
    bad = df.index[coerced.isna() & (df[STAYTIME_COLUMN].astype(str).str.strip() != "")]
    if len(bad) > 0:
        samples = df.loc[bad, STAYTIME_COLUMN].head(5).tolist()
        raise TransformError(
            f"{STAYTIME_COLUMN} 有 {len(bad)} 列無法轉為數值,例如 {samples}。"
            "請 Phase 2 先 parse(如 '12小时30分'),不可靜默吞。"
        )
    return coerced


def transform(df_in: pd.DataFrame) -> pd.DataFrame:
    """Pure transform: select 16 cols, filter to BGA 線路課, add red flags.

    Returns the 16 output columns (fixed order) plus the two boolean flag
    columns. Input is not mutated.
    """
    _assert_schema(df_in)

    df = df_in.copy()

    # Phase 2: ensure 工站停留时间 is numeric (raises on bad data).
    staytime = _to_staytime_float(df)

    # Phase 3a — filter rows by normalised 课别.
    keep_mask = df[KEBIE_COLUMN].map(lambda v: normalize(v) == TARGET_KEBIE)

    out = df.loc[keep_mask, OUTPUT_COLUMNS].copy()
    staytime = staytime.loc[keep_mask]

    # Phase 3b — independent red flags.
    out[FLAG_STAYTIME] = (staytime >= STAYTIME_THRESHOLD).to_numpy()
    out[FLAG_LOTTYPE] = out[LOTTYPE_COLUMN].map(
        lambda v: normalize(v) in URGENT_LOTTYPES
    ).to_numpy()

    return out.reset_index(drop=True)
