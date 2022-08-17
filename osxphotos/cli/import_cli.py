"""import command for osxphotos CLI to import photos into Photos"""

import datetime
import logging
import os.path
import uuid
from pathlib import Path
from typing import Optional, Union

import click
from photoscript import PhotosLibrary

from osxphotos.datetime_utils import datetime_naive_to_local
from osxphotos.exiftool import ExifToolCaching, get_exiftool_path
from osxphotos.photosalbum import PhotosAlbumPhotoScript
from osxphotos.phototemplate import PhotoTemplate, RenderOptions
from osxphotos.utils import pluralize

from .click_rich_echo import (
    rich_click_echo,
    set_rich_console,
    set_rich_theme,
    set_rich_timestamp,
)
from .color_themes import get_theme
from .common import DB_OPTION, THEME_OPTION, get_photos_db
from .help import get_help_msg
from .list import _list_libraries
from .verbose import get_verbose_console, verbose_print


def echo(message, emoji=True, **kwargs):
    """Echo text with rich"""
    if emoji:
        if "[error]" in message:
            message = f":cross_mark-emoji:  {message}"
        elif "[warning]" in message:
            message = f":warning-emoji:  {message}"
    rich_click_echo(message, **kwargs)


class PhotoInfoFromFile:
    """Mock PhotoInfo class for a file to be imported

    Returns None for most attributes but allows some templates like exiftool and created to work correctly"""

    def __init__(self, filepath: Union[str, Path], exiftool: Optional[str] = None):
        self._path = str(filepath)
        self._exiftool_path = exiftool
        self._uuid = str(uuid.uuid1()).upper()

    @property
    def uuid(self):
        return self._uuid

    @property
    def original_filename(self):
        return Path(self._path).name

    @property
    def date(self):
        """Use file creation date and local timezone"""
        ctime = os.path.getctime(self._path)
        dt = datetime.datetime.fromtimestamp(ctime)
        return datetime_naive_to_local(dt)

    @property
    def path(self):
        """Path to photo file"""
        return self._path

    @property
    def exiftool(self):
        """Returns a ExifToolCaching (read-only instance of ExifTool) object for the photo.
        Requires that exiftool (https://exiftool.org/) be installed
        If exiftool not installed, logs warning and returns None
        If photo path is missing, returns None
        """
        try:
            # return the memoized instance if it exists
            return self._exiftool
        except AttributeError:
            try:
                exiftool_path = self._exiftool_path or get_exiftool_path()
                if self._path is not None and os.path.isfile(self._path):
                    exiftool = ExifToolCaching(self._path, exiftool=exiftool_path)
                else:
                    exiftool = None
            except FileNotFoundError:
                # get_exiftool_path raises FileNotFoundError if exiftool not found
                exiftool = None
                logging.warning(
                    "exiftool not in path; download and install from https://exiftool.org/"
                )

            self._exiftool = exiftool
            return self._exiftool

    def render_template(
        self, template_str: str, options: Optional[RenderOptions] = None
    ):
        """Renders a template string for PhotoInfo instance using PhotoTemplate

        Args:
            template_str: a template string with fields to render
            options: a RenderOptions instance

        Returns:
            ([rendered_strings], [unmatched]): tuple of list of rendered strings and list of unmatched template values
        """
        options = options or RenderOptions()
        template = PhotoTemplate(self, exiftool_path=self._exiftool_path)
        return template.render(template_str, options)

    def __getattr__(self, name):
        """Return None for any other non-private attribute"""
        if not name.startswith("_"):
            return None
        raise AttributeError()


# TODO: Add --merge-metadata (to merge with what Photos will read from XMP)
# Add --no-metadata (to import with no metadata)
@click.command(name="import")
@click.option(
    "--album",
    "-a",
    metavar="ALBUM_TEMPLATE",
    multiple=True,
    help="Import photos into album ALBUM_TEMPLATE. "
    "ALBUM_TEMPLATE is an osxphotos template string. "
    "Photos may be imported into more than one album by repeating --album.",
)
@click.option(
    "--relative-to",
    metavar="RELATIVE_TO_PATH",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="If set, the '{filepath}' template "
    "will be computed relative to RELATIVE_TO_PATH. "
    "For example, if path to import is '/Volumes/photos/import/album/img_1234.jpg' "
    "then '{filepath}' will be this same value. "
    "If you set '--relative-to /Volumes/photos/import' "
    "then '{filepath}' will be set to 'album/img_1234.jpg'",
)
@click.option("--dup-check", is_flag=True, help="Check for duplicates on import.")
@click.option(
    "--auto-folder",
    is_flag=True,
    help="Automatically create folders for albums as needed. "
    "If album name contains '/' (e.g. 'Folder/Album') and '--auto-folder' is set, "
    "folders and albums will be split on '/' and automatically created as needed. ",
)
@DB_OPTION
@click.option("--verbose", "-V", "verbose_", is_flag=True, help="Print verbose output.")
@click.option("--timestamp", is_flag=True, help="Add time stamp to verbose output")
@THEME_OPTION
@click.argument("files", nargs=-1)
@click.pass_obj
@click.pass_context
def import_cli(
    ctx,
    cli_obj,
    album,
    relative_to,
    dup_check,
    auto_folder,
    db,
    verbose_,
    timestamp,
    theme,
    files,
):
    """Import photos and videos into Photos"""

    color_theme = get_theme(theme)
    verbose = verbose_print(
        verbose_, timestamp, rich=True, theme=color_theme, highlight=False
    )
    # set console for rich_echo to be same as for verbose_
    set_rich_console(get_verbose_console())
    set_rich_theme(color_theme)
    set_rich_timestamp(timestamp)

    if not files:
        echo("Nothing to import", err=True)
        return

    # below needed for to make CliRunner work for testing
    cli_db = cli_obj.db if cli_obj is not None else None
    db = get_photos_db(db, cli_db)
    if not db:
        echo(get_help_msg(import_cli), err=True)
        echo("\n\nLocated the following Photos library databases: ", err=True)
        _list_libraries()
        return

    relative_to = Path(relative_to) if relative_to else None

    photoslib = PhotosLibrary()

    imported_count = 0
    error_count = 0
    echo(f"Importing [num]{len(files)}[/] {pluralize(len(files), 'file', 'files')}")
    for file in files:
        file = Path(file).resolve().absolute()
        filepath = file
        verbose(f"Importing [filepath]{file}[/]")
        if relative_to:
            try:
                filepath = filepath.relative_to(relative_to)
            except ValueError as e:
                echo(
                    f"--relative-to value of '{relative_to}' is not in the same path as '{filepath}'",
                    err=True,
                )
                raise click.Abort() from e

        # render album names and metadata templates
        photoinfo = PhotoInfoFromFile(file)
        options = RenderOptions(filepath=filepath)
        albums = []
        for a in album:
            album_names, _ = photoinfo.render_template(a, options=options)
            # filter out empty strings
            album_names = [a for a in album_names if a]
            albums.extend(album_names)

        if imported := photoslib.import_photos(
            [file], skip_duplicate_check=not dup_check
        ):
            verbose(
                f"Imported [filename]{filepath.name}[/] with UUID [uuid]{imported[0].uuid}[/]"
            )
            photo = imported[0]
            imported_count += 1
        else:
            echo(f"[error]Error importing file [filepath]{file}[/][/]", err=True)
            error_count += 1
            continue

        for a in albums:
            verbose(
                f"Adding photo [filename]{filepath.name}[/] to album [filepath]{a}[/]"
            )
            photos_album = PhotosAlbumPhotoScript(
                a, verbose=verbose, auto_folder=auto_folder
            )
            photos_album.add(photo)

    echo(
        f"Done: imported [num]{imported_count}[/] {pluralize(imported_count, 'file', 'files')}, "
        f"[num]{error_count}[/] {pluralize(error_count, 'error', 'errors')}",
        emoji=False,
    )
