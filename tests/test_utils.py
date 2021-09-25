import pytest

DB_LOCKED_10_12 = "./tests/Test-Lock-10_12.photoslibrary/database/photos.db"
DB_LOCKED_10_15 = "./tests/Test-Lock-10_15_1.photoslibrary/database/Photos.sqlite"
DB_UNLOCKED_10_15 = "./tests/Test-10.15.1.photoslibrary/database/photos.db"

UTI_DICT = {"public.jpeg": "jpeg", "com.canon.cr2-raw-image": "cr2"}


def test_debug_enable():
    import logging

    import osxphotos

    osxphotos._set_debug(True)
    logger = osxphotos._get_logger()
    assert logger.isEnabledFor(logging.DEBUG)


def test_debug_disable():
    import logging

    import osxphotos

    osxphotos._set_debug(False)
    logger = osxphotos._get_logger()
    assert not logger.isEnabledFor(logging.DEBUG)


def test_dd_to_dms():
    # expands coverage for edge case in _dd_to_dms
    from osxphotos.utils import _dd_to_dms

    assert _dd_to_dms(-0.001) == (0, 0, -3.6)


@pytest.mark.skip(reason="Fails on some machines")
def test_get_system_library_path():
    import osxphotos

    _, major, _ = osxphotos.utils._get_os_version()
    if int(major) < 15:
        assert osxphotos.utils.get_system_library_path() is None
    else:
        assert osxphotos.utils.get_system_library_path() is not None


def test_db_is_locked_locked():
    import osxphotos

    assert osxphotos.utils._db_is_locked(DB_LOCKED_10_12)
    assert osxphotos.utils._db_is_locked(DB_LOCKED_10_15)


def test_db_is_locked_unlocked():
    import osxphotos

    assert not osxphotos.utils._db_is_locked(DB_UNLOCKED_10_15)


def test_findfiles():
    import os.path
    import tempfile

    from osxphotos.utils import findfiles

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    fd = open(os.path.join(temp_dir.name, "file1.jpg"), "w+")
    fd.close
    fd = open(os.path.join(temp_dir.name, "file2.JPG"), "w+")
    fd.close
    files = findfiles("*.jpg", temp_dir.name)
    assert len(files) == 2
    assert "file1.jpg" in files
    assert "file2.JPG" in files


def test_findfiles_invalid_dir():
    import tempfile

    from osxphotos.utils import findfiles

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    files = findfiles("*.jpg", f"{temp_dir.name}/no_such_dir")
    assert len(files) == 0


def test_increment_filename():
    # test that increment_filename works
    import pathlib
    import tempfile

    from osxphotos.utils import increment_filename, increment_filename_with_count

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
