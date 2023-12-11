"""Perform diffs of dictionaries"""

from __future__ import annotations

import sys
from typing import Any

EPSILON = sys.float_info.epsilon


def _compare(a: Any, b: Any, tolerance: float):
    """Compare two values, return True if equal, False if not"""
    if tolerance is None:
        return a == b
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tolerance
    else:
        return a == b


def dictdiff(
    d1: dict[Any, Any],
    d2: dict[Any, Any],
    tolerance: float = EPSILON,
) -> list[list[Any, str, tuple[Any, ...]]]:
    """Perform recursive diff of two dictionaries

    Args:
        d1: first dictionary
        d2: second dictionary
        tolerance: tolerance for comparing floats

    Returns:
        list of differences in the form of a list of tuples of the form:
        [path, change_type, (old_value, new_value)]
        where:
            path: path to the key in the dictionary
            change_type: one of "added", "removed", "changed"
            old_value: old value of the key
            new_value: new value of the key
    """
    return _dictdiff(d1, d2, tolerance)


def _dictdiff(
    d1: dict[Any, Any],
    d2: dict[Any, Any],
    tolerance: float = EPSILON,
    path: str = "",
) -> list[list[Any, str, tuple[Any, ...]]]:
    """Perform recursive diff of two dictionaries

    Args:
        d1: first dictionary
        d2: second dictionary
        tolerance: tolerance for comparing floats
        path: path to current key in dictionary (used for recursion)

    Returns:
        list of differences in the form of a list of tuples of the form:
        [path, change_type, (old_value, new_value)]
        where:
            path: path to the key in the dictionary
            change_type: one of "added", "removed", "changed"
            old_value: old value of the key
            new_value: new value of the key
    """
    diffs = []
    for k in d1.keys():
        new_path = f"{path}[{k}]" if path else k
        if k not in d2:
            diffs.append([new_path, "removed", (d1[k],)])
        elif isinstance(d1[k], dict) and isinstance(d2[k], dict):
            diffs.extend(_dictdiff(d1[k], d2[k], tolerance, new_path))
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
                    diffs.extend(
                        _dictdiff(d1[k][i], d2[k][i], tolerance, f"{new_path}[{i}]")
                    )
                elif not _compare(d1[k][i], d2[k][i], tolerance):
                    diffs.append([f"{new_path}[{i}]", "changed", (d1[k][i], d2[k][i])])
        elif not _compare(d1[k], d2[k], tolerance):
            diffs.append([new_path, "changed", (d1[k], d2[k])])
    for k in set(d2.keys()) - set(d1.keys()):
        new_path = f"{path}[{k}]" if path else k
        diffs.append([new_path, "added", (d2[k],)])
    return diffs
