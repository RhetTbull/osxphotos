"""Perform diffs of dictionaries"""

from __future__ import annotations

from typing import Any
import sys

EPSILON = sys.float_info.epsilon


def _compare(a: Any, b: Any, tolerance: float):
    """Compare two values, return True if equal, False if not"""
    if tolerance is None:
        return a == b
    elif isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= tolerance
    else:
        return a == b


def dictdiff(
    d1: dict[Any, Any],
    d2: dict[Any, Any],
    tolerance: float = EPSILON,
    path: str = "",
):
    diffs = []
    for k in d1.keys():
        new_path = f"{path}[{k}]" if path else k
        if k not in d2:
            diffs.append([new_path, "removed", (d1[k],)])
        elif isinstance(d1[k], dict) and isinstance(d2[k], dict):
            diffs.extend(dictdiff(d1[k], d2[k], new_path))
        elif isinstance(d1[k], list) and isinstance(d2[k], list):
            for i in range(max(len(d1[k]), len(d2[k]))):
                if i >= len(d1[k]):
                    diffs.append([f"{new_path}[{i}]", "added", (d2[k][i],)])
                elif i >= len(d2[k]):
                    diffs.append([f"{new_path}[{i}]", "removed", (d1[k][i],)])
                elif (
                    d1[k]
                    and isinstance(d1[k][i], dict)
                    and d2[k]
                    and isinstance(d2[k][i], dict)
                ):
                    diffs.extend(dictdiff(d1[k][i], d2[k][i], f"{new_path}[{i}]"))
                elif not _compare(d1[k][i], d2[k][i], tolerance):
                    diffs.append([f"{new_path}[{i}]", "changed", (d1[k][i], d2[k][i])])
        elif not _compare(d1[k], d2[k], tolerance):
            diffs.append([new_path, "changed", (d1[k], d2[k])])
    for k in set(d2.keys()) - set(d1.keys()):
        new_path = f"{path}[{k}]" if path else k
        diffs.append([new_path, "added", (d2[k],)])
    return diffs
