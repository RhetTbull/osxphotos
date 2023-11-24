"""Simple example to show count of photos in library using osxphotos; used for testing `osxphotos run`"""

import click

import osxphotos


@click.command()
@click.option(
    "--library",
    default=None,
    metavar="PHOTOS_LIBRARY",
    help="Path to Photos library, default to last used library",
)
def main(library):
    photosdb = osxphotos.PhotosDB(dbfile=library)
    photos = [p for p in photosdb.photos(movies=False) if not p.shared and not p.hidden]
    videos = [p for p in photosdb.photos(images=False) if not p.shared and not p.hidden]
    print(f"{len(photos)} Photos, {len(videos)} Videos")


if __name__ == "__main__":
    main()
