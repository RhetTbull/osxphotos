import pytest

from osxphotos._constants import _UNKNOWN_PERSON

PHOTOS_DB = "./tests/Test-10.15.4.photoslibrary/database/photos.db"

TOP_LEVEL_FOLDERS = ["Folder1"]

TOP_LEVEL_CHILDREN = ["SubFolder1", "SubFolder2"]

FOLDER_ALBUM_DICT = {"Folder1": [], "SubFolder1": [], "SubFolder2": ["AlbumInFolder"]}

ALBUM_NAMES = ["Pumpkin Farm", "AlbumInFolder", "Test Album", "Test Album"]

ALBUM_PARENT_DICT = {
    "Pumpkin Farm": None,
    "AlbumInFolder": "SubFolder2",
    "Test Album": None,
}

ALBUM_FOLDER_NAMES_DICT = {
    "Pumpkin Farm": [],
    "AlbumInFolder": ["Folder1", "SubFolder2"],
    "Test Album": [],
}

ALBUM_LEN_DICT = {"Pumpkin Farm": 3, "AlbumInFolder": 2, "Test Album": 1}

ALBUM_PHOTO_UUID_DICT = {
    "Pumpkin Farm": [
        "F12384F6-CD17-4151-ACBA-AE0E3688539E",
        "D79B8D77-BFFC-460B-9312-034F2877D35B",
        "1EB2B765-0765-43BA-A90C-0D0580E6172C",
    ],
    "Test Album": [
        "F12384F6-CD17-4151-ACBA-AE0E3688539E",
        "D79B8D77-BFFC-460B-9312-034F2877D35B",
    ],
    "AlbumInFolder": [
        "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
        "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    ],
}

UUID_DICT = {
    "two_albums": "F12384F6-CD17-4151-ACBA-AE0E3688539E",
    "in_album": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "xmp": "F12384F6-CD17-4151-ACBA-AE0E3688539E",
}


def test_exiftool_json_sidecar_keyword_template_long(caplog):
    import osxphotos
    from osxphotos._constants import _MAX_IPTC_KEYWORD_LEN
    import json

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["in_album"]])

    json_expected = json.loads(
        """
        [{"_CreatedBy": "osxphotos, https://github.com/RhetTbull/osxphotos", 
        "EXIF:ImageDescription": "Bride Wedding day", 
        "XMP:Description": "Bride Wedding day", 
        "XMP:TagsList": ["wedding", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"], 
        "IPTC:Keywords": ["wedding", "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"], 
        "XMP:PersonInImage": ["Maria"], 
        "XMP:Subject": ["wedding", "Maria"], 
        "EXIF:DateTimeOriginal": "2019:04:15 14:40:24", 
        "EXIF:OffsetTimeOriginal": "-04:00", "EXIF:ModifyDate": "2019:11:24 13:09:17"}]
        """
    )[0]

    long_str = "x" * (_MAX_IPTC_KEYWORD_LEN + 1)
    json_got = photos[0]._exiftool_json_sidecar(keyword_template=[long_str])
    json_got = json.loads(json_got)[0]

    assert "Some keywords exceed max IPTC Keyword length" in caplog.text
    # some gymnastics to account for different sort order in different pythons
    for k, v in json_got.items():
        if type(v) in (list, tuple):
            assert sorted(json_expected[k]) == sorted(v)
        else:
            assert json_expected[k] == v

    for k, v in json_expected.items():
        if type(v) in (list, tuple):
            assert sorted(json_got[k]) == sorted(v)
        else:
            assert json_got[k] == v

    for k, v in json_expected.items():
        if type(v) in (list, tuple):
            assert sorted(json_got[k]) == sorted(v)
        else:
            assert json_got[k] == v


def test_exiftool_json_sidecar_keyword_template():
    import osxphotos
    import json

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["in_album"]])

    json_expected = json.loads(
        """
        [{"_CreatedBy": "osxphotos, https://github.com/RhetTbull/osxphotos", 
        "EXIF:ImageDescription": "Bride Wedding day", 
        "XMP:Description": "Bride Wedding day", 
        "XMP:TagsList": ["wedding", "Folder1/SubFolder2/AlbumInFolder"], 
        "IPTC:Keywords": ["wedding", "Folder1/SubFolder2/AlbumInFolder"], 
        "XMP:PersonInImage": ["Maria"], 
        "XMP:Subject": ["wedding", "Maria"], 
        "EXIF:DateTimeOriginal": "2019:04:15 14:40:24", 
        "EXIF:OffsetTimeOriginal": "-04:00", "EXIF:ModifyDate": "2019:11:24 13:09:17"}]
        """
    )[0]

    json_got = photos[0]._exiftool_json_sidecar(keyword_template=["{folder_album}"])
    json_got = json.loads(json_got)[0]

    # some gymnastics to account for different sort order in different pythons
    for k, v in json_got.items():
        if type(v) in (list, tuple):
            assert sorted(json_expected[k]) == sorted(v)
        else:
            assert json_expected[k] == v

    for k, v in json_expected.items():
        if type(v) in (list, tuple):
            assert sorted(json_got[k]) == sorted(v)
        else:
            assert json_got[k] == v

    # some gymnastics to account for different sort order in different pythons
    for k, v in json_got.items():
        if type(v) in (list, tuple):
            assert sorted(json_expected[k]) == sorted(v)
        else:
            assert json_expected[k] == v

    for k, v in json_expected.items():
        if type(v) in (list, tuple):
            assert sorted(json_got[k]) == sorted(v)
        else:
            assert json_got[k] == v

    for k, v in json_expected.items():
        if type(v) in (list, tuple):
            assert sorted(json_got[k]) == sorted(v)
        else:
            assert json_got[k] == v


def test_xmp_sidecar_keyword_template():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["xmp"]])

    xmp_expected = """<!-- Created with osxphotos https://github.com/RhetTbull/osxphotos -->
    <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.4.0">
    <!-- mirrors Photos 5 "Export IPTC as XMP" option -->
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about="" 
            xmlns:dc="http://purl.org/dc/elements/1.1/" 
            xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/">
        <dc:description>Girls with pumpkins</dc:description>
        <dc:title>Can we carry this?</dc:title>
        <!-- keywords and persons listed in <dc:subject> as Photos does -->
        <dc:subject>
            <rdf:Seq>
                <rdf:li>Kids</rdf:li>
                <rdf:li>Suzy</rdf:li>
                <rdf:li>Katie</rdf:li>
            </rdf:Seq>
        </dc:subject>
        <photoshop:DateCreated>2018-09-28T15:35:49.063000-04:00</photoshop:DateCreated>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:Iptc4xmpExt='http://iptc.org/std/Iptc4xmpExt/2008-02-29/'>
        <Iptc4xmpExt:PersonInImage>
            <rdf:Bag>
                    <rdf:li>Suzy</rdf:li>
                    <rdf:li>Katie</rdf:li>
            </rdf:Bag>
        </Iptc4xmpExt:PersonInImage>
        </rdf:Description>
        <rdf:Description rdf:about="" 
            xmlns:digiKam='http://www.digikam.org/ns/1.0/'>
        <digiKam:TagsList>
            <rdf:Seq>
                <rdf:li>Kids</rdf:li>
                <rdf:li>Pumpkin Farm</rdf:li>
                <rdf:li>Test Album</rdf:li>
                <rdf:li>2018</rdf:li>
            </rdf:Seq>
        </digiKam:TagsList>
        </rdf:Description>
        <rdf:Description rdf:about=""
            xmlns:xmp='http://ns.adobe.com/xap/1.0/'>
        <xmp:CreateDate>2018-09-28T15:35:49</xmp:CreateDate>
        <xmp:ModifyDate>2018-09-28T15:35:49</xmp:ModifyDate>
        </rdf:Description>
        <rdf:Description rdf:about=""
            xmlns:exif='http://ns.adobe.com/exif/1.0/'>
        </rdf:Description>
    </rdf:RDF>
    </x:xmpmeta>"""

    xmp_expected_lines = [line.strip() for line in xmp_expected.split("\n")]

    xmp_got = photos[0]._xmp_sidecar(
        keyword_template=["{created.year}", "{folder_album}"]
    )
    xmp_got_lines = [line.strip() for line in xmp_got.split("\n")]

    for line_expected, line_got in zip(
        sorted(xmp_expected_lines), sorted(xmp_got_lines)
    ):
        assert line_expected == line_got
