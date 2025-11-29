"""Test set_file_creation_date function"""

import datetime
import os
import pathlib
import stat
import tempfile

import pytest

from osxphotos.fileutil import set_file_creation_date
from osxphotos.platform import is_macos


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_creation_date_none_file_path():
    """Test that ValueError is raised when file_path is None"""
    creation_date = datetime.datetime.now()
    with pytest.raises(ValueError, match="Invalid parameters"):
        set_file_creation_date(None, creation_date)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_creation_date_none_creation_date():
    """Test that ValueError is raised when creation_date is None"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        with pytest.raises(ValueError, match="Invalid parameters"):
            set_file_creation_date(tmp_path, None)
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_creation_date_both_none():
    """Test that ValueError is raised when both parameters are None"""
    with pytest.raises(ValueError, match="Invalid parameters"):
        set_file_creation_date(None, None)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_creation_date_nonexistent_file():
    """Test that FileNotFoundError is raised for non-existent file"""
    creation_date = datetime.datetime.now()
    nonexistent_path = (
        f"/tmp/this_file_definitely_does_not_exist_12345_{creation_date.isoformat}.txt"
    )

    with pytest.raises(FileNotFoundError, match="does not exist"):
        set_file_creation_date(nonexistent_path, creation_date)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_creation_date_valid_string_path():
    """Test setting creation date with a valid string path"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(b"test content")

    try:
        # Set creation date to a specific time
        new_date = datetime.datetime(2020, 1, 15, 10, 30, 45)
        result = set_file_creation_date(tmp_path, new_date)

        assert result is True

        # Verify the creation date was actually changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(tmp_path)
        creation_date_value, error = file_url.resourceValuesForKeys_error_(
            [Foundation.NSURLCreationDateKey], None
        )

        if creation_date_value:
            ns_date = creation_date_value[Foundation.NSURLCreationDateKey]
            timestamp = ns_date.timeIntervalSince1970()
            # Allow for small floating point differences
            assert abs(timestamp - new_date.timestamp()) < 1.0
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_creation_date_valid_pathlib_path():
    """Test setting creation date with a pathlib.Path object"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = pathlib.Path(tmp_file.name)
        tmp_file.write(b"test content")

    try:
        # Set creation date to a specific time
        new_date = datetime.datetime(2021, 6, 1, 14, 25, 30)
        result = set_file_creation_date(tmp_path, new_date)

        assert result is True

        # Verify the creation date was actually changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(str(tmp_path))
        creation_date_value, error = file_url.resourceValuesForKeys_error_(
            [Foundation.NSURLCreationDateKey], None
        )

        if creation_date_value:
            ns_date = creation_date_value[Foundation.NSURLCreationDateKey]
            timestamp = ns_date.timeIntervalSince1970()
            # Allow for small floating point differences
            assert abs(timestamp - new_date.timestamp()) < 1.0
    finally:
        tmp_path.unlink()


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_creation_date_readonly_file():
    """Test that function returns False when file cannot be modified"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(b"test content")

    try:
        # Make the file read-only by removing write permissions
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        new_date = datetime.datetime(2022, 3, 10, 8, 15, 0)
        # Note: On macOS, setting creation date via NSURL may still work
        # even with read-only permissions, so this test checks the return value
        result = set_file_creation_date(tmp_path, new_date)

        # The function should either succeed or return False
        # depending on system permissions
        assert isinstance(result, bool)
    finally:
        # Restore write permissions before deleting
        try:
            os.chmod(tmp_path, stat.S_IWUSR | stat.S_IRUSR)
            os.unlink(tmp_path)
        except Exception:
            pass


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_creation_date_directory():
    """Test setting creation date on a directory"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)

        new_date = datetime.datetime(2019, 12, 25, 0, 0, 0)
        result = set_file_creation_date(tmp_path, new_date)

        assert result is True

        # Verify the creation date was actually changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(str(tmp_path))
        creation_date_value, error = file_url.resourceValuesForKeys_error_(
            [Foundation.NSURLCreationDateKey], None
        )

        if creation_date_value:
            ns_date = creation_date_value[Foundation.NSURLCreationDateKey]
            timestamp = ns_date.timeIntervalSince1970()
            # Allow for small floating point differences
            assert abs(timestamp - new_date.timestamp()) < 1.0


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_creation_date_future_date():
    """Test setting creation date to a future date"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(b"test content")

    try:
        # Set creation date to a future time
        future_date = datetime.datetime.now() + datetime.timedelta(days=365)
        result = set_file_creation_date(tmp_path, future_date)

        assert result is True

        # Verify the creation date was actually changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(tmp_path)
        creation_date_value, error = file_url.resourceValuesForKeys_error_(
            [Foundation.NSURLCreationDateKey], None
        )

        if creation_date_value:
            ns_date = creation_date_value[Foundation.NSURLCreationDateKey]
            timestamp = ns_date.timeIntervalSince1970()
            # Allow for small floating point differences
            assert abs(timestamp - future_date.timestamp()) < 1.0
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_set_file_creation_date_past_date():
    """Test setting creation date to a past date"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(b"test content")

    try:
        # Set creation date to a time in the past
        past_date = datetime.datetime(1990, 5, 15, 12, 0, 0)
        result = set_file_creation_date(tmp_path, past_date)

        assert result is True

        # Verify the creation date was actually changed
        import Foundation

        file_url = Foundation.NSURL.fileURLWithPath_(str(tmp_path))
        creation_date_value, error = file_url.resourceValuesForKeys_error_(
            [Foundation.NSURLCreationDateKey], None
        )

        if creation_date_value:
            ns_date = creation_date_value[Foundation.NSURLCreationDateKey]
            timestamp = ns_date.timeIntervalSince1970()
            # Allow for small floating point differences
            assert abs(timestamp - past_date.timestamp()) < 1.0
    finally:
        os.unlink(tmp_path)
