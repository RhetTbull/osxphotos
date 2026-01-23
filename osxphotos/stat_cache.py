"""Directory stat cache for efficient network volume operations.

This module provides a cache for os.stat results using os.scandir() to batch-read
directory metadata. This is significantly faster for network volumes (SMB/NFS)
where individual stat() calls have high latency.
"""

from __future__ import annotations

import logging
import os
import pathlib
import stat as stat_module
import threading
import time
from dataclasses import dataclass
from typing import NamedTuple

from .unicode import normalize_fs_path

__all__ = ["DirectoryStatCache", "are_same_filesystem"]

logger = logging.getLogger("osxphotos")


class CachedEntry(NamedTuple):
    """Cached directory entry with lazy stat support.

    Attributes:
        is_file: True if entry is a regular file.
        is_dir: True if entry is a directory.
        stat_result: Cached stat result, or None if not yet fetched.
    """

    is_file: bool
    is_dir: bool
    stat_result: os.stat_result | None


class DirectoryStatCache:
    """Cache for os.stat results using os.scandir() for efficient batch reading.

    This cache is designed to reduce the number of individual stat() calls when
    exporting to network volumes. Instead of calling stat() for each file,
    os.scandir() is used to read directory entries efficiently.

    The cache uses lazy stat: file type info (is_file, is_dir) is captured from
    DirEntry objects without calling stat(), and actual stat() calls are deferred
    until size/mtime is actually needed.

    The cache is thread-safe and supports TTL-based expiration.

    Attributes:
        ttl_seconds: Time-to-live for cached entries in seconds.
    """

    def __init__(self, ttl_seconds: float = 300.0):
        """Initialize the directory stat cache.

        Args:
            ttl_seconds: Time-to-live for cached entries. After this time,
                entries are considered stale and will be re-fetched.
                Default is 300 seconds.
        """
        self._ttl = ttl_seconds
        self._cache: dict[str, dict[str, CachedEntry]] = {}
        self._timestamps: dict[str, float] = {}
        self._lock = threading.Lock()

    def _normalize_dir(self, directory: str | pathlib.Path) -> str:
        """Normalize directory path for use as cache key."""
        return normalize_fs_path(str(directory))

    def _normalize_filename(self, filename: str) -> str:
        """Normalize filename for consistent cache lookups.

        This handles Unicode normalization to ensure filenames with
        accented characters match regardless of NFD/NFC form.
        """
        return normalize_fs_path(filename)

    def _is_stale(self, dir_path: str) -> bool:
        """Check if cached entry is stale."""
        if dir_path not in self._timestamps:
            return True
        return time.monotonic() - self._timestamps[dir_path] > self._ttl

    def _populate_directory(self, directory: str | pathlib.Path) -> None:
        """Use scandir to get file type info for all files in directory.

        This uses lazy stat: DirEntry.is_file() and is_dir() typically use
        d_type from readdir() which doesn't require stat() syscalls on most
        Unix systems. Actual stat() calls are deferred until needed.

        Args:
            directory: Directory path to scan.
        """
        dir_path = self._normalize_dir(directory)

        try:
            entries: dict[str, CachedEntry] = {}
            with os.scandir(dir_path) as it:
                for entry in it:
                    try:
                        # Use is_file()/is_dir() which typically don't require stat
                        # on Unix systems (they use d_type from readdir)
                        # follow_symlinks=False for consistency
                        normalized_name = self._normalize_filename(entry.name)
                        entries[normalized_name] = CachedEntry(
                            is_file=entry.is_file(follow_symlinks=False),
                            is_dir=entry.is_dir(follow_symlinks=False),
                            stat_result=None,  # Lazy: don't stat until needed
                        )
                    except OSError:
                        # Skip files we can't access (permissions, etc.)
                        pass

            self._cache[dir_path] = entries
            self._timestamps[dir_path] = time.monotonic()
            logger.debug(f"Cached {len(entries)} entries in {dir_path} (lazy stat)")

        except OSError as e:
            # Directory doesn't exist or can't be read
            logger.debug(f"Could not scan directory {dir_path}: {e}")
            self._cache[dir_path] = {}
            self._timestamps[dir_path] = time.monotonic()

    def _ensure_directory_cached(self, dir_path: str) -> None:
        """Ensure directory is in cache, populating if needed."""
        if dir_path not in self._cache or self._is_stale(dir_path):
            self._populate_directory(dir_path)

    def _get_entry(
        self, filepath: str | pathlib.Path
    ) -> tuple[str, str, CachedEntry | None]:
        """Get cached entry for a file.

        Returns:
            Tuple of (dir_path, filename, CachedEntry or None).
        """
        path = pathlib.Path(filepath)
        dir_path = self._normalize_dir(path.parent)
        filename = self._normalize_filename(path.name)

        with self._lock:
            self._ensure_directory_cached(dir_path)
            entry = self._cache.get(dir_path, {}).get(filename)
            return dir_path, filename, entry

    def _ensure_stat(
        self, dir_path: str, filename: str, filepath: str | pathlib.Path
    ) -> os.stat_result | None:
        """Ensure stat result is cached for the given file.

        This performs the lazy stat: if stat_result is None, it calls os.stat()
        and updates the cache.

        Args:
            dir_path: Normalized directory path.
            filename: Normalized filename.
            filepath: Full path to the file.

        Returns:
            stat_result or None if file doesn't exist.
        """
        with self._lock:
            if dir_path not in self._cache:
                return None
            entry = self._cache[dir_path].get(filename)
            if entry is None:
                return None

            # If we already have stat result, return it
            if entry.stat_result is not None:
                return entry.stat_result

            # Lazy stat: fetch stat now
            try:
                stat_result = os.stat(filepath, follow_symlinks=False)
                # Update cache with stat result
                self._cache[dir_path][filename] = CachedEntry(
                    is_file=entry.is_file,
                    is_dir=entry.is_dir,
                    stat_result=stat_result,
                )
                return stat_result
            except OSError:
                # File no longer exists or can't be accessed
                self._cache[dir_path].pop(filename, None)
                return None

    def stat(self, filepath: str | pathlib.Path) -> os.stat_result | None:
        """Get cached stat result for a file.

        If the directory hasn't been scanned yet, it will be scanned first.
        If the file doesn't exist in the cached directory listing, returns None.

        Note: This triggers a stat() call if not already cached.

        Args:
            filepath: Path to the file.

        Returns:
            os.stat_result if file exists in cache, None otherwise.
        """
        dir_path, filename, entry = self._get_entry(filepath)
        if entry is None:
            return None
        return self._ensure_stat(dir_path, filename, filepath)

    def exists(self, filepath: str | pathlib.Path) -> bool:
        """Check if file exists using cached data.

        This is a cheap operation that doesn't require stat().

        Args:
            filepath: Path to the file.

        Returns:
            True if file exists in the cached directory listing.
        """
        _, _, entry = self._get_entry(filepath)
        return entry is not None

    def is_file(self, filepath: str | pathlib.Path) -> bool:
        """Check if path is a regular file using cached data.

        This is a cheap operation that doesn't require stat().

        Args:
            filepath: Path to check.

        Returns:
            True if path exists and is a regular file.
        """
        _, _, entry = self._get_entry(filepath)
        return entry is not None and entry.is_file

    def is_dir(self, filepath: str | pathlib.Path) -> bool:
        """Check if path is a directory using cached data.

        This is a cheap operation that doesn't require stat().

        Args:
            filepath: Path to check.

        Returns:
            True if path exists and is a directory.
        """
        _, _, entry = self._get_entry(filepath)
        return entry is not None and entry.is_dir

    def file_sig(self, filepath: str | pathlib.Path) -> tuple[int, int, int] | None:
        """Get file signature (mode, size, mtime) from cache.

        This returns the same signature format as FileUtil.file_sig().

        Note: This triggers a stat() call if not already cached.

        Args:
            filepath: Path to the file.

        Returns:
            Tuple of (mode, size, mtime) if file exists, None otherwise.
            Mode is the file type portion of st_mode (via stat.S_IFMT).
            Mtime is truncated to int for consistency with FileUtil.
        """
        st = self.stat(filepath)
        if st is None:
            return None
        return (stat_module.S_IFMT(st.st_mode), st.st_size, int(st.st_mtime))

    def list_directory(
        self,
        directory: str | pathlib.Path,
        startswith: str | None = None,
        case_sensitive: bool = False,
    ) -> list[str]:
        """List files in directory using cached data.

        Args:
            directory: Directory to list.
            startswith: Optional prefix filter.
            case_sensitive: If True, match case-sensitively.

        Returns:
            List of filenames in the directory.
        """
        dir_path = self._normalize_dir(directory)

        with self._lock:
            self._ensure_directory_cached(dir_path)
            files = list(self._cache.get(dir_path, {}).keys())

        if startswith:
            # Normalize the prefix for consistent comparison with cached filenames
            startswith_normalized = self._normalize_filename(startswith)
            if case_sensitive:
                files = [f for f in files if f.startswith(startswith_normalized)]
            else:
                startswith_lower = startswith_normalized.lower()
                files = [f for f in files if f.lower().startswith(startswith_lower)]

        return files

    def find_files_by_prefix(
        self,
        directory: str | pathlib.Path,
        prefix: str,
        ignore_ext: str | None = None,
    ) -> list[str]:
        """Find regular files starting with prefix, sorted by size (largest first).

        This is an optimized version of utils.find_files_by_prefix that uses
        cached directory listings to avoid repeated listdir calls.

        Args:
            directory: Directory to search.
            prefix: Filename prefix to match (case-sensitive).
            ignore_ext: Optional extension to ignore (must include leading ".").

        Returns:
            List of full file paths, sorted by size (largest first).
        """
        dir_path = self._normalize_dir(directory)
        prefix_normalized = self._normalize_filename(prefix)

        if ignore_ext is not None:
            ignore_ext = ignore_ext.lower()

        matching_files: list[tuple[str, int]] = []

        with self._lock:
            self._ensure_directory_cached(dir_path)
            entries = self._cache.get(dir_path, {})

            for filename, entry in entries.items():
                if not filename.startswith(prefix_normalized):
                    continue
                if not entry.is_file:
                    continue
                if ignore_ext is not None:
                    _, ext = os.path.splitext(filename)
                    if ext.lower() == ignore_ext:
                        continue

                full_path = os.path.join(dir_path, filename)

                # Need stat for size - ensure it's cached
                if entry.stat_result is None:
                    try:
                        stat_result = os.stat(full_path, follow_symlinks=False)
                        self._cache[dir_path][filename] = CachedEntry(
                            is_file=entry.is_file,
                            is_dir=entry.is_dir,
                            stat_result=stat_result,
                        )
                        matching_files.append((full_path, stat_result.st_size))
                    except OSError:
                        continue
                else:
                    matching_files.append((full_path, entry.stat_result.st_size))

        matching_files.sort(key=lambda x: x[1], reverse=True)
        return [f for f, _ in matching_files]

    def update_file(
        self, filepath: str | pathlib.Path, mtime: int | None = None
    ) -> None:
        """Update cache for a single file after it's been written.

        This is more efficient than invalidating the entire directory cache.
        It stats the file and updates the cache entry.

        Args:
            filepath: Path to the file that was written.
            mtime: Optional mtime to set in cache. If provided and file is already
                cached, updates only the mtime without calling stat(). This is useful
                after utime() calls where we know the new mtime.
        """
        path = pathlib.Path(filepath)
        dir_path = self._normalize_dir(path.parent)
        # Normalize filename for consistent lookups (handles Unicode NFD/NFC)
        filename = self._normalize_filename(path.name)

        with self._lock:
            # Only update if directory is already cached
            if dir_path in self._cache:
                existing = self._cache[dir_path].get(filename)
                # If mtime provided and file already cached with stat, update mtime
                if (
                    mtime is not None
                    and existing is not None
                    and existing.stat_result is not None
                ):
                    old_stat = existing.stat_result
                    # Create a new stat_result with updated mtime
                    new_stat = os.stat_result(
                        (
                            old_stat.st_mode,
                            old_stat.st_ino,
                            old_stat.st_dev,
                            old_stat.st_nlink,
                            old_stat.st_uid,
                            old_stat.st_gid,
                            old_stat.st_size,
                            mtime,  # st_atime
                            mtime,  # st_mtime
                            old_stat.st_ctime,
                        )
                    )
                    self._cache[dir_path][filename] = CachedEntry(
                        is_file=existing.is_file,
                        is_dir=existing.is_dir,
                        stat_result=new_stat,
                    )
                else:
                    try:
                        st = os.stat(filepath, follow_symlinks=False)
                        self._cache[dir_path][filename] = CachedEntry(
                            is_file=stat_module.S_ISREG(st.st_mode),
                            is_dir=stat_module.S_ISDIR(st.st_mode),
                            stat_result=st,
                        )
                    except OSError:
                        # File doesn't exist, remove from cache
                        self._cache[dir_path].pop(filename, None)

    def remove_file(self, filepath: str | pathlib.Path) -> None:
        """Remove a file from the cache after it's been deleted.

        Args:
            filepath: Path to the file that was deleted.
        """
        path = pathlib.Path(filepath)
        dir_path = self._normalize_dir(path.parent)
        # Normalize filename for consistent lookups (handles Unicode NFD/NFC)
        filename = self._normalize_filename(path.name)

        with self._lock:
            if dir_path in self._cache:
                self._cache[dir_path].pop(filename, None)

    def invalidate(self, filepath: str | pathlib.Path) -> None:
        """Invalidate cache for the directory containing filepath.

        Call this after writing/modifying a file to ensure fresh data
        on subsequent reads.

        Args:
            filepath: Path to a file whose parent directory should be invalidated.
        """
        dir_path = self._normalize_dir(pathlib.Path(filepath).parent)
        with self._lock:
            self._cache.pop(dir_path, None)
            self._timestamps.pop(dir_path, None)

    def invalidate_directory(self, directory: str | pathlib.Path) -> None:
        """Invalidate cache for a specific directory.

        Args:
            directory: Directory path to invalidate.
        """
        dir_path = self._normalize_dir(directory)
        with self._lock:
            self._cache.pop(dir_path, None)
            self._timestamps.pop(dir_path, None)

    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def prefetch_directories(self, directories: list[str | pathlib.Path]) -> None:
        """Pre-populate cache for multiple directories.

        This is useful when you know which directories will be accessed
        and want to batch the I/O operations.

        Args:
            directories: List of directory paths to prefetch.
        """
        for directory in directories:
            dir_path = self._normalize_dir(directory)
            with self._lock:
                if dir_path not in self._cache or self._is_stale(dir_path):
                    self._populate_directory(dir_path)


def are_same_filesystem(path1: str | pathlib.Path, path2: str | pathlib.Path) -> bool:
    """Check if two paths are on the same filesystem.

    This is useful for determining whether hardlinks are possible between
    two locations. Hardlinks cannot span filesystems.

    Args:
        path1: First path.
        path2: Second path.

    Returns:
        True if both paths are on the same filesystem (same st_dev),
        False if on different filesystems or if either path doesn't exist.
    """
    try:
        stat1 = os.stat(path1)
        stat2 = os.stat(path2)
        return stat1.st_dev == stat2.st_dev
    except OSError:
        return False


def get_filesystem_id(path: str | pathlib.Path) -> int | None:
    """Get the filesystem ID (st_dev) for a path.

    Args:
        path: Path to check.

    Returns:
        Filesystem ID (st_dev) or None if path doesn't exist.
    """
    try:
        return os.stat(path).st_dev
    except OSError:
        return None
