"""test FileUtil"""

import os
import pathlib
import time

import pytest

from osxphotos.fileutil import (
    FileUtil,
    FileUtilMacOS,
    FileUtilShUtil,
    cfg_fileutil_retry,
)
from osxphotos.platform import is_macos

TEST_HEIC = "tests/test-images/IMG_3092.heic"
TEST_RAW = "tests/test-images/DSC03584.dng"


def test_copy_file_valid():
    # copy file with valid src, dest
    import os.path
    import tempfile

    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    result = FileUtil.copy(src, temp_dir.name)
    assert result
    assert os.path.isfile(os.path.join(temp_dir.name, "wedding.jpg"))


def test_copy_file_invalid():
    # copy file with invalid src
    import tempfile

    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    with pytest.raises(Exception) as e:
        src = "tests/test-images/wedding_DOES_NOT_EXIST.jpg"
        assert FileUtil.copy(src, temp_dir.name)
    assert e.type == OSError


def test_copy_file_valid_shutil():
    # copy file with valid src, dest with the shutil implementation
    import os.path
    import tempfile

    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    result = FileUtilShUtil.copy(src, temp_dir.name)
    assert result
    assert os.path.isfile(os.path.join(temp_dir.name, "wedding.jpg"))


def test_copy_file_invalid_shutil():
    # copy file with invalid src with the shutil implementation
    import tempfile

    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    with pytest.raises(Exception) as e:
        src = "tests/test-images/wedding_DOES_NOT_EXIST.jpg"
        assert FileUtilShUtil.copy(src, temp_dir.name)
    assert e.type == OSError


def test_hardlink_file_valid():
    # hardlink file with valid src, dest
    import os.path
    import tempfile

    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    src2 = os.path.join(temp_dir.name, "wedding_src.jpg")
    dest = os.path.join(temp_dir.name, "wedding.jpg")
    FileUtil.copy(src, src2)
    FileUtil.hardlink(src2, dest)
    assert os.path.isfile(dest)
    assert os.path.samefile(src2, dest)


def test_unlink_file():
    import os.path
    import tempfile

    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    dest = os.path.join(temp_dir.name, "wedding.jpg")
    result = FileUtil.copy(src, temp_dir.name)
    assert os.path.isfile(dest)
    FileUtil.unlink(dest)
    assert not os.path.isfile(dest)


def test_rmdir():
    import os.path
    import tempfile

    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dir_name = temp_dir.name
    assert os.path.isdir(dir_name)
    FileUtil.rmdir(dir_name)
    assert not os.path.isdir(dir_name)


def test_makedirs():
    import os.path
    import tempfile

    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    new_dir = os.path.join(temp_dir.name, "folder1/subfolder1.1/subfolder1.1.1")

    assert not os.path.isdir(new_dir)
    FileUtil.makedirs(new_dir)
    assert os.path.isdir(new_dir)


def test_makedirs_retry(monkeypatch):
    """Test that makedirs is retried on transient failure (uses tenacity retry)."""
    import tempfile

    from osxphotos.fileutil import FileUtil

    # make sure retry is enabled
    cfg_fileutil_retry(
        retry_enabled=True, retries=3, nas_export_alias="nas_export.alias"
    )

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    new_dir = os.path.join(temp_dir.name, "folder_retry/sub1/sub2")

    # track attempts
    attempts = {"count": 0}
    original_makedirs = os.makedirs

    def fake_makedirs(path, mode=511, exist_ok=False):
        attempts["count"] += 1
        # fail the first attempt, succeed thereafter
        if attempts["count"] < 2:
            raise PermissionError("simulated transient PermissionError")
            # raise OSError("simulated transient OSError")
        return original_makedirs(path, mode=mode, exist_ok=exist_ok)

    # patch the subprocess.call used by open_alias_script to avoid running osascript
    monkeypatch.setattr("osxphotos.fileutil.subprocess.call", lambda *a, **k: 0)

    # replace os.makedirs with our flaky version
    monkeypatch.setattr(os, "makedirs", fake_makedirs)
    # avoid actual sleeping between retries
    monkeypatch.setattr(time, "sleep", lambda s: None)

    assert not os.path.isdir(new_dir)
    FileUtil.makedirs(new_dir)
    assert os.path.isdir(new_dir)
    # ensure it was attempted at least twice (one failure + one success)
    assert attempts["count"] >= 2


def test_makedirs_retry_not_macos(monkeypatch):
    """Test that makedirs is retried but alias mount is not attempted, on transient failure (uses tenacity retry)."""
    import tempfile

    from osxphotos.fileutil import FileUtil

    # make sure retry is enabled
    cfg_fileutil_retry(
        retry_enabled=True, retries=3, nas_export_alias="nas_export.alias"
    )
    monkeypatch.setattr("osxphotos.fileutil.is_macos", False)
    monkeypatch.setattr("osxphotos.platform.is_macos", False)
    monkeypatch.setattr("osxphotos.cli.common.is_macos", False)

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    new_dir = os.path.join(temp_dir.name, "folder_retry/sub1/sub2")

    # track attempts
    attempts = {"count": 0}
    original_makedirs = os.makedirs

    def fake_makedirs(path, mode=511, exist_ok=False):
        attempts["count"] += 1
        # fail the first attempt, succeed thereafter
        if attempts["count"] < 4:
            raise PermissionError("simulated transient PermissionError")
            # raise OSError("simulated transient OSError")
        return original_makedirs(path, mode=mode, exist_ok=exist_ok)

    # patch the subprocess.call used by open_alias_script to avoid running osascript
    monkeypatch.setattr("osxphotos.fileutil.subprocess.call", lambda *a, **k: 0)

    # replace os.makedirs with our flaky version
    monkeypatch.setattr(os, "makedirs", fake_makedirs)
    # avoid actual sleeping between retries
    monkeypatch.setattr(time, "sleep", lambda s: None)

    assert not os.path.isdir(new_dir)
    with pytest.raises(PermissionError) as exc_info:
        FileUtil.makedirs(new_dir)
    assert "simulated transient PermissionError" in str(exc_info.value)

    # assert os.path.isdir(new_dir)
    # no retry, so it was attempted only once
    assert attempts["count"] == 3


def test_makedirs_retry_empty_retry_nas_alias(monkeypatch):
    """Test that makedirs is retried but alias mount is not attempted (because
    --retry-nas-alias is empty) on transient failure (uses tenacity retry)."""
    import tempfile

    from osxphotos.fileutil import FileUtil

    # test for macOS and non-macOS
    for macos in (True, False):
        # make sure retry is enabled and test empty --retry-nas-alias
        cfg_fileutil_retry(retry_enabled=True, retries=2, nas_export_alias="")
        monkeypatch.setattr("osxphotos.fileutil.is_macos", macos)
        monkeypatch.setattr("osxphotos.platform.is_macos", macos)
        monkeypatch.setattr("osxphotos.cli.common.is_macos", macos)

        temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
        new_dir = os.path.join(temp_dir.name, "folder_retry/sub1/sub2")

        # track attempts
        attempts = {"count": 0}
        original_makedirs = os.makedirs

        def fake_makedirs(path, mode=511, exist_ok=False):
            attempts["count"] += 1
            # fail the first attempt, succeed thereafter
            if attempts["count"] < 3:
                raise PermissionError("simulated transient PermissionError")
                # raise OSError("simulated transient OSError")
            return original_makedirs(path, mode=mode, exist_ok=exist_ok)

        # patch the subprocess.call used by open_alias_script to avoid running osascript
        monkeypatch.setattr("osxphotos.fileutil.subprocess.call", lambda *a, **k: 0)

        # replace os.makedirs with our flaky version
        monkeypatch.setattr(os, "makedirs", fake_makedirs)
        # avoid actual sleeping between retries
        monkeypatch.setattr(time, "sleep", lambda s: None)

        assert not os.path.isdir(new_dir)
        with pytest.raises(PermissionError) as exc_info:
            FileUtil.makedirs(new_dir)
        assert "simulated transient PermissionError" in str(exc_info.value)

        # assert os.path.isdir(new_dir)
        # no retry, so it was attempted only once
        assert attempts["count"] == 2


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_CONVERT" not in os.environ,
    reason="Skip if running in Github actions, no GPU.",
)
def test_convert_to_jpeg():
    """test convert_to_jpeg"""
    import pathlib
    import tempfile

    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    with temp_dir:
        imgfile = pathlib.Path(TEST_HEIC)
        outfile = pathlib.Path(temp_dir.name) / f"{imgfile.stem}.jpeg"
        assert FileUtil.convert_to_jpeg(imgfile, outfile)
        assert outfile.is_file()


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_CONVERT" not in os.environ,
    reason="Skip if running in Github actions, no GPU.",
)
def test_convert_to_jpeg_quality():
    """test convert_to_jpeg with compression_quality"""
    import pathlib
    import tempfile

    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    with temp_dir:
        imgfile = pathlib.Path(TEST_RAW)
        outfile = pathlib.Path(temp_dir.name) / f"{imgfile.stem}.jpeg"
        assert FileUtil.convert_to_jpeg(imgfile, outfile, compression_quality=0.1)
        assert outfile.is_file()
        assert outfile.stat().st_size < 1000000


def test_rename_file():
    # rename file with valid src, dest
    import pathlib
    import tempfile

    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    dest = f"{temp_dir.name}/foo.jpg"
    dest2 = f"{temp_dir.name}/bar.jpg"
    FileUtil.copy(src, dest)
    result = FileUtil.rename(dest, dest2)
    assert result
    assert pathlib.Path(dest2).exists()
    assert not pathlib.Path(dest).exists()


def test_tempdir():
    """Test FileUtil.tmpdir"""
    tmpdir = FileUtil.tmpdir()
    assert pathlib.Path(tmpdir.name).is_dir()


def test_tempdir_context_mgr():
    """Test Fileutil.tmpdir as context manager"""
    with FileUtil.tmpdir() as tmpdir_name:
        assert pathlib.Path(tmpdir_name).is_dir()
    assert not pathlib.Path(tmpdir_name).is_dir()


def test_fileutil_utime():
    """Test FileUtil.utime method"""
    import tempfile

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    dest = os.path.join(temp_dir.name, "wedding_utime.jpg")

    # Copy a test file
    FileUtil.copy(src, dest)

    # Get original times
    original_stat = os.stat(dest)
    original_atime = original_stat.st_atime
    original_mtime = original_stat.st_mtime

    # Set new times (1 hour ago)
    new_time = time.time() - 3600
    new_times = (new_time, new_time)

    # Update times using FileUtil.utime
    result = FileUtil.utime(dest, new_times)

    # Verify times were updated
    updated_stat = os.stat(dest)
    assert abs(updated_stat.st_atime - new_time) < 1.0  # Allow small tolerance
    assert abs(updated_stat.st_mtime - new_time) < 1.0  # Allow small tolerance

    # Verify times are different from original
    assert abs(updated_stat.st_atime - original_atime) > 1.0
    assert abs(updated_stat.st_mtime - original_mtime) > 1.0


@pytest.mark.skipif(not is_macos, reason="Only runs on macOS")
def test_fileutil_macos_utime():
    """Test FileUtilMacOS.utime method"""
    import tempfile

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    dest = os.path.join(temp_dir.name, "wedding_utime_macos.jpg")

    # Copy a test file
    FileUtil.copy(src, dest)

    # Get original times
    original_stat = os.stat(dest)
    original_atime = original_stat.st_atime
    original_mtime = original_stat.st_mtime

    # Set new times (2 hours ago)
    new_time = time.time() - 7200
    new_times = (new_time, new_time)

    # Update times using FileUtilMacOS.utime
    result = FileUtilMacOS.utime(dest, new_times)

    # Verify times were updated
    updated_stat = os.stat(dest)
    assert abs(updated_stat.st_atime - new_time) < 1.0  # Allow small tolerance
    assert abs(updated_stat.st_mtime - new_time) < 1.0  # Allow small tolerance

    # Verify times are different from original
    assert abs(updated_stat.st_atime - original_atime) > 1.0
    assert abs(updated_stat.st_mtime - original_mtime) > 1.0


def test_fileutil_utime_with_pathlib():
    """Test FileUtil.utime method with pathlib.Path"""
    import tempfile

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = pathlib.Path("tests/test-images/wedding.jpg")
    dest = pathlib.Path(temp_dir.name) / "wedding_utime_pathlib.jpg"

    # Copy a test file
    FileUtil.copy(src, dest)

    # Get original times
    original_stat = dest.stat()
    original_atime = original_stat.st_atime
    original_mtime = original_stat.st_mtime

    # Set new times (30 minutes ago)
    new_time = time.time() - 1800
    new_times = (new_time, new_time)

    # Update times using FileUtil.utime with pathlib.Path
    result = FileUtil.utime(dest, new_times)

    # Verify times were updated
    updated_stat = dest.stat()
    assert abs(updated_stat.st_atime - new_time) < 1.0  # Allow small tolerance
    assert abs(updated_stat.st_mtime - new_time) < 1.0  # Allow small tolerance

    # Verify times are different from original
    assert abs(updated_stat.st_atime - original_atime) > 1.0
    assert abs(updated_stat.st_mtime - original_mtime) > 1.0
