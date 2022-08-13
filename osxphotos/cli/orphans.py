"""Find orphaned photos in a Photos library"""

import os
import os.path
import re
import sys

# using os.path.join is slightly slower inside loop than directly using the method
from os.path import join as joinpath
from os.path import splitext
from pathlib import Path
from typing import Dict

import click

from osxphotos import PhotosDB
from osxphotos._constants import _PHOTOS_4_VERSION
from osxphotos.fileutil import FileUtil
from osxphotos.utils import increment_filename, pluralize

from .click_rich_echo import rich_click_echo as echo
from .click_rich_echo import set_rich_console, set_rich_theme, set_rich_timestamp
from .color_themes import get_theme
from .common import DB_OPTION, THEME_OPTION, get_photos_db
from .help import get_help_msg
from .list import _list_libraries
from .verbose import get_verbose_console, verbose_print


@click.command(name="orphans")
@click.option(
    "--export",
    metavar="EXPORT_PATH",
    required=False,
    type=click.Path(file_okay=False, writable=True, resolve_path=True, exists=True),
    help="Export orphans to directory EXPORT_PATH. If --export not specified, orphans are listed but not exported.",
)
@DB_OPTION
@click.option("--verbose", "-V", "verbose", is_flag=True, help="Print verbose output.")
@click.option("--timestamp", is_flag=True, help="Add time stamp to verbose output")
@THEME_OPTION
@click.pass_obj
@click.pass_context
def orphans(ctx, cli_obj, export, db, verbose, timestamp, theme):
    """Find orphaned photos in a Photos library"""

    color_theme = get_theme(theme)
    verbose_ = verbose_print(
        verbose, timestamp, rich=True, theme=color_theme, highlight=False
    )
    # set console for rich_echo to be same as for verbose_
    set_rich_console(get_verbose_console())
    set_rich_theme(color_theme)
    set_rich_timestamp(timestamp)

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(db, cli_db)
    if not db:
        echo(get_help_msg(orphans), err=True)
        echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    verbose_("Loading Photos database")
    photosdb = PhotosDB(dbfile=db, verbose=verbose_, rich=True)
    if photosdb.db_version <= _PHOTOS_4_VERSION:
        echo(
            "[error]Orphans can only be used with Photos libraries > version 5 (MacOS Catalina/10.15)[/]",
            err=True,
        )
        sys.exit(1)

    photos = photosdb.photos()
    photos += photosdb.photos(intrash=True)
    # need to add unselected bursts
    burst_photos = [bp for p in photos for bp in p.burst_photos]
    # will be some duplicates but those will be removed when converting to dict
    photos.extend(burst_photos)
    uuids_in_db = {photo.uuid: photo for photo in photos}

    # walk the Photos library looking for photos associated with a uuid
    uuids_in_library = {}

    verbose_("Scanning for orphan files")
    # originals
    verbose_("Scanning original files")
    directory = joinpath(photosdb.library_path, "originals")
    scan_for_files(directory, uuids_in_library)

    # edited
    verbose_("Scanning edited files")
    directory = joinpath(photosdb.library_path, "resources", "renders")
    scan_for_files(directory, uuids_in_library)

    # derivatives
    verbose_("Scanning derivative files")
    directory = joinpath(photosdb.library_path, "resources", "derivatives")
    scan_for_files(directory, uuids_in_library)

    # shared iCloud photos
    verbose_("Scanning shared iCloud photos")
    directory = joinpath(photosdb.library_path, "resources", "cloudsharing", "data")
    scan_for_files(directory, uuids_in_library)

    # shared derivatives
    directory = joinpath(
        "resources", "cloudsharing", "resources", "derivatives", "masters"
    )
    scan_for_files(directory, uuids_in_library)

    # find orphans
    possible_orphans = []
    for uuid, files in uuids_in_library.items():
        if uuid not in uuids_in_db:
            possible_orphans.extend(files)

    echo(
        f"Found [num]{len(possible_orphans)}[/] "
        f"{pluralize(len(possible_orphans), 'orphan', 'orphans')}"
    )
    exported = []
    for orphan in possible_orphans:
        echo(f"[filepath]{orphan}[/]")
        if export:
            dest = increment_filename(Path(export) / Path(orphan).name)
            verbose_(f"Copying [filepath]{Path(orphan).name}[/] to [filepath]{dest}[/]")
            FileUtil.copy(orphan, dest)
            exported.append(dest)
    if export:
        echo(
            f"Exported [num]{len(exported)}[/] "
            f"{pluralize(len(exported), 'file', 'files')}"
        )


def scan_for_files(directory: str, uuid_dict: Dict):
    """Walk a directory path finding any files named with UUID in the filename and add to uuid_dict

    Note: modifies uuid_dict
    """
    uuid_pattern = r"([0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12})"
    uuid_regex = re.compile(uuid_pattern)
    for dirpath, dirname, filenames in os.walk(directory):
        for filename in filenames:
            if match := uuid_regex.match(filename):
                stem, ext = splitext(filename)
                # .plist and .aae files may hold data on adjustments but these
                # are not useful by themselves so skip them
                if ext.lower() in [".plist", ".aae"]:
                    continue
                filepath = joinpath(dirpath, filename)
                try:
                    uuid_dict[match[0]].append(filepath)
                except KeyError:
                    uuid_dict[match[0]] = [filepath]
