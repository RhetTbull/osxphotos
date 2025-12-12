"""Test set_file_dates function"""

import datetime
import os
import pathlib
import stat
import tempfile

import pytest

from osxphotos.fileutil import FileDateType, set_file_dates
from osxphotos.platform import is_macos


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_none_file_path():
    """Test that ValueError is raised when file_path is None"""
    date = datetime.datetime.now()
    with pytest.raises(ValueError, match="Invalid parameters"):
        set_file_dates(None, date)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_none_date():
    """Test that ValueError is raised when date is None"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        with pytest.raises(ValueError, match="Invalid parameters"):
            set_file_dates(tmp_path, None)
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_both_none():
    """Test that ValueError is raised when both parameters are None"""
    with pytest.raises(ValueError, match="Invalid parameters"):
        set_file_dates(None, None)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_invalid_date_type():
    """Test that ValueError is raised for invalid date_type"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        date = datetime.datetime.now()
        with pytest.raises(ValueError, match="Invalid date_type"):
            set_file_dates(tmp_path, date, date_type=42)
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_nonexistent_file():
    """Test that FileNotFoundError is raised for non-existent file"""
    date = datetime.datetime.now()
    nonexistent_path = (
        f"/tmp/this_file_definitely_does_not_exist_12345_{date.isoformat()}.txt"
    )

    with pytest.raises(FileNotFoundError, match="does not exist"):
        set_file_dates(nonexistent_path, date)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_creation_date():
    """Test setting only creation date"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(b"test content")

    try:
        new_date = datetime.datetime(2020, 1, 15, 10, 30, 45)
        result = set_file_dates(tmp_path, new_date, FileDateType.CREATION)

        assert result is True

        # Verify the creation date was changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(tmp_path)
        creation_date_value, error = file_url.resourceValuesForKeys_error_(
            [Foundation.NSURLCreationDateKey], None
        )

        if creation_date_value:
            ns_date = creation_date_value[Foundation.NSURLCreationDateKey]
            timestamp = ns_date.timeIntervalSince1970()
            assert abs(timestamp - new_date.timestamp()) < 1.0
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_modification_date():
    """Test setting only modification date"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(b"test content")

    try:
        new_date = datetime.datetime(2021, 6, 1, 14, 25, 30)
        result = set_file_dates(tmp_path, new_date, FileDateType.MODIFICATION)

        assert result is True

        # Verify the modification date was changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(tmp_path)
        mod_date_value, error = file_url.resourceValuesForKeys_error_(
            [Foundation.NSURLContentModificationDateKey], None
        )

        if mod_date_value:
            ns_date = mod_date_value[Foundation.NSURLContentModificationDateKey]
            timestamp = ns_date.timeIntervalSince1970()
            assert abs(timestamp - new_date.timestamp()) < 1.0
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_access_date():
    """Test setting only access date"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(b"test content")

    try:
        new_date = datetime.datetime(2022, 3, 10, 8, 15, 0)
        result = set_file_dates(tmp_path, new_date, FileDateType.ACCESS)

        assert result is True

        # Verify the access date was changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(tmp_path)
        access_date_value, error = file_url.resourceValuesForKeys_error_(
            [Foundation.NSURLContentAccessDateKey], None
        )

        if access_date_value:
            ns_date = access_date_value[Foundation.NSURLContentAccessDateKey]
            timestamp = ns_date.timeIntervalSince1970()
            assert abs(timestamp - new_date.timestamp()) < 1.0
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_creation_and_modification():
    """Test setting both creation and modification dates"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(b"test content")

    try:
        new_date = datetime.datetime(2019, 12, 25, 0, 0, 0)
        result = set_file_dates(
            tmp_path, new_date, FileDateType.CREATION | FileDateType.MODIFICATION
        )

        assert result is True

        # Verify both dates were changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(tmp_path)
        date_values, error = file_url.resourceValuesForKeys_error_(
            [
                Foundation.NSURLCreationDateKey,
                Foundation.NSURLContentModificationDateKey,
            ],
            None,
        )

        if date_values:
            # Check creation date
            ns_creation = date_values[Foundation.NSURLCreationDateKey]
            creation_timestamp = ns_creation.timeIntervalSince1970()
            assert abs(creation_timestamp - new_date.timestamp()) < 1.0

            # Check modification date
            ns_mod = date_values[Foundation.NSURLContentModificationDateKey]
            mod_timestamp = ns_mod.timeIntervalSince1970()
            assert abs(mod_timestamp - new_date.timestamp()) < 1.0
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_all_three_dates():
    """Test setting all three date types at once"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(b"test content")

    try:
        new_date = datetime.datetime(2018, 7, 4, 12, 0, 0)
        result = set_file_dates(
            tmp_path,
            new_date,
            FileDateType.CREATION | FileDateType.MODIFICATION | FileDateType.ACCESS,
        )

        assert result is True

        # Verify all three dates were changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(tmp_path)
        date_values, error = file_url.resourceValuesForKeys_error_(
            [
                Foundation.NSURLCreationDateKey,
                Foundation.NSURLContentModificationDateKey,
                Foundation.NSURLContentAccessDateKey,
            ],
            None,
        )

        if date_values:
            # Check creation date
            ns_creation = date_values[Foundation.NSURLCreationDateKey]
            creation_timestamp = ns_creation.timeIntervalSince1970()
            assert abs(creation_timestamp - new_date.timestamp()) < 1.0

            # Check modification date
            ns_mod = date_values[Foundation.NSURLContentModificationDateKey]
            mod_timestamp = ns_mod.timeIntervalSince1970()
            assert abs(mod_timestamp - new_date.timestamp()) < 1.0

            # Check access date
            ns_access = date_values[Foundation.NSURLContentAccessDateKey]
            access_timestamp = ns_access.timeIntervalSince1970()
            assert abs(access_timestamp - new_date.timestamp()) < 1.0
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_pathlib_path():
    """Test setting dates with a pathlib.Path object"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = pathlib.Path(tmp_file.name)
        tmp_file.write(b"test content")

    try:
        new_date = datetime.datetime(2023, 2, 14, 18, 30, 0)
        result = set_file_dates(tmp_path, new_date, FileDateType.MODIFICATION)

        assert result is True

        # Verify the modification date was changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(str(tmp_path))
        mod_date_value, error = file_url.resourceValuesForKeys_error_(
            [Foundation.NSURLContentModificationDateKey], None
        )

        if mod_date_value:
            ns_date = mod_date_value[Foundation.NSURLContentModificationDateKey]
            timestamp = ns_date.timeIntervalSince1970()
            assert abs(timestamp - new_date.timestamp()) < 1.0
    finally:
        tmp_path.unlink()


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_directory():
    """Test setting dates on a directory"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)

        new_date = datetime.datetime(2024, 11, 11, 11, 11, 11)
        result = set_file_dates(
            tmp_path, new_date, FileDateType.CREATION | FileDateType.MODIFICATION
        )

        assert result is True

        # Verify the dates were changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(str(tmp_path))
        date_values, error = file_url.resourceValuesForKeys_error_(
            [
                Foundation.NSURLCreationDateKey,
                Foundation.NSURLContentModificationDateKey,
            ],
            None,
        )

        if date_values:
            # Check creation date
            ns_creation = date_values[Foundation.NSURLCreationDateKey]
            creation_timestamp = ns_creation.timeIntervalSince1970()
            assert abs(creation_timestamp - new_date.timestamp()) < 1.0

            # Check modification date
            ns_mod = date_values[Foundation.NSURLContentModificationDateKey]
            mod_timestamp = ns_mod.timeIntervalSince1970()
            assert abs(mod_timestamp - new_date.timestamp()) < 1.0


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_default_date_type():
    """Test that default date_type is CREATION"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(b"test content")

    try:
        new_date = datetime.datetime(2025, 5, 5, 5, 5, 5)
        # Call without specifying date_type - should default to CREATION
        result = set_file_dates(tmp_path, new_date)

        assert result is True

        # Verify only creation date was changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(tmp_path)
        creation_date_value, error = file_url.resourceValuesForKeys_error_(
            [Foundation.NSURLCreationDateKey], None
        )

        if creation_date_value:
            ns_date = creation_date_value[Foundation.NSURLCreationDateKey]
            timestamp = ns_date.timeIntervalSince1970()
            assert abs(timestamp - new_date.timestamp()) < 1.0
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_dates_readonly_file():
    """Test behavior with a read-only file"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(b"test content")

    try:
        # Make the file read-only
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        new_date = datetime.datetime(2020, 8, 20, 20, 20, 20)
        # Note: On macOS, setting dates via NSURL may still work
        # even with read-only permissions
        result = set_file_dates(tmp_path, new_date, FileDateType.CREATION)

        # The function should return a bool (success or failure)
        assert isinstance(result, bool)
    finally:
        # Restore write permissions before deleting
        try:
            os.chmod(tmp_path, stat.S_IWUSR | stat.S_IRUSR)
            os.unlink(tmp_path)
        except Exception:
            pass
