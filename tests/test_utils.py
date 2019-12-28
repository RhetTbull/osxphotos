import pytest


def test_debug_enable():
    import osxphotos
    import logging

    osxphotos._debug(True)
    logger = osxphotos._get_logger()
    logging.warning(logger)
    assert logger.isEnabledFor(logging.DEBUG)


def test_debug_disable():
    import osxphotos
    import logging

    osxphotos._debug(False)
    logger = osxphotos._get_logger()
    logging.warning(logger)
    assert not logger.isEnabledFor(logging.DEBUG)


def test_dd_to_dms():
    # expands coverage for edge case in _dd_to_dms
    from osxphotos.utils import _dd_to_dms

    assert _dd_to_dms(-0.001) == (0, 0, -3.6)


def test_get_system_library_path():
    import osxphotos

    _, major, _ = osxphotos.utils._get_os_version()
    if int(major) < 15:
        with pytest.raises(Exception):
            assert osxphotos.utils.get_system_library_path()
    else:
        assert osxphotos.utils.get_system_library_path() is not None

