"""
Batch edit currently selected photo metadata using osxphotos.

Run this with `osxphotos run batch_edit.py` or `osxphotos run batch_edit.py --help` for more information.
"""

from __future__ import annotations

import functools
import json
import sys

import click
import photoscript

import osxphotos
from osxphotos.cli import echo, echo_error, kvstore, selection_command, verbose
from osxphotos.cli.param_types import TemplateString
from osxphotos.phototemplate import RenderOptions
from osxphotos.sqlitekvstore import SQLiteKVStore


class Latitude(click.ParamType):
    name = "Latitude"

    def convert(self, value, param, ctx):
        try:
            latitude = float(value)
            if latitude < -90 or latitude > 90:
                raise ValueError
            return latitude
        except Exception:
            self.fail(
                f"Invalid latitude {value}. Must be a floating point number between -90 and 90."
            )


class Longitude(click.ParamType):
    name = "Longitude"

    def convert(self, value, param, ctx):
        try:
            longitude = float(value)
            if longitude < -180 or longitude > 180:
                raise ValueError
            return longitude
        except Exception:
            self.fail(
                f"Invalid longitude {value}. Must be a floating point number between -180 and 180."
            )


@selection_command(name="batch-edit")
@click.option(
    "--title",
    metavar="TITLE_TEMPLATE",
    type=TemplateString(),
    help="Set title of photo.",
)
@click.option(
    "--description",
    metavar="DESCRIPTION_TEMPLATE",
    type=TemplateString(),
    help="Set description of photo.",
)
@click.option(
    "--keyword",
    metavar="KEYWORD_TEMPLATE",
    type=TemplateString(),
    multiple=True,
    help="Set keywords of photo. May be specified multiple times.",
)
@click.option(
    "--location",
    metavar="LATITUDE LONGITUDE",
    type=click.Tuple([Latitude(), Longitude()]),
    help="Set location of photo. "
    "Must be specified as a pair of numbers with latitude in the range -90 to 90 and longitude in the range -180 to 180.",
)
@click.option("--dry-run", is_flag=True, help="Don't actually change anything.")
@click.option(
    "--undo",
    is_flag=True,
    help="Restores photo metadata to what it was prior to the last batch edit. "
    "May be combined with --dry-run.",
)
def batch_edit(
    photos: list[osxphotos.PhotoInfo],
    title,
    description,
    keyword,
    location,
    dry_run,
    undo,
    **kwargs,
):
    """
    Batch edit photo metadata such as title, description, keywords, etc.
    Operates on currently selected photos.

    Select one or more photos in Photos then run this command to edit the metadata.

    For example:

    \b
        osxphotos run batch_edit.py \\
        --verbose \\
        --title "California vacation 2023 {created.year}-{created.dd}-{created.mm} {counter:03d}" \\
        --description "{place.name}" \\ 
        --keyword "Family" --keyword "Travel" --keyword "{keyword}"

    This will set the title to "California vacation 2023 2023-02-20 001", and so on,
    the description to the reverse geolocation place name, 
    and the keywords to "Family", "Travel", and any existing keywords of the photo.

    --title, --description, and --keyword may be any valid template string.
    See https://rhettbull.github.io/osxphotos/template_help.html for more information
    on the osxphotos template system.
    """

    if not title and not description and not keyword and not location and not undo:
        echo_error(
            "[error] Must specify at least one of: "
            " --title, --description, --keyword, --location, --undo. "
            "Use --help for more information."
        )
        sys.exit(1)

    if undo and (title or description or keyword or location):
        echo_error(
            "[error] Cannot specify --undo and any options other than --dry-run. "
            "Use --help for more information."
        )
        sys.exit(1)

    if not photos:
        echo_error("[error] No photos selected")
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
        set_photo_keywords_from_template(photo, keyword, dry_run)
        set_photo_location(photo, location, dry_run)


# cache photoscript Photo object to avoid re-creating it for each photo
# maxsize=1 as this function is called repeatedly for each photo then
# the next photo is processed
@functools.lru_cache(maxsize=1)
def photoscript_photo(photo: osxphotos.PhotoInfo) -> photoscript.Photo:
    """Return photoscript Photo object for photo"""
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
    photo: osxphotos.PhotoInfo, keyword_template: list[str], dry_run: bool
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


if __name__ == "__main__":
    batch_edit()
