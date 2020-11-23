""" test photokit.py methods """

import os
import pathlib
import tempfile

import pytest

from osxphotos.photokit import (
    LivePhotoAsset,
    PhotoAsset,
    PhotoLibrary,
    VideoAsset,
    PHOTOS_VERSION_CURRENT,
    PHOTOS_VERSION_ORIGINAL,
    PHOTOS_VERSION_UNADJUSTED,
)

skip_test = "OSXPHOTOS_TEST_EXPORT" not in os.environ
pytestmark = pytest.mark.skipif(
    skip_test, reason="Skip if not running with author's personal library."
)


UUID_DICT = {
    "plain_photo": {
        "uuid": "A8D646C3-89A9-4D74-8001-4EB46BA55B94",
        "filename": "IMG_8844.JPG",
    },
    "hdr": {"uuid": "DA87C6FF-60E8-4DCB-A21D-9C57595667F1", "filename": "IMG_6162.JPG"},
    "selfie": {
        "uuid": "316AEBE0-971D-4A33-833C-6BDBFF83469B",
        "filename": "IMG_1929.JPG",
    },
    "video": {
        "uuid": "5814D9DE-FAB6-473A-9C9A-5A73C6DD1AF5",
        "filename": "IMG_9411.TRIM.MOV",
    },
    "hasadjustments": {
        "uuid": "2B2D5434-6D31-49E2-BF47-B973D34A317B",
        "filename": "IMG_2860.JPG",
        "adjusted_size": 3012634,
        "unadjusted_size": 2580058,
    },
    "slow_mo": {
        "uuid": "DAABC6D9-1FBA-4485-AA39-0A2B100300B1",
        "filename": "IMG_4055.MOV",
    },
    "live_photo": {
        "uuid": "612CE30B-3D8F-417A-9B14-EC42CBA10ACC",
        "filename": "IMG_3259.HEIC",
        "filename_video": "IMG_3259.mov",
    },
    "burst": {
        "uuid": "CD97EC84-71F0-40C6-BAC1-2BABEE305CAC",
        "filename": "IMG_8196.JPG",
        "burst_selected": 3,
        "burst_all": 5,
    },
}


def test_fetch_uuid():
    """ test fetch_uuid """
    uuid = UUID_DICT["plain_photo"]["uuid"]
    filename = UUID_DICT["plain_photo"]["filename"]

    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)
    assert isinstance(photo, PhotoAsset)


def test_plain_photo():
    """ test plain_photo """
    uuid = UUID_DICT["plain_photo"]["uuid"]
    filename = UUID_DICT["plain_photo"]["filename"]

    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)
    assert photo.original_filename == filename
    assert photo.isphoto
    assert not photo.ismovie


def test_hdr():
    """ test hdr """
    uuid = UUID_DICT["hdr"]["uuid"]
    filename = UUID_DICT["hdr"]["filename"]

    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)
    assert photo.original_filename == filename
    assert photo.hdr


def test_burst():
    """ test burst and burstid """
    test_dict = UUID_DICT["burst"]
    uuid = test_dict["uuid"]
    filename = test_dict["filename"]

    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)
    assert photo.original_filename == filename
    assert photo.burst
    assert photo.burstid



# def test_selfie():
#     """ test selfie """
#     uuid = UUID_DICT["selfie"]["uuid"]
#     filename = UUID_DICT["selfie"]["filename"]

#     lib = PhotoLibrary()
#     photo = lib.fetch_uuid(uuid)
#     assert photo.original_filename == filename
#     assert photo.selfie


def test_video():
    """ test ismovie """
    uuid = UUID_DICT["video"]["uuid"]
    filename = UUID_DICT["video"]["filename"]

    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)
    assert isinstance(photo, VideoAsset)
    assert photo.original_filename == filename
    assert photo.ismovie
    assert not photo.isphoto


def test_slow_mo():
    """ test slow_mo """
    test_dict = UUID_DICT["slow_mo"]
    uuid = test_dict["uuid"]
    filename = test_dict["filename"]

    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)
    assert isinstance(photo, VideoAsset)
    assert photo.original_filename == filename
    assert photo.ismovie
    assert photo.slow_mo
    assert not photo.isphoto


### PhotoAsset


def test_export_photo_original():
    """ test PhotoAsset.export """
    test_dict = UUID_DICT["hasadjustments"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, version=PHOTOS_VERSION_ORIGINAL)
        export_path = pathlib.Path(export_path[0])
        assert export_path.is_file()
        filename = test_dict["filename"]
        assert export_path.stem == pathlib.Path(filename).stem
        assert export_path.stat().st_size == test_dict["unadjusted_size"]


def test_export_photo_unadjusted():
    """ test PhotoAsset.export """
    test_dict = UUID_DICT["hasadjustments"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, version=PHOTOS_VERSION_UNADJUSTED)
        export_path = pathlib.Path(export_path[0])
        assert export_path.is_file()
        filename = test_dict["filename"]
        assert export_path.stem == pathlib.Path(filename).stem
        assert export_path.stat().st_size == test_dict["unadjusted_size"]


def test_export_photo_current():
    """ test PhotoAsset.export """
    test_dict = UUID_DICT["hasadjustments"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir)
        export_path = pathlib.Path(export_path[0])
        assert export_path.is_file()
        filename = test_dict["filename"]
        assert export_path.stem == pathlib.Path(filename).stem
        assert export_path.stat().st_size == test_dict["adjusted_size"]


### VideoAsset


def test_export_video_original():
    """ test VideoAsset.export """
    test_dict = UUID_DICT["video"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, version=PHOTOS_VERSION_ORIGINAL)
        export_path = pathlib.Path(export_path[0])
        assert export_path.is_file()
        filename = test_dict["filename"]
        assert export_path.stem == pathlib.Path(filename).stem


def test_export_video_unadjusted():
    """ test VideoAsset.export """
    test_dict = UUID_DICT["video"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, version=PHOTOS_VERSION_UNADJUSTED)
        export_path = pathlib.Path(export_path[0])
        assert export_path.is_file()
        filename = test_dict["filename"]
        assert export_path.stem == pathlib.Path(filename).stem


def test_export_video_current():
    """ test VideoAsset.export """
    test_dict = UUID_DICT["video"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, version=PHOTOS_VERSION_CURRENT)
        export_path = pathlib.Path(export_path[0])
        assert export_path.is_file()
        filename = test_dict["filename"]
        assert export_path.stem == pathlib.Path(filename).stem


### Slow-Mo VideoAsset


def test_export_slow_mo_original():
    """ test VideoAsset.export for slow mo video"""
    test_dict = UUID_DICT["slow_mo"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, version=PHOTOS_VERSION_ORIGINAL)
        export_path = pathlib.Path(export_path[0])
        assert export_path.is_file()
        filename = test_dict["filename"]
        assert export_path.stem == pathlib.Path(filename).stem


def test_export_slow_mo_unadjusted():
    """ test VideoAsset.export for slow mo video"""
    test_dict = UUID_DICT["slow_mo"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, version=PHOTOS_VERSION_UNADJUSTED)
        export_path = pathlib.Path(export_path[0])
        assert export_path.is_file()
        filename = test_dict["filename"]
        assert export_path.stem == pathlib.Path(filename).stem


def test_export_slow_mo_current():
    """ test VideoAsset.export for slow mo video"""
    test_dict = UUID_DICT["slow_mo"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, version=PHOTOS_VERSION_CURRENT)
        export_path = pathlib.Path(export_path[0])
        assert export_path.is_file()
        filename = test_dict["filename"]
        assert export_path.stem == pathlib.Path(filename).stem


### LivePhotoAsset


def test_export_live_original():
    """ test LivePhotoAsset.export """
    test_dict = UUID_DICT["live_photo"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, version=PHOTOS_VERSION_ORIGINAL)
        for f in export_path:
            filepath = pathlib.Path(f)
            assert filepath.is_file()
            filename = test_dict["filename"]
            assert filepath.stem == pathlib.Path(filename).stem


def test_export_live_unadjusted():
    """ test LivePhotoAsset.export """
    test_dict = UUID_DICT["live_photo"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, version=PHOTOS_VERSION_UNADJUSTED)
        for file in export_path:
            filepath = pathlib.Path(file)
            assert filepath.is_file()
            filename = test_dict["filename"]
            assert filepath.stem == pathlib.Path(filename).stem


def test_export_live_current():
    """ test LivePhotAsset.export """
    test_dict = UUID_DICT["live_photo"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, version=PHOTOS_VERSION_CURRENT)
        for file in export_path:
            filepath = pathlib.Path(file)
            assert filepath.is_file()
            filename = test_dict["filename"]
            assert filepath.stem == pathlib.Path(filename).stem


def test_export_live_current_just_photo():
    """ test LivePhotAsset.export """
    test_dict = UUID_DICT["live_photo"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, photo=True, video=False)
        assert len(export_path) == 1
        assert export_path[0].lower().endswith(".heic")


def test_export_live_current_just_video():
    """ test LivePhotAsset.export """
    test_dict = UUID_DICT["live_photo"]
    uuid = test_dict["uuid"]
    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)

    with tempfile.TemporaryDirectory(prefix="photokit_test") as tempdir:
        export_path = photo.export(tempdir, photo=False, video=True)
        assert len(export_path) == 1
        assert export_path[0].lower().endswith(".mov")


def test_fetch_burst_uuid():
    """ test fetch_burst_uuid """
    test_dict = UUID_DICT["burst"]
    uuid = test_dict["uuid"]
    filename = test_dict["filename"]

    lib = PhotoLibrary()
    photo = lib.fetch_uuid(uuid)
    bursts_selected = lib.fetch_burst_uuid(photo.burstid)
    assert len(bursts_selected) == test_dict["burst_selected"]
    assert isinstance(bursts_selected[0], PhotoAsset)

    bursts_all = lib.fetch_burst_uuid(photo.burstid, all=True)
    assert len(bursts_all) == test_dict["burst_all"]
    assert isinstance(bursts_all[0], PhotoAsset)
