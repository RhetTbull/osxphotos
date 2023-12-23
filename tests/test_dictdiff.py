"""Test dictdiff"""

import pytest

from osxphotos.dictdiff import _dictdiff

data = [
    ({"a": 1, "b": 2}, {"a": 1, "b": 2}, None, []),
    ({"a": 1, "b": 2}, {"a": 1, "b": 3}, None, [["b", "changed", (2, 3)]]),
    ({"a": 1}, {"a": 1, "b": 3}, None, [["b", "added", (3,)]]),
    ({"a": 1, "b": 2}, {"a": 1}, None, [["b", "removed", (2,)]]),
    ({"a": 1.01, "b": 2}, {"a": 1, "b": 2.0}, None, [["a", "changed", (1.01, 1)]]),
    ({"a": 1.01, "b": 2}, {"a": 1, "b": 2.0}, 0.015, []),
]


@pytest.mark.parametrize("d1, d2, tolerance, expected", data)
def test_dictdiff(d1, d2, tolerance, expected):
    if tolerance is None:
        assert _dictdiff(d1, d2) == expected
    else:
        assert _dictdiff(d1, d2, tolerance=tolerance) == expected
