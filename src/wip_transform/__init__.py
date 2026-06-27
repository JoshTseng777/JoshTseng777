"""WIP 報表轉換 — build-time developed, run-time deterministic pipeline.

See CLAUDE_wip_report.md for the build spec.
"""
from .ingest import read_crm_batch
from .pipeline import run
from .render import write_report
from .transform import transform

__all__ = ["read_crm_batch", "transform", "write_report", "run"]
