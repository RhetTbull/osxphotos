import pytest

DB_LOCKED_10_12 = "./tests/Test-Lock-10_12.photoslibrary/database/photos.db"
DB_LOCKED_10_15 = "./tests/Test-Lock-10_15_1.photoslibrary/database/Photos.sqlite"
DB_UNLOCKED_10_15 = "./tests/Test-10.15.1.photoslibrary/database/photos.db"

UTI_DICT = {"public.jpeg": "jpeg", "com.canon.cr2-raw-image": "cr2"}


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


def test_get_preferred_uti_extension():
    from osxphotos.utils import get_preferred_uti_extension

    for uti, extension in UTI_DICT.items():
        assert get_preferred_uti_extension(uti) == extension


def test_findfiles():
    import tempfile
    import os.path
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
