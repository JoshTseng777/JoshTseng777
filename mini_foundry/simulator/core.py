"""Mini-Foundry simulator 核心邏輯。

純函式，不依賴 DB 連線或系統時間（`datetime.now()`），
以便 v2 即時模式重用，也讓 pytest 可對固定 seed 斷言固定結果。

停留時間、當前狀態、當前站點皆不在此落地，只產生 events 事實列。
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from .routes import PRODUCT_IDS, get_all_route_steps

MODULE_SECTION_CHOICES = [
    ("製一部", "曝光課"),
    ("製二部", "線路課"),
    ("製三部", "壓合課"),
]
QTY_INITIAL_CHOICES = [200, 250, 300, 350, 400]

HOT_LOT_RATIO = 0.10
HOLD_PROBABILITY = 0.15
SCRAP_PROBABILITY = 0.08
DEFAULT_LOTS_PER_DAY = 5


def simulate(
    seed: int = 42,
    months: int = 3,
    end_date: date | None = None,
    lots_per_day: int = DEFAULT_LOTS_PER_DAY,
) -> dict:
    """產生 3 表資料：route_steps / lots / events。

    end_date 必須由呼叫端明確指定（例如批次執行時傳入 date.today()），
    本函式本身不讀取系統時間，確保同 seed + 同 end_date 必產出相同結果。
    """
    if end_date is None:
        raise ValueError(
            "end_date 必須明確指定以確保結果可重現；批次執行請由呼叫端傳入 date.today()"
        )

    rng = random.Random(seed)
    end_dt = datetime.combine(end_date, datetime.min.time())
    start_dt = end_dt - timedelta(days=30 * months)
    total_days = (end_dt - start_dt).days

    route_steps_rows = get_all_route_steps()
    route_steps_by_product: dict[str, list[dict]] = {}
    for row in route_steps_rows:
        route_steps_by_product.setdefault(row["product_id"], []).append(row)

    lots_rows: list[dict] = []
    events_rows: list[dict] = []
    event_id = 1
    lot_no = 0

    for day_offset in range(total_days):
        day_start = start_dt + timedelta(days=day_offset)
        for _ in range(lots_per_day):
            lot_no += 1
            lot_id = f"LOT{lot_no:06d}"
            product_id = rng.choice(PRODUCT_IDS)
            lot_type = "hot" if rng.random() < HOT_LOT_RATIO else "normal"
            qty_initial = rng.choice(QTY_INITIAL_CHOICES)
            module, section = rng.choice(MODULE_SECTION_CHOICES)
            created_at = day_start + timedelta(hours=rng.uniform(0, 24))

            lots_rows.append({
                "lot_id": lot_id,
                "product_id": product_id,
                "lot_type": lot_type,
                "qty_initial": qty_initial,
                "module": module,
                "section": section,
                "created_at": created_at,
            })

            qty = qty_initial
            current_time = created_at

            for step in route_steps_by_product[product_id]:
                if current_time >= end_dt:
                    break

                plan = _plan_step_events(rng, lot_type)
                step_completed = False

                for event_type, offset in plan:
                    event_time = current_time + offset
                    if event_time >= end_dt:
                        break

                    if event_type == "track_out" and rng.random() < SCRAP_PROBABILITY:
                        scrap_amt = rng.randint(1, max(1, qty // 20))
                        qty = max(0, qty - scrap_amt)

                    events_rows.append({
                        "event_id": event_id,
                        "lot_id": lot_id,
                        "product_id": product_id,
                        "seq": step["seq"],
                        "event_type": event_type,
                        "qty": qty,
                        "event_time": event_time,
                    })
                    event_id += 1

                    if event_type == "track_out":
                        step_completed = True
                        current_time = event_time

                if not step_completed:
                    break

    return {
        "route_steps": route_steps_rows,
        "lots": lots_rows,
        "events": events_rows,
    }


def _plan_step_events(rng: random.Random, lot_type: str) -> list[tuple[str, timedelta]]:
    """規劃單一站點的事件序列（相對於 track_in 的時間偏移）。"""
    dwell_hours = _sample_dwell_hours(rng, lot_type)
    plan: list[tuple[str, timedelta]] = [("track_in", timedelta(hours=0))]

    if rng.random() < HOLD_PROBABILITY:
        hold_offset = timedelta(hours=dwell_hours * rng.uniform(0.2, 0.6))
        hold_duration = timedelta(hours=rng.uniform(2, 12))
        plan.append(("hold", hold_offset))
        plan.append(("release", hold_offset + hold_duration))
        plan.append(("track_out", timedelta(hours=dwell_hours) + hold_duration))
    else:
        plan.append(("track_out", timedelta(hours=dwell_hours)))

    return plan


def _sample_dwell_hours(rng: random.Random, lot_type: str) -> float:
    if lot_type == "hot":
        return rng.uniform(1, 6)
    return rng.uniform(4, 24)
