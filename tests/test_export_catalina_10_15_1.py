import pytest

from osxphotos import _UNKNOWN_PERSON

# TODO: put some of this code into a pre-function

PHOTOS_DB = "./tests/Test-10.15.1.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-10.15.1.photoslibrary/database/Photos.sqlite"
PHOTOS_LIBRARY_PATH = "/Test-10.15.1.photoslibrary"

KEYWORDS = [
    "Kids",
    "wedding",
    "flowers",
    "England",
    "London",
    "London 2018",
    "St. James's Park",
    "UK",
    "United Kingdom",
]
# Photos 5 includes blank person for detected face
PERSONS = ["Katie", "Suzy", "Maria", _UNKNOWN_PERSON]
ALBUMS = [
    "Pumpkin Farm",
    "Test Album",
]  # Note: there are 2 albums named "Test Album" for testing duplicate album names
KEYWORDS_DICT = {
    "Kids": 4,
    "wedding": 2,
    "flowers": 1,
    "England": 1,
    "London": 1,
    "London 2018": 1,
    "St. James's Park": 1,
    "UK": 1,
    "United Kingdom": 1,
}
PERSONS_DICT = {"Katie": 3, "Suzy": 2, "Maria": 1, _UNKNOWN_PERSON: 1}
ALBUM_DICT = {
    "Pumpkin Farm": 3,
    "Test Album": 2,
}  # Note: there are 2 albums named "Test Album" for testing duplicate album names

UUID_DICT = {
    "missing": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "favorite": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "not_favorite": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "hidden": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "not_hidden": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "has_adjustments": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "no_adjustments": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "location": "DC99FBDD-7A52-4100-A5BB-344131646C30",
    "no_location": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "external_edit": "DC99FBDD-7A52-4100-A5BB-344131646C30",
    "no_external_edit": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "export": "D79B8D77-BFFC-460B-9312-034F2877D35B",  # "Pumkins2.jpg"
}

def test_export_1():
    # test basic export
    # get an unedited image and export it using default filename
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename()
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest)

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)

    # remove the temporary file
    os.remove(got_dest)


def test_export_2():
    # test export with user provided filename
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename)

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)

    # remove the temporary file
    os.remove(got_dest)


def test_export_3():
    # test file already exists and test increment=True (default)
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename()
    filename2 = pathlib.Path(filename)
    filename2 = f"{filename2.stem} (1){filename2.suffix}"
    expected_dest = os.path.join(dest, filename)
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest = photos[0].export(dest)
    got_dest_2 = photos[0].export(dest)

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)

    # remove the temporary file
    os.remove(got_dest)
    os.remove(got_dest_2)


def test_export_4():
    # test user supplied file already exists and test increment=True (default)
    import os
    import os.path
    import pathlib
    import tempfile
    import time

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    filename2 = f"osxphotos-export-2-test-{timestamp} (1).jpg"
    expected_dest = os.path.join(dest, filename)
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest = photos[0].export(dest, filename)
    got_dest_2 = photos[0].export(dest, filename)

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)

    # remove the temporary file
    os.remove(got_dest)
    os.remove(got_dest_2)


def test_export_5():
    # test file already exists and test increment=True (default)
    # and overwrite = True
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename()
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)
    got_dest_2 = photos[0].export(dest, overwrite=True)

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)

    # remove the temporary file
    os.remove(got_dest)


def test_export_6():
    # test user supplied file already exists and test increment=True (default)
    # and overwrite = True
    import os
    import os.path
    import pathlib
    import tempfile
    import time

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename)
    got_dest_2 = photos[0].export(dest, filename, overwrite=True)

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)

    # remove the temporary file
    os.remove(got_dest)


def test_export_7():
    # test file already exists and test increment=False (not default), overwrite=False (default)
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename()
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)
    with pytest.raises(Exception) as e:
        # try to export again with increment = False
        assert photos[0].export(dest, increment=False)
    assert e.type == type(FileExistsError())

    # remove the temporary file
    os.remove(got_dest)


def test_export_8():
    # try to export missing file
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["missing"]])

    filename = photos[0].filename()
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest)
    assert e.type == type(FileNotFoundError())


def test_export_9():
    # try to export edited file that's not edited
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    filename = photos[0].filename()
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, edited=True)
    assert e.type == type(FileNotFoundError())


def test_export_10():
    # try to export edited file that's not edited and name provided
    # should raise exception
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, filename, edited=True)
    assert e.type == type(FileNotFoundError())


def test_export_11():
    # export edited file with name provided
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename, edited=True)
    assert got_dest == expected_dest

    # remove the temporary file
    os.remove(got_dest)


def test_export_12():
    # export edited file with default name
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    edited_name = pathlib.Path(photos[0].path_edited()).name
    edited_suffix = pathlib.Path(edited_name).suffix
    filename = pathlib.Path(photos[0].filename()).stem + "_edited" + edited_suffix
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, edited=True)
    assert got_dest == expected_dest

    # remove the temporary file
    os.remove(got_dest)


def test_export_13():
    # export to invalid destination
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    dest = tempfile.gettempdir()

    # create a folder that doesn't exist
    i = 0
    while os.path.isdir(dest):
        dest = os.path.join(dest, str(i))
        i += 1

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename()
    expected_dest = os.path.join(dest, filename)

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest)
    assert e.type == type(FileNotFoundError())
