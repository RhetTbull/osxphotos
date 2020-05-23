"""Utilities for comparing files 

Modified from CPython/Lib/filecmp.py

Functions:
    cmp_file(f1, s2) -> int
    file_sig(f1) -> Tuple[int, int, float]

"""

import os
import stat

__all__ = ["cmp", "sig"]


def cmp_file(f1, s2):
    """Compare file f1 to signature s2.

    Arguments:

    f1 --  File name

    s2 -- stats as returned by sig

    Return value:

    True if the files are the same, False otherwise.

    This function uses a cache for past comparisons and the results,
    with cache entries invalidated if their stat information
    changes.  The cache may be cleared by calling clear_cache().

    """

    if not s2:
        return False

    s1 = _sig(os.stat(f1))

    if s1[0] != stat.S_IFREG or s2[0] != stat.S_IFREG:
        return False
    if s1 == s2:
        return True
    return False


def _sig(st):
    return (stat.S_IFMT(st.st_mode), st.st_size, st.st_mtime)


def file_sig(f1):
    """ return os.stat signature for file f1 """
    return _sig(os.stat(f1))
