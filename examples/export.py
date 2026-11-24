"""Export all photos to ~/Desktop/export
If file has been edited, export the edited version,
otherwise, export the original version"""

import os.path

import osxphotos


def main():
    db = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")
    photosdb = osxphotos.PhotosDB(db)
    photos = photosdb.photos()

    export_path = os.path.expanduser("~/Desktop/export")

    for p in photos:
        if not p.ismissing:
            try:
                exported = p.export(export_path, edited=p.hasadjustments)
            except FileNotFoundError:
                print(f"Skipping missing photo: {p.filename}")
                continue
            print(f"Exported {p.filename} to {exported}")
        else:
            print(f"Skipping missing photo: {p.filename}")


if __name__ == "__main__":
    main()
