"""Test {seq} template """

import pytest

import osxphotos.phototemplate
import osxphotos.template_counter as template_counter

PHOTOSDB = "tests/Test-13.0.0.photoslibrary"

TEMPLATE_TEST_DATA = [
    ("{counter}", "0"),
    ("{counter:03d}", "000"),
    ("{counter:03d} {counter:03d}", "000 001"),
    ("{counter:05d(2,,2)}-{counter:05d(2,,2)}", "00002-00004"),
    ("{counter.a}-{counter.b}-{counter.a}", "0-0-1"),
    ("{counter.a:03d(3)}", "003"),
    ("{counter(1,3,)}{counter(1,3,)}{counter(1,3,)}{counter(1,3,)}", "1212"),
    ("{counter(,,2)}{counter(,,2)}{counter(,,2)}{counter(,,2)}", "0246"),
]

INVALID_TEMPLATES = [
    "{counter(1,2,3,4)}",
    "{counter(1,-1,1)}",
    "{counter.a}-{counter.a(1,10,2)}",
    "{counter(a,b,c)}",
]


@pytest.fixture(scope="function", autouse=True)
def reset_seq_count():
    """Reset _global_seq_count to 0 before each test"""
    template_counter.reset_all_counters()


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOSDB)


@pytest.mark.parametrize("template,expected", TEMPLATE_TEST_DATA)
def test_counter(photosdb, template, expected):
    """Test {seq} template"""
    photo = photosdb.photos()[0]
    result = photo.render_template(template)
    assert result[0][0] == expected
    template_counter.reset_all_counters()


@pytest.mark.parametrize("template", INVALID_TEMPLATES)
def test_invalid_counter(photosdb, template):
    """Test invalid {counter} template"""
    photo = photosdb.photos()[0]
    with pytest.raises(ValueError):
        photo.render_template(template)


def test_reset_counter(photosdb):
    """Test reset_counter()"""
    photo = photosdb.photos()[0]
    result = photo.render_template("{counter}")
    assert result[0][0] == "0"
    result = photo.render_template("{counter}")
    assert result[0][0] == "1"

    template_counter.reset_counter("counter")
    result = photo.render_template("{counter}")
    assert result[0][0] == "0"


def test_reset_all_counters(photosdb):
    """Test reset_all_counters()"""
    photo = photosdb.photos()[0]
    result = photo.render_template("{counter.a}")
    assert result[0][0] == "0"
    result = photo.render_template("{counter.b}")
    assert result[0][0] == "0"

    template_counter.reset_all_counters()
    result = photo.render_template("{counter.a}")
    assert result[0][0] == "0"
    result = photo.render_template("{counter.b}")
    assert result[0][0] == "0"
