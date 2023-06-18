#!/usr/bin/env python3 -i

# Open an interactive REPL with photosdb and photos defined
# as osxphotos.PhotosDB() and PhotosDB.photos respectively
# useful for debugging or exploring the Photos database

# If you run this using python from command line, do so with -i flag:
# python3 -i examples/photos_repl.py

import os
import sys
import time

# click needed since this uses a couple of functions from CLI (__main__.py)
import click

import osxphotos
from osxphotos.cli import _list_libraries, get_photos_db


def show(photo):
    """open image with default image viewer

    Note: This is for debugging only -- it will actually open any filetype which could
    be very, very bad.

    Args:
        photo: PhotoInfo object or a path to a photo on disk
    """
    photopath = photo.path if isinstance(photo, osxphotos.PhotoInfo) else photo

    if not os.path.isfile(photopath):
        return f"'{photopath}' does not appear to be a valid photo path"

    os.system(f"open '{photopath}'")


def main():
    db = None

    db = sys.argv[1] if len(sys.argv) > 1 else get_photos_db()
    if db:
        print("loading database")
        tic = time.perf_counter()
        photosdb = osxphotos.PhotosDB(dbfile=db, verbose=print)
        toc = time.perf_counter()
        print(f"done: took {toc-tic} seconds")
        return photosdb
    else:
        _list_libraries()
        sys.exit()


if __name__ == "__main__":
    print(f"osxphotos version: {osxphotos._version.__version__}")
    photosdb = main()
    print(f"database version: {photosdb.db_version}")
    print("getting photos")
    tic = time.perf_counter()
    photos = photosdb.photos(images=True, movies=True)
    photos.extend(photosdb.photos(images=True, movies=True, intrash=True))
    toc = time.perf_counter()
    print(f"found {len(photos)} photos in {toc-tic} seconds")
