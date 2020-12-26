""" Create the test data needed for test_search_info_10_15_7.py """

# reads data from the author's system photo library to build the test data
# used to test SearchInfo

import json

import osxphotos

UUID = [
    "C8EAF50A-D891-4E0C-8086-C417E1284153",
    "71DFB4C3-E868-4BE4-906E-D96BD8692D7E",
    "2C151013-5BBA-4D00-B70F-1C9420418B86",
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
