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
EXIF_UUID_NONE = ["A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"]

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
    exif._read_exif()
    assert exif.data["IPTC:Keywords"] == "test"


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


def test_json():
    import osxphotos.exiftool
    import json

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    exifdata = json.loads(exif1.json())
    assert exifdata[0]["XMP:TagsList"] == "wedding"


def test_str():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifTool(TEST_FILE_ONE_KEYWORD)
    assert "file: " in str(exif1)
    assert "exiftool: " in str(exif1)


def test_photoinfo_exiftool():
    """ test PhotoInfo.exiftool which returns ExifTool object for photo """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    for uuid in EXIF_UUID:
        photo = photosdb.photos(uuid=[uuid])[0]
        exiftool = photo.exiftool
        exif_dict = exiftool.asdict()
        for key, val in EXIF_UUID[uuid].items():
            assert exif_dict[key] == val


def test_photoinfo_exiftool_none():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    for uuid in EXIF_UUID_NONE:
        photo = photosdb.photos(uuid=[uuid])[0]
        exiftool = photo.exiftool
        assert exiftool is None
