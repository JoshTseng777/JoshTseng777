"""簡繁正規化 (CONSTRAINT §1.2).

所有中文「值」的比對都必須先過這裡,統一成简体字形再比。
禁止在別處直接用字面 `==` 比中文值。
"""
from functools import lru_cache

from opencc import OpenCC

# t2s = Traditional -> Simplified. We normalise everything to simplified so a
# traditional value (e.g. "BGA線路課") and a simplified value ("BGA线路课")
# collapse to the same canonical string.
_CONVERTER = OpenCC("t2s")


@lru_cache(maxsize=None)
def normalize(value: str) -> str:
    """Return the canonical (simplified, stripped) form of a Chinese value.

    Non-str input is coerced to str first. Surrounding whitespace is stripped
    because CRM exports often pad cells.
    """
    if value is None:
        return ""
    return _CONVERTER.convert(str(value)).strip()
