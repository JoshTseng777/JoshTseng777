from __future__ import annotations

from datetime import date

import pytest
from dotenv import load_dotenv

from simulator.core import simulate
from simulator.db import get_engine, load_data, reset_schema

load_dotenv(".env.test")
load_dotenv(".env")

SEED = 42
MONTHS = 3
END_DATE = date(2026, 1, 1)


@pytest.fixture(scope="session")
def simulated_data():
    return simulate(seed=SEED, months=MONTHS, end_date=END_DATE)


@pytest.fixture(scope="session")
def db_engine(simulated_data):
    engine = get_engine()
    reset_schema(engine)
    load_data(engine, simulated_data)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def events_by_lot(simulated_data):
    by_lot: dict[str, list[dict]] = {}
    for event in simulated_data["events"]:
        by_lot.setdefault(event["lot_id"], []).append(event)
    return by_lot


@pytest.fixture(scope="session")
def route_steps_by_product(simulated_data):
    by_product: dict[str, dict[int, dict]] = {}
    for step in simulated_data["route_steps"]:
        by_product.setdefault(step["product_id"], {})[step["seq"]] = step
    return by_product


@pytest.fixture(scope="session")
def lot_product_map(simulated_data):
    return {lot["lot_id"]: lot["product_id"] for lot in simulated_data["lots"]}
