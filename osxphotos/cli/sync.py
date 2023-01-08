"""Sync metadata & albums between Photos libraries"""

from __future__ import annotations

import datetime
import json
import pathlib
from typing import Callable

import click

from osxphotos import PhotoInfo, PhotosDB, __version__
from osxphotos.photosdb.photosdb_utils import get_db_version
from osxphotos.queryoptions import QueryOptions
from osxphotos.sqlite_utils import sqlite_open_ro
from osxphotos.sqlitekvstore import SQLiteKVStore
from osxphotos.utils import pluralize

from .click_rich_echo import (
    rich_click_echo,
    rich_echo_error,
    set_rich_console,
    set_rich_theme,
    set_rich_timestamp,
)
from .color_themes import get_theme
from .common import DB_OPTION, THEME_OPTION
from .rich_progress import rich_progress
from .verbose import get_verbose_console, verbose_print

OSXPHOTOS_ABOUT_STRING = f"Sync Metadata Database created by osxphotos version {__version__} (https://github.com/RhetTbull/osxphotos) on {datetime.datetime.now()}"

METADATA_IMPORT_TYPES = [
    "all",
    "keywords",
    "albums",
    "title",
    "description",
    "favorite",
]


class MetadataImportPath(click.ParamType):
    """A path to a Photos library or a metadata export file created by --export"""

    name = "METADATA_IMPORT_PATH"

    def convert(self, value, param, ctx):
        try:
            if not pathlib.Path(value).exists():
                self.fail(f"{value} is not a file or directory")
            import_type = get_import_type(value)
            return value
        except Exception as e:
            self.fail(f"Could not determine import type for {value}: {e}")


class MetadataImportType(click.ParamType):
    """A string indicating which metadata to set or merge from the import source"""

    # valid values are specified in METADATA_IMPORT_TYPES

    name = "METADATA_IMPORT_TYPE"

    def convert(self, value, param, ctx):
        try:
            if value not in METADATA_IMPORT_TYPES:
                values = [v.strip() for v in value.split(",")]
                for v in values:
                    if v not in METADATA_IMPORT_TYPES:
                        self.fail(
                            f"{v} is not a valid import type, valid values are {', '.join(METADATA_IMPORT_TYPES)}"
                        )
            return value
        except Exception as e:
            self.fail(f"Could not determine import type for {value}: {e}")


def parse_set_merge(values: tuple[str]) -> tuple[str]:
    """Parse --set and --merge options which may be passed individually or as a comma-separated list"""
    new_values = []
    for value in values:
        new_values.extend([v.strip() for v in value.split(",")])
    return tuple(new_values)


def open_metadata_db(db_path: str):
    """Open metadata database at db_path"""
    metadata_db = SQLiteKVStore(
        db_path,
        wal=False,  # don't use WAL to keep database a single file
    )
    if not metadata_db.about:
        metadata_db.about = (
            f"osxphotos metadata sync database\n{OSXPHOTOS_ABOUT_STRING}"
        )
    return metadata_db


def key_from_photo(photo: PhotoInfo) -> str:
    """Return key for photo used to correlate photos between libraries"""
    return f"{photo.fingerprint}:{photo.original_filename}"


def get_photo_metadata(photos: list[PhotoInfo]) -> str:
    """Return JSON string of metadata for photos; if more than one photo, merge metadata"""
    if len(photos) == 1:
        return photos[0].json()

    # more than one photo with same fingerprint; merge metadata
    merge_fields = ["keywords", "persons", "albums", "title", "description", "uuid"]
    photos_dict = {}
    for photo in photos:
        data = photo.asdict()
        for k, v in data.items():
            if k not in photos_dict:
                photos_dict[k] = v.copy() if isinstance(v, (list, dict)) else v
            else:
                # merge data if it's a merge field
                if k in merge_fields and v:
                    if isinstance(v, (list, tuple)):
                        photos_dict[k] = sorted(list(set(photos_dict[k]) | set(v)))
                    else:
                        if v:
                            if not photos_dict[k]:
                                photos_dict[k] = v
                            elif photos_dict[k] and v != photos_dict[k]:
                                photos_dict[k] = f"{photos_dict[k]} {v}"
    # convert photos_dict to JSON string
    # wouldn't it be nice if json encoder handled datetimes...
    def default(o):
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()

    return json.dumps(photos_dict, sort_keys=True, default=default)


def export_metadata(
    photos: list[PhotoInfo], output_path: str, verbose: Callable[..., None]
):
    """Export metadata to metadata_db"""
    metadata_db = open_metadata_db(output_path)
    verbose(f"Exporting metadata to [filepath]{output_path}[/]")
    num_photos = len(photos)
    photo_word = pluralize(num_photos, "photo", "photos")
    verbose(f"Analyzing [num]{num_photos}[/] {photo_word} to export")
    # it is possible to have multiple photos with the same fingerprint
    # for example, the same photo was imported twice or the photo was duplicated in Photos
    # in this case, we need to merge the metadata for the photos with the same fingerprint
    # as there is no way to know which photo is the "correct" one
    key_to_photos = {}
    for photo in photos:
        key = key_from_photo(photo)
        if key in key_to_photos:
            key_to_photos[key].append(photo)
        else:
            key_to_photos[key] = [photo]

    verbose(f"Exporting [num]{len(photos)}[/] {photo_word} to {output_path}")
    with rich_progress(console=get_verbose_console()) as progress:
        task = progress.add_task("Exporting metadata", total=len(key_to_photos))
        for key, key_photos in key_to_photos.items():
            metadata_db[key] = get_photo_metadata(key_photos)
            progress.advance(task)
    verbose(
        f"Done: exported metadata for [num]{len(photos)}[/] {photo_word} to [filepath]{output_path}[/]"
    )
    metadata_db.close()


def get_import_type(import_path: str) -> str:
    """Determine if import_path is a Photos library, Photos database, or metadata export file"""
    if pathlib.Path(import_path).is_dir():
        if import_path.endswith(".photoslibrary"):
            return "library"
        else:
            raise ValueError(
                f"Unable to determine type of import library: {import_path}"
            )
    else:
        # import_path is a file, need to determine if it's a Photos database or metadata export file
        try:
            get_db_version(import_path)
        except Exception as e:
            try:
                db = SQLiteKVStore(import_path)
                if db.about:
                    return "export"
                else:
                    raise ValueError(
                        f"Unable to determine type of import file: {import_path}"
                    ) from e
            except Exception as e:
                raise ValueError(
                    f"Unable to determine type of import file: {import_path}"
                ) from e
        else:
            return "library"


@click.command()
@click.option(
    "--selected",
    is_flag=True,
    help="Filter for photos that are currently selected in Photos.",
)
@click.option(
    "--export",
    "-e",
    "export_path",
    metavar="EXPORT_FILE",
    help="Export metadata to file EXPORT_FILE for later use with --import.",
    type=click.Path(dir_okay=False, writable=True),
)
@click.option(
    "--import",
    "-i",
    "import_path",
    metavar="IMPORT_PATH",
    help="Import metadata from file IMPORT_PATH. "
    "IMPORT_PATH can a Photos library, a Photos database, or a metadata export file "
    "created with --export.",
    type=MetadataImportPath(),
)
@click.option(
    "--set",
    "-s",
    "set_",
    metavar="METADATA",
    multiple=True,
    help="When used with --import, set metadata in local Photos library to match import data. "
    "Multiple metadata properties can be specified by repeating the --set option "
    "or by using a comma-separated list. "
    f"METADATA can be one of: {', '.join(METADATA_IMPORT_TYPES)}. "
    "For example, to set keywords and favorite, use `--set keywords --set favorite` "
    "or `--set keywords,favorite`. "
    "If `--set all` is specified, all metadata will be set. "
    "Note that using --set overwrites any existing metadata in the local Photos library. "
    "For example, if a photo is marked as favorite in the local library but not in the import source, "
    "--set favorite will clear the favorite status in the local library. "
    "The exception to this is that `--set album` will not remove the photo "
    "from any existing albums in the local library but will add the photo to any new albums specified "
    "in the import source."
    "See also --merge.",
    type=MetadataImportType(),
)
@click.option(
    "--merge",
    "-m",
    "merge",
    metavar="METADATA",
    multiple=True,
    help="When used with --import, merge metadata in local Photos library with import data. "
    "Multiple metadata properties can be specified by repeating the --merge option "
    "or by using a comma-separated list. "
    f"METADATA can be one of: {', '.join(METADATA_IMPORT_TYPES)}. "
    "For example, to merge keywords and favorite, use `--merge keywords --merge favorite` "
    "or `--merge keywords,favorite`. "
    "If `--merge all` is specified, all metadata will be merged. "
    "Note that using --merge does not overwrite any existing metadata in the local Photos library. "
    "For example, if a photo is marked as favorite in the local library but not in the import source, "
    "--merge favorite will not change the favorite status in the local library. "
    "See also --set.",
    type=MetadataImportType(),
)
@click.option("--verbose", "-V", "verbose_", is_flag=True, help="Print verbose output.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Dry run; " "when used with --import, don't actually update metadata.",
)
@click.option(
    "--timestamp", "-T", is_flag=True, help="Add time stamp to verbose output."
)
@DB_OPTION
@THEME_OPTION
@click.pass_obj
@click.pass_context
def sync(
    ctx,
    cli_obj,
    db,
    dry_run,
    export_path,
    import_path,
    merge,
    selected,
    set_,
    theme,
    timestamp,
    verbose_,
):
    """Sync metadata & albums between Photos libraries"""
    color_theme = get_theme(theme)
    verbose = verbose_print(
        verbose_, timestamp, rich=True, theme=color_theme, highlight=False
    )
    # set console for rich_echo to be same as for verbose_
    set_rich_console(get_verbose_console())
    set_rich_theme(color_theme)
    set_rich_timestamp(timestamp)

    if (set_ or merge) and not import_path:
        rich_echo_error("--set and --merge can only be used with --import")
        ctx.exit(1)

    if export_path:
        photosdb = PhotosDB(dbfile=db, verbose=verbose)
        query_options = QueryOptions(selected=selected)
        photos = photosdb.query(query_options)
        export_metadata(photos, export_path, verbose)

    if import_path:
        import_type = get_import_type(import_path)
        print(f"Importing from {import_type} {import_path}")
        set_ = parse_set_merge(set_)
        merge = parse_set_merge(merge)
        print(f"{set_=}, {merge=}")
