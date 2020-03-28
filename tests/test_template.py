""" Test template.py """
import pytest

PHOTOS_DB = "./tests/Test-Places-Catalina-10_15_1.photoslibrary/database/photos.db"

UUID_DICT = {"place_dc": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546"}


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

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
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
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    for template in TEMPLATE_VALUES:
        rendered, _ = render_filepath_template(template, photo)
        assert rendered == TEMPLATE_VALUES[template]


def test_subst_default_val():
    """ Test substitution with default value specified """
    import locale
    import osxphotos
    from osxphotos.template import render_filepath_template

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{place.name.area_of_interest,UNKNOWN}"
    rendered, _ = render_filepath_template(template, photo)
    assert rendered == "UNKNOWN"


def test_subst_default_val_2():
    """ Test substitution with ',' but no default value """
    import locale
    import osxphotos
    from osxphotos.template import render_filepath_template

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{place.name.area_of_interest,}"
    rendered, _ = render_filepath_template(template, photo)
    assert rendered == "_"


def test_subst_unknown_val():
    """ Test substitution with unknown value specified """
    import locale
    import osxphotos
    from osxphotos.template import render_filepath_template

    locale.setlocale(locale.LC_ALL, "en_US")
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]

    template = "{created.year}/{foo}"
    rendered, unknown = render_filepath_template(template, photo)
    assert rendered == "2020/{foo}"
    assert unknown == ["{foo}"]
