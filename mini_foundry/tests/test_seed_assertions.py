"""Seed 斷言測試：

- seed=42 時，指定 lot 在指定時間點的位置為固定值（寫死斷言）
- 「查詢時推導值」在 DB 與純函式結果之間一致
  （此階段無 API，故以 DB 查詢推導 vs. in-memory 推導互相比對，
  作為未來 API 回傳值一致性驗收的先行驗證）
"""
from __future__ import annotations

from datetime import date, datetime

from simulator.core import simulate

from .helpers import derive_current_position, derive_current_position_from_db

SEED = 42
MONTHS = 3
END_DATE = date(2026, 1, 1)


def test_same_seed_produces_identical_output():
    run_a = simulate(seed=SEED, months=MONTHS, end_date=END_DATE)
    run_b = simulate(seed=SEED, months=MONTHS, end_date=END_DATE)

    assert run_a["lots"] == run_b["lots"]
    assert run_a["route_steps"] == run_b["route_steps"]
    assert run_a["events"] == run_b["events"]


def test_different_seed_produces_different_output(simulated_data):
    other = simulate(seed=43, months=MONTHS, end_date=END_DATE)
    assert other["events"] != simulated_data["events"]


class TestFixedLotPositionsAtSeed42:
    """以下數值是 seed=42、end_date=2026-01-01、months=3 的實際模擬結果，
    直接寫死作為回歸斷言；核心邏輯（simulator/core.py, simulator/routes.py）
    有任何會改變既有 lot 事件序列的變動，這些測試都會失敗並提示需要重新檢視。
    """

    def test_completed_lot_LOT000001(self, events_by_lot):
        position = derive_current_position(events_by_lot["LOT000001"])
        assert position == {
            "seq": 18,
            "qty": 288,
            "status": "moved_out",
            "as_of": datetime(2025, 10, 5, 13, 2, 7, 721522),
        }

    def test_in_process_lot_LOT000371(self, events_by_lot, route_steps_by_product, lot_product_map):
        position = derive_current_position(events_by_lot["LOT000371"])
        assert position == {
            "seq": 23,
            "qty": 377,
            "status": "in_process",
            "as_of": datetime(2025, 12, 31, 18, 15, 52, 576595),
        }
        product_id = lot_product_map["LOT000371"]
        step = route_steps_by_product[product_id][position["seq"]]
        assert step["step_name"] == "外觀檢查 Final AOI"
        assert step["layer"] == "L6"

    def test_holding_lot_LOT000399(self, events_by_lot):
        position = derive_current_position(events_by_lot["LOT000399"])
        assert position == {
            "seq": 19,
            "qty": 232,
            "status": "holding",
            "as_of": datetime(2025, 12, 31, 23, 24, 13, 653298),
        }


class TestDbDerivationMatchesInMemory:
    """驗收標準：『API 回傳值與直接查 DB 推導值一致』的先行版本——
    本階段沒有 API，改為驗證 DB 查詢推導的結果與 simulator 產出的
    in-memory 結果一致，確保寫入 DB 的過程沒有遺漏或竄改事實。
    """

    def test_matches_for_sample_lots(self, db_engine, events_by_lot):
        for lot_id in ("LOT000001", "LOT000371", "LOT000399"):
            expected = derive_current_position(events_by_lot[lot_id])
            actual = derive_current_position_from_db(db_engine, lot_id)
            assert actual == expected, f"{lot_id}: DB 推導值與 in-memory 不一致"
