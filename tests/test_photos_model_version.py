"""Map Photos.sqlite model versions to the right table-name set without a Photos library."""

import pytest

from osxphotos._constants import _DB_TABLE_NAMES
from osxphotos.photosdb import photosdb_utils


@pytest.mark.parametrize(
    "model_version, photos_version",
    [
        (19400, 11.1),  # macOS 26.1
        (270008501, 12),  # macOS 27.0 developer beta
        (270300300, 12.3),  # macOS 27.3 beta
    ],
)
def test_photos_version_from_model(monkeypatch, model_version, photos_version):
    monkeypatch.setattr(
        photosdb_utils, "get_model_version", lambda db_file: str(model_version)
    )
    assert photosdb_utils.get_photos_version_from_model("Photos.sqlite") == photos_version


def test_macos_27_3_tables():
    """macOS 27.3 renumbered the album, keyword and share-participant join entities"""
    names = _DB_TABLE_NAMES[12.3]
    assert names["ALBUM_JOIN"] == "Z_35ASSETS.Z_3ASSETS"
    assert names["ALBUM_SORT_ORDER"] == "Z_35ASSETS.Z_FOK_3ASSETS"
    assert names["ASSET_ALBUM_JOIN"] == "Z_35ASSETS.Z_35ALBUMS"
    assert names["ASSET_ALBUM_TABLE"] == "Z_35ASSETS"
    assert names["KEYWORD_JOIN"] == "Z_1KEYWORDS.Z_54KEYWORDS"
    assert names["ZSHAREPARTICIPANT_ZXX_SHARE"] == "Z72_SHARE"
