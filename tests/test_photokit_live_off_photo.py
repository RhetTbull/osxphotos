"""PhotoAsset must export the original paired video of a Live Photo whose Live was turned off."""

import pathlib

import pytest

from osxphotos.platform import is_macos

if is_macos:
    import Foundation
    import Photos

    from osxphotos import photokit
    from osxphotos.photokit import (
        PHOTOS_VERSION_CURRENT,
        PHOTOS_VERSION_ORIGINAL,
        PHOTOS_VERSION_UNADJUSTED,
        PhotoAsset,
    )
else:
    pytest.skip(allow_module_level=True, reason="Tests only run on macOS")


class FakeResource:
    def __init__(self, resource_type, uti, data):
        self._type = resource_type
        self._uti = uti
        self.data = data

    def type(self):
        return self._type

    def uniformTypeIdentifier(self):
        return self._uti


class FakePHAsset:
    def localIdentifier(self):
        return "TEST-ASSET-ID"

    def mediaType(self):
        return Photos.PHAssetMediaTypeImage


class FakePHAssetResource:
    """Resources of a Live Photo after Live was turned off in an edit"""

    @staticmethod
    def assetResourcesForAsset_(asset):
        return Foundation.NSArray.arrayWithArray_(
            [
                FakeResource(
                    Photos.PHAssetResourceTypePhoto, "public.heic", b"original photo"
                ),
                FakeResource(
                    Photos.PHAssetResourceTypeAdjustmentData,
                    "com.apple.property-list",
                    b"adjustments",
                ),
                FakeResource(
                    Photos.PHAssetResourceTypePairedVideo,
                    "com.apple.quicktime-movie",
                    b"original video",
                ),
                FakeResource(
                    Photos.PHAssetResourceTypeFullSizePairedVideo,
                    "com.apple.quicktime-movie",
                    b"edited video",
                ),
                FakeResource(
                    Photos.PHAssetResourceTypeFullSizePhoto,
                    "public.heic",
                    b"edited photo",
                ),
            ]
        )


class FakeImageManager:
    def requestImageDataAndOrientationForAsset_options_resultHandler_(
        self, asset, options, handler
    ):
        handler(b"photo", "public.heic", 0, {})


class FakeResourceManager:
    def requestDataForAssetResource_options_dataReceivedHandler_completionHandler_(
        self, resource, options, data_handler, completion_handler
    ):
        data_handler(resource.data)
        completion_handler(None)


PHOTO_AND_VIDEO = {"IMG_0001.heic": b"photo", "IMG_0001.mov": b"original video"}
PHOTO_ONLY = {"IMG_0001.heic": b"photo"}


@pytest.mark.parametrize(
    "version,video,expected",
    [
        (PHOTOS_VERSION_ORIGINAL, True, PHOTO_AND_VIDEO),
        (PHOTOS_VERSION_UNADJUSTED, True, PHOTO_AND_VIDEO),
        (PHOTOS_VERSION_CURRENT, True, PHOTO_ONLY),
        (PHOTOS_VERSION_ORIGINAL, False, PHOTO_ONLY),
    ],
)
def test_live_off_photo_export_video(monkeypatch, tmp_path, version, video, expected):
    resource_manager = FakeResourceManager()
    monkeypatch.setattr(photokit.Photos, "PHAssetResource", FakePHAssetResource)
    monkeypatch.setattr(
        photokit.Photos,
        "PHAssetResourceManager",
        type(
            "PHAssetResourceManager",
            (),
            {"defaultManager": lambda: resource_manager},
        ),
    )
    exported = PhotoAsset(FakeImageManager(), FakePHAsset()).export(
        tmp_path, "IMG_0001.HEIC", version=version, video=video
    )
    assert {pathlib.Path(f).name: pathlib.Path(f).read_bytes() for f in exported} == (
        expected
    )
