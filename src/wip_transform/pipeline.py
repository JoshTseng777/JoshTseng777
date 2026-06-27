"""Glue: read -> transform -> write. The deterministic run-time entry point.

Run-time is pure Python — no model calls (CONSTRAINT §1.1). This wires the
four phases together; each phase keeps its own VERIFY gate.
"""
from __future__ import annotations

import argparse

from .ingest import read_crm_batch
from .render import write_report
from .transform import transform


def run(input_path: str, output_path: str) -> int:
    """Run all phases; return the number of red rows written."""
    df_in = read_crm_batch(input_path)          # Phase 1
    df_out = transform(df_in)                    # Phase 2 + 3
    return write_report(df_out, output_path)     # Phase 4


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="CRM batch -> WIP 報表 (Excel)")
    parser.add_argument("input", help="CRM batch 檔 (tab 分隔, 72 欄)")
    parser.add_argument("output", help="輸出 .xlsx 路徑")
    args = parser.parse_args(argv)

    red = run(args.input, args.output)
    print(f"OK — wrote {args.output} (反紅 {red} 列)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
