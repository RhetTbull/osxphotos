#!/usr/bin/env python3 -i

# Open an interactive REPL with photosdb and photos defined
# as osxphotos.PhotosDB() and PhotosDB.photos respectively
# useful for debugging or exploring the Photos database

# If you run this using python from command line, do so with -i flag:
# python3 -i examples/photos_repl.py

import sys

# click needed since this uses a couple of functions from CLI (__main__.py)
import click

import osxphotos
from osxphotos.__main__ import get_photos_db, _list_libraries


def main():
    db = None

    if len(sys.argv) > 1:
        db = sys.argv[1]
    else:
        db = get_photos_db()

    if db:
        return osxphotos.PhotosDB(dbfile=db)
    else:
        _list_libraries()
        sys.exit()


if __name__ == "__main__":
    print(f"Version: {osxphotos._version.__version__}")
    photosdb = main()
    photos = photosdb.photos(images=True, movies=True)
