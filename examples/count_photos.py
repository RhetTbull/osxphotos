"""Simple example to show count of photos in library using osxphotos; used for testing `osxphotos run`"""

import osxphotos


def main():
    photosdb = osxphotos.PhotosDB()
    photos = [p for p in photosdb.photos(movies=False) if not p.shared and not p.hidden]
    videos = [p for p in photosdb.photos(images=False) if not p.shared and not p.hidden]
    print(f"{len(photos)} Photos, {len(videos)} Videos")


if __name__ == "__main__":
    main()
