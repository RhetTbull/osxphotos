# Test live photos

import pytest

import osxphotos

PHOTOS_DB = "./tests/Test-Cloud-10.15.1.photoslibrary/database/photos.db"

UUID_DICT = {
    "live": "51F2BEF7-431A-4D31-8AC1-3284A57826AE",
    "not_live": "9D671650-B2FD-4760-84CA-FD25AF622C63",
}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_live_photo(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["live"]])

    assert photos[0].live_photo
    assert photos[0].path_live_photo is not None


def test_not_live_photo(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["not_live"]])

    assert not photos[0].live_photo
    assert photos[0].path_live_photo is None


def test_export_live_1(photosdb):
    # export a live photo and associated .mov
    import glob
    import os.path
    import pathlib
    import tempfile

    dest = tempfile.TemporaryDirectory(prefix="osxphotos_")

    photos = photosdb.photos(uuid=[UUID_DICT["live"]])

    filename = photos[0].original_filename
    expected_dest = os.path.join(dest.name, filename)
    got_dest = photos[0].export(dest.name, live_photo=True)[0]
    got_movie = f"{pathlib.Path(got_dest).parent / pathlib.Path(got_dest).stem}.mov"
    files = glob.glob(os.path.join(dest.name, "*"))

    assert len(files) == 2
    assert expected_dest == got_dest
    assert expected_dest in files
    assert got_movie in files


def test_export_live_2(photosdb):
    # don't export the live photo
    import glob
    import os.path
    import pathlib
    import tempfile

    dest = tempfile.TemporaryDirectory(prefix="osxphotos_")

    photos = photosdb.photos(uuid=[UUID_DICT["live"]])

    filename = photos[0].original_filename
    expected_dest = os.path.join(dest.name, filename)
    got_dest = photos[0].export(dest.name, live_photo=False)[0]
    got_movie = f"{pathlib.Path(got_dest).parent / pathlib.Path(got_dest).stem}.mov"
    files = glob.glob(os.path.join(dest.name, "*"))

    assert len(files) == 1
    assert expected_dest == got_dest
    assert expected_dest in files
    assert got_movie not in files


def test_export_live_3(photosdb):
    # export a live photo and associated .mov,
    # check list return of export
    import glob
    import os.path
    import pathlib
    import tempfile

    dest = tempfile.TemporaryDirectory(prefix="osxphotos_")

    photos = photosdb.photos(uuid=[UUID_DICT["live"]])

    filename = photos[0].original_filename
    expected_dest = os.path.join(dest.name, filename)
    expected_mov = f"{dest.name}/{pathlib.Path(expected_dest).stem}.mov"
    got_files = photos[0].export(dest.name, live_photo=True)
    # got_dest = got_files[0]
    # got_movie = f"{pathlib.Path(got_dest).parent / pathlib.Path(got_dest).stem}.mov"
    # files = glob.glob(os.path.join(dest.name, "*"))

    assert len(got_files) == 2
    assert expected_dest in got_files
    assert expected_mov in got_files


# def test_export_live_3():
#     # export a live photo and associated .mov and edited file
#     import glob
#     import os.path
#     import pathlib
#     import tempfile

#     import osxphotos

#     dest = tempfile.TemporaryDirectory(prefix="osxphotos_")

#     photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
#     photos = photosdb.photos(uuid=[UUID_DICT["live"]])

#     filename = photos[0].filename
#     expected_dest = os.path.join(dest.name, filename)
#     got_dest = photos[0].export(dest.name, live_photo=True, edited=True)
#     got_movie = f"{pathlib.Path(got_dest).parent / pathlib.Path(got_dest).stem}.mov"
#     expected_dest = os.path.join(dest.name, filename)
#     files = glob.glob(os.path.join(dest.name, "*"))

#     assert len(files) == 2
#     assert expected_dest == got_dest
#     assert expected_dest in files
#     assert got_movie in files
