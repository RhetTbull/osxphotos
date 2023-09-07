"""Import photos from shared Photos albums into Photos library as regular (non-shared) photos.

Required questionary which is not a regular osxphotos dependency.
To use:

install osxphotos (see: https://github.com/RhetTbull/osxphotos#installation)
run `osxphotos install questionary`
run `osxphotos run import_shared.py`
"""

from __future__ import annotations

import tempfile
from typing import Callable

import click
import photoscript
import questionary
from rich.progress import Progress

import osxphotos
from osxphotos import AlbumInfo, PhotoInfo
from osxphotos.cli import echo, echo_error
from osxphotos.cli.verbose import verbose_print
from osxphotos.photosalbum import PhotosAlbumPhotoScript
from osxphotos.queryoptions import QueryOptions
from osxphotos.utils import pluralize


def pluralize_photos(photos: list[PhotoInfo]) -> str:
    """Return str with number of photos and pluralized 'photo' or 'photos'"""
    length = len(photos)
    return f"{length} {pluralize(length, 'photo', 'photos')}"


@click.command(name="import-shared")
def main():
    """Import photos from classic shared albums into Photos library.

    This command will import photos from shared albums into your Photos library as regular (non-shared) photos.

    You will be prompted to select which shared albums to import,
    which users to ignore (for example, yourself to avoid duplicates),
    album structure, and metadata to import.

    The command will export photos one at a time and import them to Photos then apply
    the albums and metadata. Thus your "Imports" folder in Photos will show an import
    for each photo imported instead of one import session for all photos.
    """

    # print documentation
    echo(main.__doc__)
    if not questionary.confirm("Continue?").ask():
        raise click.Abort()

    # load the photos database
    photos_to_import = get_photos_to_import()
    echo(
        f"Found {len(photos_to_import)} {pluralize_photos(photos_to_import)} to import."
    )

    # which albums to import into?
    same_albums = questionary.confirm(
        "Import into albums with same names as shared albums?"
    ).ask()
    if questionary.confirm(
        "Would you like to specify an album name to import into?",
        default=False,
    ).ask():
        album_name = questionary.text("Enter album name:").ask()
    else:
        album_name = None

    # metadata
    person_keywords = questionary.confirm(
        "Add keywords for owners of shared photos?"
    ).ask()
    comments = questionary.confirm(
        "Add comments for shared photos to description of imported photo?"
    ).ask()
    favorite = questionary.confirm(
        "Set favorite flag on imported photos with likes?"
    ).ask()

    if questionary.confirm("Are you sure you want to import?").ask():
        import_shared_photos(
            photos_to_import,
            same_albums,
            album_name,
            person_keywords,
            comments,
            favorite,
        )


def get_photos_to_import() -> list[PhotoInfo]:
    """Get list of photos to import from shared albums"""
    echo("Loading photos database (this could take a little while)...")
    photosdb = osxphotos.PhotosDB()
    photos = photosdb.query(QueryOptions(shared=True))
    shared_albums = photosdb.album_info_shared
    echo(
        f"Found {pluralize_photos(photos)} "
        f"in {len(shared_albums)} shared {pluralize(len(shared_albums), 'album', 'albums')}"
    )

    photos = ask_shared_albums(photos, shared_albums)
    echo(f"Filtered to {pluralize_photos(photos)}")
    if not photos:
        return []
    photos = ask_shared_owners(photos)
    echo(f"Filtered to {pluralize_photos(photos)}")
    return photos or []


def ask_shared_albums(photos: list[PhotoInfo], shared_albums: list[AlbumInfo]):
    """Ask user about which shared albums to import"""
    shared_album_info = get_shared_album_info(shared_albums)
    if questionary.confirm("Include all shared albums?").ask():
        return photos
    if include := questionary.checkbox(
        "Select shared album(s) to *include* in import or press Enter to import all",
        choices=list(shared_album_info.keys()),
    ).ask():
        shared_albums_include = [shared_album_info[x] for x in include]
    else:
        # user hit Enter without selection, return all
        return photos

    album_photos = []
    for album in shared_albums_include:
        album_photos.extend(p for p in photos if p in album.photos)
    return album_photos


def get_shared_owners(photos: list[PhotoInfo]) -> dict[str, int]:
    """Return dict of owners of shared photos"""
    owners = {}
    for photo in photos:
        try:
            owners[photo.owner] += 1
        except KeyError:
            owners[photo.owner] = 1

    return {
        f"{k} ({v} {pluralize(v, 'photo', 'photos')})": k
        for k, v in sorted(owners.items(), key=lambda x: x[1], reverse=True)
    }


def ask_shared_owners(photos: list[PhotoInfo]) -> list[PhotoInfo]:
    """Ask user which owners to include"""
    shared_owner_info = get_shared_owners(photos)
    exclude = questionary.checkbox(
        "Select shared photo owner(s) to *exclude* from import or press Enter to import all",
        choices=list(shared_owner_info.keys()),
    ).ask()
    exclude_owners = [shared_owner_info[x] for x in exclude]
    return get_shared_photos(photos, exclude_owners)


def get_shared_album_info(shared_albums: list[AlbumInfo]) -> dict[str, int]:
    """Return dict with info about shared albums"""
    albums = {}
    for album in shared_albums:
        photo_owners = {photo.owner for photo in album.photos}
        album_key = f"{album.title} ({pluralize_photos(album.photos)} by {', '.join(photo_owners)}"
        albums[album_key] = album
    return albums


def get_shared_photos(photos: list[PhotoInfo], exclude: list[str]) -> list[PhotoInfo]:
    """Return list of photos to import"""
    return [photo for photo in photos if photo.owner not in exclude]


def import_shared_photos(
    photos: list[PhotoInfo],
    same_albums: bool,
    album_name: str,
    person_keywords: bool,
    comments: bool,
    favorite: bool,
):
    """Import shared photos into Photos library"""
    echo(
        f"Importing {pluralize_photos(photos)}. Will{'' if same_albums else ' not'} import into albums with same names as shared albums."
    )
    if album_name:
        echo(f"Will import into album '{album_name}'")

    imported_count = 0
    with Progress() as progress:
        task = progress.add_task("Importing", total=len(photos))
        for photo in photos:
            progress.update(
                task,
                advance=1,
                description=f"{photo.original_filename}, [italic]{photo.albums[0]}[/i], by {photo.owner}",
            )
            imported_count += export_import_photo(
                photo, same_albums, album_name, person_keywords, comments, favorite
            )
    echo(
        f"Done. Imported {imported_count} {pluralize(imported_count, 'photo', 'photos')}."
    )


def export_import_photo(
    photo: PhotoInfo,
    same_albums: bool,
    album_name: str,
    person_keywords: bool,
    comments: bool,
    favorite: bool,
):
    """Export a shared photo and import as a regular (not shared) photo"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            exported = photo.export(
                tmpdir,
                photo.original_filename,
                use_photos_export=photo.ismissing,
                timeout=300,
            )
            if not exported:
                echo_error(f"Error exporting {photo.original_filename}")
                return 0
            import_count = import_photos(
                photo,
                exported,
                same_albums,
                album_name,
                person_keywords,
                comments,
                favorite,
            )
            return import_count
    except KeyboardInterrupt as e:
        raise KeyboardInterrupt from e
    except Exception as e:
        echo_error(f"Error importing {photo.original_filename}: {e}")
        return 0


def import_photos(
    photo: PhotoInfo,
    exported: list[str],
    same_albums: bool,
    album_name: str,
    person_keywords: bool,
    comments: bool,
    favorite: bool,
):
    """Import exported photos into Photos library"""
    photoslib = photoscript.PhotosLibrary()
    imported_photos = photoslib.import_photos(exported)

    # albums
    album_names = []
    if same_albums:
        album_names.extend(photo.albums)
    if album_name:
        album_names.append(album_name)
    for album_name in album_names:
        album = PhotosAlbumPhotoScript(album_name)
        album.add_list(imported_photos)

    # metadata
    for imported_photo in imported_photos:
        if person_keywords:
            imported_photo.keywords = [photo.owner] if photo.owner else []
        if comments:
            description = ", ".join(
                f"{comment.text} ({comment.user})" for comment in photo.comments
            )
            imported_photo.description = description
        if favorite:
            imported_photo.favorite = photo.likes

    return len(imported_photos)


if __name__ == "__main__":
    main()
