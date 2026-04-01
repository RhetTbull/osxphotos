"""Tests for DirectoryStatCache."""

from __future__ import annotations

from osxphotos.stat_cache import DirectoryStatCache


def test_directory_stat_cache_case_insensitive_lookup(tmp_path):
    """Case-insensitive caches should find existing files with different suffix case."""
    filepath = tmp_path / "IMG_8194.DNG"
    filepath.write_bytes(b"raw")

    cache = DirectoryStatCache(ttl_seconds=300.0, case_sensitive=False)

    assert cache.exists(filepath)
    assert cache.exists(tmp_path / "IMG_8194.dng")
    assert cache.file_sig(tmp_path / "IMG_8194.dng") == cache.file_sig(filepath)


def test_directory_stat_cache_case_sensitive_lookup(tmp_path):
    """Case-sensitive caches should preserve distinct case lookups."""
    filepath = tmp_path / "IMG_8194.DNG"
    filepath.write_bytes(b"raw")

    cache = DirectoryStatCache(ttl_seconds=300.0, case_sensitive=True)

    assert cache.exists(filepath)
    assert not cache.exists(tmp_path / "IMG_8194.dng")
