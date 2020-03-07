import pytest
from osxphotos.exiftool import get_exiftool_path

TEST_FILE_ONE_KEYWORD = "tests/test-images/wedding.jpg"
TEST_FILE_MULTI_KEYWORD = "tests/test-images/Tulips.jpg"
TEST_MULTI_KEYWORDS = [
    "Top Shot",
    "flowers",
    "flower",
    "design",
    "Stock Photography",
    "vibrant",
    "plastic",
    "Digital Nomad",
    "close up",
    "stock photo",
    "outdoor",
    "wedding",
    "Reiseblogger",
    "fake",
    "colorful",
    "Indoor",
    "display",
    "photography",
]

try:
    exiftool = get_exiftool_path()
except:
    exiftool = None

if exiftool is None:
    pytest.skip("could not find exiftool in path", allow_module_level=True)


def test_get_exiftool_path():
    import osxphotos.exiftool

    exiftool = osxphotos.exiftool.get_exiftool_path()
    assert exiftool is not None


def test_version():
    import osxphotos.exiftool

    exif = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    assert exif.version is not None
    assert isinstance(exif.version, str)


def test_read():
    import osxphotos.exiftool

    exif = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    assert exif.data["File:MIMEType"] == "image/jpeg"
    assert exif.data["EXIF:ISO"] == 160
    assert exif.data["IPTC:Keywords"] == "wedding"


def test_setvalue_1():
    # test setting a tag value
    import os.path
    import tempfile
    from osxphotos.utils import _copy_file
    import osxphotos.exiftool

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    _copy_file(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    exif.setvalue("IPTC:Keywords", "test")
    exif._read_exif()
    assert exif.data["IPTC:Keywords"] == "test"


def test_clear_value():
    # test clearing a tag value
    import os.path
    import tempfile
    from osxphotos.utils import _copy_file
    import osxphotos.exiftool

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    _copy_file(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    assert "IPTC:Keywords" in exif.data

    exif.setvalue("IPTC:Keywords", None)
    exif._read_exif()
    assert "IPTC:Keywords" not in exif.data


def test_addvalues_1():
    # test setting a tag value
    import os.path
    import tempfile
    from osxphotos.utils import _copy_file
    import osxphotos.exiftool

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    _copy_file(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    exif.addvalues("IPTC:Keywords", "test")
    exif._read_exif()
    assert sorted(exif.data["IPTC:Keywords"]) == sorted(["wedding", "test"])


def test_addvalues_2():
    # test setting a tag value where multiple values already exist
    import os.path
    import tempfile
    from osxphotos.utils import _copy_file
    import osxphotos.exiftool

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_MULTI_KEYWORD))
    _copy_file(TEST_FILE_MULTI_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    assert sorted(exif.data["IPTC:Keywords"]) == sorted(TEST_MULTI_KEYWORDS)
    exif.addvalues("IPTC:Keywords", "test")
    exif._read_exif()
    assert "IPTC:Keywords" in exif.data
    test_multi = TEST_MULTI_KEYWORDS.copy()
    test_multi.append("test")
    assert sorted(exif.data["IPTC:Keywords"]) == sorted(test_multi)


def test_singleton():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    exif2 = osxphotos.exiftool.ExifTool(TEST_FILE_MULTI_KEYWORD)

    assert exif1._process.pid == exif2._process.pid


def test_pid():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    assert exif1.pid == exif1._process.pid


def test_exiftoolproc_process():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    assert exif1._exiftoolproc.process is not None


def test_exiftoolproc_exiftool():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    assert exif1._exiftoolproc.exiftool == osxphotos.exiftool.get_exiftool_path()


def test_json():
    import osxphotos.exiftool
    import json

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    json1 = exif1.json()
    assert json1[0]["XMP:TagsList"] == "wedding"


def test_str():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    assert "file: " in str(exif1)
    assert "exiftool: " in str(exif1)
