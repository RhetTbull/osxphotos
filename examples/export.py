""" Export all photos to ~/Desktop/export
    If file has been edited, export the edited version, 
    otherwise, export the original version """

import os.path

import osxphotos

def main():
    photosdb = osxphotos.PhotosDB()
    photos = photosdb.photos()

    export_path = os.path.expanduser("~/Desktop/export")

    for p in photos:
        if not p.ismissing():
            if p.hasadjustments():
                exported = p.export(export_path, edited=True)
            else:
                exported = p.export(export_path)
            print(f"Exported {p.filename()} to {exported}")
        else:
            print(f"Skipping missing photo: {p.filename()}")

if __name__ == "__main__":
    main()