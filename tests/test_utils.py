"""Test osxphotos.utils"""

import pathlib
import tempfile

import pytest

import osxphotos

UTI_DICT = {"public.jpeg": "jpeg", "com.canon.cr2-raw-image": "cr2"}

from osxphotos.utils import (
    _dd_to_dms,
    increment_filename,
    increment_filename_with_count,
    list_directory,
    shortuuid_to_uuid,
    uuid_to_shortuuid,
)


def test_dd_to_dms():
    # expands coverage for edge case in _dd_to_dms

    assert _dd_to_dms(-0.001) == (0, 0, -3.6)


@pytest.mark.skip(reason="Fails on some machines")
def test_get_system_library_path():
    _, major, _ = osxphotos.utils._get_os_version()
    if int(major) < 15:
        assert osxphotos.utils.get_system_library_path() is None
    else:
        assert osxphotos.utils.get_system_library_path() is not None


def test_list_directory():
    """test list_directory"""

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    temp_dir_name = pathlib.Path(temp_dir.name)
    file1 = (temp_dir_name / "file1.jpg").touch()
    file2 = (temp_dir_name / "File2.JPG").touch()
    file3 = (temp_dir_name / "File.png").touch()
    file4 = (temp_dir_name / "document.pdf").touch()

    files = list_directory(temp_dir.name, glob="*.jpg")
    assert len(files) == 2
    assert "file1.jpg" in files
    assert "File2.JPG" in files
    assert isinstance(files[0], str)

    files = list_directory(temp_dir.name, glob="*.jpg", case_sensitive=True)
    assert len(files) == 1
    assert "file1.jpg" in files

    files = list_directory(temp_dir.name, startswith="file")
    assert len(files) == 3

    files = list_directory(temp_dir.name, endswith="jpg")
    assert len(files) == 2

    files = list_directory(temp_dir.name, contains="doc")
    assert len(files) == 1
    assert "document.pdf" in files

    files = list_directory(temp_dir.name, startswith="File", case_sensitive=True)
    assert len(files) == 2

    files = list_directory(temp_dir.name, startswith="File", case_sensitive=False)
    assert len(files) == 3

    files = list_directory(temp_dir.name, startswith="document", include_path=True)
    assert len(files) == 1
    assert files[0] == str(pathlib.Path(temp_dir.name) / "document.pdf")

    # test pathlib.Path
    files = list_directory(temp_dir_name, glob="*.jpg")
    assert isinstance(files[0], pathlib.Path)

    files = list_directory(temp_dir.name, glob="FooBar*.jpg")
    assert not files


def test_list_directory_invalid():
    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    files = list_directory(f"{temp_dir.name}/no_such_dir", glob="*.jpg")
    assert len(files) == 0


def test_increment_filename():
    # test that increment_filename works

    with tempfile.TemporaryDirectory(prefix="osxphotos_") as temp_dir:
        temp_dir = pathlib.Path(temp_dir)
        filename = str(temp_dir / "file.jpg")
        assert increment_filename(filename) == str(temp_dir / "file.jpg")

        new_file = temp_dir / "file.jpg"
        new_file.touch()
        assert increment_filename(filename) == str(temp_dir / "file (1).jpg")

        # test pathlib.Path as argument
        assert increment_filename(pathlib.Path(filename)) == str(
            temp_dir / "file (1).jpg"
        )

        new_file = temp_dir / "file (1).jpg"
        new_file.touch()
        assert increment_filename(filename) == str(temp_dir / "file (2).jpg")

        # test increment_filename_with_count
        filename = str(temp_dir / "file2.jpg")
        assert increment_filename_with_count(filename, count=2) == (
            str(temp_dir / "file2 (2).jpg"),
            2,
        )
        new_file = temp_dir / "file2 (2).jpg"
        new_file.touch()
        assert increment_filename_with_count(filename, count=2) == (
            str(temp_dir / "file2 (3).jpg"),
            3,
        )


def test_increment_filename_with_lock():
    # test that increment_filename works with lock=True

    with tempfile.TemporaryDirectory(prefix="osxphotos_") as temp_dir:
        temp_dir = pathlib.Path(temp_dir)
        filename = str(temp_dir / "file.jpg")
        assert increment_filename(filename, lock=True) == str(temp_dir / "file.jpg")

        new_file = temp_dir / "file.jpg"
        new_file.touch()
        assert increment_filename(filename, lock=True) == str(temp_dir / "file (1).jpg")

        # test increment_filename_with_count
        filename = str(temp_dir / "file2.jpg")
        assert increment_filename_with_count(filename, count=2, lock=True) == (
            str(temp_dir / "file2 (2).jpg"),
            2,
        )
        new_file = temp_dir / "file2 (2).jpg"
        new_file.touch()
        assert increment_filename_with_count(filename, count=2, lock=True) == (
            str(temp_dir / "file2 (3).jpg"),
            3,
        )


@pytest.mark.skip(reason="Lock files not yet implemented")
def test_increment_filename_with_lock_exists():
    # test that increment_filename works with lock=True when lock file already exists

    with tempfile.TemporaryDirectory(prefix="osxphotos_") as temp_dir:
        temp_dir = pathlib.Path(temp_dir)
        filename = str(temp_dir / "file.jpg")
        pathlib.Path(f"{filename}.osxphotos.lock").touch()
        assert increment_filename(filename, lock=True) == str(temp_dir / "file (1).jpg")


def test_shortuuid_uuid():
    """Test shortuuid_to_uuid and uuid_to_shortuuid"""
    uuid = "5CF8D91E-DCEB-4CC3-BFF7-920B05564EB0"
    shortuuid = "JYsxugP9UjetmCbBCHXcmu"
    assert uuid_to_shortuuid(uuid) == shortuuid
    assert shortuuid_to_uuid(shortuuid) == uuid
