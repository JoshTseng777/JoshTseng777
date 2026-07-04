"""CLI 入口：批次產生 3 個月歷史事件並寫入 PostgreSQL。

用法：
    python -m simulator.run --seed 42 --months 3
"""
from __future__ import annotations

import argparse
from datetime import date

from .core import simulate
from .db import get_engine, load_data, reset_schema


def main() -> None:
    parser = argparse.ArgumentParser(description="Mini-Foundry 批次 simulator")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--months", type=int, default=3)
    args = parser.parse_args()

    data = simulate(seed=args.seed, months=args.months, end_date=date.today())

    engine = get_engine()
    reset_schema(engine)
    load_data(engine, data)

    print(
        f"已產生 route_steps={len(data['route_steps'])} "
        f"lots={len(data['lots'])} events={len(data['events'])} 筆，並寫入資料庫。"
    )


if __name__ == "__main__":
    main()
