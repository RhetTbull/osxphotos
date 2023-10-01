"""Sync metadata and albums between Photos libraries"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
from typing import Any, Callable, Literal

import click

from osxphotos import PhotoInfo, PhotosDB, __version__
from osxphotos.photoinfo import PhotoInfoNone
from osxphotos.photoquery import (
    IncompatibleQueryOptions,
    QueryOptions,
    query_options_from_kwargs,
)
from osxphotos.photosalbum import PhotosAlbum
from osxphotos.photosdb.photosdb_utils import get_db_version
from osxphotos.phototemplate import PhotoTemplate, RenderOptions
from osxphotos.platform import assert_macos
from osxphotos.sqlitekvstore import SQLiteKVStore
from osxphotos.utils import pluralize

assert_macos()

import photoscript

from .cli_params import (
    DB_OPTION,
    QUERY_OPTIONS,
    THEME_OPTION,
    TIMESTAMP_OPTION,
    VERBOSE_OPTION,
)
from .click_rich_echo import rich_click_echo as echo
from .click_rich_echo import rich_echo_error as echo_error
from .param_types import TemplateString
from .report_writer import sync_report_writer_factory
from .rich_progress import rich_progress
from .sync_results import SYNC_PROPERTIES, SyncResults
from .verbose import get_verbose_console, verbose_print

SYNC_ABOUT_STRING = (
    f"Sync Metadata Database created by osxphotos version {__version__} "
    + f"(https://github.com/RhetTbull/osxphotos) on {datetime.datetime.now()}"
)

SYNC_IMPORT_TYPES = [
    "keywords",
    "albums",
    "title",
    "description",
    "favorite",
]
SYNC_IMPORT_TYPES_ALL = ["all"] + SYNC_IMPORT_TYPES


class SyncImportPath(click.ParamType):
    """A path to a Photos library or a metadata export file created by --export"""

    name = "SYNC_IMPORT_PATH"

    def convert(self, value, param, ctx):
        try:
            if not pathlib.Path(value).exists():
                self.fail(f"{value} is not a file or directory")
            value = str(pathlib.Path(value).expanduser().resolve())
            # call get_import_type to raise exception if not a valid import type
            get_import_type(value)
            return value
        except Exception as e:
            self.fail(f"Could not determine import type for {value}: {e}")


class SyncImportType(click.ParamType):
    """A string indicating which metadata to set or merge from the import source"""

    # valid values are specified in METADATA_IMPORT_TYPES_ALL

    name = "SYNC_IMPORT_TYPE"

    def convert(self, value, param, ctx):
        try:
            if value not in SYNC_IMPORT_TYPES_ALL:
                values = [v.strip() for v in value.split(",")]
                for v in values:
                    if v not in SYNC_IMPORT_TYPES_ALL:
                        self.fail(
                            f"{v} is not a valid import type, valid values are {', '.join(SYNC_IMPORT_TYPES_ALL)}"
                        )
            return value
        except Exception as e:
            self.fail(f"Could not determine import type for {value}: {e}")


def render_and_validate_report(report: str) -> str:
    """Render a report file template and validate the filename

    Args:
        report: the template string

    Returns:
        the rendered report filename

    Note:
        Exits with error if the report filename is invalid
    """
    # render report template and validate the filename
    template = PhotoTemplate(PhotoInfoNone())
    render_options = RenderOptions()
    report_file, _ = template.render(report, options=render_options)
    report = report_file[0]

    if os.path.isdir(report):
        echo(
            f"[error]Report '{report}' is a directory, must be file name",
            err=True,
        )
        raise click.Abort()
    return report


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
        metadata_db.about = f"osxphotos metadata sync database\n{SYNC_ABOUT_STRING}"
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
    verbose(f"Exporting [num]{len(photos)}[/] {photo_word} to {output_path}")
    export_metadata_to_db(photos, metadata_db, progress=True)
    echo(
        f"Done: exported metadata for [num]{len(photos)}[/] {photo_word} to [filepath]{output_path}[/]"
    )
    metadata_db.close()


def export_metadata_to_db(
    photos: list[PhotoInfo],
    metadata_db: SQLiteKVStore,
    progress: bool = True,
):
    """Export metadata for photos to metadata database

    Args:
        photos: list of PhotoInfo objects
        metadata_db: SQLiteKVStore object
        progress: if True, show progress bar
    """
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

    with rich_progress(console=get_verbose_console(), mock=not progress) as progress:
        task = progress.add_task("Exporting metadata", total=len(key_to_photos))
        for key, key_photos in key_to_photos.items():
            metadata_db[key] = get_photo_metadata(key_photos)
            progress.advance(task)


def get_import_type(import_path: str) -> Literal["library", "export"]:
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


def import_metadata(
    photos: list[PhotoInfo],
    import_path: str,
    set_: tuple[str, ...],
    merge: tuple[str, ...],
    dry_run: bool,
    unmatched: bool,
    verbose: Callable[..., None],
) -> SyncResults:
    """Import metadata from metadata_db"""
    import_type = get_import_type(import_path)
    photo_word = pluralize(len(photos), "photo", "photos")
    verbose(
        f"Importing metadata for [num]{len(photos)}[/] {photo_word} from [filepath]{import_path}[/]"
    )

    # build mapping of key to photo
    key_to_photo = {}
    for photo in photos:
        key = key_from_photo(photo)
        if key in key_to_photo:
            key_to_photo[key].append(photo)
        else:
            key_to_photo[key] = [photo]

    # find keys in import_path that match keys in photos
    if import_type == "library":
        # create an in memory database of the import library
        # so that the rest of the comparison code can be the same
        photosdb = PhotosDB(import_path, verbose=verbose)
        # filter out shared photos which don't have a fingerprint and
        # whose metadata can't be set
        photos = photosdb.query(QueryOptions(not_shared=True))
        import_db = SQLiteKVStore(":memory:")
        verbose(f"Loading metadata from import library: [filepath]{import_path}[/]")
        export_metadata_to_db(photos, import_db, progress=False)
    elif import_type == "export":
        import_db = open_metadata_db(import_path)
    else:
        echo_error(
            f"Unable to determine type of import file: [filepath]{import_path}[/]"
        )
        raise click.Abort()

    results = SyncResults()
    for key, key_photos in key_to_photo.items():
        if key in import_db:
            # import metadata from import_db
            for photo in key_photos:
                verbose(
                    f"Importing metadata for [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
                )
                metadata = import_db[key]
                results += import_metadata_for_photo(
                    photo, metadata, set_, merge, dry_run, verbose
                )
        elif unmatched:
            # unable to find metadata for photo in import_db
            for photo in key_photos:
                echo(
                    f"Unable to find metadata for [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/]) in [filepath]{import_path}[/]"
                )

    if unmatched:
        # find any keys in import_db that don't match keys in photos
        for key in import_db.keys():
            if key not in key_to_photo:
                echo(f"Unable to find [uuid]{key}[/] in selected photos.")

    return results


def import_metadata_for_photo(
    photo: PhotoInfo,
    metadata: str,
    set_: tuple[str, ...],
    merge: tuple[str, ...],
    dry_run: bool,
    verbose: Callable[..., None],
) -> SyncResults:
    """Update metadata for photo from metadata

    Args:
        photo: PhotoInfo object
        metadata: metadata to import (JSON string)
        set_: tuple of metadata fields to set
        merge: tuple of metadata fields to merge
        dry_run: if True, don't actually update metadata
        verbose: verbose function
    """
    # convert metadata to dict
    metadata = json.loads(metadata)

    results = SyncResults()
    if "albums" in set_ or "albums" in merge:
        # behavior is the same for albums for set and merge:
        # add photo to any new albums but do not remove from existing albums
        results += _update_albums_for_photo(photo, metadata, dry_run, verbose)

    results += _set_metadata_for_photo(photo, metadata, set_, dry_run, verbose)
    results += _merge_metadata_for_photo(photo, metadata, merge, dry_run, verbose)

    return results


def _update_albums_for_photo(
    photo: PhotoInfo,
    metadata: dict[str, Any],
    dry_run: bool,
    verbose: Callable[..., None],
) -> SyncResults:
    """Add photo to new albums if necessary"""
    # add photo to any new albums but do not remove from existing albums
    results = SyncResults()
    value = sorted(metadata["albums"])
    before = sorted(photo.albums)
    albums_to_add = set(value) - set(before)
    if not albums_to_add:
        verbose(f"\tNothing to do for albums", level=2)
        results.add_result(
            photo.uuid,
            photo.original_filename,
            photo.fingerprint,
            "albums",
            False,
            before,
            value,
        )
        return results

    for album in albums_to_add:
        verbose(f"\tAdding to album [filepath]{album}[/]")
        if not dry_run:
            PhotosAlbum(album, verbose=lambda x: verbose(f"\t{x}"), rich=True).add(
                photo
            )
    results.add_result(
        photo.uuid,
        photo.original_filename,
        photo.fingerprint,
        "albums",
        True,
        before,
        value,
    )
    return results


def _set_metadata_for_photo(
    photo: PhotoInfo,
    metadata: dict[str, Any],
    set_: tuple[str, ...],
    dry_run: bool,
    verbose: Callable[..., None],
) -> SyncResults:
    """Set metadata for photo"""
    results = SyncResults()
    photo_ = photoscript.Photo(photo.uuid)

    for field in set_:
        if field == "albums":
            continue

        value = metadata[field]
        before = getattr(photo, field)

        if isinstance(value, list):
            value = sorted(value)
        if isinstance(before, list):
            before = sorted(before)

        if value != before:
            verbose(f"\tSetting {field} to {value} from {before}")
            if not dry_run:
                set_photo_property(photo_, field, value)
        else:
            verbose(f"\tNothing to do for {field}", level=2)

        results.add_result(
            photo.uuid,
            photo.original_filename,
            photo.fingerprint,
            field,
            value != before,
            before,
            value,
        )
    return results


def _merge_metadata_for_photo(
    photo: PhotoInfo,
    metadata: dict[str, Any],
    merge: tuple[str, ...],
    dry_run: bool,
    verbose: Callable[..., None],
) -> SyncResults:
    """Merge metadata for photo"""
    results = SyncResults()
    photo_ = photoscript.Photo(photo.uuid)

    for field in merge:
        if field == "albums":
            continue

        value = metadata[field]
        before = getattr(photo, field)

        if isinstance(value, list):
            value = sorted(value)
        if isinstance(before, list):
            before = sorted(before)

        if value == before:
            verbose(f"\tNothing to do for {field}", level=2)
            results.add_result(
                photo.uuid,
                photo.original_filename,
                photo.fingerprint,
                field,
                False,
                before,
                value,
            )
            continue

        if isinstance(value, list) and isinstance(before, list):
            new_value = sorted(set(value + before))
        elif isinstance(before, bool):
            new_value = value or bool(before)
        elif isinstance(before, str):
            value = value or ""
            new_value = f"{before} {value}" if value and value not in before else before
        elif before is None:
            new_value = value
        else:
            echo_error(
                f"Unable to merge {field} for [filename]{photo.original_filename}[filename]"
            )
            raise click.Abort()

        if new_value != before:
            verbose(f"\tMerging {field} to {new_value} from {before}")
            if not dry_run:
                set_photo_property(photo_, field, new_value)
        else:
            # Merge'd value might still be the same as original value
            # (e.g. if value is str and has previously been merged)
            verbose(f"\tNothing to do for {field}", level=2)

        results.add_result(
            photo.uuid,
            photo.original_filename,
            photo.fingerprint,
            field,
            new_value != before,
            before,
            new_value,
        )
    return results


def set_photo_property(photo: photoscript.Photo, property: str, value: Any):
    """Set property on photo"""

    # do some basic validation
    if property == "keywords" and not isinstance(value, list):
        raise ValueError(f"keywords must be a list, not {type(value)}")
    elif property in {"title", "description"} and not isinstance(value, str):
        raise ValueError(f"{property} must be a str, not {type(value)}")
    elif property == "favorite":
        value = bool(value)
    elif property not in {"title", "description", "favorite", "keywords"}:
        raise ValueError(f"Unknown property: {property}")
    setattr(photo, property, value)


def print_import_summary(results: SyncResults):
    """Print summary of import results"""
    summary = results.results_summary()
    property_summary = ", ".join(
        f"updated {property}: [num]{summary.get(property,0)}[/]"
        for property in SYNC_PROPERTIES
    )
    echo(
        f"Processed [num]{summary['total']}[/] photos, updated: [num]{summary['updated']}[/], {property_summary}"
    )


@click.command()
@click.option(
    "--export",
    "-e",
    "export_path",
    metavar="EXPORT_FILE",
    help="Export metadata to file EXPORT_FILE for later use with --import. "
    "The export file will be a SQLite database; it is recommended to use the "
    ".db extension though this is not required.",
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
    type=SyncImportPath(),
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
    f"METADATA can be one of: {', '.join(SYNC_IMPORT_TYPES_ALL)}. "
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
    type=SyncImportType(),
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
    f"METADATA can be one of: {', '.join(SYNC_IMPORT_TYPES_ALL)}. "
    "For example, to merge keywords and favorite, use `--merge keywords --merge favorite` "
    "or `--merge keywords,favorite`. "
    "If `--merge all` is specified, all metadata will be merged. "
    "Note that using --merge does not overwrite any existing metadata in the local Photos library. "
    "For example, if a photo is marked as favorite in the local library but not in the import source, "
    "--merge favorite will not change the favorite status in the local library. "
    "See also --set.",
    type=SyncImportType(),
)
@click.option(
    "--unmatched",
    "-U",
    is_flag=True,
    help="When used with --import, print out a list of photos in the import source that "
    "were not matched against the local library. Also prints out a list of photos "
    "in the local library that were not matched against the import source. ",
)
@click.option(
    "--report",
    "-R",
    metavar="REPORT_FILE",
    help="Write a report of all photos that were processed with --import. "
    "The extension of the report filename will be used to determine the format. "
    "Valid extensions are: "
    ".csv (CSV file), .json (JSON), .db and .sqlite (SQLite database). "
    "REPORT_FILE may be a an osxphotos template string, for example, "
    "--report 'update_{today.date}.csv' will write a CSV report file named with today's date. "
    "See also --append.",
    type=TemplateString(),
)
@click.option(
    "--append",
    "-A",
    is_flag=True,
    help="If used with --report, add data to existing report file instead of overwriting it. "
    "See also --report.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Dry run; " "when used with --import, don't actually update metadata.",
)
@VERBOSE_OPTION
@TIMESTAMP_OPTION
@QUERY_OPTIONS(exclude=["--shared", "--not-shared"])
@DB_OPTION
@THEME_OPTION
@click.pass_obj
@click.pass_context
def sync(
    ctx,
    cli_obj,
    db,
    append,
    dry_run,
    export_path,
    import_path,
    merge,
    report,
    set_,
    theme,
    timestamp,
    unmatched,
    verbose_flag,
    **kwargs,  # query options
):
    """Sync metadata and albums between Photos libraries.

    Use sync to update metadata in a local Photos library to match
    metadata in another Photos library. The sync command works by
    finding identical photos in the local library and the import source
    and then updating the metadata in the local library to match the
    metadata in the import source. Photos are considered identical if
    their original filename and fingerprint match.

    The import source can be a Photos library or a metadata export file
    created with the --export option.

    The sync command can be useful if you have imported the same photos to
    multiple Photos libraries and want to keep the metadata in all libraries
    in sync.

    Metadata can be overwritten (--set) or merged (--merge) with the metadata
    in the import source. You may specify specific metadata to sync or sync
    all metadata. See --set and --merge for more details.

    The sync command can be used to sync metadata between an iPhone or iPad
    and a Mac, for example, in the case where you do not use iCloud but
    manually import photos from your iPhone or iPad to your Mac. To do this,
    you'll first need to copy the Photos database from the iPhone or iPad to
    your Mac. This can be done by connecting your iPhone or iPad to your Mac
    using a USB cable and then copying the Photos database from the iPhone
    using a third-party tool such as iMazing (https://imazing.com/). You can
    then use the sync command and set the import source to the Photos database
    you copied from the iPhone or iPad.

    The sync command can also be used to sync metadata between users using
    iCloud Shared Photo Library. NOTE: This use case has not yet been
    tested. If you use iCloud Shared Photo Library and would like to help
    test this use case, please connect with me on GitHub:
    https://github.com/RhetTbull/osxphotos/issues/887

    You can run the --export and --import commands together. In this case,
    the import will be run first and then the export will be run.

    For example, if you want to sync two Photos libraries between users or
    two different computers, you can export the metadata to a shared folder.

    On the first computer, run:

    osxphotos sync --export /path/to/export/folder/computer1.db --merge all --import /path/to/export/folder/computer2.db

    On the second computer, run:

    osxphotos sync --export /path/to/export/folder/computer2.db --merge all --import /path/to/export/folder/computer1.db

    """

    verbose = verbose_print(verbose=verbose_flag, timestamp=timestamp, theme=theme)

    if (set_ or merge) and not import_path:
        echo_error("--set and --merge can only be used with --import")
        ctx.exit(1)

    # filter out photos in shared albums as these cannot be updated
    kwargs["not_shared"] = True

    set_ = parse_set_merge(set_)
    merge = parse_set_merge(merge)

    if "all" in set_:
        set_ = tuple(SYNC_IMPORT_TYPES)
    if "all" in merge:
        merge = tuple(SYNC_IMPORT_TYPES)

    if set_ and merge:
        # fields in set cannot be in merge and vice versa
        set_ = set(set_)
        merge = set(merge)
        if set_ & merge:
            echo_error(
                "--set and --merge cannot be used with the same fields: "
                f"set: {set_}, merge: {merge}"
            )
            ctx.exit(1)

    if import_path:
        try:
            query_options = query_options_from_kwargs(**kwargs)
        except IncompatibleQueryOptions:
            echo_error("Incompatible query options")
            echo_error(ctx.obj.group.commands["repl"].get_help(ctx))
            ctx.exit(1)
        photosdb = PhotosDB(dbfile=db, verbose=verbose)
        photos = photosdb.query(query_options)
        results = import_metadata(
            photos, import_path, set_, merge, dry_run, unmatched, verbose
        )
        if report:
            report_path = render_and_validate_report(report)
            verbose(f"Writing report to {report_path}")
            report_writer = sync_report_writer_factory(report_path, append=append)
            report_writer.write(results)
            report_writer.close()
        print_import_summary(results)

    if export_path:
        query_options = query_options_from_kwargs(**kwargs)
        photosdb = PhotosDB(dbfile=db, verbose=verbose)
        photos = photosdb.query(query_options)
        export_metadata(photos, export_path, verbose)
