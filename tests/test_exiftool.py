import json
import os

import pytest

from osxphotos.exiftool import get_exiftool_path, unescape_str

TEST_FILE_ONE_KEYWORD = "tests/test-images/wedding.jpg"
TEST_FILE_BAD_IMAGE = "tests/test-images/badimage.jpeg"
TEST_FILE_WARNING = "tests/test-images/exiftool_warning.heic"
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

PHOTOS_DB = "tests/Test-10.15.4.photoslibrary"
EXIF_UUID = {
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4": {
        "EXIF:DateTimeOriginal": "2019:07:04 16:24:01",
        "EXIF:LensModel": "XF18-55mmF2.8-4 R LM OIS",
        "IPTC:Keywords": [
            "Digital Nomad",
            "Indoor",
            "Reiseblogger",
            "Stock Photography",
            "Top Shot",
            "close up",
            "colorful",
            "design",
            "display",
            "fake",
            "flower",
            "outdoor",
            "photography",
            "plastic",
            "stock photo",
            "vibrant",
        ],
        "IPTC:DocumentNotes": "https://flickr.com/e/l7FkSm4f2lQkSV3CG6xlv8Sde5uF3gVu4Hf0Qk11AnU%3D",
    },
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": {
        "EXIF:Make": "NIKON CORPORATION",
        "EXIF:Model": "NIKON D810",
        "IPTC:DateCreated": "2019:04:15",
    },
}
EXIF_UUID_NO_GROUPS = {
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4": {
        "DateTimeOriginal": "2019:07:04 16:24:01",
        "LensModel": "XF18-55mmF2.8-4 R LM OIS",
        "Keywords": [
            "Digital Nomad",
            "Indoor",
            "Reiseblogger",
            "Stock Photography",
            "Top Shot",
            "close up",
            "colorful",
            "design",
            "display",
            "fake",
            "flower",
            "outdoor",
            "photography",
            "plastic",
            "stock photo",
            "vibrant",
        ],
        "DocumentNotes": "https://flickr.com/e/l7FkSm4f2lQkSV3CG6xlv8Sde5uF3gVu4Hf0Qk11AnU%3D",
    },
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": {
        "Make": "NIKON CORPORATION",
        "Model": "NIKON D810",
        "DateCreated": "2019:04:15",
    },
}
EXIF_UUID_NONE = ["A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"]

QUOTED_JSON_BYTES = b'[{"ExifTool:ExifToolVersion": 12.37,"ExifTool:Now": "2022:02:22 18:14:31+00:00","ExifTool:NewGUID": "20220222181431005A76C1A4B4D508A2","ExifTool:FileSequence": 0,"ExifTool:Warning": "Error running &quot;xattr&quot; to extract XAttr tags","ExifTool:ProcessingTime": 0.157028}]'
QUOTED_JSON_STRING_UNESCAPED = '[{"ExifTool:ExifToolVersion": 12.37,"ExifTool:Now": "2022:02:22 18:14:31+00:00","ExifTool:NewGUID": "20220222181431005A76C1A4B4D508A2","ExifTool:FileSequence": 0,"ExifTool:Warning": "Error running \\"xattr\\" to extract XAttr tags","ExifTool:ProcessingTime": 0.157028}]'
QUOTED_JSON_LOADED = [
    {
        "ExifTool:ExifToolVersion": 12.37,
        "ExifTool:Now": "2022:02:22 18:14:31+00:00",
        "ExifTool:NewGUID": "20220222181431005A76C1A4B4D508A2",
        "ExifTool:FileSequence": 0,
        "ExifTool:Warning": 'Error running "xattr" to extract XAttr tags',
        "ExifTool:ProcessingTime": 0.157028,
    }
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

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    exif.setvalue("IPTC:Keywords", "test")
    assert not exif.error

    exif._read_exif()
    assert exif.data["IPTC:Keywords"] == "test"


def test_setvalue_multiline():
    # test setting a tag value with embedded newline
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    exif.setvalue("EXIF:ImageDescription", "multi\nline")
    assert not exif.error

    exif._read_exif()
    assert exif.data["EXIF:ImageDescription"] == "multi\nline"


def test_setvalue_non_alphanumeric_chars():
    # test setting a tag value non-alphanumeric characters
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    exif.setvalue("EXIF:ImageDescription", "<hello>{world}$bye#foo%bar")
    assert not exif.error

    exif._read_exif()
    assert exif.data["EXIF:ImageDescription"] == "<hello>{world}$bye#foo%bar"


def test_setvalue_warning():
    # test setting illegal tag value generates warning
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    exif.setvalue("IPTC:Foo", "test")
    assert exif.warning


def test_setvalue_error():
    # test setting tag on bad image generates error
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_BAD_IMAGE))
    FileUtil.copy(TEST_FILE_BAD_IMAGE, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    exif.setvalue("IPTC:Keywords", "test")
    assert exif.error


def test_setvalue_context_manager():
    # test setting a tag value as context manager
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    with osxphotos.exiftool.ExifTool(tempfile) as exif:
        exif.setvalue("IPTC:Keywords", "test1")
        exif.setvalue("IPTC:Keywords", "test2")
        exif.setvalue("XMP:Title", "title")
        exif.setvalue("XMP:Subject", "subject")

    assert not exif.error

    exif2 = osxphotos.exiftool.ExifTool(tempfile)
    exif2._read_exif()
    assert sorted(exif2.data["IPTC:Keywords"]) == ["test1", "test2"]
    assert exif2.data["XMP:Title"] == "title"
    assert exif2.data["XMP:Subject"] == "subject"


def test_setvalue_context_manager_warning():
    # test setting a tag value as context manager when warning generated
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    with osxphotos.exiftool.ExifTool(tempfile) as exif:
        exif.setvalue("Foo:Bar", "test1")
    assert exif.warning


def test_setvalue_context_manager_error():
    # test setting a tag value as context manager when error generated
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_BAD_IMAGE))
    FileUtil.copy(TEST_FILE_BAD_IMAGE, tempfile)

    with osxphotos.exiftool.ExifTool(tempfile) as exif:
        exif.setvalue("IPTC:Keywords", "test1")
    assert exif.error


def test_flags():
    # test that flags work
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_WARNING))
    FileUtil.copy(TEST_FILE_WARNING, tempfile)

    with osxphotos.exiftool.ExifTool(tempfile) as exif:
        exif.setvalue("XMP:Subject", "foo/bar")
    assert exif.warning

    # test again with -m: ignore minor warnings
    FileUtil.unlink(tempfile)
    FileUtil.copy(TEST_FILE_WARNING, tempfile)
    with osxphotos.exiftool.ExifTool(tempfile, flags=["-m"]) as exif:
        exif.setvalue("XMP:Subject", "foo/bar")
    assert not exif.warning


def test_clear_value():
    # test clearing a tag value
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    assert "IPTC:Keywords" in exif.data

    exif.setvalue("IPTC:Keywords", None)
    exif._read_exif()
    assert "IPTC:Keywords" not in exif.data


def test_addvalues_1():
    # test setting a tag value
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    exif.addvalues("IPTC:Keywords", "test")
    exif._read_exif()
    assert sorted(exif.data["IPTC:Keywords"]) == sorted(["wedding", "test"])


def test_addvalues_2():
    # test setting a tag value where multiple values already exist
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_MULTI_KEYWORD))
    FileUtil.copy(TEST_FILE_MULTI_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    assert sorted(exif.data["IPTC:Keywords"]) == sorted(TEST_MULTI_KEYWORDS)
    exif.addvalues("IPTC:Keywords", "test")
    exif._read_exif()
    assert "IPTC:Keywords" in exif.data
    test_multi = TEST_MULTI_KEYWORDS.copy()
    test_multi.append("test")
    assert sorted(exif.data["IPTC:Keywords"]) == sorted(test_multi)


def test_addvalues_non_alphanumeric_multiline():
    # test setting a tag value
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    exif.addvalues("IPTC:Keywords", "multi\nline", "<Foo>\t{bar}")
    assert not exif.error
    exif._read_exif()
    assert sorted(exif.data["IPTC:Keywords"]) == sorted(
        ["wedding", "multi\nline", "<Foo>\t{bar}"]
    )


def test_addvalues_unicode():
    # test setting a tag value with unicode
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    exif.setvalue("IPTC:Keywords", None)
    exif.addvalues("IPTC:Keywords", "ǂ", "Ƕ")
    assert not exif.error
    exif._read_exif()
    assert sorted(exif.data["IPTC:Keywords"]) == sorted(["ǂ", "Ƕ"])


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


def test_as_dict():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    exifdata = exif1.asdict()
    assert exifdata["XMP:TagsList"] == "wedding"


def test_as_dict_normalized():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    exifdata = exif1.asdict(normalized=True)
    assert exifdata["xmp:tagslist"] == "wedding"
    assert "XMP:TagsList" not in exifdata


def test_as_dict_no_tag_groups():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    exifdata = exif1.asdict(tag_groups=False)
    assert exifdata["TagsList"] == "wedding"


def test_json():
    import json

    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    exifdata = json.loads(exif1.json())
    assert exifdata[0]["XMP:TagsList"] == "wedding"


def test_str():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    assert "file: " in str(exif1)
    assert "exiftool: " in str(exif1)


def test_photoinfo_exiftool():
    """test PhotoInfo.exiftool which returns ExifTool object for photo"""
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    for uuid in EXIF_UUID:
        photo = photosdb.photos(uuid=[uuid])[0]
        exiftool = photo.exiftool
        exif_dict = exiftool.asdict()
        for key, val in EXIF_UUID[uuid].items():
            assert exif_dict[key] == val


def test_photoinfo_exiftool_no_groups():
    """test PhotoInfo.exiftool which returns ExifTool object for photo without tag group names"""
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    for uuid in EXIF_UUID_NO_GROUPS:
        photo = photosdb.photos(uuid=[uuid])[0]
        exiftool = photo.exiftool
        exif_dict = exiftool.asdict(tag_groups=False)
        for key, val in EXIF_UUID_NO_GROUPS[uuid].items():
            assert exif_dict[key] == val


def test_photoinfo_exiftool_none():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    for uuid in EXIF_UUID_NONE:
        photo = photosdb.photos(uuid=[uuid])[0]
        exiftool = photo.exiftool
        assert exiftool is None


@pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") == "true", reason="fails on GH actions")
def test_exiftool_terminate():
    """Test that exiftool process is terminated when exiftool.terminate() is called"""
    import subprocess

    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)

    ps = subprocess.run(["ps"], capture_output=True)
    stdout = ps.stdout.decode("utf-8")
    assert "exiftool" in stdout

    osxphotos.exiftool.terminate_exiftool()

    ps = subprocess.run(["ps"], capture_output=True)
    stdout = ps.stdout.decode("utf-8")
    assert "exiftool" not in stdout

    # verify we can create a new instance after termination
    exif2 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    assert exif2.asdict()["IPTC:Keywords"] == "wedding"


def test_unescape_str():
    """Test unescape_str, #636"""
    quoted_str = unescape_str(QUOTED_JSON_BYTES.decode("utf-8"))
    assert quoted_str == QUOTED_JSON_STRING_UNESCAPED
    quoted_json = json.loads(quoted_str)
    assert quoted_json == QUOTED_JSON_LOADED


def test_large_file_support():
    """test large file support flag"""
    # doesn't actually test against a large file, just that exiftool runs correctly
    # See #722

    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile, large_file_support=True)
    exif.setvalue("IPTC:Keywords", "test")
    assert not exif.error

    exif._read_exif()
    assert exif.data["IPTC:Keywords"] == "test"


def test_large_file_support_disabled():
    """test large file support flag disabled"""
    # doesn't actually test against a large file, just that exiftool runs correctly
    # See #722

    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile, large_file_support=False)
    exif.setvalue("IPTC:Keywords", "test")
    assert not exif.error

    exif._read_exif()
    assert exif.data["IPTC:Keywords"] == "test"
