"""Copy photos metadata from a source photo to a destination photo; update match_photos function for your use case"""

import click
import photoscript

import osxphotos
from osxphotos.cli import echo, echo_error, query_command, verbose
from osxphotos.exiftool import ExifTool, get_exiftool_path
from osxphotos.photosalbum import PhotosAlbumPhotoScript


def match_photos(
    photos: list[osxphotos.PhotoInfo],
) -> list[tuple[osxphotos.PhotoInfo, osxphotos.PhotoInfo]]:
    """Match photos based on some criteria.

    Args:
        photos (list[osxphotos.PhotoInfo]): List of photos to match.

    Returns:
        list[tuple[osxphotos.PhotoInfo, osxphotos.PhotoInfo]]: List of matched photo pairs in source, destination format.
    """

    # this is just a dumb placeholder that finds all photos with the same filename and sets the src to the smallest file size
    pairs = {}
    for photo in photos:
        if photo.original_filename not in pairs:
            pairs[photo.original_filename] = [photo]
        else:
            pairs[photo.original_filename].append(photo)
    for filename, photos in pairs.items():
        if len(photos) > 1:
            pairs[filename] = sorted(photos, key=lambda p: p.original_filesize)
    results = [
        pair[:2] for pair in pairs.values() if len(pair) > 1
    ]  # ignore single photos and only keep first two photos in the pair
    return list([tuple(pair) for pair in results])


def copy_metadata(
    src: osxphotos.PhotoInfo,
    dest: osxphotos.PhotoInfo,
    album: str | None = None,
    dry_run: bool = False,
):
    """Copy metadata from source photo to destination photo.

    Copy keywords, title, description, location, and date from source to destination using photoscript.
    Add the destination photo to the source photo's album.
    If album is not None, add the source photo to album named album.

    Args:
        src (osxphotos.PhotoInfo): Source photo.
        dest (osxphotos.PhotoInfo): Destination photo.
        album (str | None): Album name to add the source photo to.
        dry_run (bool): If True, do not actually copy metadata.
    """

    try:
        dest_photo = photoscript.Photo(dest.uuid)
    except Exception as e:
        echo_error(f"Error getting destination photo: {e}")
        return

    verbose(
        f"Copying metadata from {src.original_filename} ({src.uuid}) to {dest.original_filename} ({dest.uuid})"
    )

    if src.title:
        verbose(f"Setting title: {src.title}")
        if not dry_run:
            dest_photo.title = src.title
    else:
        verbose(f"No title to set")

    if src.description:
        verbose(f"Setting description: {src.description}")
        if not dry_run:
            dest_photo.description = src.description
    else:
        verbose(f"No description to set")

    if src.keywords:
        verbose(f"Setting keywords: {', '.join(src.keywords)}")
        if not dry_run:
            dest_photo.keywords = src.keywords
    else:
        verbose(f"No keywords to set")

    if src.location:
        verbose(f"Setting location: {src.location}")
        if not dry_run:
            dest_photo.location = src.location
    else:
        verbose(f"No location to set")

    # Add destination photo to source photo's albums, preserving folder structure
    if src.album_info:
        for album_info in src.album_info:
            album_path = "/".join(album_info.folder_names)
            if album_path:
                album_path += "/"
            album_path += album_info.title
            verbose(f"Adding destination photo to album: {album_path}")
            if not dry_run:
                photos_album = PhotosAlbumPhotoScript(album_path, split_folder="/")
                photos_album.add(dest_photo)

    # Add source photo to specified album if provided
    if album:
        verbose(f"Adding source photo to album: {album}")
        if not dry_run:
            try:
                src_photo = photoscript.Photo(src.uuid)
                photos_album = PhotosAlbumPhotoScript(album, split_folder="/")
                photos_album.add(src_photo)
            except Exception as e:
                verbose(f"Error adding source photo to album: {e}")


def copy_exif_metadata(
    src: osxphotos.PhotoInfo, dest: osxphotos.PhotoInfo, dry_run: bool = False
):
    """Copy EXIF metadata from a source photo to a destination photo."""
    if not src.path and not dest.path:
        verbose("Source or destination path is missing, cannot run exiftool")
        return

    verbose(
        f"Copying EXIF metadata from {src.original_filename} ({src.uuid}) to {dest.original_filename} ({dest.uuid})"
    )
    src_exif = src.exiftool.asdict()
    exiftool = ExifTool(dest.path)
    for key, value in src_exif.items():
        tag_group = key.split(":")[0]
        if tag_group in ("EXIF", "IPTC", "XMP") and value:
            verbose(f"Setting destination metadata: {key} = {value}")
            if not dry_run:
                exiftool.setvalue(key, value)


@query_command
@click.option(
    "--copy-exif",
    is_flag=True,
    default=False,
    help="Copy EXIF metadata from source photo to destination photo.",
)
@click.option(
    "--add-to-album",
    type=str,
    default=None,
    help="Album name to add all source photos to after copying metadata.",
)
@click.option(
    "--dry-run", is_flag=True, default=False, help="Do not actually copy metadata."
)
def main(
    photos: list[osxphotos.PhotoInfo],
    copy_exif: bool,
    add_to_album: str | None,
    dry_run: bool = False,
    **kwargs,
):
    """Copy photos metadata from a source photo to a destination photo.

    Operates on photos in the Photos library and accepts all standard osxphotos query options.

    The user must supply the matching function to determine which photos to copy metadata from and to.
    """
    if copy_exif and not get_exiftool_path():
        echo_error("exiftool not found, cannot copy EXIF metadata")
        return

    echo(f"Processing {len(photos)} photo{'s' if len(photos) > 1 else ''}")
    photo_pairs = match_photos(photos)

    for src, dest in photo_pairs:
        copy_metadata(src, dest, album=add_to_album, dry_run=dry_run)
        if copy_exif:
            copy_exif_metadata(src, dest, dry_run=dry_run)


if __name__ == "__main__":
    main()
