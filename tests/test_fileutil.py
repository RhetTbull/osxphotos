""" test FileUtil """

import pytest


def test_copy_file_valid():
    # copy file with valid src, dest
    import os.path
    import tempfile
    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    result = FileUtil.copy(src, temp_dir.name)
    assert result == 0
    assert os.path.isfile(os.path.join(temp_dir.name, "wedding.jpg"))


def test_copy_file_invalid():
    # copy file with invalid src
    import tempfile
    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding_DOES_NOT_EXIST.jpg"
    with pytest.raises(Exception) as e:
        assert FileUtil.copy(src, temp_dir.name)
    assert e.type == FileNotFoundError


def test_copy_file_norsrc():
    # copy file with --norsrc
    import os.path
    import tempfile
    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    result = FileUtil.copy(src, temp_dir.name, norsrc=True)
    assert result == 0
    assert os.path.isfile(os.path.join(temp_dir.name, "wedding.jpg"))


def test_hardlink_file_valid():
    # hardlink file with valid src, dest
    import os.path
    import tempfile
    from osxphotos.fileutil import FileUtil

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    dest = os.path.join(temp_dir.name, "wedding.jpg")
    FileUtil.hardlink(src, dest)
    assert os.path.isfile(dest)
    assert os.path.samefile(src, dest)


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
