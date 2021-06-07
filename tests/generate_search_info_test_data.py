""" Create the test data needed for test_search_info_10_15_7.py """

# reads data from the author's system photo library to build the test data
# used to test SearchInfo
# run as:
# python3 tests/generate_search_info_test_data.py >tests/search_info_test_data_10_15_7.json

import json

import osxphotos

UUID = [
    "DC09F4D8-6173-452D-AC15-725C8D7C185E",
    "AFECD4AB-937C-46AF-A79B-9C9A38AA42B1",
    "A1C36260-92CD-47E2-927A-35DAF16D7882",
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
