"""Utilities to classify volume type for a given path.

Provides detection of network/NAS volumes to enable export optimizations
when writing to SMB/AFP/WebDAV/NFS shares.
"""

from __future__ import annotations

import logging
import os
import pathlib
import subprocess
from functools import cache

from .platform import is_macos

logger = logging.getLogger("osxphotos")

__all__ = [
    "is_path_on_network_volume",
]


def _nearest_existing_path(path: pathlib.Path) -> pathlib.Path:
    """Return the nearest existing ancestor for path (or path itself if it exists)."""
    p = path
    while not p.exists() and p.parent != p:
        p = p.parent
    return p


def _network_via_nsurl(path: pathlib.Path) -> bool | None:
    """Check NSURLVolumeIsLocalKey via pyobjc; returns True/False or None on error.

    Only used on macOS.
    """
    if not is_macos:
        return None

    import Foundation  # type: ignore
    import objc  # type: ignore
    from Foundation import NSURL  # type: ignore

    try:
        with objc.autorelease_pool():
            url = NSURL.fileURLWithPath_(str(path))
            key = getattr(Foundation, "NSURLVolumeIsLocalKey", "NSURLVolumeIsLocalKey")
            values, error = url.resourceValuesForKeys_error_([key], None)
            if error is not None:
                logger.debug(f"NSURL resourceValuesForKeys_error_ failed: {error}")
                return None
            # values is an NSDictionary; use .get for safety
            result = values.get(key, None)
            if result is None:
                return None
            # True means the volume is local storage; for NAS detection, invert it
            return not bool(result)
    except Exception as e:
        logger.debug(f"NSURLVolumeIsLocalKey check failed for {path}: {e}")
        return None


def _network_via_mount(path: pathlib.Path) -> bool | None:
    """Heuristic fallback using `/sbin/mount` output; returns True/False or None on error.

    Considers fstype one of {smbfs, afpfs, webdav, nfs} as network.
    """
    try:
        # Resolve to avoid misleading matches from symlinks
        target = path.resolve()
        out = subprocess.check_output(["/sbin/mount"], text=True)
    except Exception as e:
        logger.debug(f"mount lookup failed for {path}: {e}")
        return None

    best_match = ("", "")  # (mount_point, fstype)
    for line in out.splitlines():
        # Example: "//server/share on /Volumes/Share (smbfs, nodev, nosuid, ... )"
        try:
            before_on, after_on = line.split(" on ", 1)
            mnt_point, rest = after_on.split(" (", 1)
            fstype = rest.split(",", 1)[0].strip()
        except ValueError:
            continue

        mnt_point_path = pathlib.Path(mnt_point)
        # Pick the longest mount point that is a parent of target
        try:
            if str(target).startswith(str(mnt_point_path)) and len(
                str(mnt_point_path)
            ) > len(best_match[0]):
                best_match = (str(mnt_point_path), fstype)
        except Exception:
            continue

    if not best_match[0]:
        return None

    network_fstypes = {"smbfs", "afpfs", "webdav", "nfs"}
    return best_match[1].lower() in network_fstypes


@cache
def _is_path_on_network_volume_cached(path_str: str) -> bool:
    """Cached worker that assumes a normalized, hashable string path."""
    p = pathlib.Path(path_str)
    p = _nearest_existing_path(p)

    # Prefer NSURL on macOS
    nsurl_result = _network_via_nsurl(p)
    if nsurl_result is not None:
        return nsurl_result

    # Fallback to mount parsing
    mount_result = _network_via_mount(p)
    if mount_result is not None:
        return mount_result

    # If everything fails, assume local to avoid over-applying NAS-specific behavior
    logger.debug(
        f"Could not determine volume type for {p}; defaulting to local (False)"
    )
    return False


def is_path_on_network_volume(path: str | os.PathLike | pathlib.Path) -> bool:
    """Return True if path is on a network/NAS volume, else False.

    Uses macOS NSURL volume resource keys via pyobjc when available. Falls back to
    parsing `/sbin/mount` output as a best-effort heuristic. If the path does not
    exist, the nearest existing ancestor is used.

    Args:
        path: file or directory path to classify

    Returns:
        True if classified as network/NAS; False for local or if classification
        cannot be determined.
    """
    # Normalize to a string for stable caching and to tolerate custom PathLike types
    try:
        path_str = os.fspath(path)
    except TypeError:
        path_str = str(path)
    return _is_path_on_network_volume_cached(path_str)
