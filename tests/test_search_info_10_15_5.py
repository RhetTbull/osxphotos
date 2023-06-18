""" test PhotoInfo.search_info """

import pytest

from osxphotos._constants import _UNKNOWN_PERSON

PHOTOS_DB = "./tests/Test-10.15.5.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-10.15.5.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-10.15.5.photoslibrary"

LABELS_DICT = {
    # A92D9C26-3A50-4197-9388-CB5F7DB9FA91 IMG_1994.JPG None RAW + JPEG, JPEG Original [] False
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91": [
        "Blue Sky",
        "Outdoor",
        "Palm Tree",
        "Plant",
        "Sky",
        "Tree",
    ],
    # F12384F6-CD17-4151-ACBA-AE0E3688539E Pumkins1.jpg Can we carry this? Girls with pumpkins [] False
    "F12384F6-CD17-4151-ACBA-AE0E3688539E": [
        "Vegetable",
        "Pumpkin",
        "Farm",
        "Food",
        "Outdoor",
        "Agriculture",
        "People",
        "Plant",
        "Straw Hay",
    ],
    # D79B8D77-BFFC-460B-9312-034F2877D35B Pumkins2.jpg I found one! Girl holding pumpkin [] False
    "D79B8D77-BFFC-460B-9312-034F2877D35B": [],
    # D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068 DSC03584.dng None RAW only [] False
    "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068": ["Camera"],
    # A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C Pumpkins4.jpg Pumpkin heads None [] True
    "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C": [],
    # 3DD2C897-F19E-4CA6-8C22-B027D5A71907 IMG_4547.jpg Elder Park ⁨Elder Park⁩, ⁨Adelaide⁩, ⁨Australia⁩ ['Statue', 'Art'] False
    "3DD2C897-F19E-4CA6-8C22-B027D5A71907": ["Statue", "Art"],
    # 8E1D7BC9-9321-44F9-8CFB-4083F6B9232A IMG_2000.JPG None RAW + JPEG, Not copied to library [] False
    "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A": ["Foliage", "Plant"],
    # 4D521201-92AC-43E5-8F7C-59BC41C37A96 IMG_1997.JPG None RAW + JPEG, RAW original [] False
    "4D521201-92AC-43E5-8F7C-59BC41C37A96": [
        "Decorative Plant",
        "Foliage",
        "Plant",
        "Window",
    ],
    # 6191423D-8DB8-4D4C-92BE-9BBBA308AAC4 Tulips.jpg Tulips tied together at a flower shop Wedding tulips ['Flower', 'Vase', 'Bouquet', 'Container', 'Art', 'Flower Arrangement', 'Plant'] False
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4": [
        "Flower",
        "Vase",
        "Bouquet",
        "Container",
        "Art",
        "Flower Arrangement",
        "Plant",
    ],
    # 1EB2B765-0765-43BA-A90C-0D0580E6172C Pumpkins3.jpg None Kids in pumpkin field [] False
    "1EB2B765-0765-43BA-A90C-0D0580E6172C": [
        "Child",
        "Sky",
        "Plant",
        "People",
        "Clothing",
        "Jeans",
        "Outdoor",
        "Agriculture",
        "Farm",
        "Food",
        "Vegetable",
        "Pumpkin",
    ],
    # DC99FBDD-7A52-4100-A5BB-344131646C30 St James Park.jpg St. James's Park None ['Tree', 'Plant', 'Waterways', 'River', 'Sky', 'Cloudy', 'Land', 'Water Body', 'Water', 'Outdoor'] False
    "DC99FBDD-7A52-4100-A5BB-344131646C30": [
        "Tree",
        "Plant",
        "Waterways",
        "River",
        "Sky",
        "Cloudy",
        "Land",
        "Water Body",
        "Water",
        "Outdoor",
    ],
    # E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51 wedding.jpg None Bride Wedding day [] False
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": [],
}

LABELS_NORMALIZED_DICT = {
    # DC99FBDD-7A52-4100-A5BB-344131646C30 St James Park.jpg St. James's Park None ['tree', 'plant', 'waterways', 'river', 'sky', 'cloudy', 'land', 'water body', 'water', 'outdoor'] False
    "DC99FBDD-7A52-4100-A5BB-344131646C30": [
        "tree",
        "plant",
        "waterways",
        "river",
        "sky",
        "cloudy",
        "land",
        "water body",
        "water",
        "outdoor",
    ],
    # 4D521201-92AC-43E5-8F7C-59BC41C37A96 IMG_1997.JPG None RAW + JPEG, RAW original [] False
    "4D521201-92AC-43E5-8F7C-59BC41C37A96": [
        "decorative plant",
        "foliage",
        "plant",
        "window",
    ],
    # A92D9C26-3A50-4197-9388-CB5F7DB9FA91 IMG_1994.JPG None RAW + JPEG, JPEG Original [] False
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91": [
        "blue sky",
        "outdoor",
        "palm tree",
        "plant",
        "sky",
        "tree",
    ],
    # E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51 wedding.jpg None Bride Wedding day [] False
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": [],
    # D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068 DSC03584.dng None RAW only [] False
    "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068": ["camera"],
    # 8E1D7BC9-9321-44F9-8CFB-4083F6B9232A IMG_2000.JPG None RAW + JPEG, Not copied to library [] False
    "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A": ["foliage", "plant"],
    # 3DD2C897-F19E-4CA6-8C22-B027D5A71907 IMG_4547.jpg Elder Park ⁨Elder Park⁩, ⁨Adelaide⁩, ⁨Australia⁩ ['statue', 'art'] False
    "3DD2C897-F19E-4CA6-8C22-B027D5A71907": ["statue", "art"],
    # 6191423D-8DB8-4D4C-92BE-9BBBA308AAC4 Tulips.jpg Tulips tied together at a flower shop Wedding tulips ['flower', 'vase', 'bouquet', 'container', 'art', 'flower arrangement', 'plant'] False
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4": [
        "flower",
        "vase",
        "bouquet",
        "container",
        "art",
        "flower arrangement",
        "plant",
    ],
    # D79B8D77-BFFC-460B-9312-034F2877D35B Pumkins2.jpg I found one! Girl holding pumpkin [] False
    "D79B8D77-BFFC-460B-9312-034F2877D35B": [],
    # 1EB2B765-0765-43BA-A90C-0D0580E6172C Pumpkins3.jpg None Kids in pumpkin field [] False
    "1EB2B765-0765-43BA-A90C-0D0580E6172C": [
        "child",
        "sky",
        "plant",
        "people",
        "clothing",
        "jeans",
        "outdoor",
        "agriculture",
        "farm",
        "food",
        "vegetable",
        "pumpkin",
    ],
    # F12384F6-CD17-4151-ACBA-AE0E3688539E Pumkins1.jpg Can we carry this? Girls with pumpkins [] False
    "F12384F6-CD17-4151-ACBA-AE0E3688539E": [
        "vegetable",
        "pumpkin",
        "farm",
        "food",
        "outdoor",
        "agriculture",
        "people",
        "plant",
        "straw hay",
    ],
    # A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C Pumpkins4.jpg Pumpkin heads None [] True
    "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C": [],
}

SEARCH_INFO_DICT = {
    # valid search_info
    "DC99FBDD-7A52-4100-A5BB-344131646C30": True,
    # missing, so no search_info
    "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C": False,
}


LABELS = [
    "Tree",
    "Plant",
    "Waterways",
    "River",
    "Sky",
    "Cloudy",
    "Land",
    "Water Body",
    "Water",
    "Outdoor",
    "Statue",
    "Art",
    "Foliage",
    "Window",
    "Decorative Plant",
    "Blue Sky",
    "Palm Tree",
    "Flower",
    "Flower Arrangement",
    "Bouquet",
    "Vase",
    "Container",
    "Camera",
    "Child",
    "People",
    "Clothing",
    "Jeans",
    "Agriculture",
    "Farm",
    "Food",
    "Vegetable",
    "Pumpkin",
    "Straw Hay",
]

LABELS_NORMALIZED = [
    "tree",
    "plant",
    "waterways",
    "river",
    "sky",
    "cloudy",
    "land",
    "water body",
    "water",
    "outdoor",
    "statue",
    "art",
    "foliage",
    "window",
    "decorative plant",
    "blue sky",
    "palm tree",
    "flower",
    "flower arrangement",
    "bouquet",
    "vase",
    "container",
    "camera",
    "child",
    "people",
    "clothing",
    "jeans",
    "agriculture",
    "farm",
    "food",
    "vegetable",
    "pumpkin",
    "straw hay",
]

LABELS_AS_DICT = {
    "Plant": 7,
    "Outdoor": 4,
    "Sky": 3,
    "Tree": 2,
    "Art": 2,
    "Foliage": 2,
    "People": 2,
    "Agriculture": 2,
    "Farm": 2,
    "Food": 2,
    "Vegetable": 2,
    "Pumpkin": 2,
    "Waterways": 1,
    "River": 1,
    "Cloudy": 1,
    "Land": 1,
    "Water Body": 1,
    "Water": 1,
    "Statue": 1,
    "Window": 1,
    "Decorative Plant": 1,
    "Blue Sky": 1,
    "Palm Tree": 1,
    "Flower": 1,
    "Flower Arrangement": 1,
    "Bouquet": 1,
    "Vase": 1,
    "Container": 1,
    "Camera": 1,
    "Child": 1,
    "Clothing": 1,
    "Jeans": 1,
    "Straw Hay": 1,
}

LABELS_NORMALIZED_AS_DICT = {
    "plant": 7,
    "outdoor": 4,
    "sky": 3,
    "tree": 2,
    "art": 2,
    "foliage": 2,
    "people": 2,
    "agriculture": 2,
    "farm": 2,
    "food": 2,
    "vegetable": 2,
    "pumpkin": 2,
    "waterways": 1,
    "river": 1,
    "cloudy": 1,
    "land": 1,
    "water body": 1,
    "water": 1,
    "statue": 1,
    "window": 1,
    "decorative plant": 1,
    "blue sky": 1,
    "palm tree": 1,
    "flower": 1,
    "flower arrangement": 1,
    "bouquet": 1,
    "vase": 1,
    "container": 1,
    "camera": 1,
    "child": 1,
    "clothing": 1,
    "jeans": 1,
    "straw hay": 1,
}


@pytest.fixture
def photosdb():
    # return a PhotosDB object for use by tests
    import osxphotos

    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_search_info(photosdb):
    for uuid in SEARCH_INFO_DICT:
        photo = photosdb.photos(uuid=[uuid])[0]

        if SEARCH_INFO_DICT[uuid]:
            assert photo.search_info
        else:
            # still have a search info object but should have no data
            assert photo.search_info._db_searchinfo is None


def test_labels_normalized(photosdb):
    import logging

    for uuid in LABELS_NORMALIZED_DICT:
        photo = photosdb.photos(uuid=[uuid])[0]
        assert sorted(photo.search_info_normalized.labels) == sorted(
            LABELS_NORMALIZED_DICT[uuid]
        )
        assert sorted(photo.labels_normalized) == sorted(LABELS_NORMALIZED_DICT[uuid])


def test_labels(photosdb):
    import logging

    for uuid in LABELS_DICT:
        photo = photosdb.photos(uuid=[uuid])[0]
        assert sorted(photo.search_info.labels) == sorted(LABELS_DICT[uuid])
        assert sorted(photo.labels) == sorted(LABELS_DICT[uuid])


def test_photosdb_labels(photosdb):
    assert sorted(photosdb.labels) == sorted(LABELS)
    assert sorted(photosdb.labels_normalized) == sorted(LABELS_NORMALIZED)


def test_photosdb_labels_as_dict(photosdb):
    assert photosdb.labels_as_dict == LABELS_AS_DICT
    assert photosdb.labels_normalized_as_dict == LABELS_NORMALIZED_AS_DICT
