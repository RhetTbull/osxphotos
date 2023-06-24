"""Test unicode names in PhotoAlbum PhotoAlbumPhotoScript (#1085)"""

import pathlib
from unicodedata import normalize

import pytest

from osxphotos.platform import is_macos

if not is_macos:
    pytest.skip("requires macOS", allow_module_level=True)

import osxphotos
from osxphotos.photosalbum import PhotosAlbum, PhotosAlbumPhotoScript
from osxphotos.unicode import *

UNICODE_FOLDER_NFC = normalize("NFC", "FolderUnicode/føldêr2")
UNICODE_FOLDER_NFD = normalize("NFD", UNICODE_FOLDER_NFC)

UNICODE_ALBUM_NFC = normalize("NFC", "âlbüm")
UNICODE_ALBUM_NFD = normalize("NFD", UNICODE_ALBUM_NFC)


@pytest.mark.skipif(not is_macos, reason="requires macOS")
@pytest.mark.addalbum
def test_unicode_album(addalbum_library):
    """Test that unicode album name is handled correctly and a duplicate album is not created"""

    # get some photos to add
    photosdb = osxphotos.PhotosDB()
    photos = photosdb.query(osxphotos.QueryOptions(person=["Katie"]))

    # get the album
    album_name_nfc = UNICODE_ALBUM_NFC
    album_nfc = PhotosAlbum(album_name_nfc, split_folder=None)
    album_nfc.add_list(photos)

    # again with NFD
    album_name_nfd = UNICODE_ALBUM_NFD
    album_nfd = PhotosAlbum(album_name_nfd, split_folder=None)
    album_nfd.add_list(photos)

    assert album_nfc.album.uuid == album_nfd.album.uuid


@pytest.mark.skipif(not is_macos, reason="requires macOS")
@pytest.mark.addalbum
def test_unicode_folder_album_1(addalbum_library):
    """Test that unicode album name is handled correctly and a duplicate album is not created when album is in a folder"""

    # get some photos to add
    photosdb = osxphotos.PhotosDB()
    photos = photosdb.query(osxphotos.QueryOptions(person=["Katie"]))

    # get the album
    album_name_nfc = f"{UNICODE_FOLDER_NFC}/{UNICODE_ALBUM_NFC}"
    album_nfc = PhotosAlbum(album_name_nfc, split_folder="/")
    album_nfc.add_list(photos)

    # again with NFD
    album_name_nfd = f"{UNICODE_FOLDER_NFD}/{UNICODE_ALBUM_NFD}"
    album_nfd = PhotosAlbum(album_name_nfd, split_folder="/")
    album_nfd.add_list(photos)

    assert album_nfc.album.uuid == album_nfd.album.uuid


@pytest.mark.skipif(not is_macos, reason="requires macOS")
@pytest.mark.addalbum
def test_unicode_folder_album_2(addalbum_library):
    """Test that unicode album name is handled correctly and a duplicate album is not created when album is in a folder

    This is a variation of test_unicode_folder_album_1 where the album is created in the same unicode folder as the previous album
    """

    # get some photos to add
    photosdb = osxphotos.PhotosDB()
    photos = photosdb.query(osxphotos.QueryOptions(person=["Katie"]))

    # get the album
    album_name_nfc = f"{UNICODE_FOLDER_NFC}/{UNICODE_ALBUM_NFC}"
    album_nfc = PhotosAlbum(album_name_nfc, split_folder="/")
    album_nfc.add_list(photos)

    # again with NFD
    album_name_nfd = f"{UNICODE_FOLDER_NFC}/{UNICODE_ALBUM_NFD}"
    album_nfd = PhotosAlbum(album_name_nfd, split_folder="/")
    album_nfd.add_list(photos)

    assert album_nfc.album.uuid == album_nfd.album.uuid
