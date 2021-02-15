""" Test template.py """
import pytest
import osxphotos
from osxphotos.exiftool import get_exiftool_path

from photoinfo_mock import PhotoInfoMock

try:
    exiftool = get_exiftool_path()
except:
    exiftool = None

PHOTOS_DB_PLACES = (
    "./tests/Test-Places-Catalina-10_15_7.photoslibrary/database/photos.db"
)
PHOTOS_DB_15_7 = "./tests/Test-10.15.7.photoslibrary/database/photos.db"
PHOTOS_DB_14_6 = "./tests/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_DB_COMMENTS = "tests/Test-Cloud-10.15.6.photoslibrary"
PHOTOS_DB_CLOUD = "./tests/Test-Cloud-10.15.6.photoslibrary/database/photos.db"

UUID_DICT = {
    "place_dc": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "1_1_2": "1EB2B765-0765-43BA-A90C-0D0580E6172C",
    "2_1_1": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "0_2_0": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "folder_album_1": "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
    "folder_album_no_folder": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "mojave_album_1": "15uNd7%8RguTEgNPKHfTWw",
    "date_modified": "A9B73E13-A6F2-4915-8D67-7213B39BAE9F",
    "date_not_modified": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
}

UUID_MEDIA_TYPE = {
    "photo": "C2BBC7A4-5333-46EE-BAF0-093E72111B39",
    "video": "45099D34-A414-464F-94A2-60D6823679C8",
    "selfie": "080525C4-1F05-48E5-A3F4-0C53127BB39C",
    "time_lapse": "4614086E-C797-4876-B3B9-3057E8D757C9",
    "panorama": "1C1C8F1F-826B-4A24-B1CB-56628946A834",
    "slow_mo": None,
    "screenshot": None,
    "portrait": "7CDA5F84-AA16-4D28-9AA6-A49E1DF8A332",
    "live_photo": "51F2BEF7-431A-4D31-8AC1-3284A57826AE",
    "burst": None,
}

# multi keywords
UUID_MULTI_KEYWORDS = "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4"
TEMPLATE_VALUES_MULTI_KEYWORDS = {
    "{keyword}": ["flowers", "wedding"],
    "{keyword|parens}": ["(flowers)", "(wedding)"],
    "{keyword|braces}": ["{flowers}", "{wedding}"],
    "{keyword|brackets}": ["[flowers]", "[wedding]"],
    "{keyword|parens|brackets|capitalize}": ["[(flowers)]", "[(wedding)]"],
    "{keyword|capitalize|parens|brackets}": ["[(Flowers)]", "[(Wedding)]"],
    "{keyword|upper}": ["FLOWERS", "WEDDING"],
    "{keyword|lower}": ["flowers", "wedding"],
    "{keyword|title}": ["Flowers", "Wedding"],
    "{keyword|capitalize}": ["Flowers", "Wedding"],
    "{+keyword}": ["flowerswedding"],
    "{+keyword|title}": ["Flowerswedding"],
    "{+keyword|capitalize}": ["Flowerswedding"],
    "{;+keyword}": ["flowers;wedding"],
    "{; +keyword}": ["flowers; wedding"],
    "{; +keyword|title}": ["Flowers; Wedding"],
    "{; +keyword|title|parens}": ["(Flowers; Wedding)"],
}

UUID_TITLE = "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4"
TEMPLATE_VALUES_TITLE = {
    "{title}": ["Tulips tied together at a flower shop"],
    "{title|title}": ["Tulips Tied Together At A Flower Shop"],
    "{title|upper}": ["TULIPS TIED TOGETHER AT A FLOWER SHOP"],
    "{title|title|lower|upper}": ["TULIPS TIED TOGETHER AT A FLOWER SHOP"],
    "{title|upper|title}": ["Tulips Tied Together At A Flower Shop"],
    "{title|capitalize}": ["Tulips tied together at a flower shop"],
    "{title[ ,_]}": ["Tulips_tied_together_at_a_flower_shop"],
    "{title[ ,_|e,]}": ["Tulips_tid_togthr_at_a_flowr_shop"],
    "{title[ ,|e,]}": ["Tulipstidtogthrataflowrshop"],
    "{title[e,]}": ["Tulips tid togthr at a flowr shop"],
    "{+title}": ["Tulips tied together at a flower shop"],
    "{,+title}": ["Tulips tied together at a flower shop"],
    "{, +title}": ["Tulips tied together at a flower shop"],
}

# Boolean type values that render to True
UUID_BOOL_VALUES = {
    "hdr": "D11D25FF-5F31-47D2-ABA9-58418878DC15",
    "edited": "51F2BEF7-431A-4D31-8AC1-3284A57826AE",
}

# Boolean type values that render to False
UUID_BOOL_VALUES_NOT = {
    "hdr": "51F2BEF7-431A-4D31-8AC1-3284A57826AE",
    "edited": "CCBE0EB9-AE9F-4479-BFFD-107042C75227",
}

# for exiftool template
UUID_EXIFTOOL = {
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91": {
        "{exiftool:EXIF:Make}": ["Canon"],
        "{exiftool:EXIF:Make[Canon,CANON]}": ["CANON"],
        "{exiftool:EXIF:Model}": ["Canon PowerShot G10"],
        "{exiftool:EXIF:Model[ G10,]}": ["Canon PowerShot"],
        "{exiftool:EXIF:Make}/{exiftool:EXIF:Model}": ["Canon/Canon PowerShot G10"],
        "{exiftool:IPTC:Keywords,foo}": ["foo"],
    },
    "DC99FBDD-7A52-4100-A5BB-344131646C30": {
        "{exiftool:IPTC:Keywords}": [
            "England",
            "London",
            "London 2018",
            "St. James's Park",
            "UK",
            "United Kingdom",
        ],
        "{exiftool:IPTC:Keywords[ ,_|.,]}": [
            "England",
            "London",
            "London_2018",
            "St_James's_Park",
            "UK",
            "United_Kingdom",
        ],
        "{exiftool:IPTC:Keywords[ ,_|.,|L,]}": [
            "England",
            "ondon",
            "ondon_2018",
            "St_James's_Park",
            "UK",
            "United_Kingdom",
        ],
        "{,+exiftool:IPTC:Keywords}": [
            "England,London,London 2018,St. James's Park,UK,United Kingdom"
        ],
    },
}

TEMPLATE_VALUES = {
    "{name}": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "{original_name}": "IMG_1064",
    "{original_name[_,-]}": "IMG-1064",
    "{title}": "Glen Ord",
    "{title[ ,]}": "GlenOrd",
    "{descr}": "Jack Rose Dining Saloon",
    "{created.date}": "2020-02-04",
    "{created.year}": "2020",
    "{created.yy}": "20",
    "{created.mm}": "02",
    "{created.month}": "February",
    "{created.mon}": "Feb",
    "{created.dd}": "04",
    "{created.dow}": "Tuesday",
    "{created.doy}": "035",
    "{created.hour}": "19",
    "{created.min}": "07",
    "{created.sec}": "38",
    "{place.name}": "Washington, District of Columbia, United States",
    "{place.country_code}": "US",
    "{place.name.country}": "United States",
    "{place.name.state_province}": "District of Columbia",
    "{place.name.city}": "Washington",
    "{place.name.area_of_interest}": "_",
    "{place.address}": "2038 18th St NW, Washington, DC  20009, United States",
    "{place.address.street}": "2038 18th St NW",
    "{place.address.city}": "Washington",
    "{place.address.state_province}": "DC",
    "{place.address.postal_code}": "20009",
    "{place.address.country}": "United States",
    "{place.address.country_code}": "US",
    "{uuid}": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "{exif.camera_make}": "Apple",
    "{exif.camera_model}": "iPhone 6s",
    "{exif.lens_model}": "iPhone 6s back camera 4.15mm f/2.2",
}


TEMPLATE_VALUES_DEU = {
    "{name}": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "{original_name}": "IMG_1064",
    "{title}": "Glen Ord",
    "{descr}": "Jack Rose Dining Saloon",
    "{created.date}": "2020-02-04",
    "{created.year}": "2020",
    "{created.yy}": "20",
    "{created.mm}": "02",
    "{created.month}": "Februar",
    "{created.mon}": "Feb",
    "{created.dd}": "04",
    "{created.doy}": "035",
    "{created.dow}": "Dienstag",
    "{place.name}": "Washington, District of Columbia, United States",
    "{place.country_code}": "US",
    "{place.name.country}": "United States",
    "{place.name.state_province}": "District of Columbia",
    "{place.name.city}": "Washington",
    "{place.name.area_of_interest}": "_",
    "{place.address}": "2038 18th St NW, Washington, DC  20009, United States",
    "{place.address.street}": "2038 18th St NW",
    "{place.address.city}": "Washington",
    "{place.address.state_province}": "DC",
    "{place.address.postal_code}": "20009",
    "{place.address.country}": "United States",
    "{place.address.country_code}": "US",
}

TEMPLATE_VALUES_DATE_MODIFIED = {
    "{name}": "A9B73E13-A6F2-4915-8D67-7213B39BAE9F",
    "{original_name}": "IMG_3984",
    "{modified.date}": "2020-10-31",
    "{modified.year}": "2020",
    "{modified.yy}": "20",
    "{modified.mm}": "10",
    "{modified.month}": "October",
    "{modified.mon}": "Oct",
    "{modified.dd}": "31",
    "{modified.doy}": "305",
    "{modified.dow}": "Saturday",
    "{modified.strftime,%Y-%m-%d-%H%M%S}": "2020-10-31-080321",
    "{modified.strftime}": "_",
}

TEMPLATE_VALUES_DATE_NOT_MODIFIED = {
    # uses creation date instead of modified date
    "{name}": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "{original_name}": "IMG_1064",
    "{modified.date}": "2020-02-04",
    "{modified.year}": "2020",
    "{modified.yy}": "20",
    "{modified.mm}": "02",
    "{modified.month}": "February",
    "{modified.mon}": "Feb",
    "{modified.dd}": "04",
    "{modified.dow}": "Tuesday",
    "{modified.doy}": "035",
    "{modified.hour}": "19",
    "{modified.min}": "07",
    "{modified.sec}": "38",
    "{modified.strftime,%Y-%m-%d-%H%M%S}": "2020-02-04-190738",
}


COMMENT_UUID_DICT = {
    "4AD7C8EF-2991-4519-9D3A-7F44A6F031BE": [
        "None: Nice photo!",
        "None: Wish I was back here!",
    ],
    "CCBE0EB9-AE9F-4479-BFFD-107042C75227": ["_"],
    "4E4944A0-3E5C-4028-9600-A8709F2FA1DB": ["None: Nice trophy"],
}


@pytest.fixture(scope="module")
def photosdb_places():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_7)


@pytest.fixture(scope="module")
def photosdb_14_6():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_14_6)


@pytest.fixture(scope="module")
def photosdb_comments():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_COMMENTS)


@pytest.fixture(scope="module")
def photosdb_cloud():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_CLOUD)


def test_lookup(photosdb_places):
    """ Test that a lookup is returned for every possible value """
    import re
    from osxphotos.phototemplate import TEMPLATE_SUBSTITUTIONS, PhotoTemplate

    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]
    template = PhotoTemplate(photo)

    for subst in TEMPLATE_SUBSTITUTIONS:
        lookup_str = re.match(r"\{([^\\,}]+)\}", subst).group(1)
        lookup = template.get_template_value(lookup_str, None)
        assert lookup or lookup is None


def test_lookup_multi(photosdb_places):
    """ Test that a lookup is returned for every possible value """
    import os
    import re
    from osxphotos.phototemplate import (
        TEMPLATE_SUBSTITUTIONS_MULTI_VALUED,
        PhotoTemplate,
    )

    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]
    template = PhotoTemplate(photo)

    for subst in TEMPLATE_SUBSTITUTIONS_MULTI_VALUED:
        lookup_str = re.match(r"\{([^\\,}]+)\}", subst).group(1)
        if subst == "{exiftool}":
            continue
        lookup = template.get_template_value_multi(lookup_str, path_sep=os.path.sep)
        assert isinstance(lookup, list)


def test_subst(photosdb_places):
    """ Test that substitutions are correct """
    import locale

    locale.setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for template in TEMPLATE_VALUES:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES[template]


def test_subst_date_modified(photosdb_places):
    """ Test that substitutions are correct for date modified """
    import locale

    locale.setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["date_modified"]])[0]

    for template in TEMPLATE_VALUES_DATE_MODIFIED:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES_DATE_MODIFIED[template]


def test_subst_date_not_modified(photosdb_places):
    """ Test that substitutions are correct for date modified when photo isn't modified """
    import locale

    locale.setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["date_not_modified"]])[0]

    for template in TEMPLATE_VALUES_DATE_NOT_MODIFIED:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES_DATE_NOT_MODIFIED[template]


def test_subst_locale_1(photosdb_places):
    """ Test that substitutions are correct in user locale"""
    import locale

    # osxphotos.template sets local on load so set the environment first
    # set locale to DE
    locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")

    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for template in TEMPLATE_VALUES_DEU:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES_DEU[template]


def test_subst_locale_2(photosdb_places):
    """ Test that substitutions are correct in user locale"""
    import locale
    import os

    # osxphotos.template sets local on load so set the environment first
    os.environ["LANG"] = "de_DE.UTF-8"
    os.environ["LC_COLLATE"] = "de_DE.UTF-8"
    os.environ["LC_CTYPE"] = "de_DE.UTF-8"
    os.environ["LC_MESSAGES"] = "de_DE.UTF-8"
    os.environ["LC_MONETARY"] = "de_DE.UTF-8"
    os.environ["LC_NUMERIC"] = "de_DE.UTF-8"
    os.environ["LC_TIME"] = "de_DE.UTF-8"

    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for template in TEMPLATE_VALUES_DEU:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES_DEU[template]


def test_subst_default_val(photosdb_places):
    """ Test substitution with default value specified """
    import locale
    import osxphotos

    locale.setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{place.name.area_of_interest,UNKNOWN}"
    rendered, _ = photo.render_template(template)
    assert rendered[0] == "UNKNOWN"


def test_subst_default_val_2(photosdb_places):
    """ Test substitution with ',' but no default value """
    import locale

    locale.setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{place.name.area_of_interest,}"
    rendered, _ = photo.render_template(template)
    assert rendered[0] == ""


def test_subst_unknown_val(photosdb_places):
    """ Test substitution with unknown value specified """
    import locale

    locale.setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{created.year}/{foo}"
    rendered, unknown = photo.render_template(template)
    # assert rendered[0] == "2020/{foo}"
    assert unknown == ["foo"]


# def test_subst_double_brace(photosdb_places):
#     """ Test substitution with double brace {{ which should be ignored """

#     photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

#     template = "{created.year}/{{foo}}"
#     rendered, unknown = photo.render_template(template)
#     assert rendered[0] == "2020/{foo}"
#     assert not unknown


def test_subst_unknown_val_with_default(photosdb_places):
    """ Test substitution with unknown value specified """
    import locale

    locale.setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{created.year}/{foo,bar}"
    rendered, unknown = photo.render_template(template)
    # assert rendered[0] == "2020/{foo,bar}"
    assert unknown == ["foo"]


def test_subst_multi_1_1_2(photosdb):
    """ Test that substitutions are correct """
    # one album, one keyword, two persons
    import osxphotos

    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = ["2018/Pumpkin Farm/Kids/Katie", "2018/Pumpkin Farm/Kids/Suzy"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_2_1_1(photosdb):
    """ Test that substitutions are correct """
    # 2 albums, 1 keyword, 1 person

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["2_1_1"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = ["2018/Pumpkin Farm/Kids/Katie", "2018/Test Album/Kids/Katie"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_2_1_1_single(photosdb):
    """ Test that substitutions are correct """
    # 2 albums, 1 keyword, 1 person but only do keywords

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["2_1_1"]])[0]

    template = "{keyword}"
    expected = ["Kids"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0(photosdb):
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = ["2019/_/wedding/_", "2019/_/flowers/_"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_single(photosdb):
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, but only do albums

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album}"
    expected = ["2019/_"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_default_val(photosdb):
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, default vals provided

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person,NOPERSON}"
    expected = ["2019/NOALBUM/wedding/NOPERSON", "2019/NOALBUM/flowers/NOPERSON"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_default_val_unknown_val(photosdb):
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, default vals provided, unknown val in template
    import osxphotos

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person}/{foo}/{baz}"
    expected = [
        "2019/NOALBUM/wedding/_/{foo}/{baz}",
        "2019/NOALBUM/flowers/_/{foo}/{baz}",
    ]
    rendered, unknown = photo.render_template(template)
    # assert sorted(rendered) == sorted(expected)
    assert unknown == ["foo", "baz"]


def test_subst_multi_0_2_0_default_val_unknown_val_2(photosdb):
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, default vals provided, unknown val in template

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person}/{foo,bar}/{baz,bar}"
    expected = [
        "2019/NOALBUM/wedding/_/{foo,bar}/{baz,bar}",
        "2019/NOALBUM/flowers/_/{foo,bar}/{baz,bar}",
    ]
    rendered, unknown = photo.render_template(template)
    # assert sorted(rendered) == sorted(expected)
    assert unknown == ["foo", "baz"]


def test_subst_multi_folder_albums_1(photosdb):
    """ Test substitutions for folder_album are correct """

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["folder_album_1"]])[0]
    template = "{folder_album}"
    expected = [
        "2018-10 - Sponsion, Museum, Frühstück, Römermuseum",
        "2019-10/11 Paris Clermont",
        "Folder1/SubFolder2/AlbumInFolder",
    ]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_1_path_sep(photosdb):
    """ Test substitutions for folder_album are correct with custom PATH_SEP """

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["folder_album_1"]])[0]
    template = "{folder_album(:)}"
    expected = [
        "2018-10 - Sponsion, Museum, Frühstück, Römermuseum",
        "2019-10/11 Paris Clermont",
        "Folder1:SubFolder2:AlbumInFolder",
    ]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_2(photosdb):
    """ Test substitutions for folder_album are correct """

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["folder_album_no_folder"]])[0]
    template = "{folder_album}"
    expected = ["Pumpkin Farm", "Test Album"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_2_path_sep(photosdb):
    """ Test substitutions for folder_album are correct with custom PATH_SEP """

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["folder_album_no_folder"]])[0]
    template = "{folder_album(:)}"
    expected = ["Pumpkin Farm", "Test Album"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_3(photosdb_14_6):
    """ Test substitutions for folder_album on < Photos 5 """

    # photo in an album in a folder
    photo = photosdb_14_6.photos(uuid=[UUID_DICT["mojave_album_1"]])[0]
    template = "{folder_album}"
    expected = ["Folder1/SubFolder2/AlbumInFolder", "Pumpkin Farm", "Test Album (1)"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_3_path_sep(photosdb_14_6):
    """ Test substitutions for folder_album on < Photos 5 with custom PATH_SEP """
    import osxphotos

    # photo in an album in a folder
    photo = photosdb_14_6.photos(uuid=[UUID_DICT["mojave_album_1"]])[0]
    template = "{folder_album(>)}"
    expected = ["Folder1>SubFolder2>AlbumInFolder", "Pumpkin Farm", "Test Album (1)"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_strftime(photosdb_places):
    """ Test that strftime substitutions are correct """
    import locale
    import osxphotos

    locale.setlocale(locale.LC_ALL, "en_US")
    photo = photosdb_places.photos(uuid=[UUID_DICT["place_dc"]])[0]

    rendered, unmatched = photo.render_template("{created.strftime,%Y-%m-%d-%H%M%S}")
    assert rendered[0] == "2020-02-04-190738"

    rendered, unmatched = photo.render_template("{created.strftime}")
    assert rendered[0] == "_"


def test_subst_expand_inplace_1(photosdb):
    """ Test that substitutions are correct when expand_inplace=True """

    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{person}"
    expected = ["Katie,Suzy"]
    rendered, unknown = photo.render_template(template, expand_inplace=True)
    assert sorted(rendered) == sorted(expected)


def test_subst_expand_inplace_2(photosdb):
    """ Test that substitutions are correct when expand_inplace=True """
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{person}-{keyword}"
    expected = ["Katie,Suzy-Kids"]
    rendered, unknown = photo.render_template(template, expand_inplace=True)
    assert sorted(rendered) == sorted(expected)


def test_subst_expand_inplace_3(photosdb):
    """ Test that substitutions are correct when expand_inplace=True and inplace_sep specified"""
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{person}-{keyword}"
    expected = ["Katie; Suzy-Kids"]
    rendered, unknown = photo.render_template(
        template, expand_inplace=True, inplace_sep="; "
    )
    assert sorted(rendered) == sorted(expected)


def test_comment(photosdb_comments):
    import osxphotos

    for uuid in COMMENT_UUID_DICT:
        photo = photosdb_comments.get_photo(uuid)
        comments = photo.render_template("{comment}")
        assert comments[0] == COMMENT_UUID_DICT[uuid]


def test_media_type(photosdb_cloud):
    """ test {media_type} template """

    for field, uuid in UUID_MEDIA_TYPE.items():
        if uuid is not None:
            photo = photosdb_cloud.get_photo(uuid)
            rendered, _ = photo.render_template("{media_type}")
            assert rendered[0] == osxphotos.phototemplate.MEDIA_TYPE_DEFAULTS[field]


def test_media_type_default(photosdb_cloud):
    """ test {media_type,photo=foo} template style """

    for field, uuid in UUID_MEDIA_TYPE.items():
        if uuid is not None:
            photo = photosdb_cloud.get_photo(uuid)
            rendered, _ = photo.render_template("{media_type," + f"{field}" + "=foo}")
            assert rendered[0] == "foo"


def test_bool_values(photosdb_cloud):
    """ test {bool?TRUE,FALSE} template values """

    for field, uuid in UUID_BOOL_VALUES.items():
        if uuid is not None:
            photo = photosdb_cloud.get_photo(uuid)
            rendered, _ = photo.render_template("{" + f"{field}" + "?True,False}")
            assert rendered[0] == "True"


def test_bool_values_not(photosdb_cloud):
    """ test {bool?TRUE,FALSE} template values for FALSE values """

    for field, uuid in UUID_BOOL_VALUES_NOT.items():
        if uuid is not None:
            photo = photosdb_cloud.get_photo(uuid)
            rendered, _ = photo.render_template("{" + f"{field}" + "?True,False}")
            assert rendered[0] == "False"


def test_partial_match(photosdb_cloud):
    """ test that template successfully rejects a field that is superset of valid field """

    for uuid in COMMENT_UUID_DICT:
        photo = photosdb_cloud.get_photo(uuid)
        rendered, notmatched = photo.render_template("{keywords}")
        assert [rendered, notmatched] == [[], ["keywords"]]
        rendered, notmatched = photo.render_template("{keywords,}")
        assert [rendered, notmatched] == [[], ["keywords"]]
        rendered, notmatched = photo.render_template("{keywords,foo}")
        assert [rendered, notmatched] == [[], ["keywords"]]
        rendered, notmatched = photo.render_template("{,+keywords,foo}")
        assert [rendered, notmatched] == [[], ["keywords"]]


def test_expand_in_place_with_delim(photosdb):
    """ Test that substitutions are correct when {DELIM+FIELD} format used """
    import osxphotos

    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)

    for template in TEMPLATE_VALUES_MULTI_KEYWORDS:
        rendered, _ = photo.render_template(template)
        assert sorted(rendered) == sorted(TEMPLATE_VALUES_MULTI_KEYWORDS[template])


def test_expand_in_place_with_delim_single_value(photosdb):
    """ Test that single-value substitutions are correct when {DELIM+FIELD} format used """

    photo = photosdb.get_photo(UUID_TITLE)

    for template in TEMPLATE_VALUES_TITLE:
        rendered, _ = photo.render_template(template)
        assert sorted(rendered) == sorted(TEMPLATE_VALUES_TITLE[template])


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_exiftool_template(photosdb):
    for uuid in UUID_EXIFTOOL:
        photo = photosdb.get_photo(uuid)
        for template in UUID_EXIFTOOL[uuid]:
            rendered, _ = photo.render_template(template)
            assert sorted(rendered) == sorted(UUID_EXIFTOOL[uuid][template])


def test_hdr(photosdb):
    """ Test hdr """
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    photomock = PhotoInfoMock(photo, hdr="hdr")
    rendered, _ = photomock.render_template("{hdr}")
    assert rendered == ["hdr"]


def test_edited(photosdb):
    """ Test edited """
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    photomock = PhotoInfoMock(photo, hasadjustments=True)
    rendered, _ = photomock.render_template("{edited}")
    assert rendered == ["edited"]


def test_nested_template_bool(photosdb):
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    template = "{hdr?{edited?HDR_EDITED,HDR_NOT_EDITED},{edited?NOT_HDR_EDITED,NOT_HDR_NOT_EDITED}}"

    photomock = PhotoInfoMock(photo, hdr=True, hasadjustments=True)
    rendered, _ = photomock.render_template(template)
    assert rendered == ["HDR_EDITED"]

    photomock = PhotoInfoMock(photo, hdr=True, hasadjustments=False)
    rendered, _ = photomock.render_template(template)
    assert rendered == ["HDR_NOT_EDITED"]

    photomock = PhotoInfoMock(photo, hdr=False, hasadjustments=False)
    rendered, _ = photomock.render_template(template)
    assert rendered == ["NOT_HDR_NOT_EDITED"]

    photomock = PhotoInfoMock(photo, hdr=False, hasadjustments=True)
    rendered, _ = photomock.render_template(template)
    assert rendered == ["NOT_HDR_EDITED"]


def test_nested_template(photosdb):
    photo = photosdb.get_photo(UUID_MULTI_KEYWORDS)
    photomock = PhotoInfoMock(photo, keywords=[], title="My Title")

    rendered, _ = photomock.render_template("{keyword,{title}}")
    assert rendered == ["My Title"]
