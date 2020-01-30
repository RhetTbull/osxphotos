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
