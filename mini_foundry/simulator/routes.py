"""Route 主檔定義：IC 載板製程 route，迴圈以展開後的明確步驟存放。

此檔案為 v1 demo 用的固定 route 樣板（2 個 product），非從外部資料匯入。
迴圈邏輯本身不落地儲存，只保留展開後的 step 序列（loop_code 供辨識用）。
"""
from __future__ import annotations

LOOP_CODE = "02FB"

# 建置層（build-up layer）迴圈中，每層重複的工序
BUILDUP_STEP_NAMES = ["Core LTH LDI曝光", "Core LTH DES", "AOI檢查"]

# product_id -> 建置層清單
ROUTE_DEFINITIONS: dict[str, list[str]] = {
    "PA": ["L1", "L2", "L3", "L4"],
    "PB": ["L1", "L2", "L3", "L4", "L5", "L6"],
}

PRODUCT_IDS = list(ROUTE_DEFINITIONS.keys())


def get_route_steps(product_id: str) -> list[dict]:
    """展開單一 product 的完整 route_steps（依 seq 由小到大排序）。"""
    layers = ROUTE_DEFINITIONS[product_id]
    rows: list[dict] = []
    seq = 1

    rows.append({
        "product_id": product_id,
        "seq": seq,
        "layer": layers[0],
        "loop_code": None,
        "step_name": "投料 Lot Start",
    })
    seq += 1

    for layer in layers:
        for step_name in BUILDUP_STEP_NAMES:
            rows.append({
                "product_id": product_id,
                "seq": seq,
                "layer": layer,
                "loop_code": LOOP_CODE,
                "step_name": step_name,
            })
            seq += 1

    trailing_step_names = [
        "防焊嵌合 Solder Mask",
        "表面處理 Surface Finish",
        "電測 E-Test",
        "外觀檢查 Final AOI",
        "包裝出貨 Packing",
    ]
    for step_name in trailing_step_names:
        rows.append({
            "product_id": product_id,
            "seq": seq,
            "layer": layers[-1],
            "loop_code": None,
            "step_name": step_name,
        })
        seq += 1

    return rows


def get_all_route_steps() -> list[dict]:
    rows: list[dict] = []
    for product_id in PRODUCT_IDS:
        rows.extend(get_route_steps(product_id))
    return rows
