"""Test for external adjustments"""

import osxphotos

ADJUSTMENTS_LIBRARY = "tests/ExternalAdjustments-14.4.1.photoslibrary"


def test_external_adjustments():
    """Test for external adjustments, #1518"""
    photosdb = osxphotos.PhotosDB(dbfile=ADJUSTMENTS_LIBRARY)
    photos = photosdb.photos()
    assert len(photos) == 1
    photo = photos[0]
    assert photo.adjustments is not None
    assert (
        photo.adjustments.asdict()["editor"]
        == "com.pixelmatorteam.pixelmator.touch.x.photo"
    )
