""" test FileUtil """

import os
import pathlib

import pytest

from osxphotos.fileutil import FileUtil, FileUtilShUtil

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
