import pytest

from osxphotos.exiftool import get_exiftool_path

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

try:
    exiftool = get_exiftool_path()
except:
    exiftool = None

if exiftool is None:
    pytest.skip("could not find exiftool in path", allow_module_level=True)


def test_version():
    import osxphotos.exiftool

    exif = osxphotos.exiftool.ExifToolCaching(TEST_FILE_ONE_KEYWORD)
    assert exif.version is not None
    assert isinstance(exif.version, str)


def test_singleton():
    """tests per-file singleton behavior"""
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifToolCaching(TEST_FILE_ONE_KEYWORD)
    exif2 = osxphotos.exiftool.ExifToolCaching(TEST_FILE_ONE_KEYWORD)
    assert exif1 is exif2

    exif3 = osxphotos.exiftool.ExifToolCaching(TEST_FILE_MULTI_KEYWORD)
    assert exif1 is not exif3


def test_read():
    import osxphotos.exiftool

    exif = osxphotos.exiftool.ExifToolCaching(TEST_FILE_ONE_KEYWORD)
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

    exif = osxphotos.exiftool.ExifToolCaching(tempfile)
    with pytest.raises(NotImplementedError):
        exif.setvalue("IPTC:Keywords", "test")


def test_setvalue_cache():
    # test setting a tag value doesn't affect cached value
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifTool(tempfile)
    exif.setvalue("IPTC:Keywords", "test")
    assert exif.asdict()["IPTC:Keywords"] == "test"

    exifcache = osxphotos.exiftool.ExifToolCaching(tempfile)
    assert exifcache.asdict()["IPTC:Keywords"] == "test"

    # now change the value
    exif.setvalue("IPTC:Keywords", "foo")
    assert exif.asdict()["IPTC:Keywords"] == "foo"
    assert exifcache.asdict()["IPTC:Keywords"] == "test"

    exifcache.flush_cache()
    assert exifcache.asdict()["IPTC:Keywords"] == "foo"


def test_setvalue_context_manager():
    # test setting a tag value as context manager
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    with pytest.raises(NotImplementedError):
        with osxphotos.exiftool.ExifToolCaching(tempfile) as exif:
            exif.setvalue("IPTC:Keywords", "test1")


def test_flags():
    # test that flags raise error
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_WARNING))
    FileUtil.copy(TEST_FILE_WARNING, tempfile)

    with pytest.raises(TypeError):
        # ExifToolCaching doesn't take flags arg
        with osxphotos.exiftool.ExifToolCaching(tempfile, flags=["-m"]) as exif:
            exif.setvalue("XMP:Subject", "foo/ba    r")


def test_clear_value():
    # test clearing a tag value
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifToolCaching(tempfile)

    with pytest.raises(NotImplementedError):
        exif.setvalue("IPTC:Keywords", None)


def test_addvalues_1():
    # test setting a tag value
    import os.path
    import tempfile

    import osxphotos.exiftool
    from osxphotos.fileutil import FileUtil

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    tempfile = os.path.join(tempdir.name, os.path.basename(TEST_FILE_ONE_KEYWORD))
    FileUtil.copy(TEST_FILE_ONE_KEYWORD, tempfile)

    exif = osxphotos.exiftool.ExifToolCaching(tempfile)
    with pytest.raises(NotImplementedError):
        exif.addvalues("IPTC:Keywords", "test")


def test_exiftoolproc_process():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifToolCaching(TEST_FILE_ONE_KEYWORD)
    assert exif1._exiftoolproc.process is not None


def test_exiftoolproc_exiftool():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifToolCaching(TEST_FILE_ONE_KEYWORD)
    assert exif1._exiftoolproc.exiftool == osxphotos.exiftool.get_exiftool_path()


def test_as_dict():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifToolCaching(TEST_FILE_ONE_KEYWORD)
    exifdata = exif1.asdict()
    assert exifdata["XMP:TagsList"] == "wedding"


def test_as_dict_normalized():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifToolCaching(TEST_FILE_ONE_KEYWORD)
    exifdata = exif1.asdict(normalized=True)
    assert exifdata["xmp:tagslist"] == "wedding"
    assert "XMP:TagsList" not in exifdata


def test_as_dict_no_tag_groups():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifToolCaching(TEST_FILE_ONE_KEYWORD)
    exifdata = exif1.asdict(tag_groups=False)
    assert exifdata["TagsList"] == "wedding"


def test_json():
    import json

    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifToolCaching(TEST_FILE_ONE_KEYWORD)
    exifdata = json.loads(exif1.json())
    assert exifdata[0]["XMP:TagsList"] == "wedding"


def test_str():
    import osxphotos.exiftool

    exif1 = osxphotos.exiftool.ExifToolCaching(TEST_FILE_ONE_KEYWORD)
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
