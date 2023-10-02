"""exiftool command for osxphotos CLI to update an previous export with exiftool metadata"""

import os
import pathlib
import sys
from typing import Callable

import click

from osxphotos import PhotosDB, iPhotoDB
from osxphotos._constants import OSXPHOTOS_EXPORT_DB
from osxphotos._version import __version__
from osxphotos.configoptions import ConfigOptions, ConfigOptionsLoadError
from osxphotos.export_db import ExportDB, ExportDBInMemory
from osxphotos.export_db_utils import export_db_get_config
from osxphotos.exportoptions import ExportOptions, ExportResults
from osxphotos.fileutil import FileUtil, FileUtilNoOp
from osxphotos.iphoto import is_iphoto_library
from osxphotos.photoexporter import PhotoExporter
from osxphotos.sidecars import exiftool_json_sidecar
from osxphotos.utils import pluralize

from .cli_params import DB_OPTION, THEME_OPTION, TIMESTAMP_OPTION, VERBOSE_OPTION
from .click_rich_echo import rich_click_echo, rich_echo_error
from .common import get_photos_db
from .export import export, render_and_validate_report
from .param_types import ExportDBType, TemplateString
from .report_writer import ReportWriterNoOp, export_report_writer_factory
from .rich_progress import rich_progress
from .verbose import get_verbose_console, verbose_print


@click.command(name="exiftool")
@click.option(
    "--db-config",
    is_flag=True,
    help="Load configuration options from the export database to match the last export; "
    "If any other command line options are used in conjunction with --db-config, "
    "they will override the corresponding values loaded from the export database; "
    "see also --load-config.",
)
@click.option(
    "--load-config",
    required=False,
    metavar="CONFIG_FILE",
    default=None,
    help=(
        "Load options from file as written with --save-config. "
        "If any other command line options are used in conjunction with --load-config, "
        "they will override the corresponding values in the config file; "
        "see also --db-config."
    ),
    type=click.Path(exists=True),
)
@click.option(
    "--save-config",
    required=False,
    metavar="CONFIG_FILE",
    default=None,
    help="Save options to file for use with --load-config. File format is TOML. ",
    type=click.Path(),
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
    help="Optional flag/option to pass to exiftool when using --exiftool. "
    "For example, --exiftool-option '-m' to ignore minor warnings. "
    "Specify these as you would on the exiftool command line. "
    "See exiftool docs at https://exiftool.org/exiftool_pod.html for full list of options. "
    "More than one option may be specified by repeating the option, e.g. "
    "--exiftool-option '-m' --exiftool-option '-F'. ",
)
@click.option(
    "--exiftool-merge-keywords",
    is_flag=True,
    help="Merge any keywords found in the original file with keywords used for '--exiftool' and '--sidecar'.",
)
@click.option(
    "--exiftool-merge-persons",
    is_flag=True,
    help="Merge any persons found in the original file with persons used for '--exiftool' and '--sidecar'.",
)
@click.option(
    "--ignore-date-modified",
    is_flag=True,
    help="If used with --exiftool or --sidecar, will ignore the photo "
    "modification date and set EXIF:ModifyDate to EXIF:DateTimeOriginal; "
    "this is consistent with how Photos handles the EXIF:ModifyDate tag.",
)
@click.option(
    "--person-keyword",
    is_flag=True,
    help="Use person in image as keyword/tag when exporting metadata.",
)
@click.option(
    "--album-keyword",
    is_flag=True,
    help="Use album name as keyword/tag when exporting metadata.",
)
@click.option(
    "--keyword-template",
    metavar="TEMPLATE",
    multiple=True,
    default=None,
    help="For use with --exiftool, --sidecar; specify a template string to use as "
    "keyword in the form '{name,DEFAULT}' "
    "This is the same format as --directory.  For example, if you wanted to add "
    "the full path to the folder and album photo is contained in as a keyword when exporting "
    'you could specify --keyword-template "{folder_album}" '
    'You may specify more than one template, for example --keyword-template "{folder_album}" '
    '--keyword-template "{created.year}". '
    "See '--replace-keywords' and Templating System below.",
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
    help="For use with --exiftool, --sidecar; specify a template string to use as "
    "description in the form '{name,DEFAULT}' "
    "This is the same format as --directory.  For example, if you wanted to append "
    "'exported with osxphotos on [today's date]' to the description, you could specify "
    '--description-template "{descr} exported with osxphotos on {today.date}" '
    "See Templating System below.",
    type=TemplateString(),
)
@click.option(
    "--exportdb",
    help="Optional path to export database (if not in the default location in the export directory).",
    type=ExportDBType(),
)
@click.option(
    "--report",
    metavar="REPORT_FILE",
    help="Write a report of all files that were exported. "
    "The extension of the report filename will be used to determine the format. "
    "Valid extensions are: "
    ".csv (CSV file), .json (JSON), .db and .sqlite (SQLite database). "
    "REPORT_FILE may be a template string (see Templating System), for example, "
    "--report 'export_{today.date}.csv' will write a CSV report file named with today's date. "
    "See also --append.",
    type=TemplateString(),
)
@click.option(
    "--append",
    is_flag=True,
    help="If used with --report, add data to existing report file instead of overwriting it. "
    "See also --report.",
)
@VERBOSE_OPTION
@TIMESTAMP_OPTION
@click.option(
    "--dry-run",
    is_flag=True,
    help="Run in dry-run mode (don't actually update files), e.g. for use with --update-signatures.",
)
@THEME_OPTION
@DB_OPTION
@click.argument(
    "export_dir",
    metavar="EXPORT_DIRECTORY",
    nargs=1,
    type=click.Path(exists=True, file_okay=False),
)
def exiftool(
    album_keyword,
    append,
    db_config,
    db,
    description_template,
    dry_run,
    exiftool_merge_keywords,
    exiftool_merge_persons,
    exiftool_option,
    exiftool_path,
    export_dir,
    exportdb,
    ignore_date_modified,
    keyword_template,
    load_config,
    person_keyword,
    replace_keywords,
    report,
    save_config,
    theme,
    timestamp,
    verbose_flag,
):
    """Run exiftool on previously exported files to update metadata.

    If you previously exported photos with `osxphotos export` but did not include the
    `--exiftool` option and you now want to update the metadata of the exported files with
    exiftool, you can use this command to do so.

    If you simply re-run the `osxphotos export` with `--update` and `--exiftool`, osxphotos will
    re-export all photos because it will detect that the previously exported photos do not have the
    exiftool metadata updates.  This command will run exiftool on the previously exported photos
    to update all metadata then will update the export database so that using `--exiftool --update`
    with `osxphotos export` in the future will work correctly and not unnecessarily re-export photos.
    """
    # save locals for initializing config options
    locals_ = locals()

    if load_config and db_config:
        raise click.UsageError("Cannot specify both --load-config and --db-config")

    exportdb = exportdb or pathlib.Path(export_dir) / OSXPHOTOS_EXPORT_DB
    if not exportdb.exists():
        raise click.UsageError(f"Export database {exportdb} does not exist")

    # grab all the variables we need from the export command
    # export is a click Command so can walk through it's params to get the option names
    for param in export.params:
        if param.name not in locals_:
            locals_[param.name] = None

    # need to ensure --exiftool is true in the config options
    locals_["exiftool"] = True
    locals_["verbose"] = verbose_flag
    config = ConfigOptions(
        "export",
        locals_,
        ignore=[
            "cli_obj",
            "config_only",
            "ctx",
            "db_config",
            "dest",
            "export_dir",
            "load_config",
            "save_config",
        ],
    )
    verbose = verbose_print(verbose_flag, timestamp, theme=theme)

    # load config options from either file or export database
    # values already set in config will take precedence over any values
    # in the config file or database
    if load_config:
        try:
            config.load_from_file(load_config)
        except ConfigOptionsLoadError as e:
            rich_click_echo(
                f"[error]Error parsing {load_config} config file: {e.message}", err=True
            )
            sys.exit(1)
        verbose(f"Loaded options from file [filepath]{load_config}")
    elif db_config:
        config = export_db_get_config(exportdb, config)
        verbose("Loaded options from export database")

    # from here on out, use config.param_name instead of using the params passed into the function
    # as the values may have been updated from config file or database
    if load_config or db_config:
        # config file might have changed verbose
        verbose = verbose_print(config.verbose, config.timestamp, theme=theme)

    # validate options
    if append and not report:
        raise click.UsageError("--append requires --report")

    # need to ensure we have a photos database
    config.db = get_photos_db(config.db)

    if save_config:
        verbose(f"Saving options to config file '[filepath]{save_config}'")
        config.write_to_file(save_config)

    process_files(exportdb, export_dir, verbose=verbose, options=config)


def process_files(
    exportdb: str, export_dir: str, verbose: Callable[..., None], options: ConfigOptions
):
    """Process files in the export database.

    Args:
        exportdb: Path to export database.
        export_dir: Path to export directory.
        verbose: Callable for verbose output.
        options: ConfigOptions
    """

    if options.report:
        report = render_and_validate_report(
            options.report, options.exiftool_path, export_dir
        )
        report_writer = export_report_writer_factory(report, options.append)
    else:
        report_writer = ReportWriterNoOp()

    photosdb = (
        iPhotoDB(options.db, verbose=verbose)
        if is_iphoto_library(options.db)
        else PhotosDB(options.db, verbose=verbose)
    )
    if options.dry_run:
        export_db = ExportDBInMemory(exportdb, export_dir)
        fileutil = FileUtilNoOp
    else:
        export_db = ExportDB(exportdb, export_dir)
        fileutil = FileUtil

    # get_exported_files is a generator which returns tuple of (uuid, filepath)
    files = list(export_db.get_exported_files())
    # filter out sidecar files
    files = [
        (u, f)
        for u, f in files
        if pathlib.Path(f).suffix.lower() not in [".json", ".xmp"]
    ]
    total = len(files)
    count = 1
    all_results = ExportResults()
    # process files that are hardlinked? Requires user confirmation
    hardlink_ok = False
    with rich_progress(console=get_verbose_console(), mock=options.verbose) as progress:
        task = progress.add_task("Processing files", total=total)
        for uuid, file in files:
            if not pathlib.Path(file).exists():
                verbose(f"Skipping missing file [filepath]{file}[/]")
                report_writer.write(ExportResults(missing=[file]))
                continue
            if not hardlink_ok and os.stat(file).st_nlink > 1:
                rich_click_echo(
                    f"[warning]:warning-emoji:  Warning: file [filepath]{file}[/] is hardlinked.\n"
                    "You may be modifying linked original files in your Photos library. "
                    "This is inadvisable.[/]",
                )
                click.confirm("Continue processing hardlinks?", abort=True)
                hardlink_ok = True
            verbose(f"Processing file [filepath]{file}[/] ([num]{count}/{total}[/num])")
            photo = photosdb.get_photo(uuid)
            if not photo:
                verbose(
                    f"Could not find photo for [filepath]{file}[/] ([uuid]{uuid}[/])"
                )
                report_writer.write(ExportResults(missing=[file]))
                continue
            export_options = ExportOptions(
                description_template=options.description_template,
                dry_run=options.dry_run,
                exiftool_flags=options.exiftool_option,
                exiftool=True,
                export_db=export_db,
                ignore_date_modified=options.ignore_date_modified,
                keyword_template=options.keyword_template,
                merge_exif_keywords=options.exiftool_merge_keywords,
                merge_exif_persons=options.exiftool_merge_persons,
                replace_keywords=options.replace_keywords,
                use_albums_as_keywords=options.album_keyword,
                use_persons_as_keywords=options.person_keyword,
                verbose=verbose,
            )
            exporter = PhotoExporter(photo)
            results = exporter.write_exiftool_metadata_to_file(
                src=file, dest=file, options=export_options
            )
            all_results += results

            for warning_ in results.exiftool_warning:
                verbose(
                    f"[warning]exiftool warning for file {warning_[0]}: {warning_[1]}"
                )
            for error_ in results.exiftool_error:
                rich_echo_error(
                    f"[error]exiftool error for file {error_[0]}: {error_[1]}"
                )
            for result in results.exif_updated:
                verbose(f"Updated EXIF metadata for [filepath]{result}")

            # update the database
            with export_db.get_file_record(file) as rec:
                rec.dest_sig = fileutil.file_sig(file)
                rec.export_options = export_options.bit_flags
                rec.exifdata = exiftool_json_sidecar(photo, export_options)

            report_writer.write(results)
            count += 1
            progress.advance(task)

    photo_str_total = pluralize(total, "photo", "photos")
    summary = (
        f"Processed: [num]{total}[/] {photo_str_total}, "
        f"skipped: [num]{len(all_results.skipped)}[/], "
        f"updated EXIF data: [num]{len(all_results.exif_updated)}[/], "
    )
    verbose(summary)

    if options.report:
        verbose(f"Wrote export report to [filepath]{report}")
        report_writer.close()
