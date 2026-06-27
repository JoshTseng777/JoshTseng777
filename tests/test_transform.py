"""Ground-truth checks for the fixture (CLAUDE_wip_report.md §8).

These assert the LOCKED expected answers. If they fail, Phase 3 is wrong.
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wip_transform.ingest import detect_encoding, read_crm_batch  # noqa: E402
from wip_transform.render import write_report  # noqa: E402
from wip_transform.transform import (  # noqa: E402
    FLAG_LOTTYPE,
    FLAG_STAYTIME,
    OUTPUT_COLUMNS,
    transform,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures", "crm_sample.csv")


@pytest.fixture
def df_in():
    return read_crm_batch(FIXTURE)


@pytest.fixture
def df_out(df_in):
    return transform(df_in)


# ---------- Phase 1: ingest ----------
def test_ingest_shape(df_in):
    assert df_in.shape[0] == 8          # 8 data rows
    assert df_in.shape[1] == 72         # 72 columns


def test_detect_encoding_utf8():
    assert detect_encoding(FIXTURE) == "utf-8"


def test_detect_encoding_falls_back_to_gbk(tmp_path):
    # A file that is invalid utf-8 but valid gbk must be detected as gbk.
    p = tmp_path / "gbk.tsv"
    p.write_bytes("课别\t值\nBGA线路课\t備用\n".encode("gbk"))
    assert detect_encoding(str(p)) == "gbk"


# ---------- Phase 3: filter + flag (the §8 assertions) ----------
def test_filtered_row_count(df_out):
    assert len(df_out) == 6             # R1–R6 kept; R7, R8 filtered out


def test_red_a_staytime_count(df_out):
    assert int(df_out[FLAG_STAYTIME].sum()) == 4   # R1, R3, R5, R6


def test_red_b_lottype_count(df_out):
    assert int(df_out[FLAG_LOTTYPE].sum()) == 5    # R1, R2, R4, R5, R6


def test_output_columns_order(df_out):
    assert list(df_out.columns)[: len(OUTPUT_COLUMNS)] == OUTPUT_COLUMNS


def _row(df_out, batch):
    return df_out.loc[df_out["批号"] == batch].iloc[0]


def test_R6_simplified_value_still_hits(df_out):
    # 简体 BGA线路课 / ES-样品先行批 must survive filtering AND hit both flags.
    assert "LOT0006" in set(df_out["批号"])     # survived the 课别 filter
    r6 = _row(df_out, "LOT0006")
    assert bool(r6[FLAG_STAYTIME]) is True
    assert bool(r6[FLAG_LOTTYPE]) is True


def test_R5_boundary_staytime_is_red(df_out):
    # 停留 == 10.0 must be red (condition is >=10, not >10).
    r5 = _row(df_out, "LOT0005")
    assert bool(r5[FLAG_STAYTIME]) is True


def test_R7_R8_filtered_out(df_out):
    kept = set(df_out["批号"])
    assert "LOT0007" not in kept  # 外層線路課
    assert "LOT0008" not in kept  # SMT課


# ---------- determinism / idempotency (§1.3) ----------
def test_transform_is_idempotent(df_in):
    a = transform(df_in)
    b = transform(df_in)
    pd.testing.assert_frame_equal(a, b)


def test_transform_does_not_mutate_input(df_in):
    before = df_in.copy()
    transform(df_in)
    pd.testing.assert_frame_equal(df_in, before)


# ---------- Phase 4: render ----------
def test_render_red_count_matches(df_out, tmp_path):
    out = tmp_path / "wip.xlsx"
    red = write_report(df_out, str(out))
    # all 6 kept rows are hit by A or B, so 6 red rows.
    assert red == 6
    assert out.exists()
