"""
batch-edit command for osxphotos CLI
"""

from __future__ import annotations

import functools
import json
import sys
from typing import Any

import click

import osxphotos
from osxphotos._constants import _OSXPHOTOS_NONE_SENTINEL
from osxphotos.phototemplate import RenderOptions
from osxphotos.platform import assert_macos
from osxphotos.sqlitekvstore import SQLiteKVStore
from osxphotos.utils import pluralize

assert_macos()

import photoscript

from osxphotos.photosalbum import PhotosAlbumPhotoScript

from .cli_commands import echo, echo_error, selection_command, verbose
from .kvstore import kvstore
from .param_types import Latitude, Longitude, TemplateString


@selection_command(name="batch-edit")
@click.option(
    "--title",
    "-t",
    metavar="TITLE_TEMPLATE",
    type=TemplateString(),
    help="Set title of photo.",
)
@click.option(
    "--description",
    "-d",
    metavar="DESCRIPTION_TEMPLATE",
    type=TemplateString(),
    help="Set description of photo.",
)
@click.option(
    "--keyword",
    "-k",
    metavar="KEYWORD_TEMPLATE",
    type=TemplateString(),
    multiple=True,
    help="Add keywords to photo. May be specified multiple times.",
)
@click.option(
    "--replace-keywords",
    "-K",
    is_flag=True,
    help="When specified with --keyword, replace existing keywords. "
    "Default is to add to existing keywords.",
)
@click.option(
    "--location",
    "-l",
    metavar="LATITUDE LONGITUDE",
    type=click.Tuple([Latitude(), Longitude()]),
    help="Set location of photo. "
    "Must be specified as a pair of numbers with latitude in the range -90 to 90 and longitude in the range -180 to 180.",
)
@click.option(
    "--album",
    "-a",
    metavar="ALBUM_TEMPLATE",
    multiple=True,
    type=TemplateString(),
    help="Add photo to album ALBUM_TEMPLATE. "
    "ALBUM_TEMPLATE is an osxphotos template string. "
    "Photos may be added to more than one album by repeating --album. "
    "See also, --split-folder. "
    "See Template System in help (`osxphotos docs`) for additional information.",
)
@click.option(
    "--split-folder",
    "-f",
    help="When used with --album, automatically create hierarchal folders for albums "
    "as needed by splitting album name into folders and album. "
    "You must specify the character used to split folders and albums. "
    "For example, '--split-folder \"/\"' will split the album name 'Folder/Album' "
    "into folder 'Folder' and album 'Album'. ",
)
@click.option("--dry-run", is_flag=True, help="Don't actually change anything.")
@click.option(
    "--undo",
    "-u",
    is_flag=True,
    help="Restores photo metadata to what it was prior to the last batch edit. "
    "May be combined with --dry-run to see what will be undone. "
    "Note: --undo cannot undo album changes at this time; "
    "photos added to an album with --album will remain in the album after --undo.",
)
def batch_edit(
    photos: list[osxphotos.PhotoInfo],
    title: str | None,
    description: str | None,
    keyword: tuple[str, ...],
    replace_keywords: bool,
    location: tuple[float, float],
    album: tuple[str, ...],
    split_folder: str | None,
    dry_run: bool,
    undo: bool,
    **kwargs: Any,
):
    """
    Batch edit photo metadata such as title, description, keywords, etc.
    Operates on currently selected photos.

    Select one or more photos in Photos then run this command to edit the metadata.

    For example:

    \b
        osxphotos batch-edit \\
        --verbose \\
        --title "California vacation 2023 {created.year}-{created.dd}-{created.mm} {counter:03d}" \\
        --description "{place.name}" \\ 
        --keyword "Family" --keyword "Travel"

    This will set the title to "California vacation 2023 2023-02-20 001", and so on,
    the description to the reverse geolocation place name, 
    and add the keywords "Family" and "Travel".

    --title, --description, and --keyword may be any valid template string.
    See https://rhettbull.github.io/osxphotos/template_help.html 
    or `osxphotos docs` for more information on the osxphotos template system.
    """

    try:
        validate_options(
            photos=photos,
            title=title,
            description=description,
            keyword=keyword,
            replace_keywords=replace_keywords,
            location=location,
            album=album,
            split_folder=split_folder,
            undo=undo,
        )
    except ValueError as e:
        echo_error(f"[error] {e} Use --help for more information.")
        sys.exit(1)

    # sort photos by date so that {counter} order is correct
    photos.sort(key=lambda p: p.date)

    undo_store = kvstore("batch_edit")
    verbose(f"Undo database stored in [filepath]{undo_store.path}", level=2)

    echo(f"Processing [num]{len(photos)}[/] photos...")
    for photo in photos:
        verbose(
            f"Processing [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
        )
        if undo:
            undo_photo_edits(photo, undo_store, dry_run)
            continue
        save_photo_undo_info(undo_store, photo)
        set_photo_title_from_template(photo, title, dry_run)
        set_photo_description_from_template(photo, description, dry_run)
        set_photo_keywords_from_template(photo, keyword, replace_keywords, dry_run)
        set_photo_location(photo, location, dry_run)
        set_photo_albums_from_template(photo, album, split_folder, dry_run)


def validate_options(
    photos: list[osxphotos.PhotoInfo],
    title: str | None,
    description: str | None,
    keyword: tuple[str, ...],
    replace_keywords: bool,
    location: tuple[float, float],
    album: tuple[str, ...],
    split_folder: str | None,
    undo: bool,
):
    """Validate options; raises ValueError if options are invalid"""
    if not any([title, description, keyword, location, album, undo]):
        raise ValueError(
            "Must specify at least one of: "
            " --title, --description, --keyword, --location, --album, --undo."
        )

    if undo and any([title, description, keyword, location, album]):
        raise ValueError("Cannot specify --undo and any options other than --dry-run.")

    if replace_keywords and not keyword:
        raise ValueError("Cannot specify --replace-keywords without --keyword.")

    if split_folder and not album:
        raise ValueError("Cannot specify --split-folder without --album.")

    if not photos:
        raise ValueError("No photos selected")


@functools.lru_cache(maxsize=1)
def photoscript_photo(photo: osxphotos.PhotoInfo) -> photoscript.Photo:
    """Return photoscript Photo object for photo"""
    # cache photoscript Photo object to avoid re-creating it for each photo
    # maxsize=1 as this function is called repeatedly for each photo then
    # the next photo is processed
    return photoscript.Photo(photo.uuid)


def save_photo_undo_info(undo_store: SQLiteKVStore, photo: osxphotos.PhotoInfo):
    """Save undo information to undo store"""
    undo_store[photo.uuid] = photo.json()


def undo_photo_edits(
    photo: osxphotos.PhotoInfo, undo_store: SQLiteKVStore, dry_run: bool
):
    """Undo edits for photo"""
    if not (undo_info := undo_store.get(photo.uuid)):
        verbose(
            f"[warning] No undo information for photo [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
        )
        return
    undo_info = json.loads(undo_info)
    ps_photo = photoscript_photo(photo)
    exiting_title, exiting_description, exiting_keywords, exiting_location = (
        photo.title,
        photo.description,
        sorted(photo.keywords),
        photo.location,
    )
    previous_title, previous_description, previous_keywords, previous_location = (
        undo_info.get("title"),
        undo_info.get("description"),
        sorted(undo_info.get("keywords")),
        (undo_info.get("latitude"), undo_info.get("longitude")),
    )
    verbose(
        f"Undoing edits for [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
    )
    for name, existing, previous in (
        ("title", exiting_title, previous_title),
        ("description", exiting_description, previous_description),
        ("keywords", exiting_keywords, previous_keywords),
        ("location", exiting_location, previous_location),
    ):
        if existing != previous:
            verbose(
                f"  [i]{name}[/]: [change]{existing}[/] -> [no_change]{previous}[/]"
            )
            if not dry_run:
                setattr(ps_photo, name, previous)
        else:
            verbose(f"  [i]{name} (no change)[/]: [no_change]{existing}[/]", level=2)


def set_photo_title_from_template(
    photo: osxphotos.PhotoInfo, title_template: str, dry_run: bool
):
    """Set photo title from template"""
    if not title_template:
        return

    # don't render None values
    render_options = RenderOptions(none_str="")

    title_string, _ = photo.render_template(title_template, render_options)
    title_string = [ts for ts in title_string if ts]
    if not title_string:
        verbose(
            f"No title returned from template, nothing to do: [bold]{title_template}"
        )
        return

    if len(title_string) > 1:
        echo_error(
            f"[error] Title template must return a single string: [bold]{title_string}"
        )
        sys.exit(1)

    verbose(f"Setting [i]title[/i] to [bold]{title_string[0]}")
    if not dry_run:
        ps_photo = photoscript_photo(photo)
        ps_photo.title = title_string[0]


def set_photo_description_from_template(
    photo: osxphotos.PhotoInfo, description_template: str, dry_run: bool
):
    """Set photo description from template"""
    if not description_template:
        return

    # don't render None values
    render_options = RenderOptions(none_str="")

    description_string, _ = photo.render_template(description_template, render_options)
    description_string = [ds for ds in description_string if ds]
    if not description_string:
        verbose(
            f"No description returned from template, nothing to do: [bold]{description_template}"
        )
        return

    if len(description_string) > 1:
        echo_error(
            f"[error] Description template must return a single string: [bold]{description_string}"
        )
        sys.exit(1)

    verbose(f"Setting [i]description[/] to [bold]{description_string[0]}")
    if not dry_run:
        ps_photo = photoscript_photo(photo)
        ps_photo.description = description_string[0]


def set_photo_keywords_from_template(
    photo: osxphotos.PhotoInfo,
    keyword_template: list[str],
    replace_keywords: bool,
    dry_run: bool,
):
    """Set photo keywords from template"""
    if not keyword_template:
        return

    # don't render None values
    render_options = RenderOptions(none_str="")

    keywords = set()
    for kw in keyword_template:
        kw_string, _ = photo.render_template(kw, render_options)
        if kw_string:
            # filter out empty strings
            keywords.update([k for k in kw_string if k])

    if not keywords:
        verbose(
            f"No keywords returned from template, nothing to do: [bold]{keyword_template}"
        )
        return

    if not replace_keywords:
        keywords.update(photo.keywords)

    verbose(
        f"Setting [i]keywords[/] to {', '.join(f'[bold]{kw}[/]' for kw in keywords)}"
    )
    if not dry_run:
        ps_photo = photoscript_photo(photo)
        ps_photo.keywords = list(keywords)


def set_photo_location(
    photo: osxphotos.PhotoInfo, location: tuple[float, float], dry_run: bool
):
    """Set photo location"""
    if not location or location[0] is None or location[1] is None:
        return

    latitude, longitude = location
    verbose(
        f"Setting [i]location[/] to [num]{latitude:.6f}[/], [num]{longitude:.6f}[/]"
    )
    if not dry_run:
        ps_photo = photoscript_photo(photo)
        ps_photo.location = (latitude, longitude)


def set_photo_albums_from_template(
    photo: osxphotos.PhotoInfo,
    album: tuple[str, ...],
    split_folder: str | None,
    dry_run: bool,
):
    """Add photo to album(s) based on album template"""
    if not album:
        return

    albums = []
    for a in album:
        albums.extend(render_album_template(photo, a))
    verbose(
        f"Adding photo to [num]{len(albums)}[/] [i]{pluralize(len(albums), 'album', 'albums')}[/]"
    )

    # add photo to albums
    for a in albums:
        verbose(f"Adding photo to [i]album[/] [bold]{a}[/]")
        if not dry_run:
            photos_album = PhotosAlbumPhotoScript(
                a, split_folder=split_folder, rich=True
            )
            ps_photo = photoscript_photo(photo)
            photos_album.add(ps_photo)


def render_album_template(
    photo: osxphotos.PhotoInfo,
    album_template: str,
):
    """Render template string for a photo"""
    options = RenderOptions(none_str=_OSXPHOTOS_NONE_SENTINEL, caller="batch_edit")
    template_values, _ = photo.render_template(album_template, options=options)

    # filter out empty strings
    template_values = [v.replace(_OSXPHOTOS_NONE_SENTINEL, "") for v in template_values]
    template_values = [v for v in template_values if v]
    return template_values
