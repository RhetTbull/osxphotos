"""import command for osxphotos CLI to import photos into Photos"""

from __future__ import annotations

import csv
import dataclasses
import datetime
import fnmatch
import json
import logging
import os
import os.path
import pathlib
import sqlite3
import sys
import uuid
from contextlib import suppress
from textwrap import dedent
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, Union

import click
from rich.console import Console
from rich.markdown import Markdown
from strpdatetime import strpdatetime

from osxphotos.platform import assert_macos

assert_macos()

from photoscript import Photo, PhotosLibrary

import osxphotos.sqlite3_datetime as sqlite3_datetime
from osxphotos._constants import (
    _OSXPHOTOS_NONE_SENTINEL,
    OSXPHOTOS_EXPORT_DB,
    SQLITE_CHECK_SAME_THREAD,
)
from osxphotos._version import __version__
from osxphotos.cli.cli_params import TIMESTAMP_OPTION, VERBOSE_OPTION
from osxphotos.cli.common import get_data_dir
from osxphotos.cli.help import HELP_WIDTH
from osxphotos.cli.param_types import FunctionCall, StrpDateTimePattern, TemplateString
from osxphotos.datetime_utils import (
    datetime_has_tz,
    datetime_naive_to_local,
    datetime_remove_tz,
    datetime_tz_to_utc,
    datetime_utc_to_local,
)
from osxphotos.exiftool import ExifToolCaching, get_exiftool_path
from osxphotos.fingerprint import fingerprint
from osxphotos.fingerprintquery import FingerprintQuery
from osxphotos.metadata_reader import (
    MetaData,
    get_sidecar_for_file,
    metadata_from_file,
    metadata_from_sidecar,
)
from osxphotos.photoinfo import PhotoInfoNone
from osxphotos.photosalbum import PhotosAlbumPhotoScript
from osxphotos.phototemplate import PhotoTemplate, RenderOptions
from osxphotos.sqlitekvstore import SQLiteKVStore
from osxphotos.strpdatetime_parts import (
    date_str_matches_date_time_codes,
    fmt_has_date_time_codes,
)
from osxphotos.unicode import normalize_unicode
from osxphotos.utils import get_last_library_path, pluralize

from .cli_params import THEME_OPTION
from .click_rich_echo import rich_click_echo, rich_echo_error
from .rich_progress import rich_progress
from .verbose import get_verbose_console, verbose_print

if TYPE_CHECKING:
    from .cli import CLI_Obj

# register datetime adapters/converters for sqlite3
sqlite3_datetime.register()


OSXPHOTOS_ABOUT_STRING = f"Created by osxphotos version {__version__} (https://github.com/RhetTbull/osxphotos) on {datetime.datetime.now()}"

# stores import status so imports can be resumed
IMPORT_DB = "osxphotos_import.db"

try:
    EXIFTOOL_PATH = get_exiftool_path()
except FileNotFoundError:
    EXIFTOOL_PATH = None


def echo(message, emoji=True, **kwargs):
    """Echo text with rich"""
    if emoji:
        if "[error]" in message:
            message = f":cross_mark-emoji:  {message}"
        elif "[warning]" in message:
            message = f":warning-emoji:  {message}"
    rich_click_echo(message, **kwargs)


def get_sidecar_file(
    filepath: pathlib.Path,
    relative_filepath: str | None,
    sidecar: bool,
    sidecar_template: str | None,
    exiftool_path: str | None,
    verbose: Callable[..., None],
) -> pathlib.Path | None:
    if sidecar or sidecar_template:
        if sidecar_template:
            if sidecar_file := render_photo_template(
                filepath,
                relative_filepath,
                sidecar_template,
                exiftool_path,
                None,
            ):
                sidecar_file = pathlib.Path(sidecar_file[0])
        else:
            sidecar_file = get_sidecar_for_file(filepath)
        if not sidecar_file or not sidecar_file.exists():
            verbose(f"No sidecar found for [filepath]{filepath}[/]")
            sidecar_file = None
    else:
        sidecar_file = None
    return sidecar_file


class PhotoInfoFromFile:
    """Mock PhotoInfo class for a file to be imported

    Returns None for most attributes but allows some templates like exiftool and created to work correctly
    """

    def __init__(
        self,
        filepath: Union[str, pathlib.Path],
        exiftool: str | None = None,
        sidecar: str | None = None,
    ):
        self._path = str(filepath)
        self._exiftool_path = exiftool or EXIFTOOL_PATH
        self._uuid = str(uuid.uuid1()).upper()
        self._sidecar = sidecar
        if sidecar:
            self._metadata = metadata_from_sidecar(pathlib.Path(sidecar), exiftool)
        elif self._exiftool_path:
            self._metadata = metadata_from_file(
                pathlib.Path(filepath), self._exiftool_path
            )
        else:
            self._metadata = MetaData(
                title="", description="", keywords=[], location=(None, None)
            )

    @property
    def uuid(self):
        return self._uuid

    @property
    def original_filename(self):
        return pathlib.Path(self._path).name

    @property
    def filename(self):
        return pathlib.Path(self._path).name

    @property
    def date(self):
        """Use file creation date and local time zone if not exiftool or sidecar"""
        if self._metadata.date:
            if dt := self._metadata.date:
                return datetime_naive_to_local(dt)

        ctime = os.path.getctime(self._path)
        dt = datetime.datetime.fromtimestamp(ctime)
        return datetime_naive_to_local(dt)

    @property
    def path(self):
        """Path to photo file"""
        return self._path

    @property
    def keywords(self) -> list[str]:
        """list of keywords for picture"""
        return self._metadata.keywords

    @property
    def persons(self) -> list[str]:
        """list of persons in picture"""
        return self._metadata.persons

    @property
    def title(self) -> str | None:
        """name / title of picture"""
        return self._metadata.title

    @property
    def description(self) -> str | None:
        """description of picture"""
        return self._metadata.description

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
        options = options or RenderOptions(caller="import")
        template = PhotoTemplate(self, exiftool_path=self._exiftool_path)
        return template.render(template_str, options)

    def __getattr__(self, name):
        """Return None for any other non-private attribute"""
        if not name.startswith("_"):
            return None
        raise AttributeError()


def import_photo(
    filepath: pathlib.Path, dup_check: bool, verbose: Callable[..., None]
) -> Tuple[Optional[Photo], str | None]:
    """Import a photo and return Photo object and error string if any

    Args:
        filepath: path to the file to import
        dup_check: enable or disable Photo's duplicate check on import
        verbose: Callable
    """
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
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path,
    template: str,
    exiftool_path: str | None,
    sidecar: str | None,
):
    """Render template string for a photo"""

    photoinfo = PhotoInfoFromFile(filepath, exiftool=exiftool_path, sidecar=sidecar)
    options = RenderOptions(
        none_str=_OSXPHOTOS_NONE_SENTINEL, filepath=relative_filepath, caller="import"
    )
    template_values, _ = photoinfo.render_template(template, options=options)
    # filter out empty strings
    template_values = [v.replace(_OSXPHOTOS_NONE_SENTINEL, "") for v in template_values]
    template_values = [v for v in template_values if v]
    return template_values


def add_photo_to_albums(
    photo: Photo,
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path,
    album: Tuple[str],
    split_folder: str,
    exiftool_path: pathlib.Path,
    sidecar: pathlib.Path | None,
    verbose: Callable[..., None],
    dry_run: bool,
) -> list[str]:
    """Add photo to one or more albums"""
    albums = []
    for a in album:
        albums.extend(
            render_photo_template(
                filepath, relative_filepath, a, exiftool_path, sidecar
            )
        )
    verbose(
        f"Adding photo [filename]{filepath.name}[/filename] to {len(albums)} {pluralize(len(albums), 'album', 'albums')}"
    )

    # add photo to albums
    for a in albums:
        verbose(f"Adding photo [filename]{filepath.name}[/] to album [filepath]{a}[/]")
        if not dry_run:
            photos_album = PhotosAlbumPhotoScript(
                a, verbose=verbose, split_folder=split_folder, rich=True
            )
            photos_album.add(photo)
    return albums


def add_duplicate_to_albums(
    duplicates: list[tuple[str, datetime.datetime, str]],
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path,
    album: Tuple[str],
    split_folder: str,
    exiftool_path: pathlib.Path,
    sidecar: pathlib.Path | None,
    verbose: Callable[..., None],
    dry_run: bool,
) -> list[str]:
    """For photo with already imported duplicate, add the imported photo to albums

    duplicates: list of tuples of (uuid, date, filename) for duplicates as returned by FingerprintQuery.possible_duplicates
    filepath: path to file to import
    relative_filepath: relative path to file to import
    album: list of album templates
    split_folder: str to split folders on
    exiftool_path: path to exiftool
    verbose: verbose function
    dry_run: dry run

    Returns: list of albums photo was added to or empty list if no photo found for duplicate
    """
    dup_photo = None
    for uuid, _, _ in duplicates:
        # if there are multiple duplicates, use the first one
        # there could be an error retrieving the Photo for the duplicate uuid
        # if it was deleted from the Photos library or in the hidden album
        # so if there's an error, try the next one
        try:
            dup_photo = Photo(uuid=uuid)
            break
        except Exception as e:
            # no photo found for duplicate
            rich_echo_error(f"[error] Error getting duplicate photo: {e}")

    if not dup_photo:
        return []

    return add_photo_to_albums(
        dup_photo,
        filepath,
        relative_filepath,
        album,
        split_folder,
        exiftool_path,
        sidecar,
        verbose,
        dry_run,
    )


def clear_photo_metadata(
    photo: Photo, filepath: pathlib.Path, verbose: Callable[..., None], dry_run: bool
):
    """Clear any metadata (title, description, keywords) associated with Photo in the Photos Library"""
    verbose(f"Clearing metadata for [filename]{filepath.name}[/]")
    if dry_run:
        return
    photo.title = ""
    photo.description = ""
    photo.keywords = []


def clear_photo_location(
    photo: Photo, filepath: pathlib.Path, verbose: Callable[..., None], dry_run: bool
):
    """Clear any location (latitude, longitude) associated with Photo in the Photos Library"""
    verbose(f"Clearing location for [filename]{filepath.name}[/]")
    if dry_run:
        return
    photo.location = (None, None)


def set_photo_metadata(
    photo: Photo,
    metadata: MetaData,
    merge_keywords: bool,
    dry_run: bool,
) -> MetaData:
    """Set metadata (title, description, keywords) for a Photo object

    Args:
        photo: Photo object
        metadata: MetaData object
        merge_keywords: if True, merge keywords with existing keywords
        dry_run: if True, do not actually set metadata

    Returns: MetaData object with metadata updated keywords if merge_keywords is True
    """
    if dry_run:
        return metadata
    photo.title = normalize_unicode(metadata.title)
    photo.description = normalize_unicode(metadata.description)
    keywords = metadata.keywords.copy()
    keywords = normalize_unicode(keywords)
    if merge_keywords:
        if old_keywords := normalize_unicode(photo.keywords):
            keywords.extend(old_keywords)
            keywords = list(set(keywords))
    photo.keywords = keywords
    return dataclasses.replace(metadata, keywords=keywords)


def set_photo_metadata_from_exiftool(
    photo: Photo,
    filepath: pathlib.Path,
    exiftool_path: str,
    merge_keywords: bool,
    verbose: Callable[..., None],
    dry_run: bool,
):
    """Set photo's metadata by reading metadata from file with exiftool"""
    verbose(f"Setting metadata and location from EXIF for [filename]{filepath.name}[/]")
    metadata = metadata_from_file(filepath, exiftool_path)
    set_photo_metadata_from_metadata(
        photo, filepath, metadata, merge_keywords, True, verbose, dry_run
    )


def set_photo_metadata_from_metadata(
    photo: Photo,
    filepath: pathlib.Path,
    metadata: MetaData,
    merge_keywords: bool,
    ignore_date: bool,
    verbose: Callable[..., None],
    dry_run: bool,
) -> MetaData:
    """Set metadata from a MetaData object"""
    if any([metadata.title, metadata.description, metadata.keywords]):
        metadata = set_photo_metadata(photo, metadata, merge_keywords, dry_run)
        verbose(f"Set metadata for [filename]{filepath.name}[/]:")
        verbose(
            f"title='{metadata.title}', description='{metadata.description}', keywords={metadata.keywords}"
        )
    else:
        verbose(f"No metadata to set for [filename]{filepath.name}[/]")

    if metadata.location[0] is not None and metadata.location[1] is not None:
        # location will be set to None, None if latitude or longitude is missing
        if not dry_run:
            photo.location = metadata.location
        verbose(
            f"Set location for [filename]{filepath.name}[/]: "
            f"[num]{metadata.location[0]}[/], [num]{metadata.location[1]}[/]"
        )
    else:
        verbose(f"No location to set for [filename]{filepath.name}[/]")

    if metadata.date is not None and not ignore_date:
        verbose(
            f"Set date for [filename]{filepath.name}[/]: [time]{metadata.date.isoformat()}[/]"
        )
        if not dry_run:
            photo.date = metadata.date

    return metadata


def set_photo_metadata_from_sidecar(
    photo: Photo,
    filepath: pathlib.Path,
    sidecar: pathlib.Path,
    sidecar_ignore_date: bool,
    exiftool_path: str | None,
    merge_keywords: bool,
    verbose: Callable[..., None],
    dry_run: bool,
):
    """Set photo's metadata by reading metadata from sidecar. If sidecar format is XMP, exiftool must be installed."""
    verbose(
        f"Setting metadata and location from sidecar [filename]{sidecar.name}[/] for [filename]{filepath.name}[/]"
    )
    try:
        metadata = metadata_from_sidecar(sidecar, exiftool_path)
    except ValueError as e:
        rich_echo_error(f"Error reading sidecar [filename]{sidecar.name}[/]: {e}")
        return
    set_photo_metadata_from_metadata(
        photo, filepath, metadata, merge_keywords, sidecar_ignore_date, verbose, dry_run
    )


def set_photo_title(
    photo: Photo,
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path,
    title_template: str,
    exiftool_path: str,
    sidecar: pathlib.Path | None,
    verbose: Callable[..., None],
    dry_run: bool,
) -> str:
    """Set title of photo"""
    title_text = render_photo_template(
        filepath, relative_filepath, title_template, exiftool_path, sidecar
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
        if not dry_run:
            photo.title = normalize_unicode(title_text[0])
        return title_text[0]
    else:
        return ""


def set_photo_description(
    photo: Photo,
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path,
    description_template: str,
    exiftool_path: str,
    sidecar: pathlib.Path | None,
    verbose: Callable[..., None],
    dry_run: bool,
) -> str:
    """Set description of photo"""
    description_text = render_photo_template(
        filepath,
        relative_filepath,
        description_template,
        exiftool_path,
        sidecar,
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
        if not dry_run:
            photo.description = normalize_unicode(description_text[0])
        return description_text[0]
    else:
        return ""


def set_photo_keywords(
    photo: Photo,
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path,
    keyword_template: str,
    exiftool_path: str,
    merge: bool,
    sidecar: pathlib.Path | None,
    verbose: Callable[..., None],
    dry_run: bool,
) -> list[str]:
    """Set keywords of photo"""
    keywords = []
    for keyword in keyword_template:
        kw = render_photo_template(
            filepath, relative_filepath, keyword, exiftool_path, sidecar
        )
        keywords.extend(kw)
    if keywords:
        keywords = normalize_unicode(keywords)
        if merge:
            if old_keywords := normalize_unicode(photo.keywords):
                keywords.extend(old_keywords)
                keywords = list(set(keywords))
        verbose(f"Setting keywords of photo [filename]{filepath.name}[/] to {keywords}")
        if not dry_run:
            photo.keywords = keywords
    return keywords


def set_photo_location(
    photo: Photo,
    filepath: pathlib.Path,
    location: Tuple[float, float],
    verbose: Callable[..., None],
    dry_run: bool,
) -> tuple[float, float]:
    """Set location of photo"""
    verbose(
        f"Setting location of photo [filename]{filepath.name}[/] to {location[0]}, {location[1]}"
    )
    if not dry_run:
        photo.location = location
    return location


def combine_date_time(
    photo: Photo | None,
    filepath: str | pathlib.Path,
    parse_date: str,
    date: datetime.datetime,
) -> datetime.datetime:
    """Combine date and time from parse_date and photo.date

    If parse_date has both date and time, use the parsed date and time
    If parse_date has only date, use the parsed date and time from photo
    If parse_date has only time, use the parsed time and date from photo

    Photo may be None during --dry-run
    """
    if photo is None:
        return date
    has_date, has_time = date_str_matches_date_time_codes(str(filepath), parse_date)
    if has_date and not has_time:
        # date only, no time, set date to date but keep time from photo
        date = datetime.datetime.combine(date.date(), photo.date.time())
    elif has_time and not has_date:
        # time only, no date, set time to time but keep date from photo
        date = datetime.datetime.combine(photo.date.date(), date.time())
    return date


def set_photo_date_from_filename(
    photo: Photo,
    photo_name: str,
    filepath: pathlib.Path | str,
    parse_date: str,
    verbose: Callable[..., None],
    dry_run: bool,
) -> datetime.datetime | None:
    """Set date of photo from filename or path"""
    try:
        date = strpdatetime(str(filepath), parse_date)
        # Photo.date must be timezone naive (assumed to local timezone)
        if datetime_has_tz(date):
            local_date = datetime_remove_tz(
                datetime_utc_to_local(datetime_tz_to_utc(date))
            )
            verbose(
                f"Moving date with timezone [time]{date}[/] to local timezone: [time]{local_date.strftime('%Y-%m-%d %H:%M:%S')}[/]"
            )
            date = local_date
    except ValueError:
        verbose(f"[warning]Could not parse date from [filepath]{filepath}[/][/]")
        return None

    date = combine_date_time(photo, filepath, parse_date, date)
    verbose(
        f"Setting date of photo [filename]{photo_name}[/] to [time]{date.strftime('%Y-%m-%d %H:%M:%S')}[/]"
    )
    if not dry_run:
        photo.date = date
    return date


def get_relative_filepath(
    filepath: pathlib.Path, relative_to: str | None
) -> pathlib.Path:
    """Get relative filepath of file relative to relative_to or return filepath if relative_to is None

    Args:
        filepath: path to file
        relative_to: path to directory to which filepath is relative

    Returns: relative filepath or filepath if relative_to is None

    Raises: click.Abort if relative_to is not in the same path as filepath
    """
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

    return relative_filepath


def check_templates_and_exit(
    files: List[str],
    relative_to: Optional[pathlib.Path],
    title: str | None,
    description: str | None,
    keyword: Tuple[str],
    album: Tuple[str],
    exiftool_path: str | None,
    exiftool: bool,
    parse_date: str | None,
    parse_folder_date: str | None,
    sidecar: bool,
    sidecar_template: str | None = None,
):
    """Renders templates against each file so user can verify correctness"""
    for file in files:
        file = pathlib.Path(file).absolute().resolve()
        relative_filepath = get_relative_filepath(file, relative_to)
        sidecar_file = get_sidecar_file(
            filepath=file,
            relative_filepath=relative_filepath,
            sidecar=sidecar,
            sidecar_template=sidecar_template,
            exiftool_path=exiftool_path,
            verbose=echo,
        )
        echo(f"[filepath]{file}[/]:")
        if exiftool:
            metadata = metadata_from_file(file, exiftool_path)
            echo(f"exiftool title: {metadata.title}")
            echo(f"exiftool description: {metadata.description}")
            echo(f"exiftool keywords: {metadata.keywords}")
            echo(f"exiftool location: {metadata.location}")
        if title:
            rendered_title = render_photo_template(
                file, relative_filepath, title, exiftool_path, sidecar_file
            )
            rendered_title = rendered_title[0] if rendered_title else "None"
            echo(f"title: [italic]{title}[/]: {rendered_title}")
        if description:
            rendered_description = render_photo_template(
                file, relative_filepath, description, exiftool_path, sidecar_file
            )
            rendered_description = (
                rendered_description[0] if rendered_description else "None"
            )
            echo(f"description: [italic]{description}[/]: {rendered_description}")
        if keyword:
            for kw in keyword:
                rendered_keywords = render_photo_template(
                    file, relative_filepath, kw, exiftool_path, sidecar_file
                )
                rendered_keywords = rendered_keywords or "None"
                echo(f"keyword: [italic]{kw}[/]: {rendered_keywords}")
        if album:
            for al in album:
                rendered_album = render_photo_template(
                    file, relative_filepath, al, exiftool_path, sidecar_file
                )
                rendered_album = rendered_album[0] if rendered_album else "None"
                echo(f"album: [italic]{al}[/]: {rendered_album}")
        if parse_date:
            try:
                date = strpdatetime(file.name, parse_date)
                has_date, has_time = fmt_has_date_time_codes(parse_date)
                if has_date and not has_time:
                    date = date.date()
                elif not has_date and has_time:
                    date = date.time()
                echo(f"parse_date: [italic]{parse_date}[/]: {date}")
            except ValueError:
                echo(
                    f"[warning]Could not parse date from filename [filename]{file.name}[/][/]"
                )
        if parse_folder_date:
            try:
                date = strpdatetime(str(file.parent), parse_folder_date)
                has_date, has_time = fmt_has_date_time_codes(parse_folder_date)
                if has_date and not has_time:
                    date = date.date()
                elif not has_date and has_time:
                    date = date.time()
                echo(f"parse_folder_date: [italic]{parse_folder_date}[/]: {date}")
            except ValueError:
                echo(
                    f"[warning]Could not parse date from folder [filepath]{file.parent}[/][/]"
                )
    sys.exit(0)


@dataclasses.dataclass
class ReportRecord:
    """Dataclass that records metadata on each file imported for writing to report"""

    albums: list[str] = dataclasses.field(default_factory=list)
    description: str = ""
    error: bool = False
    filename: str = ""
    filepath: pathlib.Path = dataclasses.field(default_factory=pathlib.Path)
    import_datetime: datetime.datetime = datetime.datetime.now()
    imported: bool = False
    keywords: list[str] = dataclasses.field(default_factory=list)
    location: tuple[float, float] = dataclasses.field(default_factory=tuple)
    title: str = ""
    uuid: str = ""
    datetime: datetime.datetime | None = None

    @classmethod
    def serialize(cls, record: "ReportRecord") -> str:
        """Serialize class instance to JSON"""
        return json.dumps(record.asjsondict())

    @classmethod
    def deserialize(cls, json_string: str) -> "ReportRecord":
        """Deserialize class from JSON"""
        dict_data = json.loads(json_string)
        dict_data["filepath"] = pathlib.Path(dict_data["filepath"])
        dict_data["import_datetime"] = datetime.datetime.fromisoformat(
            dict_data["import_datetime"]
        )
        dict_data["datetime"] = (
            datetime.datetime.fromisoformat(dict_data["datetime"])
            if dict_data["datetime"]
            else None
        )
        return cls(**dict_data)

    def update_from_metadata(self, metadata: MetaData):
        """Update a ReportRecord with data from a MetaData"""
        self.title = metadata.title
        self.description = metadata.description
        self.keywords = metadata.keywords
        self.location = metadata.location

    def asdict(self):
        return dataclasses.asdict(self)

    def asjsondict(self):
        """Return a JSON serializable dict"""
        dict_data = self.asdict()
        dict_data["filepath"] = str(dict_data["filepath"])
        dict_data["import_datetime"] = dict_data["import_datetime"].isoformat()
        dict_data["datetime"] = (
            dict_data["datetime"].isoformat() if dict_data["datetime"] else None
        )
        return dict_data


def update_report_record(
    report_record: ReportRecord, photo: Photo, filepath: pathlib.Path
):
    """Update a ReportRecord with data from a Photo"""

    # do not update albums as they are added to the report record as they are imported (#934)
    report_record.filename = filepath.name
    report_record.filepath = filepath
    report_record.uuid = photo.uuid
    report_record.title = photo.title
    report_record.description = photo.description
    report_record.keywords = photo.keywords
    report_record.location = photo.location
    report_record.datetime = photo.date

    return report_record


def write_report(
    report_file: str, report_data: dict[pathlib.Path, ReportRecord], append: bool
):
    """Write report to file"""
    report_type = os.path.splitext(report_file)[1][1:].lower()
    if report_type == "csv":
        write_csv_report(report_file, report_data, append)
    elif report_type == "json":
        write_json_report(report_file, report_data, append)
    elif report_type in ["db", "sqlite"]:
        write_sqlite_report(report_file, report_data, append)
    else:
        echo(f"Unknown report type: {report_type}", err=True)
        raise click.Abort()


def write_csv_report(
    report_file: str, report_data: dict[pathlib.Path, ReportRecord], append: bool
):
    """Write report to csv file"""
    with open(report_file, "a" if append else "w") as f:
        writer = csv.writer(f)
        if not append:
            writer.writerow(
                [
                    "filepath",
                    "filename",
                    "import_datetime",
                    "uuid",
                    "imported",
                    "error",
                    "title",
                    "description",
                    "keywords",
                    "albums",
                    "location",
                    "datetime",
                ]
            )
        for report_record in report_data.values():
            writer.writerow(
                [
                    report_record.filepath,
                    report_record.filename,
                    report_record.import_datetime,
                    report_record.uuid,
                    report_record.imported,
                    report_record.error,
                    report_record.title,
                    report_record.description,
                    ",".join(report_record.keywords),
                    ",".join(report_record.albums),
                    report_record.location,
                    report_record.datetime,
                ]
            )


def write_json_report(
    report_file: str, report_data: dict[pathlib.Path, ReportRecord], append: bool
):
    """Write report to JSON file"""
    records = [v.asjsondict() for v in report_data.values()]
    if append:
        with open(report_file, "r") as f:
            existing_records = json.load(f)
        records.extend(existing_records)
    with open(report_file, "w") as f:
        json.dump(records, f, indent=4)


def write_sqlite_report(
    report_file: str, report_data: dict[pathlib.Path, ReportRecord], append: bool
):
    """Write report to SQLite file"""
    if not append:
        with suppress(FileNotFoundError):
            os.unlink(report_file)

    file_exists = os.path.isfile(report_file)

    conn = sqlite3.connect(report_file, check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()

    if not append or not file_exists:
        # Create the tables
        c.execute(
            """CREATE TABLE IF NOT EXISTS report (
                report_id INTEGER,
                filepath TEXT,
                filename TEXT,
                import_datetime TEXT,
                uuid TEXT,
                imported INTEGER,
                error INTEGER,
                title TEXT,
                description TEXT,
                keywords TEXT,
                albums TEXT,
                location TEXT,
                datetime TEXT
            )"""
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS about (
                id INTEGER PRIMARY KEY,
                about TEXT
                );"""
        )
        c.execute(
            "INSERT INTO about(about) VALUES (?);",
            (f"OSXPhotos Import Report. {OSXPHOTOS_ABOUT_STRING}",),
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS report_id (
                report_id INTEGER PRIMARY KEY,
                datetime TEXT
            );"""
        )

    # Insert report_id
    c.execute(
        "INSERT INTO report_id(datetime) VALUES (?);",
        (datetime.datetime.now().isoformat(),),
    )
    report_id = c.lastrowid

    for report_record in report_data.values():
        c.execute(
            """INSERT INTO report (
                report_id,
                filepath,
                filename,
                import_datetime,
                uuid,
                imported,
                error,
                title,
                description,
                keywords,
                albums,
                location,
                datetime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            (
                report_id,
                str(report_record.filepath),
                report_record.filename,
                report_record.import_datetime.isoformat()
                if report_record.import_datetime
                else None,
                report_record.uuid,
                report_record.imported,
                report_record.error,
                report_record.title,
                report_record.description,
                ",".join(report_record.keywords),
                ",".join(report_record.albums),
                f"{report_record.location[0]},{report_record.location[1]}",
                report_record.datetime.isoformat() if report_record.datetime else None,
            ),
        )
    conn.commit()
    conn.close()


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
    render_options = RenderOptions(caller="import")
    report_file, _ = template.render(report, options=render_options)
    report = report_file[0]

    if os.path.isdir(report):
        rich_click_echo(
            f"[error]Report '{report}' is a directory, must be file name",
            err=True,
        )
        sys.exit(1)

    extension = os.path.splitext(report)[1]
    if extension.lower() not in [".csv", ".json", ".db", ".sqlite"]:
        rich_click_echo(
            f"[error]Report '{report}' has invalid extension, must be .csv, .json, .db, or .sqlite",
            err=True,
        )
        sys.exit(1)
    return report


def filename_matches_patterns(filename: str, patterns: Tuple[str]) -> bool:
    """Return True if filename matches any pattern in patterns"""
    return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)


def collect_files_to_import(
    files: Tuple[str], walk: bool, glob: Tuple[str]
) -> List[str]:
    """Collect files to import, recursively if necessary

    Args:
        files: list of initial files or directories to import
        walk: whether to walk directories
        glob: optional glob patterns to match files

    Note: ignores any files that appear to be image sidecar files
    """
    files_to_import = []
    for file in files:
        if os.path.isfile(file):
            if glob and filename_matches_patterns(os.path.basename(file), glob):
                files_to_import.append(file)
            elif not glob:
                files_to_import.append(file)
        elif os.path.isdir(file):
            if walk:
                for root, dirs, files in os.walk(file):
                    for file in files:
                        if glob and filename_matches_patterns(
                            os.path.basename(file), glob
                        ):
                            files_to_import.append(os.path.join(root, file))
                        elif not glob:
                            files_to_import.append(os.path.join(root, file))
        else:
            continue

    # strip any sidecar files
    files_to_import = [
        f
        for f in files_to_import
        if pathlib.Path(f).suffix.lower() not in [".json", ".xmp"]
    ]

    # strip osxphotos export db in case importing an osxphotos export
    files_to_import = [
        f for f in files_to_import if not pathlib.Path(f).name == OSXPHOTOS_EXPORT_DB
    ]

    # strip .DS_Store
    files_to_import = [
        f for f in files_to_import if not pathlib.Path(f).name == ".DS_Store"
    ]

    return files_to_import


def import_files(
    last_library: str,
    files: list[str],
    no_progress: bool,
    resume: bool,
    clear_metadata: bool,
    clear_location: bool,
    exiftool: bool,
    exiftool_path: str,
    sidecar: bool,
    sidecar_ignore_date: bool,
    sidecar_template: str,
    merge_keywords: bool,
    title: str | None,
    description: str | None,
    keyword: tuple[str, ...],
    location: tuple[float, float],
    parse_date: str | None,
    parse_folder_date: str | None,
    album: tuple[str, ...],
    dup_albums: bool,
    split_folder: str,
    post_function: tuple[Callable[..., None]],
    skip_dups: bool,
    dup_check: bool,
    dry_run: bool,
    report_data: dict[pathlib.Path, ReportRecord],
    relative_to: str | None,
    import_db: SQLiteKVStore,
    verbose: Callable[..., None],
):
    """Import files into Photos library

    Returns: tuple of imported_count, skipped_count, error_count
    """

    # initialize FingerprintQuery to be able to find duplicates
    fq = FingerprintQuery(last_library)

    imported_count = 0
    error_count = 0
    skipped_count = 0
    filecount = len(files)
    with rich_progress(console=get_verbose_console(), mock=no_progress) as progress:
        task = progress.add_task(
            f"Importing [num]{filecount}[/] {pluralize(filecount, 'file', 'files')}",
            total=filecount,
        )
        for filepath in files:
            filepath = pathlib.Path(filepath).resolve().absolute()
            relative_filepath = get_relative_filepath(filepath, relative_to)

            # check if file already imported
            if resume:
                if record := import_db.get(str(filepath)):
                    if record.imported and not record.error:
                        # file already imported
                        verbose(
                            f"Skipping [filepath]{filepath}[/], "
                            f"already imported on [time]{record.import_datetime.isoformat()}[/] "
                            f"with UUID [uuid]{record.uuid}[/]"
                        )
                        skipped_count += 1
                        progress.advance(task)
                        continue

            verbose(f"Importing [filepath]{filepath}[/]")

            report_data[filepath] = ReportRecord(
                filepath=filepath, filename=filepath.name
            )
            report_record = report_data[filepath]

            if sidecar or sidecar_template:
                sidecar_file = get_sidecar_file(
                    filepath=filepath,
                    relative_filepath=relative_filepath,
                    sidecar=sidecar,
                    sidecar_template=sidecar_template,
                    exiftool_path=exiftool_path,
                    verbose=verbose,
                )
            else:
                sidecar_file = None

            if duplicates := fq.possible_duplicates(filepath):
                # duplicate of file already in Photos library
                verbose(
                    f"File [filepath]{filepath}[/] appears to be a duplicate of photos in the library: "
                    f"{', '.join([f'[filename]{f}[/] ([uuid]{u}[/]) added [datetime]{d}[/] ' for u, d, f in duplicates])}"
                )

                if skip_dups:
                    verbose(f"Skipping duplicate [filepath]{filepath}[/]")
                    skipped_count += 1
                    report_record.imported = False

                    if dup_albums and album:
                        report_record.albums = add_duplicate_to_albums(
                            duplicates,
                            filepath,
                            relative_filepath,
                            album,
                            split_folder,
                            exiftool_path,
                            sidecar_file,
                            verbose,
                            dry_run,
                        )

                    continue

            if not dry_run:
                photo, error = import_photo(filepath, dup_check, verbose)
                if error:
                    error_count += 1
                    report_record.error = True
                    continue
            else:
                photo = None
            report_record.imported = True
            imported_count += 1

            if clear_metadata:
                clear_photo_metadata(photo, filepath, verbose, dry_run)

            if clear_location:
                clear_photo_location(photo, filepath, verbose, dry_run)

            if exiftool:
                set_photo_metadata_from_exiftool(
                    photo, filepath, exiftool_path, merge_keywords, verbose, dry_run
                )

            if sidecar_file:
                set_photo_metadata_from_sidecar(
                    photo,
                    filepath,
                    sidecar_file,
                    sidecar_ignore_date,
                    exiftool_path,
                    merge_keywords,
                    verbose,
                    dry_run,
                )

            if title:
                set_photo_title(
                    photo,
                    filepath,
                    relative_filepath,
                    title,
                    exiftool_path,
                    sidecar_file,
                    verbose,
                    dry_run,
                )

            if description:
                set_photo_description(
                    photo,
                    filepath,
                    relative_filepath,
                    description,
                    exiftool_path,
                    sidecar_file,
                    verbose,
                    dry_run,
                )

            if keyword:
                set_photo_keywords(
                    photo,
                    filepath,
                    relative_filepath,
                    keyword,
                    exiftool_path,
                    merge_keywords,
                    sidecar_file,
                    verbose,
                    dry_run,
                )

            if location:
                set_photo_location(photo, filepath, location, verbose, dry_run)

            if parse_date:
                set_photo_date_from_filename(
                    photo, filepath.name, filepath.name, parse_date, verbose, dry_run
                )

            if parse_folder_date:
                set_photo_date_from_filename(
                    photo,
                    filepath.name,
                    filepath.parent,
                    parse_folder_date,
                    verbose,
                    dry_run,
                )

            if album:
                report_record.albums = add_photo_to_albums(
                    photo,
                    filepath,
                    relative_filepath,
                    album,
                    split_folder,
                    exiftool_path,
                    sidecar_file,
                    verbose,
                    dry_run,
                )

            if post_function:
                for function in post_function:
                    # post function is tuple of (function, filename.py::function_name)
                    verbose(f"Calling post-function [bold]{function[1]}")
                    if not dry_run:
                        try:
                            function[0](photo, filepath, verbose, report_record)
                        except Exception as e:
                            rich_echo_error(
                                f"[error]Error running post-function [italic]{function[1]}[/italic]: {e}"
                            )

            # update report data
            if not dry_run:
                update_report_record(report_record, photo, filepath)
                import_db.set(str(filepath), report_record)

            progress.advance(task)

    return imported_count, skipped_count, error_count


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

            Import files into Photos and add to album named for 4-digit year of file creation date:

            `oxphotos import /Volumes/photos/*.jpg --album "{created.year}"`

            Import files into Photos and add to album named for month of the year in folder named
            for the 4-digit year of the file creation date:

            `osxphotos import /Volumes/photos/*.jpg --album "{created.year}/{created.month}" --split-folder "/"`

            ## Albums

            The imported files may be added to one or more albums using the `--album` option.
            The value passed to `--album` may be a literal string or an osxphotos template
            (see Template System below).  For example:

            `osxphotos import /Volumes/photos/*.jpg --album "Vacation"` 

            adds all photos to the album "Vacation".  The album will be created if it does not
            already exist.

            `osxphotos import /Volumes/photos/Madrid/*.jpg --album "{filepath.parent.name}"`

            adds all photos to the album "Madrid" (the name of the file's parent folder).

            ## Folders

            If you want to organize the imported photos into both folders and albums, you can
            use the `--split-folder` option.  For example, if your photos are organized into 
            folders as follows:
            
                .
                ├── 2021
                │   ├── Family
                │   └── Travel
                └── 2022
                    ├── Family
                    └── Travel

            You can recreate this hierarchal structure on import using 
            
            `--album "{filepath.parent}" --split-folder "/"`

            In this example, `{filepath.parent}` renders to '2021/Family', '2021/Travel', etc.
            and `--split-folder "/"` instructs osxphotos to split the album name into separate 
            parts '2021' and 'Family'.
            
            If your photos are organized in a set of folders but you want to exclude one or more parent
            folders from the list of folders and album, you can use the `--relative-to` option to specify
            the parent path that all subsequent paths should be relative to.  For example, if your photos
            are organized into photos as follows:

                /
                └── Volumes
                    └── Photos
                        ├── 2021
                        │   ├── Family
                        │   └── Travel
                        └── 2022
                            ├── Family
                            └── Travel

            and you want to exclude /Volumes/Photos from the folder/album path, you can do this:

            `osxphotos import /Volumes/Photos/* --walk --album "{filepath.parent}" --relative-to "/Volumes/Photos" --split-folder "/"`

            This will produce folders/albums `2021/Family`, `2021/Travel`, and so on.

            Note: in Photos, only albums can contain photos and folders
            may contain albums or other folders. 

            ## Duplicate Checking

            By default, `osxphotos import` will import all files passed to it even if duplicates
            exist in the Photos library. If you want to skip duplicate files, you can use the
            `--skip-dups` option which will cause osxphotos to check for exact duplicates (based on file fingerprint)
            and skip those files. Alternatively, you can use `--dup-check` to enable Photos' own duplicate
            checking. If a duplicate is encountered with `--dup-check`, Photos will prompt you
            to skip or import the duplicate file.

            If you use the `--verbose` option, osxphotos will report on any duplicates it finds
            even if you don't use `--skip-dups` or `--dup-check`.  This is useful with --dry-run
            to see if any duplicates exist in the Photos library before importing.

            ## Metadata

            `osxphotos import` can set metadata (title, description, keywords, and location) for 
            imported photos/videos using several options. 

            If you have exiftool (https://exiftool.org/) installed, osxphotos can use
            exiftool to extract metadata from the imported file and use this to update
            the metadata in Photos.

            The `--exiftool` option will automatically attempt to update title, 
            description, keywords, and location from the file's metadata:
            
            `osxphotos import *.jpg --exiftool` 

            The following metadata fields are read (in priority order) and used to set 
            the metadata of the imported photo:

            - Title: XMP:Title, IPTC:ObjectName, QuickTime:DisplayName
            - Description: XMP:Description, IPTC:Caption-Abstract, EXIF:ImageDescription, QuickTime:Description
            - Keywords: XMP:Subject, XMP:TagsList, IPTC:Keywords (QuickTime:Keywords not supported)
            - Location: EXIF:GPSLatitude/EXIF:GPSLatitudeRef, EXIF:GPSLongitude/EXIF:GPSLongitudeRef, QuickTime:GPSCoordinates, UserData:GPSCoordinates

            When importing photos, Photos itself will usually read most of these same fields 
            and set the metadata but when importing via AppleScript (which is how `osxphotos 
            import` interacts with Photos), Photos does not always reliably do this. It is 
            recommended you use `--exiftool` to ensure metadata gets correctly imported.

            You can also use `--clear-metadata` to remove any metadata automatically set by
            Photos upon import.

            In addition to `--exiftool`, you can specify a template (see Template System below) 
            for setting title (`--title`), description (`--description`), and keywords (`--keywords`). 
            Location can be set using `--location`.  The album(s) of the imported file can likewise
            be specified with `--album`.

            `--title`, `--description`, `--keyword`, and `--album` all take a literal string or an 
            osxphotos template string.  If a template string is used, the template is rendered 
            using the osxphotos template language to produce the final value.

            For example:

            `--title "{exiftool:XMP:Title}"` sets the title of the imported file to whatever value
            is in the `XMP:Title` metadata field (as read by `exiftool`).

            `--keyword "Vacation"` sets the keyword for the imported file to the literal string "Vacation".

            If the photo metadata or sidecar contains the names of persons in the image (e.g. `XMP:PersonInImage`),
            you can use the `{person}` template to add the names of the persons to the keywords.  For example:

            `--keyword "{person}"` will add the names of the persons in the image to the keywords.

            This is helpful as Photos will not import person names from the metadata and osxphotos
            cannot set person names in Photos (this is a limitation of Photos).

            To use the `{person}` template, you must have exiftool installed and in your path or
            the data must be in a sidecar file.

            ## Template System

            As mentioned above, the `--title`, `--description`, `--keyword`, and `--album` options 
            all take an osxphotos template language template string that is further rendered to
            produce the final value.  The template system used by `osxphotos import` is a subset
            of the template system used by `osxphotos export`. For a complete description of the
            template system, see `osxphotos help export`.

            Most fields in the osxphotos template system are not available to `osxphotos import` as
            they are derived from data in the Photos library and the photos will obviously not be
            imported yet. The following fields are available:

            #### {exiftool}
            - `{exiftool}`: Format: '{exiftool:GROUP:TAGNAME}'; use exiftool (https://exiftool.org)
            to extract metadata, in form GROUP:TAGNAME, from image.
            E.g. '{exiftool:EXIF:Make}' to get camera make, or {exiftool:IPTC:Keywords} to extract
            keywords. See https://exiftooip=l.org/TagNames/ for list of valid tag names.
            You must specify group (e.g. EXIF, IPTC, etc) as used in `exiftool -G`.
            exiftool must be installed in the path to use this template (alternatively, you can use
            `--exiftool-path` to specify the path to exiftool.)
            
            #### {filepath}
            
            - `{filepath}`: The full path to the file being imported.
            For example, `/Volumes/photos/img_1234.jpg`. 
            
            `{filepath}` has several subfields that
            allow you to access various parts of the path using the following subfield modifiers:

            - `{filepath.parent}`: the parent directory
            - `{filepath.name}`: the name of the file or final sub-directory
            - `{filepath.stem}`: the name of the file without the extension
            - `{filepath.suffix}`: the suffix of the file including the leading '.'

            For example, if the field `{filepath}` is '/Shared/Backup/Photos/IMG_1234.JPG':
            - `{filepath.parent}` is '/Shared/Backup/Photos'
            - `{filepath.name}` is 'IMG_1234.JPG'
            - `{filepath.stem}` is 'IMG_1234'
            - `{filepath.suffix}` is '.JPG'

            Subfields may be chained, for example, `{filepath.parent.parent}` in the above
            example would be `/Shared/Backup` and `{filepath.parent.name}` would be `Photos`.

            `{filepath}` may be modified using the `--relative-to` option.  For example,
            if the path to the imported photo is `/Volumes/Photos/Folder1/Album1/IMG_1234.jpg` 
            and you specify `--relative-to "/Volumes/Photos"` then `{filepath}` will be set
            to `Folder1/Album1/IMG_1234.jpg`
            (a subset of the path relative to the value of `--relative-to`).

            #### {created}

            - `{created}`: The date the file was created.  `{created}` must be used with a subfield to 
            specify the format of the date.

            - `{created.date}`: Photo's creation date in ISO format, e.g. '2020-03-22'
            - `{created.year}`: 4-digit year of photo creation time
            - `{created.yy}`: 2-digit year of photo creation time
            - `{created.mm}`: 2-digit month of the photo creation time (zero padded)
            - `{created.month}`: Month name in user's locale of the photo creation time
            - `{created.mon}`: Month abbreviation in the user's locale of the photo creation time
            - `{created.dd}`: 2-digit day of the month (zero padded) of photo creation time
            - `{created.dow}`: Day of week in user's locale of the photo creation time
            - `{created.doy}`: 3-digit day of year (e.g Julian day) of photo creation time, starting from 1 (zero padded)
            - `{created.hour}`: 2-digit hour of the photo creation time
            - `{created.min}`: 2-digit minute of the photo creation time
            - `{created.sec}`: 2-digit second of the photo creation time
            - `{created.strftime}`: Apply strftime template to file creation date/time. Should be used in form
            `{created.strftime,TEMPLATE}` where TEMPLATE is a valid strftime template, e.g. 
            `{created.strftime,%Y-%U}` would result in year-week number of year: '2020-23'. 
            If used with no template will return null value. 
            See https://strftime.org/ for help on strftime templates.

            You may find the `--check-templates` option useful for testing templates. 
            When run with `--check-templates` osxphotos will not actually import anything 
            but will instead print out the rendered value for each `--title`, `--description`,
            `--keyword`, and `--album` option. It will also print out the values extracted by
            the `--exiftool` option.

            ## Parsing Dates/Times from File and Folder Names

            The `--parse-date` option allows you to parse dates/times from the filename of the
            file being imported.  This is useful if you have a large number of files with
            dates/times embedded in the filename but not in the metadata.

            Likewise, you can use `--parse-folder-date` to parse dates/times from the name of the
            folder containing the file being imported.
    
            The argument to `--parse-date` is a pattern string that is used to parse the date/time
            from the filename. The pattern string is a superset of the python `strftime/strptime`
            format with the following additions:

            - *: Match any number of characters
            - ^: Match the beginning of the string
            - $: Match the end of the string
            - {n}: Match exactly n characters
            - {n,}: Match at least n characters
            - {n,m}: Match at least n characters and at most m characters
            - In addition to `%%` for a literal `%`, the following format codes are supported: 
                `%^`, `%$`, `%*`, `%|`, `%{`, `%}` for `^`, `$`, `*`, `|`, `{`, `}` respectively
            - |: join multiple format codes; each code is tried in order until one matches
            - Unlike the standard library, the leading zero is not optional for 
                %d, %m, %H, %I, %M, %S, %j, %U, %W, and %V
            - For optional leading zero, use %-d, %-m, %-H, %-I, %-M, %-S, %-j, %-U, %-W, and %-V

            For more information on strptime format codes, see: 
            https://docs.python.org/3/library/datetime.html?highlight=strptime#strftime-and-strptime-format-codes

            **Note**: The time zone of the parsed date/time is assumed to be the local time zone.
            If the parse pattern includes a time zone, the photo's time will be converted from
            the specified time zone to the local time zone. osxphotos import does not
            currently support setting the time zone of imported photos.
            See also `osxphotos help timewarp` for more information on the timewarp
            command which can be used to change the time zone of photos after import.

            ### Examples

            If you have photos with embedded names in filenames like `IMG_1234_20200322_123456.jpg`
            and `12345678_20200322.jpg`, you can parse the dates with the following pattern:
            `--parse-date "IMG_*_%Y%m%d_%H%M%S|*_%Y%m%d.*"`. The first pattern matches the first format
            and the second pattern matches the second. The `|` character is used to separate the two
            patterns. The order is important as the first pattern will be tried first then the second
            and so on. If you have multiple formats in your filenames you will want to order the patterns
            from most specific to least specific to avoid false matches.

            If your photos are organized by date into folders in format `YYYY/MM/DD`, for example,
            `/Volumes/Photos/2020/03/22/IMG_1234.jpg`, you can parse the date from the folder name
            using `--parse-folder-date "%Y/%m/%d$"`. In this example, the pattern is anchored to the
            end of the string using `$` to avoid false matches if other parts of the path happen to match
            the pattern.

            ## Post Function

            You can run a custom python function after each photo is imported using `--post-function`.
            The format is `osxphotos import /file/to/import --post-function post_function.py::post_function`
            where `post_function.py` is the name of the python file containing the function and `post_function`
            is the name of the function. The function will be called with the following arguments:
            `post_function(photo: photoscript.Photo, filepath: pathlib.Path, verbose: t.Callable, **kwargs)`

            - photo: photoscript.Photo instance for the photo that's just been imported
            - filepath: pathlib.Path to the file that was imported (this is the path to the source file, not the path inside the Photos library)
            - verbose: A function to print verbose output if --verbose is set; if --verbose is not set, acts as a no-op (nothing gets printed)
            - **kwargs: reserved for future use; recommend you include **kwargs so your function still works if additional arguments are added in future versions

            The function will get called immediately after the photo has been imported into Photos
            and all metadata been set (e.g. --exiftool, --title, etc.)

            You may call more than one function by repeating the `--post-function` option.
        
            See https://rhettbull.github.io/PhotoScript/
            for documentation on photoscript and the Photo class that is passed to the function.

            ## Google Takeout

            If you have a Google Takeout archive of your Google Photos library, you can import
            it using the following steps:

            - Download the Google Takout archive from Google Photos
            - Unzip the archive
            - Run the following command to import the photos into Photos:

            `osxphotos import /path/to/Takeout --walk --album "{filepath.parent.name}" --sidecar  --verbose --report takeout_import.csv`
            
            If you have persons tagged in Google Photos you can add this option to create keywords
            for each person in the photo: `--keyword "{person}"`

            Google Takeout does not preserve the timezone of the photo. The metadata JSON sidecar
            produced by Google converts photo times to UTC. The import command will convert these
            to the correct time in the local timezone upon import. If your photos contain the correct
            date/time and timezone information in the metadata you can use the `--sidecar-ignore-date`
            option to ignore the date/time in the sidecar and use the date/time from the photo metadata.

        """
        )
        console = Console()
        with console.capture() as capture:
            console.print(Markdown(extra_help), width=min(HELP_WIDTH, console.width))
        formatter.write(capture.get())
        help_text += "\n\n" + formatter.getvalue()
        return help_text


@click.command(name="import", cls=ImportCommand)
@click.option(
    "--album",
    "-a",
    metavar="ALBUM_TEMPLATE",
    multiple=True,
    type=TemplateString(),
    help="Import photos into album ALBUM_TEMPLATE. "
    "ALBUM_TEMPLATE is an osxphotos template string. "
    "Photos may be imported into more than one album by repeating --album. "
    "See also --skip-dups, --dup-albums, --split-folder, --relative-to. "
    "See Template System in help for additional information.",
)
@click.option(
    "--title",
    "-t",
    metavar="TITLE_TEMPLATE",
    type=TemplateString(),
    help="Set title of imported photos to TITLE_TEMPLATE. "
    "TITLE_TEMPLATE is a an osxphotos template string. "
    "See Template System in help for additional information.",
)
@click.option(
    "--description",
    "-d",
    metavar="DESCRIPTION_TEMPLATE",
    type=TemplateString(),
    help="Set description of imported photos to DESCRIPTION_TEMPLATE. "
    "DESCRIPTION_TEMPLATE is a an osxphotos template string. "
    "See Template System in help for additional information.",
)
@click.option(
    "--keyword",
    "-k",
    metavar="KEYWORD_TEMPLATE",
    multiple=True,
    type=TemplateString(),
    help="Set keywords of imported photos to KEYWORD_TEMPLATE. "
    "KEYWORD_TEMPLATE is a an osxphotos template string. "
    "More than one keyword may be set by repeating --keyword. "
    "See Template System in help for additional information.",
)
@click.option(
    "--merge-keywords",
    "-m",
    is_flag=True,
    help="Merge keywords created by --exiftool, --sidecar, --sidecar-template, or --keyword "
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
    "--parse-date",
    "-P",
    metavar="DATE_PATTERN",
    type=StrpDateTimePattern(),
    help="Parse date from filename using DATE_PATTERN. "
    "If file does not match DATE_PATTERN, the date will be set by Photos using Photo's default behavior. "
    "DATE_PATTERN is a strptime-compatible pattern with extensions as pattern described below. "
    "If DATE_PATTERN matches time zone information, the time will be set to the local time in the timezone "
    "as the import command does not yet support setting time zone information. "
    "For example, if your photos are named 'IMG_1234_2022_11_23_12_34_56.jpg' where the date/time is "
    "'2022-11-23 12:34:56', you could use the pattern '%Y_%m_%d_%H_%M_%S' or "
    "'IMG_*_%Y_%m_%d_%H_%M_%S' to further narrow the pattern to only match files with 'IMG_xxxx_' in the name. "
    "If the pattern matches only date or only time, the missing information will be set to the "
    "default date/time used by Photos when importing the photo. This is either the EXIF date/time "
    "if it exists or the file modification date/time. "
    "For example, if photos are named 'IMG_1234_2022_11_23.jpg' where the date is '2022-11-23', "
    "you could use the pattern '%Y_%m_%d' to set the date but the time would be set from the EXIF "
    "or the file's modification time. "
    "See also --parse-folder-date, --check-templates.",
)
@click.option(
    "--parse-folder-date",
    "-F",
    metavar="DATE_PATTERN",
    type=StrpDateTimePattern(),
    help="Parse date from folder name using DATE_PATTERN. "
    "If folder does not match DATE_PATTERN, the date will be set by Photos using Photo's default behavior. "
    "DATE_PATTERN is a strptime-compatible pattern with extensions as pattern described below. "
    "If DATE_PATTERN matches time zone information, the time will be set to the local time in the timezone "
    "as the import command does not yet support setting time zone information. "
    "For example, if your photos are in folder '2023/12/17/IMG_1234.jpg` where the date is "
    "'2023-12-17', you could use the pattern '%Y/%m/%d$' as the DATE_PATTERN. "
    "If the pattern matches only date or only time, the missing information will be set to the "
    "default date/time used by Photos when importing the photo. This is either the EXIF date/time "
    "if it exists or the file modification date/time. "
    "See also --parse-folder-date, --check-templates.",
)
@click.option(
    "--clear-metadata",
    "-X",
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
    "the imported file's metadata. "
    "See also --sidecar, --sidecar-template. "
    "Note: importing keywords from video files is not currently supported.",
)
@click.option(
    "--exiftool-path",
    "-p",
    metavar="EXIFTOOL_PATH",
    type=click.Path(exists=True, dir_okay=False),
    help="Optionally specify path to exiftool; if not provided, will look for exiftool in $PATH.",
)
@click.option(
    "--sidecar",
    "-s",
    is_flag=True,
    help="Use sidecar files to import metadata (title, description, keywords, location). "
    "Sidecar files must be in the same directory as the imported file and have the same name. "
    "For example, if image is named img_1234.jpg, sidecar must be named one of: "
    "img_1234.xmp, img_1234.json, img_1234.jpg.xmp, img_1234.jpg.json. "
    "Supported sidecar formats are XMP and JSON (as generated by exiftool). "
    "If both JSON and XMP sidecars are found, the JSON sidecar will be used. "
    "If sidecar format is XMP, exiftool must be installed as it is used to read the XMP files. "
    "See also --sidecar-template if you need control over the sidecar name. "
    "See also --sidecar-ignore-date. "
    "Note: --sidecar and --sidecar-template are mutually exclusive.",
)
@click.option(
    "--sidecar-template",
    "-T",
    metavar="TEMPLATE",
    type=TemplateString(),
    help="Use sidecar files to import metadata (title, description, keywords, location). "
    "The TEMPLATE is an osxphotos template string that is rendered to produce the sidecar filename. "
    "The path to the current file is available as {filepath}. "
    "Thus if file is named 'IMG_1234.jpg' and sidecar is named 'IMG_1234.xmp', "
    "you would use the template '{filepath.parent}/{filepath.stem}.xmp'. "
    "If the sidecar name was 'IMG_1234.jpg.xmp', you would use the template "
    "'{filepath}.xmp'. "
    "If the sidecar format is XMP, exiftool must be installed as it is used to read the XMP files. "
    "See Template System in help for additional information. "
    "See also --sidecar-ignore-date. "
    "Note: --sidecar and --sidecar-template are mutually exclusive.",
)
@click.option(
    "--sidecar-ignore-date",
    "-i",
    is_flag=True,
    help="Do not use date in sidecar to set photo date/time. "
    "Setting the timezone from sidecar files is not currently supported so when using --sidecar "
    "or --sidecar-template, the date/time found in the sidecar will be converted to the local timezone "
    "and that value will be used to set the photo date/time. "
    "If your photos have correct timezone information in the embedded metadata you can use "
    "--sidecar-ignore-date to ignore the date/time in the sidecar and use the date/time from the "
    "file (which will be read by Photos on import).",
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
@click.option(
    "--dup-check",
    "-D",
    is_flag=True,
    help="Use Photos' built-in duplicate checkign to check for duplicates on import. "
    "Using --dup-check will cause Photos to display a dialog box for each duplicate photo found, "
    "requesting confirmation to import the duplicate. See also --skip-dups.",
)
@click.option(
    "--skip-dups",
    "-S",
    is_flag=True,
    help="Skip duplicate photos on import; osxphotos will not import any photos that appear to be duplicates. "
    "Unlike --dup-check, this does not use Photos' built in duplicate checking feature and "
    "does not display a dialog box for each duplicate found. See also --dup-check and --dup-albums.",
)
@click.option(
    "--dup-albums",
    "-A",
    is_flag=True,
    help="If used with --skip-dups, the matching duplicate already in the Photos library "
    "will be added to any albums the current file would have been added to had it not been skipped. "
    "This is useful if you have duplicate photos in separate folders and want to avoid duplicates "
    "in Photos but keep the photos organized in albums that match the folder structure. "
    "Must be used with --skip-dups and --album. See also --skip-dups.",
)
@click.option(
    "--split-folder",
    "-f",
    help="Automatically create hierarchal folders for albums as needed by splitting album name "
    "into folders and album. You must specify the character used to split folders and "
    "albums. For example, '--split-folder \"/\"' will split the album name 'Folder/Album' "
    "into folder 'Folder' and album 'Album'. ",
)
@click.option(
    "--walk", "-w", is_flag=True, help="Recursively walk through directories."
)
@click.option(
    "--glob",
    "-g",
    metavar="GLOB",
    multiple=True,
    help="Only import files matching GLOB. "
    "GLOB is a Unix shell-style glob pattern, for example: '--glob \"*.jpg\"'. "
    "GLOB may be repeated to import multiple patterns.",
)
@click.option(
    "--check",
    "-c",
    is_flag=True,
    help="Check which FILES have been previously imported but do not actually import anything. "
    "Prints a report showing which files have been imported (and when they were added) "
    "and which files have not been imported. "
    "See also, --check-not.",
)
@click.option(
    "--check-not",
    "-C",
    is_flag=True,
    help="Check which FILES have not been previously imported but do not actually import anything. "
    "Prints the path to each file that has not been previously imported. "
    "See also, --check.",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Dry run; do not actually import. Useful with --verbose to see what would be imported.",
)
@click.option(
    "--report",
    "-o",
    metavar="REPORT_FILE",
    help="Write a report of all files that were imported. "
    "The extension of the report filename will be used to determine the format. "
    "Valid extensions are: "
    ".csv (CSV file), .json (JSON), .db and .sqlite (SQLite database). "
    "REPORT_FILE may be a template string (see Template System), for example, "
    "--report 'export_{today.date}.csv' will write a CSV report file named with today's date. "
    "See also --append.",
    type=TemplateString(),
)
@click.option(
    "--resume",
    "-R",
    is_flag=True,
    help="Resume previous import. "
    f"Note: data on each imported file is kept in a database in '{get_data_dir() / IMPORT_DB}'. "
    "This data can be used to resume a previous import if there was an error or the import was cancelled.",
)
@click.option(
    "--append",
    "-O",
    is_flag=True,
    help="If used with --report, add data to existing report file instead of overwriting it. "
    "See also --report.",
)
@VERBOSE_OPTION
@TIMESTAMP_OPTION
@click.option(
    "--no-progress",
    "-N",
    is_flag=True,
    help="Do not display progress bar during import.",
)
@click.option(
    "--check-templates",
    is_flag=True,
    help="Don't actually import anything; "
    "renders template strings and date patterns so you can verify they are correct.",
)
@click.option(
    "--post-function",
    metavar="filename.py::function",
    nargs=1,
    type=FunctionCall(),
    multiple=True,
    help="Run python function after importing file."
    "Use this in format: --post-function filename.py::function where filename.py is a python "
    "file you've created and function is the name of the function in the python file you want to call. "
    "The function will be passed a reference to the photo object and the path to the file that was imported. "
    "You can run more than one function by repeating the '--post-function' option with different arguments. "
    "You may also specify a post function using a URL in format --post-function 'https://path/to/module.py::function' "
    "See Post Function below.",
)
@click.option(
    "--library",
    metavar="LIBRARY_PATH",
    type=click.Path(exists=True),
    help="Path to the Photos library you are importing into. This is not usually needed. "
    "You will only need to specify this if osxphotos cannot determine the path to the library "
    "in which case osxphotos will tell you to use the --library option when you run the import command.",
)
@THEME_OPTION
@click.argument("files", nargs=-1)
@click.pass_obj
@click.pass_context
def import_main(
    ctx: click.Context,
    cli_obj: CLI_Obj,
    album: tuple[str, ...],
    append: bool,
    check: bool,
    check_not: bool,
    check_templates: bool,
    clear_location: bool,
    clear_metadata: bool,
    description: str | None,
    dry_run: bool,
    dup_albums: bool,
    dup_check: bool,
    exiftool: bool,
    exiftool_path: str | None,
    files: tuple[str, ...],
    glob: tuple[str, ...],
    keyword: tuple[str, ...],
    library: str | None,
    location: tuple[float, float],
    merge_keywords: bool,
    no_progress: bool,
    parse_date: str | None,
    parse_folder_date: str | None,
    post_function: tuple[Callable[..., None]],
    relative_to: str | None,
    report: str | None,
    resume: bool,
    sidecar: bool,
    sidecar_ignore_date: bool,
    sidecar_template: str | None,
    skip_dups: bool,
    split_folder: str | None,
    theme: str | None,
    timestamp: bool,
    title: str | None,
    verbose_flag: bool,
    walk: bool,
):
    """Import photos and videos into Photos. Photos will be imported into the
    most recently opened Photos library.

    Limitations:

    - Photos are imported one at a time thus the "Imports" album in Photos will show
    a new import group for each photo imported.

    - Live photos and RAW+JPEG pairs are imported as separate files, not as a single asset.

    - If there's an edited version of a photo along with the original, they will be imported as separate files, not as a single asset.
    """

    kwargs = locals()
    kwargs.pop("ctx")
    kwargs.pop("cli_obj")
    import_cli(**kwargs)


def import_cli(
    album: tuple[str, ...] = (),
    append: bool = False,
    check: bool = False,
    check_not: bool = False,
    check_templates: bool = False,
    clear_location: bool = False,
    clear_metadata: bool = False,
    description: str | None = None,
    dry_run: bool = False,
    dup_albums: bool = False,
    dup_check: bool = False,
    exiftool: bool = False,
    exiftool_path: str | None = None,
    files: tuple[str, ...] = (),
    glob: tuple[str, ...] = (),
    keyword: tuple[str, ...] = (),
    library: str | None = None,
    location: tuple[float, float] = (),
    merge_keywords: bool = False,
    no_progress: bool = False,
    parse_date: str | None = None,
    parse_folder_date: str | None = None,
    post_function: tuple[Callable[..., None]] = (),
    relative_to: str | None = None,
    report: str | None = None,
    resume: bool = False,
    sidecar: bool = False,
    sidecar_ignore_date: bool = False,
    sidecar_template: str | None = None,
    skip_dups: bool = False,
    split_folder: str | None = None,
    theme: str | None = None,
    timestamp: bool = False,
    title: str | None = None,
    verbose_flag: bool = False,
    walk: bool = False,
):
    """Import photos and videos into Photos. Photos will be imported into the
    most recently opened Photos library.

    Photos are imported one at a time thus the "Imports" album in Photos will show
    a new import group for each photo imported.

    This function is called by import_main() and is pulled out as a separate function
    so it could be called directly in your own code without the Click instrumentation.
    """
    verbose = verbose_print(verbose=verbose_flag, timestamp=timestamp, theme=theme)

    if not files:
        echo("Nothing to import", err=True)
        return

    report_file = render_and_validate_report(report) if report else None
    relative_to = pathlib.Path(relative_to) if relative_to else None

    files = collect_files_to_import(files, walk, glob)
    if check_templates:
        check_templates_and_exit(
            files=files,
            relative_to=relative_to,
            title=title,
            description=description,
            keyword=keyword,
            album=album,
            exiftool_path=exiftool_path,
            exiftool=exiftool,
            parse_date=parse_date,
            parse_folder_date=parse_folder_date,
            sidecar=sidecar,
            sidecar_template=sidecar_template,
        )

    # need to get the library path to initialize FingerprintQuery
    last_library = library or get_last_library_path()
    if not last_library:
        rich_echo_error(
            "[error]Could not determine path to Photos library. "
            "Please specify path to library with --library option."
        )

    if check:
        check_imported_files(files, last_library, verbose)
        sys.exit(0)

    if check_not:
        check_not_imported_files(files, last_library, verbose)
        sys.exit(0)

    if exiftool and not exiftool_path:
        # ensure exiftool is installed in path
        try:
            get_exiftool_path()
        except FileNotFoundError as e:
            rich_echo_error(f"[error] {e}")
            raise click.Abort()

    if sidecar and sidecar_template:
        rich_echo_error(
            "[error] Only one of --sidecar or --sidecar-template may be used"
        )
        raise click.Abort()

    if sidecar_ignore_date and not (sidecar or sidecar_template):
        rich_echo_error(
            "[error] --sidecar-ignore-date must be used with --sidecar or --sidecar-template"
        )
        raise click.Abort()

    if dup_albums and not (skip_dups and album):
        rich_echo_error(
            "[error] --dup-albums must be used with --skip-dups and --album"
        )
        raise click.Abort()

    # initialize report data
    # report data is set even if no report is generated
    report_data: dict[pathlib.Path, ReportRecord] = {}

    import_db = SQLiteKVStore(
        get_data_dir() / IMPORT_DB,
        wal=True,
        serialize=ReportRecord.serialize,
        deserialize=ReportRecord.deserialize,
    )
    import_db.about = f"osxphotos import database\n{OSXPHOTOS_ABOUT_STRING}"

    imported_count, skipped_count, error_count = import_files(
        last_library=last_library,
        files=files,
        no_progress=no_progress,
        resume=resume,
        clear_metadata=clear_metadata,
        clear_location=clear_location,
        exiftool=exiftool,
        exiftool_path=exiftool_path,
        sidecar=sidecar,
        sidecar_ignore_date=sidecar_ignore_date,
        sidecar_template=sidecar_template,
        merge_keywords=merge_keywords,
        title=title,
        description=description,
        keyword=keyword,
        location=location,
        parse_date=parse_date,
        parse_folder_date=parse_folder_date,
        album=album,
        dup_albums=dup_albums,
        split_folder=split_folder,
        post_function=post_function,
        skip_dups=skip_dups,
        dup_check=dup_check,
        dry_run=dry_run,
        report_data=report_data,
        relative_to=relative_to,
        import_db=import_db,
        verbose=verbose,
    )

    import_db.close()

    if report and not dry_run:
        write_report(report_file, report_data, append)
        verbose(f"Wrote import report to [filepath]{report_file}[/]")

    skipped_str = f", [num]{skipped_count}[/] skipped" if resume or skip_dups else ""
    echo(
        f"Done: imported [num]{imported_count}[/] {pluralize(imported_count, 'file', 'files')}, "
        f"[num]{error_count}[/] {pluralize(error_count, 'error', 'errors')}"
        f"{skipped_str}",
        emoji=False,
    )


def check_imported_files(files: list[str], library: str, verbose: Callable[..., None]):
    """Check if files have been previously imported and print results"""

    if not files:
        rich_echo_error("No files to check")
        return

    file_word = pluralize(len(files), "file", "files")
    verbose(f"Checking {len(files)} {file_word} to see if previously imported")
    fq = FingerprintQuery(library)
    for filepath in files:
        if duplicates := fq.possible_duplicates(filepath):
            echo(
                f"[filepath]:white_check_mark-emoji: {filepath}[/], imported, "
                + f"{', '.join([f'[filename]{f}[/] ([uuid]{u}[/]) added [datetime]{d}[/] ' for u, d, f in duplicates])}"
            )
        else:
            echo(f"[error]{filepath}[/], not imported")


def check_not_imported_files(
    files: list[str], library: str, verbose: Callable[..., None]
):
    """Check if files have not been previously imported and print results"""

    if not files:
        rich_echo_error("No files to check")
        return

    file_word = pluralize(len(files), "file", "files")
    verbose(f"Checking {len(files)} {file_word} to see if not previously imported")
    fq = FingerprintQuery(library)
    for filepath in files:
        if fq.possible_duplicates(filepath):
            continue
        echo(f"{filepath}")
