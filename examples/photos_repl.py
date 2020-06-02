#!/usr/bin/env python3 -i

# Open an interactive REPL with photosdb and photos defined
# as osxphotos.PhotosDB() and PhotosDB.photos respectively
# useful for debugging or exploring the Photos database

# If you run this using python from command line, do so with -i flag:
# python3 -i examples/photos_repl.py

import sys
import time

# click needed since this uses a couple of functions from CLI (__main__.py)
import click

import osxphotos
from osxphotos.__main__ import get_photos_db, _list_libraries


def main():
    db = None

    db = sys.argv[1] if len(sys.argv) > 1 else get_photos_db()
    if db:
        print("loading database")
        tic = time.perf_counter()
        photosdb = osxphotos.PhotosDB(dbfile=db)
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
    toc = time.perf_counter()
    print(f"found {len(photos)} photos in {toc-tic} seconds")
