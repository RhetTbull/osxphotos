"""import command for osxphotos CLI to import photos into Photos"""

import datetime
import logging
import os.path
import uuid
from collections import namedtuple
from pathlib import Path
from textwrap import dedent
from typing import Callable, List, Optional, Tuple, Union

import click
from photoscript import Photo, PhotosLibrary
from rich.console import Console
from rich.markdown import Markdown

from osxphotos._constants import _OSXPHOTOS_NONE_SENTINEL
from osxphotos.cli.help import HELP_WIDTH
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
from .rich_progress import rich_progress
from .verbose import get_verbose_console, verbose_print

MetaData = namedtuple("MetaData", ["title", "description", "keywords", "location"])


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


def import_photo(
    filepath: Path, dup_check: bool, verbose: Callable[..., None]
) -> Tuple[Optional[Photo], Optional[str]]:
    """Import a photo and return Photo object and error string if any

    Args:
        filepath: path to the file to import
        dup_check: enable or disable Photo's duplicate check on import
        verbose: Callable"""
    if imported := PhotosLibrary().import_photos(
        [filepath], skip_duplicate_check=not dup_check
    ):
        verbose(
            f"Imported [filename]{filepath.name}[/] with UUID [uuid]{imported[0].uuid}[/]"
        )
        photo = imported[0]
        return photo, None
    else:
        error_str = f"[error]Error importing file [filepath]{filepath}[/][/]"
        echo(error_str, err=True)
        return None, error_str


def render_photo_template(
    filepath: Path,
    relative_filepath: Path,
    template: str,
    exiftool_path: Optional[str],
):
    """Render template string for a photo"""

    photoinfo = PhotoInfoFromFile(filepath, exiftool=exiftool_path)
    options = RenderOptions(
        none_str=_OSXPHOTOS_NONE_SENTINEL, filepath=relative_filepath
    )
    template_values, _ = photoinfo.render_template(template, options=options)
    # filter out empty strings
    template_values = [v.replace(_OSXPHOTOS_NONE_SENTINEL, "") for v in template_values]
    template_values = [v for v in template_values if v]
    return template_values


def add_photo_to_albums(
    photo: Photo,
    filepath: Path,
    relative_filepath: Path,
    album: Tuple[str],
    auto_folder: bool,
    exiftool_path: Path,
    verbose: Callable[..., None],
):
    """Add photo to one or more albums"""
    albums = []
    for a in album:
        albums.extend(
            render_photo_template(filepath, relative_filepath, a, exiftool_path)
        )
    verbose(
        f"Adding photo [filename]{filepath.name}[/filename] to {len(albums)} {pluralize(len(albums), 'album', 'albums')}"
    )

    # add photo to albums
    for a in albums:
        verbose(f"Adding photo [filename]{filepath.name}[/] to album [filepath]{a}[/]")
        photos_album = PhotosAlbumPhotoScript(
            a, verbose=verbose, auto_folder=auto_folder
        )
        photos_album.add(photo)


def clear_photo_metadata(photo: Photo, filepath: Path, verbose: Callable[..., None]):
    """Clear any metadata (title, description, keywords) associated with Photo in the Photos Library"""
    verbose(f"Clearing metadata for [filename]{filepath.name}[/]")
    photo.title = ""
    photo.description = ""
    photo.keywords = []


def clear_photo_location(photo: Photo, filepath: Path, verbose: Callable[..., None]):
    """Clear any location (latitude, longitude) associated with Photo in the Photos Library"""
    verbose(f"Clearing location for [filename]{filepath.name}[/]")
    photo.location = (None, None)


def metadata_from_file(filepath: Path, exiftool_path: str) -> MetaData:
    """Get metadata from file with exiftool

    Returns the following metadata from EXIF/XMP/IPTC fields as a MetaData named tuple
        title: str, XMP:Title, IPTC:ObjectName, QuickTime:DisplayName
        description: str, XMP:Description, IPTC:Caption-Abstract, EXIF:ImageDescription, QuickTime:Description
        keywords: str, XMP:Subject, XMP:TagsList, IPTC:Keywords (QuickTime:Keywords not supported)
        location: Tuple[lat, lon],  EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef, EXIF:GPSLatitude, EXIF:GPSLongitude, QuickTime:GPSCoordinates, UserData:GPSCoordinates
    """
    exiftool = ExifToolCaching(filepath, exiftool_path)
    metadata = exiftool.asdict()
    title = (
        metadata.get("XMP:Title")
        or metadata.get("IPTC:ObjectName")
        or metadata.get("QuickTime:DisplayName")
    )
    description = (
        metadata.get("XMP:Description")
        or metadata.get("IPTC:Caption-Abstract")
        or metadata.get("EXIF:ImageDescription")
        or metadata.get("QuickTime:Description")
    )
    keywords = (
        metadata.get("XMP:Subject")
        or metadata.get("XMP:TagsList")
        or metadata.get("IPTC:Keywords")
    )

    title = title or ""
    description = description or ""
    keywords = keywords or []
    if not isinstance(keywords, (tuple, list)):
        keywords = [keywords]

    location = location_from_file(filepath, exiftool_path)
    return MetaData(title, description, keywords, location)


def location_from_file(
    filepath: Path, exiftool_path: str
) -> Tuple[Optional[float], Optional[float]]:
    """Get location from file with exiftool

    Returns:
        Tuple of lat, long or None, None if not set

    Note:
        Attempts to get location from the following EXIF fields:
            EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef
            EXIF:GPSLatitude, EXIF:GPSLongitude
            QuickTime:GPSCoordinates
            UserData:GPSCoordinates
    """
    exiftool = ExifToolCaching(filepath, exiftool_path)
    metadata = exiftool.asdict()

    # photos and videos store location data differently
    # for photos, location in EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef, EXIF:GPSLatitude, EXIF:GPSLongitude
    # the GPSLatitudeRef and GPSLongitudeRef are needed to determine N/S, E/W respectively
    # for example:
    #   EXIF:GPSLatitudeRef N
    #   EXIF:GPSLongitudeRef W
    #   EXIF:GPSLatitude 33.7198027777778
    #   EXIF:GPSLongitude 118.285491666667
    # for video, location in QuickTime:GPSCoordinates or UserData:GPSCoordinates as a
    # pair of positive/negative numbers thus no ref needed
    # for example:
    #   QuickTime:GPSCoordinates 34.0533 -118.2423

    latitude, longitude = None, None
    try:
        if latitude := metadata.get("EXIF:GPSLatitude"):
            latitude = float(latitude)
            latitude_ref = metadata.get("EXIF:GPSLatitudeRef")
            if latitude_ref == "S":
                latitude = -latitude
            elif latitude_ref != "N":
                latitude = None
        if longitude := metadata.get("EXIF:GPSLongitude"):
            longitude = float(longitude)
            longitude_ref = metadata.get("EXIF:GPSLongitudeRef")
            if longitude_ref == "W":
                longitude = -longitude
            elif longitude_ref != "E":
                longitude = None
        if latitude is None or longitude is None:
            # maybe it's a video
            if lat_lon := metadata.get("QuickTime:GPSCoordinates") or metadata.get(
                "UserData:GPSCoordinates"
            ):
                lat_lon = lat_lon.split()
                if len(lat_lon) != 2:
                    latitude = None
                    longitude = None
                else:
                    latitude = float(lat_lon[0])
                    longitude = float(lat_lon[1])
    except ValueError:
        # couldn't convert one of the numbers to float
        return None, None
    return latitude, longitude


def set_photo_metadata(photo: Photo, metadata: MetaData, merge_keywords: bool):
    """Set metadata (title, description, keywords) for a Photo object"""
    photo.title = metadata.title
    photo.description = metadata.description
    keywords = metadata.keywords.copy()
    if merge_keywords:
        if old_keywords := photo.keywords:
            keywords.extend(old_keywords)
            keywords = list(set(keywords))
    photo.keywords = keywords


def set_photo_metadata_from_exiftool(
    photo: Photo,
    filepath: Path,
    exiftool_path: str,
    merge_keywords: bool,
    verbose: Callable[..., None],
):
    """Set photo's metadata by reading metadata form file with exiftool"""
    verbose(f"Setting metadata and location from EXIF for [filename]{filepath.name}[/]")
    metadata = metadata_from_file(filepath, exiftool_path)
    if any([metadata.title, metadata.description, metadata.keywords]):
        set_photo_metadata(photo, metadata, merge_keywords)
        verbose(f"Set metadata for [filename]{filepath.name}[/]:")
        verbose(
            f"title='{metadata.title}', description='{metadata.description}', keywords={metadata.keywords}"
        )
    else:
        verbose(f"No metadata to set for [filename]{filepath.name}[/]")
    if metadata.location[0] is not None and metadata.location[1] is not None:
        # location will be set to None, None if latitude or longitude is missing
        photo.location = metadata.location
        verbose(
            f"Set location for [filename]{filepath.name}[/]: "
            f"[num]{metadata.location[0]}[/], [num]{metadata.location[1]}[/]"
        )
    else:
        verbose(f"No location to set for [filename]{filepath.name}[/]")


def set_photo_title(
    photo: Photo,
    filepath: Path,
    relative_filepath: Path,
    title_template: str,
    exiftool_path: str,
    verbose: Callable[..., None],
):
    """Set title of photo"""
    title_text = render_photo_template(
        filepath, relative_filepath, title_template, exiftool_path
    )
    if len(title_text) > 1:
        echo(
            f"photo can have only a single title: '{title_template}' = {title_text}",
            err=True,
        )
        raise click.Abort()
    if title_text:
        verbose(
            f"Setting title of photo [filename]{filepath.name}[/] to '{title_text[0]}'"
        )
        photo.title = title_text[0]


def set_photo_description(
    photo: Photo,
    filepath: Path,
    relative_filepath: Path,
    description_template: str,
    exiftool_path: str,
    verbose: Callable[..., None],
):
    """Set description of photo"""
    description_text = render_photo_template(
        filepath, relative_filepath, description_template, exiftool_path
    )
    if len(description_text) > 1:
        echo(
            f"photo can have only a single description: '{description_template}' = {description_text}",
            err=True,
        )
        raise click.Abort()
    if description_text:
        verbose(
            f"Setting description of photo [filename]{filepath.name}[/] to '{description_text[0]}'"
        )
        photo.description = description_text[0]


def set_photo_keywords(
    photo: Photo,
    filepath: Path,
    relative_filepath: Path,
    keyword_template: str,
    exiftool_path: str,
    merge: bool,
    verbose: Callable[..., None],
):
    """Set keywords of photo"""
    keywords = []
    for keyword in keyword_template:
        kw = render_photo_template(filepath, relative_filepath, keyword, exiftool_path)
        keywords.extend(kw)
    if keywords:
        if merge:
            if old_keywords := photo.keywords:
                keywords.extend(old_keywords)
                keywords = list(set(keywords))
        verbose(f"Setting keywords of photo [filename]{filepath.name}[/] to {keywords}")
        photo.keywords = keywords


def set_photo_location(
    photo: Photo,
    filepath: Path,
    location: Tuple[float, float],
    verbose: Callable[..., None],
):
    """Set location of photo"""
    verbose(
        f"Setting location of photo [filename]{filepath.name}[/] to {location[0]}, {location[1]}"
    )
    photo.location = location


class ImportCommand(click.Command):
    """Custom click.Command that overrides get_help() to show additional help info for import"""

    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        formatter = click.HelpFormatter(width=HELP_WIDTH)
        extra_help = dedent(
            """
            ## Examples

            Import a file into Photos:
            `osxphotos import /Volumes/photos/img_1234.jpg`

            Import multiple jpg files into Photos:

            `osxphotos import /Volumes/photos/*.jpg`

            Import files into Photos and add to album:

            `osxphotos import /Volumes/photos/*.jpg --album "My Album"`

            ## Albums

            TODO:

            ## Metadata

            `osxphotos import` can set metadata (title, description, keywords) for 
            imported photos using several options. 

            If you have exiftool (https://exiftool.org/) installed, osxphotos can use
            exiftool to extract metadata from the imported file and use this to update
            the metadata in Photos.

            The `--exiftool` option will automatically attempt to update title, 
            description, keywords, and location from the file's metadata:
            
            `osxphotos import *.jpg --exiftool` 

            The following metadata fields are read (in priority order) and used to set 
            the metadata of the imported photo:

            - Title: XMP:Title, IPTC:ObjectName
            - Description: XMP:Description, IPTC:Caption-Abstract, EXIF:ImageDescription
            - Keywords: XMP:Subject, XMP:TagsList, IPTC:Keywords

            When importing photos, Photos itself will usually read most of these same fields 
            and set the metadata but when importing via AppleScript (which is how `osxphotos 
            import` interacts with Photos), Photos does not always reliably do this. It is 
            recommended you use `--exiftool` to ensure metadata gets correctly imported.

            You can also use `--clear-metadata` to remove any metadata automatically set by
            Photos upon import.

            ## Template System

            TODO
        """
        )
        console = Console()
        with console.capture() as capture:
            console.print(Markdown(extra_help), width=min(HELP_WIDTH, console.width))
        formatter.write(capture.get())
        help_text += "\n\n" + formatter.getvalue()
        return help_text


# TODO: add --location
@click.command(name="import", cls=ImportCommand)
@click.option(
    "--album",
    "-a",
    metavar="ALBUM_TEMPLATE",
    multiple=True,
    help="Import photos into album ALBUM_TEMPLATE. "
    "ALBUM_TEMPLATE is an osxphotos template string. "
    "Photos may be imported into more than one album by repeating --album. "
    "See Templating System in help for additional information.",
)
@click.option(
    "--title",
    "-t",
    metavar="TITLE_TEMPLATE",
    help="Set title of imported photos to TITLE_TEMPLATE. "
    "TITLE_TEMPLATE is a an osxphotos template string. "
    "See Templating System in help for additional information.",
)
@click.option(
    "--description",
    "-d",
    metavar="DESCRIPTION_TEMPLATE",
    help="Set description of imported photos to DESCRIPTION_TEMPLATE. "
    "DESCRIPTION_TEMPLATE is a an osxphotos template string. "
    "See Templating System in help for additional information.",
)
@click.option(
    "--keyword",
    "-k",
    metavar="KEYWORD_TEMPLATE",
    multiple=True,
    help="Set keywords of imported photos to KEYWORD_TEMPLATE. "
    "KEYWORD_TEMPLATE is a an osxphotos template string. "
    "More than one keyword may be set by repeating --keyword. "
    "See Templating System in help for additional information.",
)
@click.option(
    "--merge-keywords",
    is_flag=True,
    help="Merge keywords created by --exiftool or --keyword "
    "with any keywords already associated with the photo. "
    "Without --merge-keywords, existing keywords will be overwritten.",
)
@click.option(
    "--location",
    "-l",
    metavar="LATITUDE LONGITUDE",
    nargs=2,
    type=click.Tuple([click.FloatRange(-90.0, 90.0), click.FloatRange(-180.0, 180.0)]),
    help="Set location of imported photo to LATITUDE LONGITUDE. "
    "Latitude is a number in the range -90.0 to 90.0; "
    "positive latitudes are north of the equator, negative latitudes are south of the equator. "
    "Longitude is a number in the range -180.0 to 180.0; "
    "positive longitudes are east of the Prime Meridian; negative longitudes are west of the Prime Meridian.",
)
@click.option(
    "--clear-metadata",
    "-C",
    is_flag=True,
    help="Clear any metadata set automatically "
    "by Photos upon import. Normally, Photos will set title, description, and keywords "
    "from XMP metadata in the imported file.  If you specify --clear-metadata, any metadata "
    "set by Photos will be cleared after import.",
)
@click.option(
    "--clear-location",
    "-L",
    is_flag=True,
    help="Clear any location data automatically imported by Photos. "
    "Normally, Photos will set location of the photo to the location data found in the "
    "metadata in the imported file.  If you specify --clear-location, "
    "this data will be cleared after import.",
)
@click.option(
    "--exiftool",
    "-e",
    is_flag=True,
    help="Use third party tool exiftool (https://exiftool.org/) to automatically "
    "update metadata (title, description, keywords, location) in imported photos from "
    "the imported file's metadata.",
)
@click.option(
    "--exiftool-path",
    "-p",
    metavar="EXIFTOOL_PATH",
    type=click.Path(exists=True, dir_okay=False),
    help="Optionally specify path to exiftool; if not provided, will look for exiftool in $PATH.",
)
@click.option(
    "--relative-to",
    "-r",
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
    "-f",
    is_flag=True,
    help="Automatically create folders for albums as needed. "
    "If album name contains '/' (e.g. 'Folder/Album') and '--auto-folder' is set, "
    "folders and albums will be split on '/' and automatically created as needed. ",
)
@DB_OPTION
@click.option("--verbose", "-V", "verbose_", is_flag=True, help="Print verbose output.")
@click.option(
    "--timestamp", "-T", is_flag=True, help="Add time stamp to verbose output"
)
@click.option(
    "--no-progress", is_flag=True, help="Do not display progress bar during import."
)
@THEME_OPTION
@click.argument("files", nargs=-1)
@click.pass_obj
@click.pass_context
def import_cli(
    ctx,
    cli_obj,
    album,
    title,
    description,
    keyword,
    merge_keywords,
    location,
    clear_metadata,
    clear_location,
    exiftool,
    exiftool_path,
    relative_to,
    dup_check,
    auto_folder,
    db,
    verbose_,
    timestamp,
    no_progress,
    theme,
    files,
):
    """Import photos and videos into Photos."""

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

    imported_count = 0
    error_count = 0
    filecount = len(files)
    with rich_progress(console=get_verbose_console(), mock=no_progress) as progress:
        task = progress.add_task(
            f"Importing [num]{filecount}[/] {pluralize(filecount, 'file', 'files')}",
            total=filecount,
        )
        for filepath in files:
            filepath = Path(filepath).resolve().absolute()
            relative_filepath = filepath

            # check relative_to here so we abort before import if relative_to is bad
            if relative_to:
                try:
                    relative_filepath = relative_filepath.relative_to(relative_to)
                except ValueError as e:
                    echo(
                        f"--relative-to value of '{relative_to}' is not in the same path as '{relative_filepath}'",
                        err=True,
                    )
                    raise click.Abort() from e

            verbose(f"Importing [filepath]{filepath}[/]")
            photo, error = import_photo(filepath, dup_check, verbose)
            if error:
                error_count += 1
                continue
            imported_count += 1

            if clear_metadata:
                clear_photo_metadata(photo, filepath, verbose)

            if clear_location:
                clear_photo_location(photo, filepath, verbose)

            if exiftool:
                set_photo_metadata_from_exiftool(
                    photo, filepath, exiftool_path, merge_keywords, verbose
                )

            if title:
                set_photo_title(
                    photo, filepath, relative_filepath, title, exiftool_path, verbose
                )

            if description:
                set_photo_description(
                    photo,
                    filepath,
                    relative_filepath,
                    description,
                    exiftool_path,
                    verbose,
                )

            if keyword:
                set_photo_keywords(
                    photo,
                    filepath,
                    relative_filepath,
                    keyword,
                    exiftool_path,
                    merge_keywords,
                    verbose,
                )

            if location:
                set_photo_location(photo, filepath, location, verbose)

            if album:
                add_photo_to_albums(
                    photo,
                    filepath,
                    relative_filepath,
                    album,
                    auto_folder,
                    exiftool_path,
                    verbose,
                )

            progress.advance(task)

    echo(
        f"Done: imported [num]{imported_count}[/] {pluralize(imported_count, 'file', 'files')}, "
        f"[num]{error_count}[/] {pluralize(error_count, 'error', 'errors')}",
        emoji=False,
    )
