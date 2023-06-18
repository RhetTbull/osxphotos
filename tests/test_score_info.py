""" Test ScoreInfo """

from math import isclose

import pytest

from osxphotos.scoreinfo import ScoreInfo

PHOTOS_DB_5 = "tests/Test-10.15.5.photoslibrary"
PHOTOS_DB_4 = "tests/Test-10.14.6.photoslibrary"

SCORE_DICT = {
    "4D521201-92AC-43E5-8F7C-59BC41C37A96": ScoreInfo(
        overall=0.470703125,
        curation=0.5,
        promotion=0.0,
        highlight_visibility=0.03816793893129771,
        behavioral=0.0,
        failure=-0.0006928443908691406,
        harmonious_color=0.017852783203125,
        immersiveness=0.003086090087890625,
        interaction=0.019999999552965164,
        interesting_subject=-0.0885009765625,
        intrusive_object_presence=-0.037872314453125,
        lively_color=0.10540771484375,
        low_light=0.00824737548828125,
        noise=-0.015655517578125,
        pleasant_camera_tilt=-0.006256103515625,
        pleasant_composition=0.028564453125,
        pleasant_lighting=-0.00439453125,
        pleasant_pattern=0.09088134765625,
        pleasant_perspective=0.11859130859375,
        pleasant_post_processing=0.00698089599609375,
        pleasant_reflection=-0.01523590087890625,
        pleasant_symmetry=0.01242828369140625,
        sharply_focused_subject=0.08538818359375,
        tastefully_blurred=0.022125244140625,
        well_chosen_subject=0.05596923828125,
        well_framed_subject=0.5986328125,
        well_timed_shot=0.0134124755859375,
    ),
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4": ScoreInfo(
        overall=0.853515625,
        curation=0.75,
        promotion=0.0,
        highlight_visibility=0.05725190839694656,
        behavioral=0.0,
        failure=-0.0004916191101074219,
        harmonious_color=0.382080078125,
        immersiveness=0.0133209228515625,
        interaction=0.03999999910593033,
        interesting_subject=0.1632080078125,
        intrusive_object_presence=-0.00966644287109375,
        lively_color=0.44091796875,
        low_light=0.01322174072265625,
        noise=-0.0026721954345703125,
        pleasant_camera_tilt=0.028045654296875,
        pleasant_composition=0.33642578125,
        pleasant_lighting=0.46142578125,
        pleasant_pattern=0.1944580078125,
        pleasant_perspective=0.494384765625,
        pleasant_post_processing=0.4970703125,
        pleasant_reflection=0.00910186767578125,
        pleasant_symmetry=0.00930023193359375,
        sharply_focused_subject=0.52490234375,
        tastefully_blurred=0.63916015625,
        well_chosen_subject=0.64208984375,
        well_framed_subject=0.485595703125,
        well_timed_shot=0.01531219482421875,
    ),
}


@pytest.fixture
def photosdb():
    import osxphotos

    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_5)


def test_score_info_v5(photosdb):
    """test score"""
    # use math.isclose to compare floats
    # on MacOS x64 these can probably compared for equality but would possibly
    # fail if osxphotos ever ported to other platforms
    for uuid in SCORE_DICT:
        photo = photosdb.photos(uuid=[uuid], movies=True)[0]
        for attr in photo.score.__dict__:
            assert isclose(getattr(photo.score, attr), getattr(SCORE_DICT[uuid], attr))


def test_score_info_v4():
    """test version 4, score should be None"""
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_4)
    for photo in photosdb.photos():
        assert photo.score is None
