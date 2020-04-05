import pytest

DB_LOCKED_10_12 = "./tests/Test-Lock-10_12.photoslibrary/database/photos.db"
DB_LOCKED_10_15 = "./tests/Test-Lock-10_15_1.photoslibrary/database/Photos.sqlite"
DB_UNLOCKED_10_15 = "./tests/Test-10.15.1.photoslibrary/database/photos.db"


def test_debug_enable():
    import osxphotos
    import logging

    osxphotos._set_debug(True)
    logger = osxphotos._get_logger()
    assert logger.isEnabledFor(logging.DEBUG)


def test_debug_disable():
    import osxphotos
    import logging

    osxphotos._set_debug(False)
    logger = osxphotos._get_logger()
    assert not logger.isEnabledFor(logging.DEBUG)


def test_dd_to_dms():
    # expands coverage for edge case in _dd_to_dms
    from osxphotos.utils import _dd_to_dms

    assert _dd_to_dms(-0.001) == (0, 0, -3.6)


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


def test_copy_file_valid():
    # _copy_file with valid src, dest
    import os.path
    import tempfile
    from osxphotos.utils import _copy_file

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    result = _copy_file(src, temp_dir.name)
    assert result == 0
    assert os.path.isfile(os.path.join(temp_dir.name, "wedding.jpg"))


def test_copy_file_invalid():
    # _copy_file with invalid src
    import tempfile
    from osxphotos.utils import _copy_file

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding_DOES_NOT_EXIST.jpg"
    with pytest.raises(Exception) as e:
        assert _copy_file(src, temp_dir.name)
    assert e.type == FileNotFoundError


def test_copy_file_norsrc():
    # _copy_file with --norsrc
    import os.path
    import tempfile
    from osxphotos.utils import _copy_file

    temp_dir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    src = "tests/test-images/wedding.jpg"
    result = _copy_file(src, temp_dir.name, norsrc=True)
    assert result == 0
    assert os.path.isfile(os.path.join(temp_dir.name, "wedding.jpg"))
