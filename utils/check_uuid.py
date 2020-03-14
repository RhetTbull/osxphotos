""" Use with output file created by dump_photo_info.scpt to check ouput
    of osxphotos vs what Photos reports """

import csv

import osxphotos

photosdb = osxphotos.PhotosDB()
photos = photosdb.photos(movies=True)
photos_uuid = {p.uuid: p for p in photos}
got_uuid = {}

inputfile = "photoslib1.txt"

# check that each uuid in the library is in photos
with open(inputfile) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=",")
    for row in csv_reader:
        uuid, *_ = row[0].split("/")
        fname = row[1]
        if uuid in got_uuid:
            print(f"WARNING: uuid already in got_dict: {uuid} {fname}")
        got_uuid[uuid] = fname

        if uuid not in photos_uuid:
            print(f"missing uuid not in photos_uuid: {uuid}, {fname}")

# check for uuids in photos not in the library
shared = 0
not_shared = 0
for uuid in photos_uuid:
    if uuid not in got_uuid:
        if photos_uuid[uuid].shared:
            shared += 1
        else:
            not_shared += 1
            print(f"missing uuid not in library:\n{photos_uuid[uuid].json()}")

print(f"shared: {shared}, not_shared: {not_shared}")
