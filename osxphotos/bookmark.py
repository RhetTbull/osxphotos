"""Work with macOS CFURL Bookmarks"""

from __future__ import annotations

import os
import pathlib

from .platform import assert_macos, is_macos

if is_macos:
    import mac_alias


def resolve_bookmark_path(bookmark_data: bytes) -> pathlib.Path | None:
    """Get the path from a CFURL file bookmark
    This works without calling CFURLCreateByResolvingBookmarkData
    which fails if the target file does not exist
    """
    assert_macos()
    try:
        bookmark = mac_alias.Bookmark.from_bytes(bookmark_data)
    except Exception as e:
        raise ValueError(f"Invalid bookmark: {e}") from e
    path_components = bookmark.get(mac_alias.kBookmarkPath, None)
    if not path_components:
        return None
    return pathlib.Path(f"/{os.path.join(*path_components)}")
