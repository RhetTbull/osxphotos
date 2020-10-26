""" Test template.py """
import pytest

PHOTOS_DB_PLACES = (
    "./tests/Test-Places-Catalina-10_15_1.photoslibrary/database/photos.db"
)
PHOTOS_DB_15_1 = "./tests/Test-10.15.1.photoslibrary/database/photos.db"
PHOTOS_DB_15_4 = "./tests/Test-10.15.4.photoslibrary/database/photos.db"
PHOTOS_DB_14_6 = "./tests/Test-10.14.6.photoslibrary/database/photos.db"

PHOTOS_DB_COMMENTS = "tests/Test-Cloud-10.15.6.photoslibrary"

UUID_DICT = {
    "place_dc": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "1_1_2": "1EB2B765-0765-43BA-A90C-0D0580E6172C",
    "2_1_1": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "0_2_0": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "folder_album_1": "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
    "folder_album_no_folder": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "mojave_album_1": "15uNd7%8RguTEgNPKHfTWw",
}

TEMPLATE_VALUES = {
    "{name}": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "{original_name}": "IMG_1064",
    "{title}": "Glen Ord",
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
    "{modified.date}": "2020-03-21",
    "{modified.year}": "2020",
    "{modified.yy}": "20",
    "{modified.mm}": "03",
    "{modified.month}": "March",
    "{modified.mon}": "Mar",
    "{modified.dd}": "21",
    "{modified.doy}": "081",
    "{modified.hour}": "01",
    "{modified.min}": "33",
    "{modified.sec}": "08",
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
    "{modified.date}": "2020-03-21",
    "{modified.year}": "2020",
    "{modified.yy}": "20",
    "{modified.mm}": "03",
    "{modified.month}": "März",
    "{modified.mon}": "Mär",
    "{modified.dd}": "21",
    "{modified.doy}": "081",
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

COMMENT_UUID_DICT = {
    "4AD7C8EF-2991-4519-9D3A-7F44A6F031BE": [
        "None: Nice photo!",
        "None: Wish I was back here!",
    ],
    "CCBE0EB9-AE9F-4479-BFFD-107042C75227": ["_"],
    "4E4944A0-3E5C-4028-9600-A8709F2FA1DB": ["None: Nice trophy"],
}


def test_lookup():
    """ Test that a lookup is returned for every possible value """
    import re
    import osxphotos
    from osxphotos.phototemplate import TEMPLATE_SUBSTITUTIONS, PhotoTemplate

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]
    template = PhotoTemplate(photo)

    for subst in TEMPLATE_SUBSTITUTIONS:
        lookup_str = re.match(r"\{([^\\,}]+)\}", subst).group(1)
        lookup = template.get_template_value(lookup_str, None)
        assert lookup or lookup is None


def test_lookup_multi():
    """ Test that a lookup is returned for every possible value """
    import os
    import re
    import osxphotos
    from osxphotos.phototemplate import (
        TEMPLATE_SUBSTITUTIONS_MULTI_VALUED,
        PhotoTemplate,
    )

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]
    template = PhotoTemplate(photo)

    for subst in TEMPLATE_SUBSTITUTIONS_MULTI_VALUED:
        lookup_str = re.match(r"\{([^\\,}]+)\}", subst).group(1)
        lookup = template.get_template_value_multi(lookup_str, path_sep=os.path.sep)
        assert isinstance(lookup, list)
        assert len(lookup) >= 1


def test_subst():
    """ Test that substitutions are correct """
    import locale
    import osxphotos

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for template in TEMPLATE_VALUES:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES[template]


def test_subst_locale_1():
    """ Test that substitutions are correct in user locale"""
    import locale
    import osxphotos

    # osxphotos.template sets local on load so set the environment first
    # set locale to DE
    locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for template in TEMPLATE_VALUES_DEU:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES_DEU[template]


def test_subst_locale_2():
    """ Test that substitutions are correct in user locale"""
    import locale
    import os
    import osxphotos

    # osxphotos.template sets local on load so set the environment first
    os.environ["LANG"] = "de_DE.UTF-8"
    os.environ["LC_COLLATE"] = "de_DE.UTF-8"
    os.environ["LC_CTYPE"] = "de_DE.UTF-8"
    os.environ["LC_MESSAGES"] = "de_DE.UTF-8"
    os.environ["LC_MONETARY"] = "de_DE.UTF-8"
    os.environ["LC_NUMERIC"] = "de_DE.UTF-8"
    os.environ["LC_TIME"] = "de_DE.UTF-8"

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for template in TEMPLATE_VALUES_DEU:
        rendered, _ = photo.render_template(template)
        assert rendered[0] == TEMPLATE_VALUES_DEU[template]


def test_subst_default_val():
    """ Test substitution with default value specified """
    import locale
    import osxphotos

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{place.name.area_of_interest,UNKNOWN}"
    rendered, _ = photo.render_template(template)
    assert rendered[0] == "UNKNOWN"


def test_subst_default_val_2():
    """ Test substitution with ',' but no default value """
    import locale
    import osxphotos

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{place.name.area_of_interest,}"
    rendered, _ = photo.render_template(template)
    assert rendered[0] == "_"


def test_subst_unknown_val():
    """ Test substitution with unknown value specified """
    import locale
    import osxphotos

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{created.year}/{foo}"
    rendered, unknown = photo.render_template(template)
    assert rendered[0] == "2020/{foo}"
    assert unknown == ["foo"]

    template = "{place.name.area_of_interest,}"
    rendered, _ = photo.render_template(template)
    assert rendered[0] == "_"


def test_subst_double_brace():
    """ Test substitution with double brace {{ which should be ignored """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{created.year}/{{foo}}"
    rendered, unknown = photo.render_template(template)
    assert rendered[0] == "2020/{foo}"
    assert not unknown


def test_subst_unknown_val_with_default():
    """ Test substitution with unknown value specified """
    import locale
    import osxphotos

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{created.year}/{foo,bar}"
    rendered, unknown = photo.render_template(template)
    assert rendered[0] == "2020/{foo,bar}"
    assert unknown == ["foo"]


def test_subst_multi_1_1_2():
    """ Test that substitutions are correct """
    # one album, one keyword, two persons
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_1)
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = ["2018/Pumpkin Farm/Kids/Katie", "2018/Pumpkin Farm/Kids/Suzy"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_2_1_1():
    """ Test that substitutions are correct """
    # 2 albums, 1 keyword, 1 person
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_1)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["2_1_1"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = [
        "2018/Pumpkin Farm/Kids/Katie",
        "2018/Test Album/Kids/Katie",
        "2018/Multi Keyword/Kids/Katie",
    ]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_2_1_1_single():
    """ Test that substitutions are correct """
    # 2 albums, 1 keyword, 1 person but only do keywords
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_1)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["2_1_1"]])[0]

    template = "{keyword}"
    expected = ["Kids"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0():
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_1)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = ["2019/_/wedding/_", "2019/_/flowers/_"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_single():
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, but only do albums
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_1)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album}"
    expected = ["2019/_"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_default_val():
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, default vals provided
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_1)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person,NOPERSON}"
    expected = ["2019/NOALBUM/wedding/NOPERSON", "2019/NOALBUM/flowers/NOPERSON"]
    rendered, _ = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_default_val_unknown_val():
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, default vals provided, unknown val in template
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_1)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = (
        "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person}/{foo}/{{baz}}"
    )
    expected = [
        "2019/NOALBUM/wedding/_/{foo}/{baz}",
        "2019/NOALBUM/flowers/_/{foo}/{baz}",
    ]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == ["foo"]


def test_subst_multi_0_2_0_default_val_unknown_val_2():
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, default vals provided, unknown val in template
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_1)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person}/{foo,bar}/{{baz,bar}}"
    expected = [
        "2019/NOALBUM/wedding/_/{foo,bar}/{baz,bar}",
        "2019/NOALBUM/flowers/_/{foo,bar}/{baz,bar}",
    ]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == ["foo"]


def test_subst_multi_folder_albums_1():
    """ Test substitutions for folder_album are correct """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_4)

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["folder_album_1"]])[0]
    template = "{folder_album}"
    expected = ["Folder1/SubFolder2/AlbumInFolder"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_2():
    """ Test substitutions for folder_album are correct """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_4)

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["folder_album_no_folder"]])[0]
    template = "{folder_album}"
    expected = ["Pumpkin Farm", "Test Album"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_multi_folder_albums_3():
    """ Test substitutions for folder_album on < Photos 5 """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_14_6)

    # photo in an album in a folder
    photo = photosdb.photos(uuid=[UUID_DICT["mojave_album_1"]])[0]
    template = "{folder_album}"
    expected = ["Folder1/SubFolder2/AlbumInFolder", "Pumpkin Farm", "Test Album (1)"]
    rendered, unknown = photo.render_template(template)
    assert sorted(rendered) == sorted(expected)
    assert unknown == []


def test_subst_strftime():
    """ Test that strftime substitutions are correct """
    import locale
    import osxphotos

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_PLACES)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    rendered, unmatched = photo.render_template("{created.strftime,%Y-%m-%d-%H%M%S}")
    assert rendered[0] == "2020-02-04-190738"

    rendered, unmatched = photo.render_template("{created.strftime}")
    assert rendered[0] == "_"


def test_subst_expand_inplace_1():
    """ Test that substitutions are correct when expand_inplace=True """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_1)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{person}"
    expected = ["Katie,Suzy"]
    rendered, unknown = photo.render_template(template, expand_inplace=True)
    assert sorted(rendered) == sorted(expected)


def test_subst_expand_inplace_2():
    """ Test that substitutions are correct when expand_inplace=True """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_1)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{person}-{keyword}"
    expected = ["Katie,Suzy-Kids"]
    rendered, unknown = photo.render_template(template, expand_inplace=True)
    assert sorted(rendered) == sorted(expected)


def test_subst_expand_inplace_3():
    """ Test that substitutions are correct when expand_inplace=True and inplace_sep specified"""
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_1)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{person}-{keyword}"
    expected = ["Katie; Suzy-Kids"]
    rendered, unknown = photo.render_template(
        template, expand_inplace=True, inplace_sep="; "
    )
    assert sorted(rendered) == sorted(expected)


def test_comment():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_COMMENTS)
    for uuid in COMMENT_UUID_DICT:
        photo = photosdb.get_photo(uuid)
        comments = photo.render_template("{comment}")
        assert comments[0] == COMMENT_UUID_DICT[uuid]
