"""DB 存取層：讀取環境變數取得連線資訊，套用 schema，寫入 simulate() 產出的資料。

禁止 hardcode 連線資訊；優先讀取 DATABASE_URL，否則由 PG* 環境變數組成。
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine import Engine

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "schema.sql"


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    host = os.environ["PGHOST"]
    port = os.environ.get("PGPORT", "5432")
    user = os.environ["PGUSER"]
    password = os.environ["PGPASSWORD"]
    dbname = os.environ["PGDATABASE"]
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


def get_engine() -> Engine:
    return create_engine(get_database_url())


def reset_schema(engine: Engine) -> None:
    """卸除並重建三張表與其 ENUM 型別（供批次重跑 / 測試使用，具冪等性）。"""
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS events CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS lots CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS route_steps CASCADE"))
        conn.execute(text("DROP TYPE IF EXISTS event_type_enum"))
        conn.execute(text("DROP TYPE IF EXISTS lot_type_enum"))
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.execute(text(schema_sql))


def load_data(engine: Engine, data: dict) -> None:
    """依 FK 相依順序（route_steps -> lots -> events）批次寫入。"""
    metadata = MetaData()
    metadata.reflect(bind=engine, only=["route_steps", "lots", "events"])
    route_steps_t = metadata.tables["route_steps"]
    lots_t = metadata.tables["lots"]
    events_t = metadata.tables["events"]

    with engine.begin() as conn:
        if data["route_steps"]:
            conn.execute(route_steps_t.insert(), data["route_steps"])
        if data["lots"]:
            conn.execute(lots_t.insert(), data["lots"])
        if data["events"]:
            conn.execute(events_t.insert(), data["events"])
