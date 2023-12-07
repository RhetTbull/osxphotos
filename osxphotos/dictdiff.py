"""Perform diffs of dictionaries"""

from __future__ import annotations

from typing import Any

import dictdiffer

def dictdiff(a: dict[Any, Any], b: dict[Any, Any]) -> list[tuple[Any, ...]]:
    """Return list of differences between two dictionaries
    """
    return list(dictdiffer.diff(a, b, tolerance=0.01))
