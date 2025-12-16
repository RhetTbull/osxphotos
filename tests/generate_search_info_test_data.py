"""Create the test data needed for test_search_info_10_15_7.py"""

# reads data from the author's system photo library to build the test data
# used to test SearchInfo
# run as:
# python3 tests/generate_search_info_test_data.py >tests/search_info_test_data_10_15_7.json

import json

import osxphotos

UUID = [
    "E22A7BCA-442D-46A6-B064-8E0345961EC8",  # IMG_4179.HEIC
    "ADDEC5FD-F3DC-418A-B358-717C748C34BC",  # IMG_1929.JPG,
    "C2BB17B6-306D-421E-A1FC-7CD1A1541FE3",  # IMG_6162.JPG
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
