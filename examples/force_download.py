""" use osxphotos to force the download of photos from iCloud
    downloads images to a temporary directory then deletes them
    resulting in the photo being downloaded to Photos library
"""

import os
import sys
import tempfile

import osxphotos


def main():
    photosdb = osxphotos.PhotosDB(verbose=print)
    tempdir = tempfile.TemporaryDirectory()
    photos = photosdb.photos()
    downloaded = 0
    missing = [photo for photo in photos if photo.ismissing and not photo.shared]

    if not missing:
        print(f"Did not find any missing photos to download")
        sys.exit(0)

    print(f"Downloading {len(missing)} photos")
    for photo in missing:
        if photo.ismissing:
            print(f"Downloading photo {photo.original_filename}")
            downloaded += 1
            exported = photo.export(tempdir.name, use_photos_export=True, timeout=300)
            if photo.hasadjustments:
                exported.extend(
                    photo.export(
                        tempdir.name, use_photos_export=True, edited=True, timeout=300
                    )
                )
            for filename in exported:
                print(f"Removing temporary file {filename}")
                os.unlink(filename)
    print(f"Downloaded {downloaded} photos")
    tempdir.cleanup()


if __name__ == "__main__":
    main()
