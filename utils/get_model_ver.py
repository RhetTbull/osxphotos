"""Get the Photos database model version."""

import os
import sys

from osxphotos.photosdb.photosdb_utils import get_db_version, get_model_version

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if os.path.isdir(sys.argv[1]):
            db = os.path.join(sys.argv[1], "database", "Photos.sqlite")
        else:
            db = sys.argv[1]

        print(f"Photos database version: {get_db_version(db)}")
        print(f"Photos database model version: {get_model_version(db)}")
    else:
        print("Usage: get_model_ver.py <photoslibrary>")
        sys.exit(1)
