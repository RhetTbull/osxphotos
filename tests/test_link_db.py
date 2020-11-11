""" Test PhotosDB._link_db_file """

import pytest

from tempdiskimage import TempDiskImage

PHOTOS_DB = "tests/Test-Movie-5_0.photoslibrary"

def test_link_db(capsys):
    """ Test that database doesn't get copied when opened """
    import osxphotos
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB, verbose=print)
    captured = capsys.readouterr()
    assert "creating temporary copy" not in captured.out

def test_copy_db(capsys):
    """ Test that database does get copied if on different filesystem """
    import pathlib
    import tempfile
    import osxphotos
    
    from osxphotos.fileutil import FileUtil
    
    with TempDiskImage(prefix="osxphotos") as tmpimg:
        newdb = pathlib.Path(tmpimg.name) / pathlib.Path(PHOTOS_DB).name
        FileUtil.copy(PHOTOS_DB,newdb)
        photosdb = osxphotos.PhotosDB(dbfile=newdb, verbose=print)
        captured = capsys.readouterr()
        assert "creating temporary copy" in captured.out