"""VideoAsset must request PHVideoRequestOptionsVersion values, not the image ones."""

import pytest

from osxphotos.platform import is_macos

if is_macos:
    import Photos

    from osxphotos.photokit import (
        PHOTOS_VERSION_CURRENT,
        PHOTOS_VERSION_ORIGINAL,
        PHOTOS_VERSION_UNADJUSTED,
        VideoAsset,
    )
else:
    pytest.skip(allow_module_level=True, reason="Tests only run on macOS")


class FakePHAsset:
    def localIdentifier(self):
        return "TEST-ASSET-ID"


class FakeImageManager:
    def requestAVAssetForVideo_options_resultHandler_(self, asset, options, handler):
        self.version = options.version()
        handler(None, None, None)


@pytest.mark.parametrize(
    "version,expected",
    [
        (PHOTOS_VERSION_CURRENT, Photos.PHVideoRequestOptionsVersionCurrent),
        (PHOTOS_VERSION_ORIGINAL, Photos.PHVideoRequestOptionsVersionOriginal),
        (PHOTOS_VERSION_UNADJUSTED, Photos.PHVideoRequestOptionsVersionOriginal),
    ],
)
def test_request_video_data_version(version, expected):
    manager = FakeImageManager()
    VideoAsset(manager, FakePHAsset())._request_video_data(version=version)
    assert manager.version == expected
