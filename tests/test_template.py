""" Test template.py """
import pytest

PHOTOS_DB_1 = "./tests/Test-Places-Catalina-10_15_1.photoslibrary/database/photos.db"
PHOTOS_DB_2 = "./tests/Test-10.15.1.photoslibrary/database/photos.db"
UUID_DICT = {
    "place_dc": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "1_1_2": "1EB2B765-0765-43BA-A90C-0D0580E6172C",
    "2_1_1": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "0_2_0": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
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
    "{created.doy}": "035",
    "{modified.date}": "2020-03-21",
    "{modified.year}": "2020",
    "{modified.yy}": "20",
    "{modified.mm}": "03",
    "{modified.month}": "March",
    "{modified.mon}": "Mar",
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


def test_lookup():
    """ Test that a lookup is returned for every possible value """
    import re
    import osxphotos
    from osxphotos.template import (
        get_template_value,
        render_filepath_template,
        TEMPLATE_SUBSTITUTIONS,
    )

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_1)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for subst in TEMPLATE_SUBSTITUTIONS:
        lookup_str = re.match(r"\{([^\\,}]+)\}", subst).group(1)
        lookup = get_template_value(lookup_str, photo)
        assert lookup or lookup is None


def test_subst():
    """ Test that substitutions are correct """
    import locale
    import osxphotos
    from osxphotos.template import render_filepath_template

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_1)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for template in TEMPLATE_VALUES:
        rendered, _ = render_filepath_template(template, photo)
        assert rendered[0] == TEMPLATE_VALUES[template]


def test_subst_default_val():
    """ Test substitution with default value specified """
    import locale
    import osxphotos
    from osxphotos.template import render_filepath_template

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_1)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{place.name.area_of_interest,UNKNOWN}"
    rendered, _ = render_filepath_template(template, photo)
    assert rendered[0] == "UNKNOWN"


def test_subst_default_val_2():
    """ Test substitution with ',' but no default value """
    import locale
    import osxphotos
    from osxphotos.template import render_filepath_template

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_1)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{place.name.area_of_interest,}"
    rendered, _ = render_filepath_template(template, photo)
    assert rendered[0] == "_"


def test_subst_unknown_val():
    """ Test substitution with unknown value specified """
    import locale
    import osxphotos
    from osxphotos.template import render_filepath_template

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_1)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{created.year}/{foo}"
    rendered, unknown = render_filepath_template(template, photo)
    assert rendered[0] == "2020/{foo}"
    assert unknown == ["foo"]

    template = "{place.name.area_of_interest,}"
    rendered, _ = render_filepath_template(template, photo)
    assert rendered[0] == "_"


def test_subst_double_brace():
    """ Test substitution with double brace {{ which should be ignored """
    import osxphotos
    from osxphotos.template import render_filepath_template

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_1)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{created.year}/{{foo}}"
    rendered, unknown = render_filepath_template(template, photo)
    assert rendered[0] == "2020/{foo}"
    assert not unknown


def test_subst_unknown_val_with_default():
    """ Test substitution with unknown value specified """
    import locale
    import osxphotos
    from osxphotos.template import render_filepath_template

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_1)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{created.year}/{foo,bar}"
    rendered, unknown = render_filepath_template(template, photo)
    assert rendered[0] == "2020/{foo,bar}"
    assert unknown == ["foo"]


def test_subst_multi_1_1_2():
    """ Test that substitutions are correct """
    # one album, one keyword, two persons
    import osxphotos
    from osxphotos.template import render_filepath_template

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_2)
    photo = photosdb.photos(uuid=[UUID_DICT["1_1_2"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = ["2018/Pumpkin Farm/Kids/Katie", "2018/Pumpkin Farm/Kids/Suzy"]
    rendered, _ = render_filepath_template(template, photo)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_2_1_1():
    """ Test that substitutions are correct """
    # 2 albums, 1 keyword, 1 person
    import osxphotos
    from osxphotos.template import render_filepath_template

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_2)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["2_1_1"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = ["2018/Pumpkin Farm/Kids/Katie", "2018/Test Album/Kids/Katie"]
    rendered, _ = render_filepath_template(template, photo)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_2_1_1_single():
    """ Test that substitutions are correct """
    # 2 albums, 1 keyword, 1 person but only do keywords
    import osxphotos
    from osxphotos.template import render_filepath_template

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_2)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["2_1_1"]])[0]

    template = "{keyword}"
    expected = ["Kids"]
    rendered, _ = render_filepath_template(template, photo)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0():
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons
    import osxphotos
    from osxphotos.template import render_filepath_template

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_2)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album}/{keyword}/{person}"
    expected = ["2019/_/wedding/_", "2019/_/flowers/_"]
    rendered, _ = render_filepath_template(template, photo)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_single():
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, but only do albums
    import osxphotos
    from osxphotos.template import render_filepath_template

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_2)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album}"
    expected = ["2019/_"]
    rendered, _ = render_filepath_template(template, photo)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_default_val():
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, default vals provided
    import osxphotos
    from osxphotos.template import render_filepath_template

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_2)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person,NOPERSON}"
    expected = ["2019/NOALBUM/wedding/NOPERSON", "2019/NOALBUM/flowers/NOPERSON"]
    rendered, _ = render_filepath_template(template, photo)
    assert sorted(rendered) == sorted(expected)


def test_subst_multi_0_2_0_default_val_unknown_val():
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, default vals provided, unknown val in template
    import osxphotos
    from osxphotos.template import render_filepath_template

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_2)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = (
        "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person}/{foo}/{{baz}}"
    )
    expected = [
        "2019/NOALBUM/wedding/_/{foo}/{baz}",
        "2019/NOALBUM/flowers/_/{foo}/{baz}",
    ]
    rendered, unknown = render_filepath_template(template, photo)
    assert sorted(rendered) == sorted(expected)
    assert unknown == ["foo"]


def test_subst_multi_0_2_0_default_val_unknown_val_2():
    """ Test that substitutions are correct """
    # 0 albums, 2 keywords, 0 persons, default vals provided, unknown val in template
    import osxphotos
    from osxphotos.template import render_filepath_template

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_2)
    # one album, one keyword, two persons
    photo = photosdb.photos(uuid=[UUID_DICT["0_2_0"]])[0]

    template = "{created.year}/{album,NOALBUM}/{keyword,NOKEYWORD}/{person}/{foo,bar}/{{baz,bar}}"
    expected = [
        "2019/NOALBUM/wedding/_/{foo,bar}/{baz,bar}",
        "2019/NOALBUM/flowers/_/{foo,bar}/{baz,bar}",
    ]
    rendered, unknown = render_filepath_template(template, photo)
    assert sorted(rendered) == sorted(expected)
    assert unknown == ["foo"]
