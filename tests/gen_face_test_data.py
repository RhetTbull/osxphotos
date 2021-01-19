""" Generate test data for test_faceinfo.py
    This outputs a list of dictionaries that are passed to the test methods for testing
    You must verify the data output is correct (e.g. matches the photos) before adding it to the test 
"""
import sys

import osxphotos

db = sys.argv[1]
photosdb = osxphotos.PhotosDB(dbfile=db)

face_photos = [p for p in photosdb.photos() if p.face_info]

faces = []
for p in face_photos:
    print(f"processing photo {p.uuid}", file=sys.stderr)
    face_data = {p.uuid: {}}
    for f in p.face_info:
        face_data[p.uuid][f.uuid] = f.asdict()
    faces.append(face_data)
print(faces)
