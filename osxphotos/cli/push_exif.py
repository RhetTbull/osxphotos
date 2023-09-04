"""Push EXIF data to original files in the Photos library"""

from __future__ import annotations

import os
from typing import Any

import click
from rich.progress import Progress

from osxphotos import PhotoInfo
from osxphotos.exif_datetime_updater import get_exif_date_time_offset
from osxphotos.exiftool import get_exiftool_path
from osxphotos.exifwriter import ExifOptions, ExifWriter, exif_options_from_locals
from osxphotos.photoinfo import PhotoInfoNone
from osxphotos.phototemplate import PhotoTemplate, RenderOptions
from osxphotos.platform import assert_macos
from osxphotos.sidecars import exiftool_json_sidecar
from osxphotos.sqlitekvstore import SQLiteKVStore
from osxphotos.utils import pluralize

from .cli_commands import echo, echo_error, query_command, verbose
from .common import OSXPHOTOS_HIDDEN
from .kvstore import kvstore
from .param_types import CSVOptions, TemplateString
from .push_results import PushResults
from .report_writer import ReportWriterNoOp, push_exif_report_writer_factory
from .verbose import get_verbose_console

assert_macos()


@query_command(name="push-exif")
@click.option(
    "--compare",
    is_flag=True,
    help="Compare metadata only; do not push (write) metadata.",
)
@click.option(
    "--push-edited",
    is_flag=True,
    help="Push EXIF data to edited photos in addition to originals.",
)
@click.option(
    "--exiftool-path",
    metavar="EXIFTOOL_PATH",
    type=click.Path(exists=True),
    help="Optionally specify path to exiftool; if not provided, will look for exiftool in $PATH.",
)
@click.option(
    "--exiftool-option",
    "exiftool_flags",  # match ExifOptions
    multiple=True,
    metavar="OPTION",
    help="Optional flag/option to pass to exiftool. "
    "For example, --exiftool-option '-m' to ignore minor warnings. "
    "Specify these as you would on the exiftool command line. "
    "See exiftool docs at https://exiftool.org/exiftool_pod.html for full list of options. "
    "More than one option may be specified by repeating the option, e.g. "
    "--exiftool-option '-m' --exiftool-option '-F'. ",
)
@click.option(
    "--exiftool-merge-keywords",
    "merge_exif_keywords",  # match ExifOptions
    is_flag=True,
    help="Merge any keywords found in the original file with keywords from Photos.",
)
@click.option(
    "--exiftool-merge-persons",
    "merge_exif_persons",  # match ExifOptions
    is_flag=True,
    help="Merge any persons found in the original file with persons from Photos.",
)
@click.option(
    "--favorite-rating",
    is_flag=True,
    help="Set XMP:Rating=5 for photos marked as Favorite and XMP:Rating=0 for non-Favorites. "
    "If not specified, XMP:Rating is not set.",
)
@click.option(
    "--ignore-date-modified",
    is_flag=True,
    help="Will ignore the photo modification date and set EXIF:ModifyDate "
    "to EXIF:DateTimeOriginal; this is consistent with how Photos handles the EXIF:ModifyDate tag.",
)
@click.option(
    "--person-keyword",
    "use_persons_as_keywords",  # match ExifOptions
    is_flag=True,
    help="Use person in image as keyword/tag when writing metadata.",
)
@click.option(
    "--album-keyword",
    "use_albums_as_keywords",  # match ExifOptions
    is_flag=True,
    help="Use album name as keyword/tag when writing metadata.",
)
@click.option(
    "--keyword-template",
    metavar="TEMPLATE",
    multiple=True,
    default=None,
    help="Specify a template string to use as keyword. "
    "For example, if you wanted to add "
    "the full path to the folder and album photo is contained in as a keyword when writing metadata, "
    'you could specify --keyword-template "{folder_album}" '
    'You may specify more than one template, for example --keyword-template "{folder_album}" '
    '--keyword-template "{created.year}". '
    "See '--replace-keywords' and OSXPhotos Template System in `osxphotos docs`.",
    type=TemplateString(),
)
@click.option(
    "--replace-keywords",
    is_flag=True,
    help="Replace keywords with any values specified with --keyword-template. "
    "By default, --keyword-template will add keywords to any keywords already associated "
    "with the photo.  If --replace-keywords is specified, values from --keyword-template "
    "will replace any existing keywords instead of adding additional keywords.",
)
@click.option(
    "--description-template",
    metavar="TEMPLATE",
    multiple=False,
    default=None,
    help="Specify a template string to use as description. "
    "For example, if you wanted to append "
    "'updated with osxphotos on [today's date]' to the description, you could specify "
    '--description-template "{descr} updated with osxphotos on {today.date}" '
    "See OSXPhotos Template System in `osxphotos docs` for more details.",
    type=TemplateString(),
)
@click.option(
    "--report",
    metavar="REPORT_FILE",
    help="Write a report of all files that were processed. "
    "The extension of the report filename will be used to determine the format. "
    "Valid extensions are: "
    ".csv (CSV file), .json (JSON), .db and .sqlite (SQLite database). "
    "REPORT_FILE may be a template string (see OSXPhotos Template System), for example, "
    "--report 'push_exif_{today.date}.csv' will write a CSV report file named with today's date. "
    "See also --append.",
    type=TemplateString(),
)
@click.option(
    "--append",
    is_flag=True,
    help="If used with --report, add data to existing report file instead of overwriting it. "
    "See also --report.",
)
@click.option(
    "--force",
    is_flag=True,
    hidden=OSXPHOTOS_HIDDEN,
    help="Force writing metadata to all files and bypass warning.",
)
@click.argument(
    "metadata",
    required=True,
    type=CSVOptions(
        [
            "all",
            "keywords",
            "location",
            "faces",
            "persons",
            "datetime",
            "title",
            "description",
        ]
    ),
)
def push_exif(
    photos: list[PhotoInfo],
    compare: bool,
    push_edited: bool,
    exiftool_path: str,
    exiftool_flags: tuple[str],
    merge_exif_keywords: bool,
    merge_exif_persons: bool,
    favorite_rating: bool,
    ignore_date_modified: bool,
    use_persons_as_keywords: bool,
    use_albums_as_keywords: bool,
    keyword_template: tuple[str],
    replace_keywords: bool,
    description_template: str,
    report: str,
    append: bool,
    force: bool,
    metadata: str,
    **kwargs,
):
    """Write photo metadata to original files in the Photos library

    METADATA must be one or more of the following, separated by commas:
    all keywords location faces persons datetime title description

    - all: all metadata

    - keywords: keywords/tags (e.g. IPTC:Keywords, etc.)

    - location: location information (e.g. EXIF:GPSLatitude, EXIF:GPSLongitude, etc.)

    - faces: face region information (e.g. XMP:RegionName, etc.)

    - persons: person in image information (e.g. XMP:PersonInImage, etc.)

    - datetime: date/time information (e.g. EXIF:DateTimeOriginal, etc.)

    - title: title information (e.g. XMP:Title, etc.)

    - description: description information (e.g. XMP:Description, etc.)

    For example to push (write) keywords and faces information to the original files:
    `osxphotos push-exif keywords,faces`

    To write all metadata to the original files:
    `osxphotos push-exif all`

    This command will use exiftool (which must be installed separately)
    to write metadata to the original files in the Photos library.

    The metadata in Photos database including keywords, persons/faces, titles, etc.
    will be written to the original files.  This is useful if you want to ensure that
    the original file retains the metadata in the Photos database.

    You may use options to control which metadata is written to the original files.
    Metadata may also optionally be written to edited photos/videos using `--push-edited`.

    WARNING: This command will modify the original files in the Photos library.
    It is recommended that you make a backup of your Photos library before running
    this command. It is also not recommended that you run this command on a library
    that is managed by iCloud Photos. Changes to files in an iCloud library may not
    be synced back to iCloud. This is most useful for libraries that are not managed
    by iCloud Photos or for libraries using referenced files.

    The metadata is stored in a SQLite database in your home directory and will be used
    to automatically update or skip files as needed on subsequent runs of this command.

    Several options such as `--keyword-template` allow you to specify a template string
    to use to generate keywords.  See OSXPhotos Template System in `osxphotos docs` for more details
    as well as `osxphotos template` for an interactive template editor.

    If you want to compare metadata between Photos and the original files without
    writing metadata, use the `--compare` option.  This will print a report of any
    differences between the metadata in Photos and the original files but will not
    modify any files.

    push-exif cannot be used on photos in classic shared albums. These photos will
    be automatically skipped.
    """

    if shared := [p for p in photos if p.shared]:
        echo_error(
            f"[warning]Found {len(shared)} shared {pluralize(len(shared), 'photo', 'photos')} "
            "which cannot be processed by push-exif. Shared photos will be skipped."
        )
    photos = [p for p in photos if not p.shared]
    if not photos:
        echo_error("[error]No photos selected for processing")
        raise click.Abort()

    exiftool_path = exiftool_path or get_exiftool_path()
    verbose(f"Found exiftool at: [filepath]{exiftool_path}")

    # monkeypatch exiftool path in the db
    # TODO: need a more elegant way to do this
    # maybe a set_exiftool_path() that get_exiftool_path() checks
    photos[0]._db._exiftool_path = exiftool_path

    options = exif_options_from_locals(locals())
    options = set_options_from_metadata(options, metadata)

    if compare:
        compare_exif(photos, options)
        return

    library_path = photos[0]._db.library_path

    echo(f"[num]{len(photos)}[/] photos selected for processing")
    echo(
        f":warning-emoji: [warning]This command will modify files in the Photos library: [filepath]{library_path}[/]"
    )
    if not force:
        click.confirm("Do you want to continue?", abort=True)

    if any(p.iscloudasset for p in photos):
        echo(
            f":warning-emoji: [warning]WARNING: [filepath]{library_path}[/] appears to be an iCloud library"
        )
        if not force:
            click.confirm("Are you sure you want to continue?", abort=True)

    process_photos(photos, options, push_edited, report, append, exiftool_path)


def process_photos(
    photos: list[PhotoInfo],
    options: ExifOptions,
    push_edited: bool,
    report: str,
    append: bool,
    exiftool_path: str,
):
    """Process the photos, pushing metadata to files as needed"""

    update_db = kvstore("push_exif")
    echo(f"Using update database: [filepath]{update_db.path}[/]")

    report_name = render_and_validate_report(report, exiftool_path) if report else None
    verbose(f"Will write report to: [filepath]{report_name}[/]")

    report_writer = (
        push_exif_report_writer_factory(report_name, append)
        if report
        else ReportWriterNoOp()
    )

    results = {}
    with Progress(console=get_verbose_console()) as progress:
        num_photos = len(photos)
        task = progress.add_task(
            f"Processing [num]{num_photos}[/] {pluralize(num_photos, 'photo', 'photos')}",
            total=num_photos,
        )

        for photo in photos:
            photo_str = (
                f"[filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
            )
            progress.print(f"Processing {photo_str}")
            photo_results = process_photo(photo, options, push_edited, update_db)
            results[photo.uuid] = photo_results
            report_writer.write(photo.uuid, photo.original_filename, photo_results)
            progress.advance(task)

    print_results_summary(results)
    if report:
        echo(f"Wrote results to report: [filepath]{report_name}[/]")
        report_writer.close()
    echo("Done.")


def process_photo(
    photo: PhotoInfo,
    options: ExifOptions,
    push_edited: bool,
    update_db: SQLiteKVStore,
) -> PushResults:
    """
    Process a photo, writing metadata to files as needed

    Args:
        photo (PhotoInfo): The photo to process
        options (ExifOptions): The options to use when writing metadata
        push_edited (bool): Whether to write metadata to edited photos
        update_db (SQLiteKVStore): The database to use for storing metadata

    Returns:
        PushResults: The results of processing the photo
    """
    files_to_write = []
    results = PushResults()
    photo_str = f"[filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
    exif_sidecar = exiftool_json_sidecar(photo, options)

    # collect files to write
    if photo.path:
        files_to_write.append(photo.path)
    else:
        verbose(f"Skipping original for {photo_str} (missing path)")
        results.missing.append("original")
    if photo.live_photo:
        if photo.path_live_photo:
            files_to_write.append(photo.path_live_photo)
        else:
            verbose(f"Skipping live photo for {photo_str} (missing path_live_photo)")
            results.missing.append("live_photo")
    if push_edited:
        if photo.path_edited:
            files_to_write.append(photo.path_edited)
        else:
            verbose(f"Skipping edited for {photo_str} (missing path_edited)")
            results.missing.append("edited")
        if photo.live_photo and photo.path_edited_live_photo:
            files_to_write.append(photo.path_edited_live_photo)
        else:
            verbose(
                f"Skipping edited live photo for {photo_str} (missing path_edited_live_photo)"
            )
            results.missing.append("edited_live_photo")
    if photo.has_raw:
        if photo.path_raw:
            files_to_write.append(photo.path_raw)
        else:
            verbose(f"Skipping RAW for {photo_str} (missing path_raw)")
            results.missing.append("raw")

    for filepath in files_to_write:
        photo_key = f"{photo.uuid}:{filepath}"
        if photo_key in update_db:
            # already processed this file
            if update_db[photo_key] == exif_sidecar:
                verbose(f"Skipping [filepath]{filepath}[/] (no update needed)")
                results.skipped.append(filepath)
                continue
            else:
                verbose(f"Updating [filepath]{filepath}[/] (metadata changed)")
                results.updated.append(filepath)
        else:
            verbose(
                f"Writing metadata to [filepath]{filepath}[/] (not previously written)"
            )
            results.written.append(filepath)
        warnings, errors = write_exif(photo, filepath, options)
        if not errors:
            update_db[photo_key] = exif_sidecar
        else:
            results.error.append((filepath, errors))
        if warnings:
            results.warning.append((filepath, warnings))
    return results


def write_exif(
    photo: PhotoInfo, filepath: str, options: ExifOptions
) -> tuple[str | None, str | None]:
    """Write metadata to file with exiftool"""
    exif_writer = ExifWriter(photo)
    warnings, error = exif_writer.write_exif_data(filepath, options)
    if warnings:
        echo_error(f"[warning]{warnings}")
    if error:
        echo_error(f"[error]{error}")
    return warnings, error


def print_results_summary(results: dict[str, PushResults]):
    """Print results summary"""
    written = 0
    updated = 0
    skipped = 0
    missing = 0
    warnings = 0
    errors = 0
    for result in results.values():
        written += len(result.written)
        updated += len(result.updated)
        skipped += len(result.skipped)
        missing += len(result.missing)
        warnings += len(result.warning)
        errors += len(result.error)
    echo(
        f"Summary: {written} written, {updated} updated, {skipped} skipped, {missing} missing, {warnings} warning, {errors} error"
    )


def render_and_validate_report(report: str, exiftool_path: str) -> str:
    """Render a report file template and validate the filename

    Args:
        report: the template string
        exiftool_path: the path to the exiftool binary

    Returns:
        the rendered report filename

    Note:
        Exits with error if the report filename is invalid
    """
    # render report template and validate the filename
    template = PhotoTemplate(PhotoInfoNone(), exiftool_path=exiftool_path)
    render_options = RenderOptions()
    report_file, _ = template.render(report, options=render_options)
    report = report_file[0]

    if os.path.isdir(report):
        echo_error(
            f"[error]Report '{report}' is a directory, must be file name",
            err=True,
        )
        raise click.Abort()

    return report


def set_options_from_metadata(options: ExifOptions, metadata: list[str]) -> ExifOptions:
    """Set options flags for metadata to export for ExifOptions from a list of metadata named flags

    Args:
        options: ExifOptions to set flags on
        metadata: list of metadata flags to set

    Note:
        Valid flags are: all keywords location faces persons datetime title description
    Returns ExifOptions with flags set for metadata to export
    """
    if "all" in metadata:
        _set_exifoptions_metadata_flags(options, True)
        return options

    _set_exifoptions_metadata_flags(options, False)
    if "keywords" in metadata:
        options.keywords = True
    if "location" in metadata:
        options.location = True
    if "faces" in metadata:
        options.face_regions = True
    if "datetime" in metadata:
        options.datetime = True
    if "title" in metadata:
        options.title = True
    if "description" in metadata:
        options.description = True
    if "persons" in metadata:
        options.persons = True

    return options


def _set_exifoptions_metadata_flags(options: ExifOptions, value: bool):
    """Set or clear all metadata flags on ExifOptions to value"""
    options.datetime = value
    options.description = value
    options.face_regions = value
    options.keywords = value
    options.location = value
    options.persons = value
    options.title = value


def compare_exif(photos: list[PhotoInfo], options: ExifOptions):
    """Compare metadata between Photos and original files"""
    echo(
        f"[num]{len(photos)}[/] {pluralize(len(photos), 'photo', 'photos')} selected for processing"
    )

    for photo in photos:
        compare_photo(photo, options)


def compare_photo(photo: PhotoInfo, options: ExifOptions):
    """Compare metadata between Photos and original file for a single photo"""
    if not photo.path:
        echo(
            f"Cannot compare [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/]): missing original file"
        )
        return

    file_data = photo.exiftool.asdict()

    # all keywords location faces persons datetime title description favorite
    cmp_str = ""
    if options.keywords:
        cmp_str += compare_keywords(photo, file_data)

    if options.location:
        cmp_str += compare_location(photo, file_data)

    if options.face_regions:
        cmp_str += compare_face_regions(photo, file_data)

    if options.persons:
        cmp_str += compare_persons(photo, file_data)

    if options.datetime:
        cmp_str += compare_datetime(photo, file_data)

    if options.title:
        cmp_str += compare_title(photo, file_data)

    if options.description:
        cmp_str += compare_description(photo, file_data)

    if cmp_str:
        echo(
            f"Metadata differs for [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
        )
        echo(f"Path: [filepath]{photo.path}[/]")
        if cmp_str.endswith("\n"):
            cmp_str = cmp_str[:-1]
        echo(cmp_str)


def get_dict_values_as_list(d: dict[Any, Any], key: Any) -> list[Any]:
    """Get values from dict as list; if not already a list, convert to list; if key not in dict, return empty list"""
    if key in d:
        return d[key] if isinstance(d[key], list) else [d[key]]
    else:
        return []


def approx(a: float | None, b: float | None, epsilon: float = 0.00001) -> bool:
    """Return True if a and b are approximately equal"""
    if a is None and b is None:
        return True
    elif a is None or b is None:
        return False
    return abs(a - b) < epsilon


def compare_keywords(photo: PhotoInfo, file_data: dict[str, Any]) -> str:
    """Compare keywords between Photos and original file for a single photo"""
    photo_keywords = set(photo.keywords)
    exif_keywords = get_dict_values_as_list(file_data, "IPTC:Keywords")
    exif_keywords += get_dict_values_as_list(file_data, "XMP:Subject")
    exif_keywords += get_dict_values_as_list(file_data, "XMP:TagsList")
    exif_keywords = set(exif_keywords)
    if photo_keywords != exif_keywords:
        return "\n".join(
            [
                "  Keywords do not match",
                f"    Photos: {list(photo_keywords)}",
                f"      File: {list(exif_keywords)}\n",
            ],
        )
    return ""


def compare_location(photo: PhotoInfo, file_data: dict[str, Any]) -> str:
    """Compare location between Photos and original file for a single photo"""
    photo_latitude = photo.latitude
    photo_longitude = photo.longitude
    exif_latitude = file_data.get("EXIF:GPSLatitude")
    exif_longitude = file_data.get("EXIF:GPSLongitude")
    exif_latitude_ref = file_data.get("EXIF:GPSLatitudeRef")
    exif_longitude_ref = file_data.get("EXIF:GPSLongitudeRef")

    if exif_longitude and exif_longitude_ref == "W":
        exif_longitude = -exif_longitude
    if exif_latitude and exif_latitude_ref == "S":
        exif_latitude = -exif_latitude
    if not approx(photo_latitude, exif_latitude) or not approx(
        photo_longitude, exif_longitude
    ):
        return "\n".join(
            [
                "  Location does not match",
                f"    Photos: {photo_latitude}, {photo_longitude}",
                f"      File: {exif_latitude}, {exif_longitude}\n",
            ],
        )
    return ""


def compare_face_regions(photo: PhotoInfo, file_data: dict[str, Any]) -> str:
    """Compare face regions between Photos and original file for a single photo"""
    exif_writer = ExifWriter(photo)
    face_regions_photo = exif_writer._get_mwg_face_regions_exiftool()

    xmp_region_photos = get_dict_values_as_list(face_regions_photo, "XMP:RegionName")
    xmp_region_files = get_dict_values_as_list(file_data, "XMP:RegionName")
    if set(xmp_region_photos) != set(xmp_region_files):
        return "\n".join(
            [
                "  Face regions do not match (only XMP:RegionName is compared)",
                f"    Photos: {xmp_region_photos}",
                f"      File: {xmp_region_files}\n",
            ],
        )
    return ""


def compare_persons(photo: PhotoInfo, file_data: dict[str, Any]) -> str:
    """Compare persons between Photos and original file for a single photo"""
    photo_persons = set(photo.persons)
    exif_persons = set(get_dict_values_as_list(file_data, "XMP:PersonInImage"))
    if photo_persons != exif_persons:
        return "\n".join(
            [
                "  Persons do not match",
                f"    Photos: {list(photo_persons)}",
                f"      File: {list(exif_persons)}\n",
            ],
        )
    return ""


def compare_datetime(photo: PhotoInfo, file_data: dict[str, Any]) -> str:
    """Compare datetime between Photos and original file for a single photo"""
    photo_datetime = photo.date.strftime("%Y:%m:%d %H:%M:%S")
    photo_offset = photo.date.tzinfo.utcoffset(photo.date).total_seconds() / 3600
    photo_offset = f"{photo_offset//1:+03.0f}{photo_offset%1*60:02.0f}"

    exif_dt_offset = get_exif_date_time_offset(file_data)
    exif_datetime = (
        exif_dt_offset.datetime.strftime("%Y:%m:%d %H:%M:%S")
        if exif_dt_offset.datetime
        else None
    )
    exif_offset = exif_dt_offset.offset_str

    if photo_datetime != exif_datetime or photo_offset != exif_offset:
        return "\n".join(
            [
                "  Datetime does not match",
                f"    Photos: {photo_datetime} {photo_offset}",
                f"      File: {exif_datetime} {exif_offset}\n",
            ],
        )
    return ""


def compare_title(photo: PhotoInfo, file_data: dict[str, Any]) -> str:
    """Compare title between Photos and original file for a single photo"""
    photo_title = photo.title
    exif_title = file_data.get("XMP:Title") or file_data.get("IPTC:ObjectName")
    if photo_title != exif_title:
        return "\n".join(
            [
                "  Title does not match",
                f"    Photos: {photo_title}",
                f"      File: {exif_title}\n",
            ],
        )
    return ""


def compare_description(photo: PhotoInfo, file_data: dict[str, Any]) -> str:
    """Compare description between Photos and original file for a single photo"""
    photo_description = photo.description
    exif_description = (
        file_data.get("EXIF:ImageDescription")
        or file_data.get("XMP:Description")
        or file_data.get("IPTC:Caption-Abstract")
    )
    if photo_description != exif_description:
        return "\n".join(
            [
                "  Description does not match",
                f"    Photos: {photo_description}",
                f"      File: {exif_description}\n",
            ],
        )
    return ""
