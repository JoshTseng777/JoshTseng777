"""測試專用輔助函式：從 events 推導「當前狀態 / 當前站點」。

此推導邏輯之後會成為 API 層的一部分，但本階段（schema + simulator + pytest）
刻意不建置 API，故僅放在 tests/ 下供驗收測試使用，不對外暴露為產品程式碼。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def derive_current_position(events_for_lot: list[dict]) -> dict:
    """依 event_time（同時間以 event_id 為序）取最後一筆事件，推導目前狀態。"""
    ordered = sorted(events_for_lot, key=lambda e: (e["event_time"], e["event_id"]))
    last = ordered[-1]

    if last["event_type"] == "track_out":
        status = "moved_out"
    elif last["event_type"] == "hold":
        status = "holding"
    else:
        status = "in_process"

    return {
        "seq": last["seq"],
        "qty": last["qty"],
        "status": status,
        "as_of": last["event_time"],
    }


def derive_current_position_from_db(engine: Engine, lot_id: str) -> dict:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT event_id, seq, qty, event_type, event_time
                FROM events
                WHERE lot_id = :lot_id
                ORDER BY event_time, event_id
                """
            ),
            {"lot_id": lot_id},
        ).mappings().all()

    events_for_lot = [dict(row) for row in rows]
    return derive_current_position(events_for_lot)
