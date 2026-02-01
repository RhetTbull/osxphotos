"""Directory stat cache for efficient network volume operations.

This module provides a cache for os.stat results using os.scandir() to batch-read
directory metadata. This is significantly faster for network volumes (SMB/NFS)
where individual stat() calls have high latency.
"""

from __future__ import annotations

import logging
import os
import pathlib
import stat
import threading
import time

from .unicode import normalize_fs_path

__all__ = ["DirectoryStatCache", "are_same_filesystem"]

logger = logging.getLogger("osxphotos")


class DirectoryStatCache:
    """Cache for os.stat results using os.scandir() for efficient batch reading.

    This cache is designed to reduce the number of individual stat() calls when
    exporting to network volumes. Instead of calling stat() for each file,
    os.scandir() is used to read stat info for all files in a directory at once.

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
        self._cache: dict[str, dict[str, os.stat_result]] = {}
        self._timestamps: dict[str, float] = {}
        self._lock = threading.Lock()
        self._virtual_files: dict[str, dict[str, os.stat_result]] = {}

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
        """Use scandir to get stat info for all files in directory.

        This is the key optimization: os.scandir() returns DirEntry objects
        that cache stat information from the directory read operation,
        avoiding individual stat() calls.

        Args:
            directory: Directory path to scan.
        """
        dir_path = self._normalize_dir(directory)

        try:
            entries: dict[str, os.stat_result] = {}
            with os.scandir(dir_path) as it:
                for entry in it:
                    try:
                        # entry.stat() uses cached info from scandir on most platforms
                        # follow_symlinks=False for efficiency; we want link stat
                        # Normalize filename for consistent lookups (handles Unicode NFD/NFC)
                        normalized_name = self._normalize_filename(entry.name)
                        entries[normalized_name] = entry.stat(follow_symlinks=False)
                    except OSError:
                        # Skip files we can't stat (permissions, etc.)
                        pass

            # Merge any virtual files back so they survive cache refresh
            if dir_path in self._virtual_files:
                entries.update(self._virtual_files[dir_path])

            self._cache[dir_path] = entries
            self._timestamps[dir_path] = time.monotonic()
            logger.debug(f"Cached stat info for {len(entries)} files in {dir_path}")

        except OSError as e:
            # Directory doesn't exist or can't be read
            logger.debug(f"Could not scan directory {dir_path}: {e}")
            entries = {}
            if dir_path in self._virtual_files:
                entries.update(self._virtual_files[dir_path])
            self._cache[dir_path] = entries
            self._timestamps[dir_path] = time.monotonic()

    def _ensure_directory_cached(self, dir_path: str) -> None:
        """Ensure directory is in cache, populating if needed."""
        if dir_path not in self._cache or self._is_stale(dir_path):
            self._populate_directory(dir_path)

    def stat(self, filepath: str | pathlib.Path) -> os.stat_result | None:
        """Get cached stat result for a file.

        If the directory hasn't been scanned yet, it will be scanned first.
        If the file doesn't exist in the cached directory listing, returns None.

        Args:
            filepath: Path to the file.

        Returns:
            os.stat_result if file exists in cache, None otherwise.
        """
        path = pathlib.Path(filepath)
        dir_path = self._normalize_dir(path.parent)
        # Normalize filename for consistent lookups (handles Unicode NFD/NFC)
        filename = self._normalize_filename(path.name)

        with self._lock:
            self._ensure_directory_cached(dir_path)
            return self._cache.get(dir_path, {}).get(filename)

    def exists(self, filepath: str | pathlib.Path) -> bool:
        """Check if file exists using cached data.

        Args:
            filepath: Path to the file.

        Returns:
            True if file exists in the cached directory listing.
        """
        return self.stat(filepath) is not None

    def is_file(self, filepath: str | pathlib.Path) -> bool:
        """Check if path is a regular file using cached data.

        Args:
            filepath: Path to check.

        Returns:
            True if path exists and is a regular file.
        """
        st = self.stat(filepath)
        return st is not None and stat.S_ISREG(st.st_mode)

    def is_dir(self, filepath: str | pathlib.Path) -> bool:
        """Check if path is a directory using cached data.

        Args:
            filepath: Path to check.

        Returns:
            True if path exists and is a directory.
        """
        st = self.stat(filepath)
        return st is not None and stat.S_ISDIR(st.st_mode)

    def file_sig(self, filepath: str | pathlib.Path) -> tuple[int, int, int] | None:
        """Get file signature (mode, size, mtime) from cache.

        This returns the same signature format as FileUtil.file_sig().

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
        return (stat.S_IFMT(st.st_mode), st.st_size, int(st.st_mtime))

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
                # If mtime provided and file already cached, update mtime without stat
                if mtime is not None and filename in self._cache[dir_path]:
                    existing = self._cache[dir_path][filename]
                    # Create a new stat_result with updated mtime
                    # os.stat_result can be constructed from a sequence
                    self._cache[dir_path][filename] = os.stat_result(
                        (
                            existing.st_mode,
                            existing.st_ino,
                            existing.st_dev,
                            existing.st_nlink,
                            existing.st_uid,
                            existing.st_gid,
                            existing.st_size,
                            mtime,  # st_atime
                            mtime,  # st_mtime
                            existing.st_ctime,
                        )
                    )
                else:
                    try:
                        st = os.stat(filepath)
                        self._cache[dir_path][filename] = st
                    except OSError:
                        # File doesn't exist; remove from cache unless it's
                        # a virtual file (registered for dry_run tracking)
                        if (
                            dir_path in self._virtual_files
                            and filename in self._virtual_files[dir_path]
                        ):
                            pass
                        else:
                            self._cache[dir_path].pop(filename, None)

    def register_virtual_file(self, filepath: str | pathlib.Path) -> None:
        """Register a file that doesn't exist on disk in the cache.

        This is used during dry_run/pre-load mode to track filenames that
        have been claimed but not written to disk, so that collision detection
        in increment_filename() works correctly.

        Args:
            filepath: Path to the virtual file to register.
        """
        path = pathlib.Path(filepath)
        dir_path = self._normalize_dir(path.parent)
        filename = self._normalize_filename(path.name)

        # Create a synthetic stat_result for the virtual file
        synthetic_stat = os.stat_result(
            (
                0o100644,  # st_mode: regular file
                0,  # st_ino
                0,  # st_dev
                1,  # st_nlink
                0,  # st_uid
                0,  # st_gid
                0,  # st_size
                0,  # st_atime
                0,  # st_mtime
                0,  # st_ctime
            )
        )

        with self._lock:
            # Track in virtual files so it survives cache refresh
            if dir_path not in self._virtual_files:
                self._virtual_files[dir_path] = {}
            self._virtual_files[dir_path][filename] = synthetic_stat

            # Also add to the live cache
            self._ensure_directory_cached(dir_path)
            self._cache[dir_path][filename] = synthetic_stat

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
            self._virtual_files.clear()

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
