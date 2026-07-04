"""資料完整性規則（驗收標準）：

- 同一 lot 的 track_out 時間必晚於對應 track_in
- 同一 lot 不得同時存在於兩站（事件序列必須交替合法）
- lot 的 seq 必須嚴格遞增且不跳站
- qty 只能遞減（報廢），不得增加
"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.usefixtures("simulated_data")


def _sorted_events(events: list[dict]) -> list[dict]:
    return sorted(events, key=lambda e: (e["event_time"], e["event_id"]))


class TestTrackOutAfterTrackIn:
    def test_every_track_out_is_later_than_its_track_in(self, events_by_lot):
        checked = 0
        for lot_id, events in events_by_lot.items():
            ordered = _sorted_events(events)
            open_track_in: dict[int, object] = {}
            for event in ordered:
                if event["event_type"] == "track_in":
                    open_track_in[event["seq"]] = event["event_time"]
                elif event["event_type"] == "track_out":
                    track_in_time = open_track_in.get(event["seq"])
                    assert track_in_time is not None, (
                        f"{lot_id} seq={event['seq']} 有 track_out 卻無對應 track_in"
                    )
                    assert event["event_time"] > track_in_time, (
                        f"{lot_id} seq={event['seq']} track_out 未晚於 track_in"
                    )
                    checked += 1
        assert checked > 0


class TestNoConcurrentStationPresence:
    """事件序列必須交替合法：track_in -> (hold -> release)* -> track_out，
    且新 seq 的 track_in 只能發生在前一個 seq 的 track_out 之後。
    lot 在模擬結束前尚未完成的最後一站可以停在 track_in / hold / release
    （代表仍在製程中），但不可以在該站 track_out 之後、下一站 track_in 之前
    出現任何與此 lot 有關的「同時在兩站」情形——這由 seq 單調遞增即可保證。
    """

    def test_event_type_sequence_alternates_legally(self, events_by_lot):
        for lot_id, events in events_by_lot.items():
            ordered = _sorted_events(events)
            state = "awaiting_track_in"
            current_seq = None
            for event in ordered:
                etype = event["event_type"]
                if state == "awaiting_track_in":
                    assert etype == "track_in", (
                        f"{lot_id}: 預期 track_in，實際 {etype} (seq={event['seq']})"
                    )
                    current_seq = event["seq"]
                    state = "in_station"
                elif state == "in_station":
                    assert event["seq"] == current_seq, (
                        f"{lot_id}: 站內事件 seq 不一致 ({event['seq']} != {current_seq})"
                    )
                    if etype == "hold":
                        state = "on_hold"
                    elif etype == "track_out":
                        state = "awaiting_track_in"
                    else:
                        pytest.fail(f"{lot_id}: 站內不合法事件 {etype}")
                elif state == "on_hold":
                    assert event["seq"] == current_seq
                    assert etype == "release", (
                        f"{lot_id}: hold 之後預期 release，實際 {etype}"
                    )
                    state = "in_station"

    def test_no_lot_has_duplicate_open_stations(self, events_by_lot):
        """同一 lot 在任一時刻，開啟中的 track_in 最多只有一個 seq。"""
        for lot_id, events in events_by_lot.items():
            ordered = _sorted_events(events)
            open_seqs: set[int] = set()
            for event in ordered:
                if event["event_type"] == "track_in":
                    assert len(open_seqs) == 0, (
                        f"{lot_id}: 在 seq={event['seq']} track_in 時，"
                        f"仍有未關閉的站點 {open_seqs}"
                    )
                    open_seqs.add(event["seq"])
                elif event["event_type"] == "track_out":
                    assert event["seq"] in open_seqs, (
                        f"{lot_id}: track_out seq={event['seq']} 沒有對應開啟中的站點"
                    )
                    open_seqs.discard(event["seq"])


class TestSeqStrictlyIncreasingNoSkip:
    def test_seq_increments_by_exactly_one_between_steps(
        self, events_by_lot, route_steps_by_product, lot_product_map
    ):
        for lot_id, events in events_by_lot.items():
            ordered = _sorted_events(events)
            track_in_seqs = [e["seq"] for e in ordered if e["event_type"] == "track_in"]
            product_id = lot_product_map[lot_id]
            all_seqs = sorted(route_steps_by_product[product_id].keys())
            first_seq = all_seqs[0]

            assert track_in_seqs[0] == first_seq, (
                f"{lot_id}: 第一個 track_in seq={track_in_seqs[0]} 應為 {first_seq}"
            )
            for prev, nxt in zip(track_in_seqs, track_in_seqs[1:]):
                assert nxt == prev + 1, (
                    f"{lot_id}: seq 從 {prev} 跳到 {nxt}，違反嚴格遞增不跳站"
                )


class TestQtyOnlyDecreases:
    def test_qty_never_increases_within_a_lot(self, events_by_lot):
        for lot_id, events in events_by_lot.items():
            ordered = _sorted_events(events)
            qty_sequence = [e["qty"] for e in ordered]
            for prev, nxt in zip(qty_sequence, qty_sequence[1:]):
                assert nxt <= prev, (
                    f"{lot_id}: qty 從 {prev} 增加到 {nxt}"
                )


class TestDbEnforcesConstraints:
    """DB 層級的完整性驗證：透過真實 constraint violation 確認 schema 本身把關。"""

    def test_qty_check_constraint_rejects_negative(self, db_engine, simulated_data):
        from sqlalchemy import text

        any_event = simulated_data["events"][0]
        with pytest.raises(DBAPIError):
            with db_engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO events (lot_id, product_id, seq, event_type, qty, event_time)
                        VALUES (:lot_id, :product_id, :seq, 'track_in', -1, now())
                        """
                    ),
                    {
                        "lot_id": any_event["lot_id"],
                        "product_id": any_event["product_id"],
                        "seq": any_event["seq"],
                    },
                )

    def test_event_type_enum_rejects_invalid_value(self, db_engine, simulated_data):
        from sqlalchemy import text

        any_event = simulated_data["events"][0]
        with pytest.raises(DBAPIError):
            with db_engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO events (lot_id, product_id, seq, event_type, qty, event_time)
                        VALUES (:lot_id, :product_id, :seq, 'not_a_real_type', 1, now())
                        """
                    ),
                    {
                        "lot_id": any_event["lot_id"],
                        "product_id": any_event["product_id"],
                        "seq": any_event["seq"],
                    },
                )

    def test_events_fk_rejects_unknown_lot(self, db_engine):
        from sqlalchemy import text

        with pytest.raises(DBAPIError):
            with db_engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO events (lot_id, product_id, seq, event_type, qty, event_time)
                        VALUES ('LOT_DOES_NOT_EXIST', 'PA', 1, 'track_in', 100, now())
                        """
                    )
                )

    def test_row_counts_match_simulated_data(self, db_engine, simulated_data):
        from sqlalchemy import text

        with db_engine.connect() as conn:
            db_events = conn.execute(text("SELECT count(*) FROM events")).scalar_one()
            db_lots = conn.execute(text("SELECT count(*) FROM lots")).scalar_one()
            db_route_steps = conn.execute(
                text("SELECT count(*) FROM route_steps")
            ).scalar_one()

        assert db_events == len(simulated_data["events"])
        assert db_lots == len(simulated_data["lots"])
        assert db_route_steps == len(simulated_data["route_steps"])
