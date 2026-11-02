"""LivePhotoAsset must export an edited Live Photo's original pair, not its edit (#866)."""

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
        LivePhotoAsset,
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


class FakePHAssetResource:
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
                    Photos.PHAssetResourceTypeFullSizePhoto,
                    "public.heic",
                    b"edited photo",
                ),
                FakeResource(
                    Photos.PHAssetResourceTypeFullSizePairedVideo,
                    "com.apple.quicktime-movie",
                    b"edited video",
                ),
            ]
        )


class FakeLivePhotoRequest:
    """The PHLivePhoto of an edited Live Photo holds the edited pair for any version"""

    @classmethod
    def alloc(cls):
        return cls()

    def initWithManager_Asset_(self, manager, asset):
        return self

    def requestLivePhotoResources(self, version):
        return [
            FakeResource(
                Photos.PHAssetResourceTypePhoto, "public.heic", b"edited photo"
            ),
            FakeResource(
                Photos.PHAssetResourceTypePairedVideo,
                "com.apple.quicktime-movie",
                b"edited video",
            ),
        ]

    def dealloc(self):
        pass


class FakeResourceManager:
    def requestDataForAssetResource_options_dataReceivedHandler_completionHandler_(
        self, resource, options, data_handler, completion_handler
    ):
        data_handler(resource.data)
        completion_handler(None)


@pytest.mark.parametrize(
    "version,expected",
    [
        (PHOTOS_VERSION_CURRENT, (b"edited photo", b"edited video")),
        (PHOTOS_VERSION_ORIGINAL, (b"original photo", b"original video")),
        (PHOTOS_VERSION_UNADJUSTED, (b"original photo", b"original video")),
    ],
)
def test_live_photo_export_version(monkeypatch, tmp_path, version, expected):
    manager = FakeResourceManager()
    monkeypatch.setattr(photokit, "LivePhotoRequest", FakeLivePhotoRequest)
    monkeypatch.setattr(photokit.Photos, "PHAssetResource", FakePHAssetResource)
    monkeypatch.setattr(
        photokit.Photos,
        "PHAssetResourceManager",
        type("PHAssetResourceManager", (), {"defaultManager": lambda: manager}),
    )
    exported = LivePhotoAsset(None, FakePHAsset()).export(
        tmp_path, "IMG_0001.HEIC", version=version
    )
    assert [pathlib.Path(f).name for f in exported] == ["IMG_0001.heic", "IMG_0001.mov"]
    assert tuple(pathlib.Path(f).read_bytes() for f in exported) == expected
