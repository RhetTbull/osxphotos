"""Push EXIF data to original files in the Photos library"""

from __future__ import annotations

import os

import click
from rich.progress import Progress

from osxphotos import PhotoInfo
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
from .param_types import TemplateString
from .push_results import PushResults
from .report_writer import ReportWriterNoOp, push_exif_report_writer_factory
from .verbose import get_verbose_console

assert_macos()


@query_command(name="push-exif")
@click.option(
    "--push-edited",
    is_flag=True,
    help="Push EXIF data to edited photos in addition to originals",
)
@click.option(
    "--exiftool-path",
    metavar="EXIFTOOL_PATH",
    type=click.Path(exists=True),
    help="Optionally specify path to exiftool; if not provided, will look for exiftool in $PATH.",
)
@click.option(
    "--exiftool-option",
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
def push_exif(
    photos: list[PhotoInfo],
    push_edited: bool,
    exiftool_path: str,
    exiftool_option: tuple[str],
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
    **kwargs,
):
    """Write photo metadata to original files in the Photos library

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
    """

    # validation
    if not photos:
        echo_error("No photos selected for processing")
        raise click.Abort()

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

    exiftool_path = exiftool_path or get_exiftool_path()
    verbose(f"Found exiftool at: [filepath]{exiftool_path}")

    update_db = kvstore("push_exif")
    echo(f"Using update database: [filepath]{update_db.path}[/]")

    report_name = render_and_validate_report(report, exiftool_path) if report else None
    verbose(f"Will write report to: [filepath]{report_name}[/]")

    report_writer = (
        push_exif_report_writer_factory(report_name, append)
        if report
        else ReportWriterNoOp()
    )

    options = exif_options_from_locals(locals())
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
