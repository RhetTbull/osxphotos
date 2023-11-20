""" Create the test data needed for test_search_info_10_15_7.py """

# reads data from the author's system photo library to build the test data
# used to test SearchInfo
# run as:
# python3 tests/generate_search_info_test_data.py >tests/search_info_test_data_10_15_7.json

import json

import osxphotos

UUID = [
    "14B8DE1D-4113-4948-BC11-C7046656C58C", # IMG_4179.HEIC
    "F21DFA19-E3E8-4610-8401-0447345F3074", # IMG_1929.JPG,
    "7D852FC8-EA03-49C9-96F7-B049CE44A7EA", # IMG_6162.JPG
]

data = {
    "UUID_SEARCH_INFO": {},
    "UUID_SEARCH_INFO_NORMALIZED": {},
    "UUID_SEARCH_INFO_ALL": {},
    "UUID_SEARCH_INFO_ALL_NORMALIZED": {},
}

photosdb = osxphotos.PhotosDB()

for uuid in UUID:
    photo = photosdb.get_photo(uuid)
    search = photo.search_info
    search_norm = photo.search_info_normalized
    data["UUID_SEARCH_INFO"][uuid] = search.asdict()
    data["UUID_SEARCH_INFO_NORMALIZED"][uuid] = search_norm.asdict()
    data["UUID_SEARCH_INFO_ALL"][uuid] = search.all
    data["UUID_SEARCH_INFO_ALL_NORMALIZED"][uuid] = search_norm.all

print(json.dumps(data))
