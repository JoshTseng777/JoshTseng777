"""Phase 1 — 讀檔 (ingest).

把 CRM 檔穩定讀成 DataFrame。編碼自動偵測 (utf-8 -> gbk -> big5),禁止寫死。
讀進來不可靜默漏行。

分隔符:合約 (§2) 規定 production CRM batch 是 Tab;但隨附的開發 fixture
(`fixtures/crm_sample.csv`) 是逗號分隔。為了同時吃下兩者、又不放鬆「欄數必須
== 72」這條 VERIFY,我們用「哪個分隔符切出 72 欄就用哪個」來偵測(優先 Tab),
做法與編碼自動偵測同構。
"""
from __future__ import annotations

import pandas as pd

# CONSTRAINT §2: try in this order, take the first that decodes cleanly.
ENCODING_CANDIDATES = ("utf-8", "gbk", "big5")
# Tab first (production contract §2), then comma (the dev fixture).
DELIMITER_CANDIDATES = ("\t", ",")
EXPECTED_COLUMNS = 72


class IngestError(RuntimeError):
    """Raised when the CRM batch can't be read or fails its shape VERIFY."""


def detect_encoding(path: str, candidates=ENCODING_CANDIDATES) -> str:
    """Return the first candidate encoding that decodes the whole file.

    We decode the entire file (not a sample) so a late mojibake byte can't slip
    through — losing rows silently is an incident (§1.2 / §2).
    """
    with open(path, "rb") as f:
        raw = f.read()
    for enc in candidates:
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    raise IngestError(
        f"無法以 {candidates} 任一編碼解碼 {path};請人工檢查檔案。"
    )


def detect_delimiter(path: str, encoding: str, candidates=DELIMITER_CANDIDATES) -> str:
    """Return the first candidate delimiter whose header splits into 72 columns.

    Prefers Tab (the production contract); falls back to comma (the fixture).
    """
    with open(path, encoding=encoding) as f:
        header = f.readline()
    for sep in candidates:
        if len(header.split(sep)) == EXPECTED_COLUMNS:
            return sep
    raise IngestError(
        f"分隔符偵測失敗:{tuple(candidates)} 都切不出 {EXPECTED_COLUMNS} 欄。停止。"
    )


def _count_data_rows(path: str, encoding: str) -> int:
    """Ground-truth row count straight from the file (header excluded)."""
    with open(path, encoding=encoding) as f:
        lines = f.read().splitlines()
    # drop a trailing blank line if present, then drop the header line.
    while lines and lines[-1] == "":
        lines.pop()
    return max(len(lines) - 1, 0)


def read_crm_batch(path: str) -> pd.DataFrame:
    """Read a 72-column CRM batch into a DataFrame.

    VERIFY (§ Phase 1): row count == file's row count; column count == 72.
    Any mismatch stops the pipeline with a clear error (never a half read).
    """
    encoding = detect_encoding(path)
    delimiter = detect_delimiter(path, encoding)
    expected_rows = _count_data_rows(path, encoding)

    df = pd.read_csv(
        path,
        sep=delimiter,
        encoding=encoding,
        dtype=str,            # keep everything textual; typing happens in Phase 2
        keep_default_na=False,  # don't turn empty cells into NaN -> no silent loss
        na_filter=False,
    )

    if len(df) != expected_rows:
        raise IngestError(
            f"列數不符:檔案有 {expected_rows} 列,pandas 讀到 {len(df)} 列 "
            f"(編碼={encoding}, 分隔符={delimiter!r})。停止。"
        )
    if df.shape[1] != EXPECTED_COLUMNS:
        raise IngestError(
            f"欄數不符:預期 {EXPECTED_COLUMNS} 欄,實得 {df.shape[1]} 欄 "
            f"(編碼={encoding}, 分隔符={delimiter!r})。停止。"
        )
    return df
