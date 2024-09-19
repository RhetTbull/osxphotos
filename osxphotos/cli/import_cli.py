"""import command for osxphotos CLI to import photos into Photos"""

from __future__ import annotations

import csv
import dataclasses
import datetime
import fnmatch
import itertools
import json
import logging
import os
import os.path
import pathlib
import re
import sqlite3
import sys
import tempfile
from collections.abc import Iterable
from contextlib import suppress
from textwrap import dedent
from typing import TYPE_CHECKING, Callable, Tuple

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn
from strpdatetime import strpdatetime

from osxphotos.fileutil import FileUtilMacOS
from osxphotos.photoinfo_protocol import PhotoInfoProtocol
from osxphotos.platform import assert_macos

assert_macos()

try:
    # makelive does not work on macOS <= 10.15.x
    import makelive
except ImportError:
    makelive = None

from photoscript import Photo, PhotosLibrary

import osxphotos.sqlite3_datetime as sqlite3_datetime
from osxphotos._constants import (
    DEFAULT_EDITED_SUFFIX,
    OSXPHOTOS_EXPORT_DB,
    SQLITE_CHECK_SAME_THREAD,
)
from osxphotos._version import __version__
from osxphotos.cli.cli_params import TIMESTAMP_OPTION, VERBOSE_OPTION
from osxphotos.cli.common import get_data_dir
from osxphotos.cli.help import HELP_WIDTH
from osxphotos.cli.param_types import FunctionCall, StrpDateTimePattern, TemplateString
from osxphotos.cli.sidecar import get_sidecar_file_with_template
from osxphotos.cli.signaturequery import SignatureQuery
from osxphotos.datetime_utils import (
    datetime_has_tz,
    datetime_remove_tz,
    datetime_tz_to_utc,
    datetime_utc_to_local,
)
from osxphotos.exiftool import get_exiftool_path
from osxphotos.export_db_utils import (
    export_db_get_photoinfo_for_filepath,
    export_db_migrate_photos_library,
)
from osxphotos.fingerprintquery import FingerprintQuery
from osxphotos.image_file_utils import (
    EDITED_RE,
    ORIGINAL_RE,
    burst_uuid_from_path,
    is_apple_photos_aae_file,
    is_edited_version_of_file,
    is_image_file,
    is_live_pair,
    is_possible_live_pair,
    is_raw_image,
    is_raw_pair,
    is_video_file,
)
from osxphotos.metadata_reader import (
    MetaData,
    metadata_from_exiftool,
    metadata_from_photoinfo,
    metadata_from_sidecar,
)
from osxphotos.photoinfo import PhotoInfoNone
from osxphotos.photoinfo_file import (
    PhotoInfoFromFile,
    render_photo_template_from_filepath,
)
from osxphotos.photosalbum import PhotosAlbumPhotoScript, PhotosAlbumPhotoScriptByPath
from osxphotos.phototemplate import PhotoTemplate, RenderOptions
from osxphotos.sqlite_utils import sqlite_columns
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

logger = logging.getLogger("osxphotos")

OSXPHOTOS_ABOUT_STRING = f"Created by osxphotos version {__version__} (https://github.com/RhetTbull/osxphotos) on {datetime.datetime.now()}"

# stores import status so imports can be resumed
IMPORT_DB = "osxphotos_import.db"

try:
    EXIFTOOL_PATH = get_exiftool_path()
except FileNotFoundError:
    EXIFTOOL_PATH = None

# bit mask for import groups, live, raw+jpeg, burst, and aae
FILE_TYPE_IS_IMPORT_GROUP = 1
FILE_TYPE_IS_LIVE_PAIR = 2
FILE_TYPE_IS_RAW_JPEG_PAIR = 4
FILE_TYPE_IS_BURST_GROUP = 8
FILE_TYPE_HAS_AAE_FILE = 16
FILE_TYPE_HAS_NON_APPLE_AAE = 32
FILE_TYPE_AUTO_LIVE_PAIR = 64
FILE_TYPE_SHOULD_STAGE_FILES = 128
FILE_TYPE_HAS_EDITED_FILE = 256
FILE_TYPE_SHOULD_RENAME_EDITED = 512


_global_image_counter = 1


def _increment_image_counter() -> str:
    global _global_image_counter
    counter_str = f"{_global_image_counter:04d}"
    _global_image_counter += 1
    if _global_image_counter > 9999:
        _global_image_counter = 1
    return counter_str


def echo(message, emoji=True, **kwargs):
    """Echo text with rich"""
    if emoji:
        if "[error]" in message:
            message = f":cross_mark-emoji:  {message}"
        elif "[warning]" in message:
            message = f":warning-emoji:  {message}"
    rich_click_echo(message, **kwargs)


# a decorator that when applied to a function, prints the name of the function and the name and type of each argument
def watch(func):
    """Print name of function, name type of each argument"""
    # this is to help figure out type hint issues

    def wrapper(*args, **kwargs):
        print(f"Running {func.__name__}")
        for arg in itertools.chain(args, kwargs.values()):
            print(f"{arg=}, {type(arg)=}")
            if arg and isinstance(arg, (list, tuple)):
                print(f"{arg[0]=} {type(arg[0])=}")
                if arg[0] and isinstance(arg[0], (list, tuple)):
                    print(f"{arg[0][0]=} {type(arg[0][0])=}")
        results = func(*args, **kwargs)
        print(f"returned: {results=} {type(results)=}")
        return results

    return wrapper


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

            `osxphotos import /Volumes/photos/*.jpg --album "{created.year}"`

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
    help="Merge keywords created by --exiftool, --sidecar, --sidecar-filename, or --keyword "
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
    "--favorite-rating",
    "-G",
    metavar="RATING",
    type=click.IntRange(1, 5),
    help="If XMP:Rating is set to RATING or higher, mark imported photo as a favorite. "
    "RATING must be in range 1 to 5. "
    "XMP:Rating will be read from asset's metadata or from sidecar if --sidecar, --sidecare-filename is used. "
    "Requires that exiftool be installed to read the rating from the asset's XMP data.",
)
@click.option(
    "--auto-live",
    "-E",
    is_flag=True,
    help="Automatically convert photo+video pairs into live images. "
    "Live Photos (photo+video pair) exported from Photos contain a metadata content identifier that Photos "
    "uses to associate the pair as a single Live Photo asset when re-imported. "
    "Photo+video pairs taken on non-Apple devices will lack the content identifier and "
    "thus will be imported as separate assets. "
    "Use --auto-live to automatically convert these pairs to Live Photos upon import. "
    "When --auto-live is used, a photo and a video with same base name, "
    "for example 'IMG_1234.JPG' and 'IMG_1234.mov', in the same directory will be converted to Live Photos. "
    "*NOTE*: Using this feature will modify the metadata in the files prior to import. "
    "Ensure you have a backup of the original files if you want to preserve unmodified versions. "
    "*NOTE*: this option does not work on macOS < 11.0.",
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
    "See also --sidecar, --sidecar-filename, --exportdb. "
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
    "See also --sidecar-filename if you need control over the sidecar name. "
    "See also --sidecar-ignore-date, --exiftool, --exportdb. "
    "Note: --sidecar and --sidecar-filename are mutually exclusive.",
)
@click.option(
    "--sidecar-filename",
    "-T",
    "sidecar_filename_template",
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
    "See also --sidecar-ignore-date, --exiftool, --exportdb. "
    "Note: --sidecar and --sidecar-filename are mutually exclusive.",
)
@click.option(
    "--edited-suffix",
    metavar="TEMPLATE",
    help="Optional suffix template used for naming edited photos. "
    "This is used to associate sidecars to the edited version of a file when --sidecar or --sidecar-filename is used "
    "and also to associate edited images to the original when importing adjustments exported with 'osxphotos export --export-aae'. "
    f"By default, osxphotos will look for edited photos using default 'osxphotos export' suffix of '{DEFAULT_EDITED_SUFFIX}' "
    "If your edited photos have a different suffix you can use '--edited-suffix' to specify the suffix. "
    "For example, with '--edited-suffix _bearbeiten', the import command will look for a file named 'photoname_bearbeiten.ext' "
    "and associated that with a sidecar named 'photoname.xmp', etc. "
    "Multi-value templates (see Templating System in the OSXPhotos docs) are not permitted with --edited-suffix.",
    type=TemplateString(),
)
@click.option(
    "--sidecar-ignore-date",
    "-i",
    is_flag=True,
    help="Do not use date in sidecar to set photo date/time. "
    "Setting the timezone from sidecar files is not currently supported so when using --sidecar "
    "or --sidecar-filename, the date/time found in the sidecar will be converted to the local timezone "
    "and that value will be used to set the photo date/time. "
    "If your photos have correct timezone information in the embedded metadata you can use "
    "--sidecar-ignore-date to ignore the date/time in the sidecar and use the date/time from the "
    "file (which will be read by Photos on import).",
)
@click.option(
    "--exportdb",
    "-B",
    metavar="EXPORTDB_PATH",
    type=click.Path(exists=True),
    help="Use an osxphotos export database (created by 'osxphotos export') "
    "to set metadata (title, description, keywords, location, album). "
    "See also --exportdir, --sidecar, --sidecar-filename, --exiftool.",
)
@click.option(
    "--exportdir",
    "-I",
    metavar="EXPORT_DIR_PATH",
    type=click.Path(exists=True),
    help="Specify the path to the export directory when using --exportdb "
    "to import metadata from an osxphotos export database created by 'osxphotos export'. "
    "This is only needed if you have moved the exported files to a new location since the export. "
    "If you have moved the exported files, osxphotos will need to know the path to the top-level of "
    "the export directory in order to use --exportdb to read the metadata for the files. "
    "For example, if you used 'osxphotos export' to export photos to '/Volumes/Exported' "
    "but you subsequently moved the files to '/Volumes/PhotosBackup' you would use: "
    "'--exportdb /Volumes/PhotosBackup --exportdir /Volumes/PhotosBackup' to import the metadata "
    "from the export database. This is needed because osxphotos needs to know both the path to the "
    "export database and the root folder of the exported files in order to match the files to the "
    "correct entry in the export database and the database may be in a different location than the "
    "exported files. "
    "See also --exportdb.",
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
    "does not display a dialog box for each duplicate found. See also --dup-check, --dup-albums, and --resume.",
)
@click.option(
    "--signature",
    "-U",
    type=TemplateString(),
    help="Custom template for signature when using --skip-dups, --dup-check, and --dup-albums. "
    "The signature is used to match photos in the library to those being imported. "
    "If you do not use --signature, the fingerprint will be used for photos "
    "and lowercase filename + size will be used for videos "
    "(a fingerprint is not always stored for videos in the Photos library). "
    "*Note*: When using --signature, the Photos library will be scanned before import "
    "which may take some time. If there are duplicates files in the list of files to be imported, "
    "these will not be detected as each imported file will only be compared to the state of the Photos "
    "library at the start of the import.",
)
@click.option(
    "--dup-albums",
    "-A",
    is_flag=True,
    help="If used with --skip-dups, the matching duplicate already in the Photos library "
    "will be added to any albums the current file would have been added to had it not been skipped. "
    "This is useful if you have duplicate photos in separate folders and want to avoid duplicates "
    "in Photos but keep the photos organized in albums that match the folder structure. "
    "Must be used with --skip-dups and --album or --exportdb. See also --skip-dups.",
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
    help="Resume previous import, skipping any files which have already been imported. "
    f"Note: data on each imported file is kept in a database in '{get_data_dir() / IMPORT_DB}'. "
    "This data can be used to resume a previous import if there was an error or the import was cancelled. "
    "Any files which were already imported will be skipped. See also --skip-dups.",
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
    "--stop-on-error",
    metavar="COUNT",
    help="Stops importing after COUNT errors. "
    "Useful if you experience a large number of errors during import.",
    type=click.IntRange(min=0),
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
@click.argument("FILES_OR_DIRS", nargs=-1)
@click.pass_obj
@click.pass_context
def import_main(
    ctx: click.Context,
    cli_obj: CLI_Obj,
    album: tuple[str, ...],
    append: bool,
    auto_live: bool,
    check: bool,
    check_not: bool,
    check_templates: bool,
    clear_location: bool,
    clear_metadata: bool,
    description: str | None,
    dry_run: bool,
    dup_albums: bool,
    dup_check: bool,
    edited_suffix: str | None,
    exiftool: bool,
    exiftool_path: str | None,
    exportdb: str | None,
    exportdir: str | None,
    favorite_rating: int | None,
    files_or_dirs: tuple[str, ...],
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
    sidecar_filename_template: str | None,
    signature: str | None,
    skip_dups: bool,
    split_folder: str | None,
    stop_on_error: int | None,
    theme: str | None,
    timestamp: bool,
    title: str | None,
    verbose_flag: bool,
    walk: bool,
):
    """Import photos and videos into Photos. Photos will be imported into the
    most recently opened Photos library.

    Limitations:

    - Photos are imported one at a time

    Thus the "Imports" album in Photos will show a new import group for each photo imported.

    Exception: On macOS >= 11.0, Live photos (photo+video pair), burst photos, edited photos,
    and RAW+JPEG pairs will be imported together so that Photos processes them correctly.
    Automatic grouping of live photos and burst photos is not supported on macOS <= 10.15.

    Edited Photos:

    The import command will attempt to preserve adjustments to photos so that the imported asset
    preserves the non-destructive edits. For this to work, there must be an associated .AAE file
    for the photo. The .AAE file stores non-destructive edits to the photo and can be exported with
    'osxphotos export ... --export-aae'. If the original file is named IMG_1234.jpg, the .AAE file
    should be named IMG_1234.aae or IMG_1234.AAE.

    The edited version of the file must also be named following one of these two conventions:

        \b
        Original: IMG_1234.jpg, edited: IMG_E1234.jpg

        Original: IMG_1234.jpg, original: IMG_1234_edited.jpg

    In the first form, the original is named with 3 letters, followed by underscore, followed by
    4 digits and the edited has the same name with "E" in front of the 4 digits.

    In the second form, a suffix is appended to the original name, in this example, "_edited", which
    is the default suffix used by 'osxphotos export'. If you have used a different suffix, you can specify
    it using '--edited-suffix SUFFIX'.

    If edited files do not contain an associated .AAE or if they do not match one of these two conventions,
    they will be imported as separate assets.
    """
    kwargs = locals()
    kwargs.pop("ctx")
    kwargs.pop("cli_obj")
    import_cli(**kwargs)


def import_cli(
    album: tuple[str, ...] = (),
    append: bool = False,
    auto_live: bool = False,
    check: bool = False,
    check_not: bool = False,
    check_templates: bool = False,
    clear_location: bool = False,
    clear_metadata: bool = False,
    description: str | None = None,
    dry_run: bool = False,
    dup_albums: bool = False,
    dup_check: bool = False,
    edited_suffix: str | None = None,
    exiftool: bool = False,
    exiftool_path: str | None = None,
    exportdb: str | None = None,
    exportdir: str | None = None,
    favorite_rating: int | None = None,
    files_or_dirs: tuple[str, ...] = (),
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
    sidecar_filename_template: str | None = None,
    signature: str | None = None,
    skip_dups: bool = False,
    split_folder: str | None = None,
    stop_on_error: int | None = None,
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

    if not files_or_dirs:
        echo("Nothing to import", err=True)
        return

    report_file = render_and_validate_report(report) if report else None
    relative_to = pathlib.Path(relative_to) if relative_to else None

    files_or_dirs = collect_files_to_import(
        files_or_dirs, walk, glob, verbose, no_progress
    )
    if check_templates:
        check_templates_and_exit(
            files=files_or_dirs,
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
            sidecar_filename_template=sidecar_filename_template,
            edited_suffix=edited_suffix,
            signature=signature,
        )

    files_to_import = group_files_to_import(
        files_or_dirs,
        auto_live,
        edited_suffix,
        relative_to,
        exiftool_path,
        sidecar,
        sidecar_filename_template,
        verbose,
        no_progress,
    )

    # need to get the library path to initialize FingerprintQuery
    last_library = library or get_last_library_path()
    if not last_library:
        rich_echo_error(
            "[error]Could not determine path to Photos library. "
            "Please specify path to library with --library option."
        )
        raise click.Abort()

    if check:
        check_imported_files(
            files_to_import,
            relative_to,
            last_library,
            signature,
            sidecar,
            sidecar_filename_template,
            edited_suffix,
            exiftool_path,
            verbose,
        )
        sys.exit(0)

    if check_not:
        check_not_imported_files(
            files_to_import,
            relative_to,
            last_library,
            signature,
            sidecar,
            sidecar_filename_template,
            edited_suffix,
            exiftool_path,
            verbose,
        )
        sys.exit(0)

    if exiftool and not exiftool_path:
        # ensure exiftool is installed in path
        try:
            get_exiftool_path()
        except FileNotFoundError as e:
            rich_echo_error(f"[error] {e}")
            raise click.Abort()

    if sidecar and sidecar_filename_template:
        rich_echo_error(
            "[error] Only one of --sidecar or --sidecar-filename may be used"
        )
        raise click.Abort()

    if sidecar_ignore_date and not (sidecar or sidecar_filename_template):
        rich_echo_error(
            "[error] --sidecar-ignore-date must be used with --sidecar or --sidecar-filename"
        )
        raise click.Abort()

    if dup_albums and not (skip_dups and (album or exportdb)):
        rich_echo_error(
            "[error] --dup-albums must be used with --skip-dups and --album"
        )
        raise click.Abort()

    # initialize report data
    # report data is set even if no report is generated
    report_data: dict[pathlib.Path, ReportRecord] = {}

    import_db = SQLiteKVStore(
        str(get_data_dir() / IMPORT_DB),
        wal=True,
        serialize=ReportRecord.serialize,
        deserialize=ReportRecord.deserialize,
    )
    import_db.about = f"osxphotos import database\n{OSXPHOTOS_ABOUT_STRING}"

    imported_count, skipped_count, error_count = import_files(
        last_library=last_library,
        files=files_to_import,
        no_progress=no_progress,
        resume=resume,
        clear_metadata=clear_metadata,
        clear_location=clear_location,
        edited_suffix=edited_suffix,
        exiftool=exiftool,
        exiftool_path=exiftool_path,
        exportdb=exportdb,
        exportdir=exportdir,
        favorite_rating=favorite_rating,
        sidecar=sidecar,
        sidecar_ignore_date=sidecar_ignore_date,
        sidecar_filename_template=sidecar_filename_template,
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
        auto_live=auto_live,
        signature=signature,
        stop_on_error=stop_on_error,
        verbose=verbose,
    )

    import_db.close()

    if report and not dry_run:
        write_report(report_file, report_data, append)
        verbose(f"Wrote import report to [filepath]{report_file}[/]")

    skipped_str = f", [num]{skipped_count}[/] skipped" if resume or skip_dups else ""
    echo(
        f"Done: imported [num]{imported_count}[/] {pluralize(imported_count, 'file group', 'file groups')}, "
        f"[num]{error_count}[/] {pluralize(error_count, 'error', 'errors')}"
        f"{skipped_str}",
        emoji=False,
    )


def collect_filepaths_for_import_check(
    filegroup: Iterable[pathlib.Path],
    edited_suffix: str,
    relative_filepath: pathlib.Path | None,
    exiftool_path: str | None,
    sidecar: bool,
    sidecar_filename_template: str | None,
) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    """Collect filepaths for import check"""
    filepaths = []
    # exclude .AAE files
    file_type = file_type_for_import_group(
        tuple(filegroup),
        False,
        edited_suffix,
        relative_filepath,
        exiftool_path,
        sidecar,
        sidecar_filename_template,
    )
    filegroup = [f for f in filegroup if not f.name.lower().endswith(".aae")]
    if len(filegroup) == 1:
        filepaths.append(filegroup[0])
    elif file_type & FILE_TYPE_IS_BURST_GROUP:
        # include all burst images
        filepaths.extend(filegroup)
    elif file_type & FILE_TYPE_IS_LIVE_PAIR:
        # include only the image
        filepaths.append(filegroup[0])
    elif file_type & FILE_TYPE_IS_RAW_JPEG_PAIR:
        # Photos always makes the non-RAW image the original upon import
        # only include the non-RAW image
        filepaths.append(non_raw_file(filegroup))
    elif file_type & FILE_TYPE_HAS_EDITED_FILE and file_type & FILE_TYPE_HAS_AAE_FILE:
        # exclude the edited version
        filepaths.extend(
            non_edited_files(
                filegroup, edited_suffix, relative_filepath, exiftool_path, sidecar
            )
        )
    else:
        # include everything else
        filepaths.extend(filegroup)
    return filepaths, [f for f in filegroup if f not in filepaths]


def import_photo_group(
    filepaths: tuple[pathlib.Path, ...], dup_check: bool, verbose: Callable[..., None]
) -> tuple[Photo | None, str | None]:
    """Import a photo and return Photo object and error string if any

    Args:
        filepath: path to the file to import
        dup_check: enable or disable Photo's duplicate check on import
        verbose: Callable

    Returns:
        tuple of Photo object and error string if any
    """
    if imported := PhotosLibrary().import_photos(
        filepaths, skip_duplicate_check=not dup_check
    ):
        verbose(
            f"Imported [filename]{filepaths[0].name}[/] with UUID [uuid]{imported[0].uuid}[/]"
        )
        # this assumes the only groups being imported are live, raw+jpeg, bursts
        # if modified to import arbitrary groups, will need to be updated
        # to match the associated UUID and image file
        if len(imported) > 1:
            logger.warning(f"Warning: imported {len(imported)} images, expected 1")
        photo = imported[0]
        return photo, None
    else:
        error_str = f"[error]Error importing file [filepath]{filepaths[0].name}[/][/]"
        echo(error_str, err=True)
        return None, error_str


def add_photo_to_albums(
    photo: Photo | None,
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path,
    album: tuple[str, ...],
    split_folder: str | None,
    exiftool_path: str | None,
    sidecar: pathlib.Path | None,
    verbose: Callable[..., None],
    dry_run: bool,
) -> list[str]:
    """Add photo to one or more albums"""
    albums = []
    for a in album:
        album_names = render_photo_template_from_filepath(
            filepath, relative_filepath, a, exiftool_path, sidecar
        )
        albums.extend(normalize_unicode(aa) for aa in album_names)
    verbose(
        f"Adding photo [filename]{filepath.name}[/filename] to {len(albums)} {pluralize(len(albums), 'album', 'albums')}"
    )

    # add photo to albums
    for a in albums:
        verbose(f"Adding photo [filename]{filepath.name}[/] to album [filepath]{a}[/]")
        if photo and not dry_run:
            photos_album = PhotosAlbumPhotoScript(
                a, verbose=verbose, split_folder=split_folder, rich=True
            )
            photos_album.add(photo)
    return albums


def add_photo_to_photoinfo_albums(
    photo: Photo | None,
    photoinfo: PhotoInfoProtocol,
    filepath: pathlib.Path,
    verbose: Callable[..., None],
    dry_run: bool,
) -> list[str]:
    """Add photo to one or more albums"""
    if not photoinfo.album_info:
        return []

    verbose(
        f"Adding photo [filename]{filepath.name}[/filename] to {len(photoinfo.album_info)} {pluralize(len(photoinfo.album_info), 'album', 'albums')}"
    )
    albums = []
    for album_info in photoinfo.album_info:
        album_path = album_info.folder_names if album_info.folder_names else []
        album_path.append(album_info.title)
        album_name = "/".join(album_path)
        albums.append(album_name)
        verbose(
            f"Adding photo [filename]{filepath.name}[/] to album [filepath]{album_name}[/]"
        )
        if photo and not dry_run:
            photos_album = PhotosAlbumPhotoScriptByPath(
                album_path, verbose=verbose, rich=True
            )
            photos_album.add(photo)
    return albums


def add_photo_to_albums_from_exportdb(
    photo: Photo | None,
    filepath: pathlib.Path,
    exportdb_path: str,
    exportdir_path: str | None,
    exiftool_path: str,
    verbose: Callable[..., None],
    dry_run: bool,
) -> list[str]:
    """Add photo to one or more albums from data found in export database"""
    with suppress(ValueError):
        if photoinfo := export_db_get_photoinfo_for_filepath(
            exportdb_path=exportdb_path,
            filepath=filepath,
            exiftool=exiftool_path,
            exportdir_path=exportdir_path,
        ):
            if photoinfo.album_info:
                verbose(
                    f"Setting albums from export database for [filename]{filepath.name}[/]"
                )
                return add_photo_to_photoinfo_albums(
                    photo, photoinfo, filepath, verbose, dry_run
                )
        else:
            verbose(
                f"Could not load metadata from export database for [filename]{filepath.name}[/]"
            )
        return []


def add_duplicate_to_albums(
    duplicates: list[tuple[str, datetime.datetime, str]],
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path,
    album: tuple[str, ...],
    split_folder: str | None,
    exiftool_path: str | None,
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


def add_duplicate_to_albums_from_exportdb(
    duplicates: list[tuple[str, datetime.datetime, str]],
    filepath: pathlib.Path,
    exportdb_path: str,
    exportdir_path: str | None,
    exiftool_path: str,
    verbose: Callable[..., None],
    dry_run: bool,
) -> list[str]:
    """For photo with already imported duplicate, add the imported photo to albums

    duplicates: list of tuples of (uuid, date, filename) for duplicates as returned by FingerprintQuery.possible_duplicates
    filepath: path to file to import
    exportdb_path: path to the export db
    exportdir_path: path to the export directory if it cannot be determined from exportdb_path (e.g. the export was moved)
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

    return add_photo_to_albums_from_exportdb(
        dup_photo,
        filepath,
        exportdb_path,
        exportdir_path,
        exiftool_path,
        verbose,
        dry_run,
    )


def clear_photo_metadata(
    photo: Photo | None,
    filepath: pathlib.Path,
    verbose: Callable[..., None],
    dry_run: bool,
):
    """Clear any metadata (title, description, keywords) associated with Photo in the Photos Library"""
    verbose(f"Clearing metadata for [filename]{filepath.name}[/]")

    if dry_run or not photo:
        return
    photo.title = ""
    photo.description = ""
    photo.keywords = []


def clear_photo_location(
    photo: Photo | None,
    filepath: pathlib.Path,
    verbose: Callable[..., None],
    dry_run: bool,
):
    """Clear any location (latitude, longitude) associated with Photo in the Photos Library"""
    verbose(f"Clearing location for [filename]{filepath.name}[/]")
    if dry_run or not photo:
        return
    photo.location = (None, None)


def set_photo_metadata(
    photo: Photo | None,
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
    if dry_run or not photo:
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
    if metadata.favorite:
        # this will set favorite if True but cannot clear favorite as lack of favorite and not favorite is ambiguous
        photo.favorite = True
    return dataclasses.replace(metadata, keywords=keywords)


def set_photo_metadata_from_exportdb(
    photo: Photo | None,
    filepath: pathlib.Path,
    exportdb_path: pathlib.Path,
    exportdir_path: pathlib.Path | None,
    exiftool_path: str,
    merge_keywords: bool,
    verbose: Callable[..., None],
    dry_run: bool,
):
    """Set photo's metadata by reading metadata from exportdb"""
    photoinfo = None
    with suppress(ValueError):
        photoinfo = export_db_get_photoinfo_for_filepath(
            exportdb_path=exportdb_path,
            filepath=filepath,
            exiftool=exiftool_path,
            exportdir_path=exportdir_path,
        )
    if photoinfo:
        metadata = metadata_from_photoinfo(photoinfo)
        verbose(
            f"Setting metadata and location from export database for [filename]{filepath.name}[/]"
        )
        set_photo_metadata_from_metadata(
            photo, filepath, metadata, merge_keywords, True, verbose, dry_run
        )
    else:
        verbose(
            f"Could not load metadata from export database for [filename]{filepath.name}[/]"
        )


def set_photo_metadata_from_exiftool(
    photo: Photo | None,
    filepath: pathlib.Path,
    exiftool_path: str,
    merge_keywords: bool,
    verbose: Callable[..., None],
    dry_run: bool,
):
    """Set photo's metadata by reading metadata from file with exiftool"""
    verbose(f"Setting metadata and location from EXIF for [filename]{filepath.name}[/]")
    metadata = metadata_from_exiftool(filepath, exiftool_path)
    set_photo_metadata_from_metadata(
        photo, filepath, metadata, merge_keywords, True, verbose, dry_run
    )


def set_photo_metadata_from_metadata(
    photo: Photo | None,
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
        empty_str = ""
        verbose(
            f"title='{metadata.title or empty_str}', description='{metadata.description or empty_str}', "
            f"favorite={metadata.favorite}, keywords={metadata.keywords}"
        )
    else:
        verbose(f"No metadata to set for [filename]{filepath.name}[/]")

    if metadata.location[0] is not None and metadata.location[1] is not None:
        # location will be set to None, None if latitude or longitude is missing
        if photo and not dry_run:
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
        if photo and not dry_run:
            photo.date = metadata.date

    return metadata


def set_photo_metadata_from_sidecar(
    photo: Photo | None,
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
    photo: Photo | None,
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path,
    title_template: str,
    exiftool_path: str,
    sidecar: pathlib.Path | None,
    verbose: Callable[..., None],
    dry_run: bool,
) -> str:
    """Set title of photo"""
    title_text = render_photo_template_from_filepath(
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
        if photo and not dry_run:
            photo.title = normalize_unicode(title_text[0])
        return title_text[0]
    else:
        return ""


def set_photo_description(
    photo: Photo | None,
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path,
    description_template: str,
    exiftool_path: str,
    sidecar: pathlib.Path | None,
    verbose: Callable[..., None],
    dry_run: bool,
) -> str:
    """Set description of photo"""
    description_text = render_photo_template_from_filepath(
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
        if photo and not dry_run:
            photo.description = normalize_unicode(description_text[0])
        return description_text[0]
    else:
        return ""


def set_photo_keywords(
    photo: Photo | None,
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
        kw = render_photo_template_from_filepath(
            filepath, relative_filepath, keyword, exiftool_path, sidecar
        )
        keywords.extend(kw)
    if keywords:
        keywords = normalize_unicode(keywords)
        if merge and photo is not None:
            if old_keywords := normalize_unicode(photo.keywords):
                keywords.extend(old_keywords)
                keywords = list(set(keywords))
        verbose(f"Setting keywords of photo [filename]{filepath.name}[/] to {keywords}")
        if photo and not dry_run:
            photo.keywords = keywords
    return keywords


def set_photo_location(
    photo: Photo | None,
    filepath: pathlib.Path,
    location: Tuple[float, float],
    verbose: Callable[..., None],
    dry_run: bool,
) -> tuple[float, float]:
    """Set location of photo"""
    verbose(
        f"Setting location of photo [filename]{filepath.name}[/] to {location[0]}, {location[1]}"
    )
    if photo and not dry_run:
        photo.location = location
    return location


def set_photo_favorite(
    photo: Photo | None,
    filepath: pathlib.Path,
    sidecar_filepath: pathlib.Path | None,
    exiftool_path: str,
    favorite_rating: int | None,
    verbose: Callable[..., None],
    dry_run: bool,
):
    """Set favorite status of photo based on XMP:Rating value"""
    rating = get_photo_rating(filepath, sidecar_filepath, exiftool_path)
    if rating is not None and rating >= favorite_rating:
        verbose(
            f"Setting favorite status of photo [filename]{filepath.name}[/] (XMP:Rating=[num]{rating}[/])"
        )
        if photo and not dry_run:
            photo.favorite = True


def get_photo_rating(
    filepath: pathlib.Path, sidecar: pathlib.Path | None, exiftool_path: str
) -> int | None:
    """Get XMP:Rating from file"""
    photoinfo = PhotoInfoFromFile(
        filepath, exiftool=exiftool_path, sidecar=str(sidecar) if sidecar else None
    )
    return photoinfo.rating


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
    if photo and not dry_run:
        photo.date = date
    return date


def get_relative_filepath(
    filepath: pathlib.Path, relative_to: pathlib.Path | None
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


def apply_photo_metadata(
    clear_location: bool,
    clear_metadata: bool,
    description: str | None,
    dry_run: bool,
    exiftool: bool,
    exiftool_path: str,
    exportdb: pathlib.Path | None,
    exportdir: pathlib.Path | None,
    favorite_rating: bool,
    filepath: pathlib.Path,
    keyword: str | None,
    location: tuple[float, float],
    merge_keywords: bool,
    parse_date: str | None,
    parse_folder_date: str | None,
    photo: Photo,
    relative_filepath: pathlib.Path,
    sidecar_file: pathlib.Path | None,
    sidecar_ignore_date: bool,
    title: str | None,
    verbose: Callable[..., None],
):
    """Set metdata for photo"""

    if clear_metadata:
        clear_photo_metadata(photo, filepath, verbose, dry_run)

    if clear_location:
        clear_photo_location(photo, filepath, verbose, dry_run)

    if exportdb:
        set_photo_metadata_from_exportdb(
            photo,
            filepath,
            exportdb,
            exportdir,
            exiftool_path,
            merge_keywords,
            verbose,
            dry_run,
        )
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

    if favorite_rating:
        set_photo_favorite(
            photo,
            filepath,
            sidecar_file,
            exiftool_path,
            favorite_rating,
            verbose,
            dry_run,
        )

    if parse_date:
        set_photo_date_from_filename(
            photo,
            filepath.name,
            filepath.name,
            parse_date,
            verbose,
            dry_run,
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


def apply_photo_albums(
    album: tuple[str, ...],
    dry_run: bool,
    exiftool: bool,
    exiftool_path: str | None,
    exportdb: str | None,
    exportdir: str | None,
    filepath: pathlib.Path,
    photo: Photo,
    relative_filepath: pathlib.Path,
    report_record: ReportRecord,
    sidecar_file: pathlib.Path | None,
    split_folder: str | None,
    verbose: Callable[..., None],
):
    """Apply album changes to photo"""
    if album:
        report_record.albums += add_photo_to_albums(
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

    if exportdb:
        # add photo to any albums defined in the exportdb data
        report_record.albums += add_photo_to_albums_from_exportdb(
            photo, filepath, exportdb, exportdir, exiftool_path, verbose, dry_run
        )


def check_templates_and_exit(
    files: list[pathlib.Path],
    relative_to: pathlib.Path | None,
    title: str | None,
    description: str | None,
    keyword: tuple[str, ...],
    album: tuple[str, ...],
    exiftool_path: str | None,
    exiftool: bool,
    parse_date: str | None,
    parse_folder_date: str | None,
    sidecar: bool,
    sidecar_filename_template: str | None,
    edited_suffix: str | None,
    signature: str | None,
):
    """Renders templates against each file so user can verify correctness"""
    for file in files:
        if not (is_image_file(file) or is_video_file(file)):
            continue
        file = pathlib.Path(file).absolute().resolve()
        relative_filepath = get_relative_filepath(file, relative_to)
        sidecar_file = get_sidecar_file_with_template(
            filepath=file,
            sidecar=sidecar,
            sidecar_filename_template=sidecar_filename_template,
            edited_suffix=edited_suffix,
            exiftool_path=exiftool_path,
        )
        echo(f"[filepath]{file}[/]:")
        if sidecar and not sidecar_file:
            echo("no sidecar file found")
        else:
            echo(f"sidecar file: {sidecar_file}")
        if exiftool:
            metadata = metadata_from_exiftool(file, exiftool_path)
            echo(f"exiftool title: {metadata.title}")
            echo(f"exiftool description: {metadata.description}")
            echo(f"exiftool keywords: {metadata.keywords}")
            echo(f"exiftool location: {metadata.location}")
        if title:
            rendered_title = render_photo_template_from_filepath(
                file, relative_filepath, title, exiftool_path, sidecar_file
            )
            rendered_title = rendered_title[0] if rendered_title else "None"
            echo(f"title: [italic]{title}[/]: {rendered_title}")
        if description:
            rendered_description = render_photo_template_from_filepath(
                file, relative_filepath, description, exiftool_path, sidecar_file
            )
            rendered_description = (
                rendered_description[0] if rendered_description else "None"
            )
            echo(f"description: [italic]{description}[/]: {rendered_description}")
        if keyword:
            for kw in keyword:
                rendered_keywords = render_photo_template_from_filepath(
                    file, relative_filepath, kw, exiftool_path, sidecar_file
                )
                rendered_keywords = rendered_keywords or "None"
                echo(f"keyword: [italic]{kw}[/]: {rendered_keywords}")
        if album:
            for al in album:
                rendered_album = render_photo_template_from_filepath(
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
        if signature:
            rendered_signature = render_photo_template_from_filepath(
                file, relative_filepath, signature, exiftool_path, sidecar_file
            )
            rendered_signature = rendered_signature[0] if rendered_signature else "None"
            echo(f"signature: [italic]{signature}[/]: {rendered_signature}")
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
    burst: bool = False
    burst_images: int = 0
    live_photo: bool = False
    live_video: str = ""
    raw_pair: bool = False
    raw_image: str = ""
    aae_file: bool = False
    skipped_aae_file: bool = False
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
    report_record.location = photo.location or (None, None)
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
                    "burst",
                    "burst_images",
                    "live_photo",
                    "live_video",
                    "raw_pair",
                    "raw_image",
                    "aae_file",
                    "skipped_aae_file",
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
                    1 if report_record.imported else 0,
                    1 if report_record.burst else 0,
                    report_record.burst_images,
                    1 if report_record.live_photo else 0,
                    report_record.live_video,
                    1 if report_record.raw_pair else 0,
                    report_record.raw_image,
                    1 if report_record.aae_file else 0,
                    1 if report_record.skipped_aae_file else 0,
                    1 if report_record.error else 0,
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

    conn = sqlite3.connect(report_file, check_same_thread=SQLITE_CHECK_SAME_THREAD)
    create_or_migrate_sql_report_db(conn)

    c = conn.cursor()
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
                datetime,
                burst,
                burst_images,
                live_photo,
                live_video,
                raw_pair,
                raw_image,
                aae_file,
                skipped_aae_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            (
                report_id,
                str(report_record.filepath),
                report_record.filename,
                (
                    report_record.import_datetime.isoformat()
                    if report_record.import_datetime
                    else None
                ),
                report_record.uuid,
                report_record.imported,
                report_record.error,
                report_record.title,
                report_record.description,
                ",".join(report_record.keywords),
                ",".join(report_record.albums),
                (
                    f"{report_record.location[0]},{report_record.location[1]}"
                    if report_record.location and report_record.location is not None
                    else None
                ),
                report_record.datetime.isoformat() if report_record.datetime else None,
                report_record.burst,
                report_record.burst_images,
                report_record.live_photo,
                report_record.live_video,
                report_record.raw_pair,
                report_record.raw_image,
                report_record.aae_file,
                report_record.skipped_aae_file,
            ),
        )
    conn.commit()
    conn.close()


def create_or_migrate_sql_report_db(conn: sqlite3.Connection):
    """Create or migrate the SQLite DB for the import report"""

    c = conn.cursor()

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
    conn.commit()

    # migrate report table for additional records
    if "burst" not in sqlite_columns(conn, "report"):
        c.execute("ALTER TABLE report ADD COLUMN burst INTEGER;")
        conn.commit()

    if "burst_images" not in sqlite_columns(conn, "report"):
        c.execute("ALTER TABLE report ADD COLUMN burst_images INTEGER;")
        conn.commit()

    if "live_photo" not in sqlite_columns(conn, "report"):
        c.execute("ALTER TABLE report ADD COLUMN live_photo INTEGER;")
        conn.commit()

    if "live_video" not in sqlite_columns(conn, "report"):
        c.execute("ALTER TABLE report ADD COLUMN live_video TEXT;")
        conn.commit()

    if "raw_pair" not in sqlite_columns(conn, "report"):
        c.execute("ALTER TABLE report ADD COLUMN raw_pair INTEGER;")
        conn.commit()

    if "raw_image" not in sqlite_columns(conn, "report"):
        c.execute("ALTER TABLE report ADD COLUMN raw_image TEXT;")
        conn.commit()

    if "aae_file" not in sqlite_columns(conn, "report"):
        c.execute("ALTER TABLE report ADD COLUMN aae_file INTEGER;")
        conn.commit()

    if "skipped_aae_file" not in sqlite_columns(conn, "report"):
        c.execute("ALTER TABLE report ADD COLUMN skipped_aae_file INTEGER;")


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


def filename_matches_patterns(filename: str, patterns: tuple[str, ...]) -> bool:
    """Return True if filename matches any pattern in patterns"""
    return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)


def collect_files_to_import(
    files: tuple[str, ...],
    walk: bool,
    glob: tuple[str, ...],
    verbose: Callable[..., None],
    no_progress: bool,
) -> list[pathlib.Path]:
    """Collect files to import, recursively if necessary

    Args:
        files: list of initial files or directories to import
        walk: whether to walk directories
        glob: glob patterns to match files or empty tuple if none
        verbose: function to print verbose output
        no_progress: if True, do not print progress bars

    Note: ignores any files that appear to be image sidecar files
    """
    files_to_import = []
    with rich_progress(console=get_verbose_console(), mock=no_progress) as progress:
        task = progress.add_task("Collecting files to import...", total=None)
        for file in files:
            if os.path.isfile(file):
                files_to_import.append(file)
                progress.advance(task)
            elif os.path.isdir(file):
                if not walk:
                    # don't recurse but do collect all files in the directory
                    dir_files = [
                        os.path.join(file, f)
                        for f in os.listdir(file)
                        if os.path.isfile(os.path.join(file, f))
                    ]
                    files_to_import.extend(dir_files)
                    progress.advance(task)
                else:
                    for root, dirs, filenames in os.walk(file):
                        for file in filenames:
                            files_to_import.append(os.path.join(root, file))
                            progress.advance(task)
            else:
                progress.advance(task)
                continue

    if glob:
        verbose("Filtering files with glob...")
        files_to_import = [
            f
            for f in files_to_import
            if filename_matches_patterns(os.path.basename(f), glob)
        ]

    verbose(f"Getting absolute path of each import file...", level=2)
    files_to_import = [pathlib.Path(f).absolute() for f in files_to_import]

    # keep only image files, video files, and .aae files
    filtered_file_list = []
    with rich_progress(console=get_verbose_console(), mock=no_progress) as progress:
        task = progress.add_task(
            "Filtering import list for image & video files...",
            total=len(files_to_import),
        )
        for f in files_to_import:
            if is_image_file(f) or is_video_file(f) or f.suffix.lower() == ".aae":
                filtered_file_list.append(f)
            progress.advance(task)

    # there may be duplicates if user passed both a directory and files in that directory
    # e.g. /Volumes/import /Volumes/import/IMG_1234.*
    # so strip duplicates before returning the list
    return list(set(filtered_file_list))


def group_files_to_import(
    files: list[pathlib.Path],
    auto_live: bool,
    edited_suffix: str,
    relative_filepath: pathlib.Path | None,
    exiftool_path: str | None,
    sidecar: bool,
    sidecar_filename_template: str | None,
    verbose: Callable[..., None],
    no_progress: bool,
) -> list[tuple[pathlib.Path, ...]]:
    """Group files by live photo, burst UUID, raw+jpeg, etc."""
    # first collect all files by parent directory
    files_by_parent = {}
    with rich_progress(console=get_verbose_console(), mock=no_progress) as progress:
        task = progress.add_task(
            "Grouping files by parent directory...", total=len(files)
        )
        for file in files:
            parent = file.parent
            if parent not in files_by_parent:
                files_by_parent[parent] = []
            files_by_parent[parent].append(file)
            progress.advance(task)

    # walk through each parent directory and group files by same stem
    grouped_files = []
    with rich_progress(console=get_verbose_console(), mock=no_progress) as progress:
        task = progress.add_task(
            "Grouping files into import groups...", total=len(files_by_parent)
        )
        for parent, files in files_by_parent.items():
            grouped = group_files_by_stem(
                files,
                edited_suffix,
                relative_filepath,
                exiftool_path,
                sidecar,
                sidecar_filename_template,
                auto_live,
            )
            grouped_files.extend(grouped)
            progress.advance(task)

    files_to_import = []
    for group in grouped_files:
        files_to_import.append(sort_paths(group))

    # verify each group is a valid import type and if not, break in separate groups
    return group_files_to_import_by_type(
        files_to_import,
        auto_live,
        edited_suffix,
        relative_filepath,
        exiftool_path,
        sidecar,
        sidecar_filename_template,
    )


def group_files_to_import_by_type(
    files_to_import: list[tuple[pathlib.Path, ...]],
    auto_live: bool,
    edited_suffix: str,
    relative_filepath: pathlib.Path | None,
    exiftool_path: str | None,
    sidecar: bool,
    sidecar_filename_template: str | None,
) -> list[tuple[pathlib.Path, ...]]:
    """Given a list of import tuples created by group_files_to_import, validate the types and adjust the groups if needed

    The returned list of tuples will include all file groups that should be imported together;
    any files that should not be imported with a group will be moved to a group of 1 file
    to be imported individually.
    """
    new_files_to_import = []
    for file_tuple in files_to_import:
        if file_type := file_type_for_import_group(
            file_tuple,
            auto_live,
            edited_suffix,
            relative_filepath,
            exiftool_path,
            sidecar,
            sidecar_filename_template,
        ):
            if (
                file_type & FILE_TYPE_HAS_EDITED_FILE
                and not file_type & FILE_TYPE_HAS_AAE_FILE
            ):
                # edited versions can only be imported together with original + AAE
                new_files_to_import.extend(
                    split_edited_from_file_group(
                        file_tuple,
                        relative_filepath,
                        edited_suffix,
                        exiftool_path,
                        sidecar,
                        sidecar_filename_template,
                    )
                )
            else:
                new_files_to_import.append(file_tuple)
        else:
            # unpack into tuples of single files
            new_files_to_import.extend((f,) for f in file_tuple)
    return new_files_to_import


def split_edited_from_file_group(
    file_tuple: tuple[pathlib.Path, ...],
    relative_filepath: pathlib.Path | None,
    edited_suffix: str,
    exiftool_path: str | None,
    sidecar: bool,
    sidecar_filename_template: str | None,
) -> list[tuple[pathlib.Path, ...]]:
    """Split any edited files out from the file_tuple group.

    Args:
        file_tuple (tuple[Path, ...]): Tuple of file paths to evaluate.
        relative_filepath (Path | None): Relative file path for template generation.
        edited_suffix (str): Suffix to denote edited files.
        exiftool_path (str | None): Path to exiftool for metadata extraction.
        sidecar (bool): Whether to use sidecar files.
        sidecar_filename_template (str | None): Optional template to render sidecar filename

    Returns:
        list[tuple[Path, ...]]: List of tuples with the edited file as an individual tuple.
    """
    edited_files_group = []
    original_file_list = []

    for file in file_tuple:
        if re.match(EDITED_RE, str(file)):
            # Add the edited file as its own tuple
            edited_files_group.append((file,))
        else:
            original_file_list.append(file)

    possible_edited_files = []
    for file in original_file_list:
        sidecar_filename = (
            get_sidecar_file_with_template(
                filepath=file,
                sidecar=sidecar,
                sidecar_filename_template=sidecar_filename_template,
                edited_suffix=edited_suffix,
                exiftool_path=exiftool_path,
            )
            if sidecar
            else None
        )
        edited_filename = edited_filename_from_template(
            pathlib.Path(file),
            relative_filepath,
            edited_suffix,
            exiftool_path,
            sidecar_filename,
        )
        if edited_filename.is_file():
            possible_edited_files.append(edited_filename)

        original_file_list = [
            file for file in original_file_list if file not in possible_edited_files
        ]

    for edited_file in possible_edited_files:
        edited_files_group.append((edited_file,))

    if original_file_list:
        edited_files_group.append(tuple(original_file_list))

    return edited_files_group


def sort_paths(paths: Iterable[pathlib.Path]) -> tuple[pathlib.Path, ...]:
    """Sort paths into desired order for import so the key file is first

    Sort order is : alphabetically, length of filename (shorter first), MOV files, AAE file

    For example:

    ABC_1234.jpg, ABC_1234.mov, ABC_1234.aae, ABC_1234_edited.mov, IMG_1234.jpg

    """

    def path_key(path: pathlib.Path) -> tuple[str, int, int, int, int]:
        extension = path.suffix.lower()
        is_aae = extension == ".aae"
        is_mov = extension in (".mov", ".mp4")
        base_name = path.stem.split("_")[0]  # Extract the base name without suffixes
        return (base_name, len(path.stem), is_aae, is_mov)

    return tuple(sorted(paths, key=path_key))


def group_files_by_stem(
    files: list[pathlib.Path],
    edited_suffix: str,
    relative_filepath: pathlib.Path | None,
    exiftool_path: str | None,
    sidecar: bool,
    sidecar_filename_template: str | None,
    auto_live: bool,
) -> list[tuple[pathlib.Path, ...]]:
    """Group files by stem (filename without extension) and
    return list of tuples of files with same stem and list of files without a match"""
    if not files:
        return []

    # avoid foot-gun by verifying that all paths have the same parent
    parent = files[0].parent
    for f in files:
        if f.parent != parent:
            raise ValueError("All files must have the same parent path")

    file_list = list(sort_paths(files))
    grouped_files = []
    i = 0
    while i < len(file_list):
        path1 = file_list[i]
        stem1 = path1.stem.lower()
        edited_stem1 = filepath_with_edited_suffix(
            path1,
            edited_suffix,
            relative_filepath,
            exiftool_path,
            sidecar,
            sidecar_filename_template,
        ).stem.lower()
        burst_uuid1 = burst_uuid_from_path(path1)
        group = [path1]
        j = i + 1

        while j < len(file_list):
            path2 = file_list[j]
            stem2 = path2.stem.lower()
            if (
                (stem1 == stem2)
                or (is_edited_version_of_file(path1, path2))
                or (path2.stem.lower() == edited_stem1)
                or (burst_uuid1 and burst_uuid_from_path(path2) == burst_uuid1)
            ):
                group.append(path2)
                file_list.pop(j)
            else:
                j = j + 1
        file_list.pop(i)
        grouped_files.append(tuple(group))
    return grouped_files


def file_type_for_import_group(
    file_tuple: tuple[pathlib.Path, ...],
    auto_live: bool,
    edited_suffix: str,
    relative_filepath: pathlib.Path | None,
    exiftool_path: str | None,
    sidecar: bool,
    sidecar_filename_template: str | None,
) -> int:
    """Determine the file type for a given group of files; also strips non-Apple AAE files from file_tuple.

    Args:
        file_tuple: tuple of files to import
        auto_live: if True, find possible live pairs
        edited_suffix: suffix template for edited files
        relative_filepath: relative filepath for template generation
        exiftool_path: path to exiftool for metadata extraction
        sidecar: whether to use sidecar files
        sidecar_filename_template: template for sidecar filename

    Returns: bit mask for the file type
    """
    file_type = 0
    if len(file_tuple) > 1:
        if burst_uuid_from_path(file_tuple[0]):
            file_type |= FILE_TYPE_IS_BURST_GROUP
        elif is_live_pair(*file_tuple[:2]):
            file_type |= FILE_TYPE_IS_LIVE_PAIR
        elif is_raw_pair(*file_tuple[:2]):
            file_type |= FILE_TYPE_IS_RAW_JPEG_PAIR
        elif auto_live and is_possible_live_pair(*file_tuple[:2]):
            file_type |= FILE_TYPE_AUTO_LIVE_PAIR
            file_type |= FILE_TYPE_SHOULD_STAGE_FILES
        if has_aae(file_tuple):
            if non_apple_aae_file := has_non_apple_aae(file_tuple):
                file_type |= FILE_TYPE_HAS_NON_APPLE_AAE
                file_type |= FILE_TYPE_SHOULD_STAGE_FILES
            else:
                file_type |= FILE_TYPE_HAS_AAE_FILE

        if has_original_and_edited_suffix(
            file_tuple,
            edited_suffix,
            relative_filepath,
            exiftool_path,
            sidecar,
            sidecar_filename_template,
        ):
            file_type |= FILE_TYPE_HAS_EDITED_FILE
            file_type |= FILE_TYPE_SHOULD_STAGE_FILES
            file_type |= FILE_TYPE_SHOULD_RENAME_EDITED
        elif has_original_and_edited(file_tuple):
            file_type |= FILE_TYPE_HAS_EDITED_FILE
    return file_type


def noun_for_file_type(file_type: int) -> str:
    """Return noun to use for a given file type in user messages.

    Args:
        file_type: bit mask file_type as returned by file_type_for_import_group

    Returns: str with the noun / description of the file type
    """
    noun = "import group"
    if file_type & FILE_TYPE_IS_IMPORT_GROUP:
        noun = "import group"
    if file_type & FILE_TYPE_IS_BURST_GROUP:
        noun = "burst group"
    if file_type & FILE_TYPE_IS_LIVE_PAIR:
        noun = "live photo pair"
    if file_type & FILE_TYPE_IS_RAW_JPEG_PAIR:
        noun = "raw+jpeg pair"
    if file_type & FILE_TYPE_AUTO_LIVE_PAIR:
        noun = "live photo pair"
    if file_type & FILE_TYPE_HAS_AAE_FILE:
        noun += " with .AAE file"
    if file_type & FILE_TYPE_HAS_EDITED_FILE:
        noun += " with edited version"
    return noun


def strip_non_apple_aae_file(
    file_tuple: tuple[pathlib.Path, ...], verbose: Callable[..., None]
) -> tuple[pathlib.Path, ...]:
    """Strip non-Apple AAE file from a file tuple.

    Args:
        file_tuple: tuple of file paths to check for non-Apple AAE files
        verbose: Callable to print verbose output

    Returns: tuple of file paths with any non-Apple AAE files stripped from the tuple
    """
    if non_apple_aae_file := has_non_apple_aae(file_tuple):
        file_tuple = tuple(f for f in file_tuple if not f.suffix.lower() == ".aae")
        verbose(
            f"Skipping import of non-Apple AAE file from external edit: {non_apple_aae_file}"
        )
    return file_tuple


def import_files(
    last_library: str,
    files: list[tuple[pathlib.Path, ...]],
    no_progress: bool,
    resume: bool,
    clear_metadata: bool,
    clear_location: bool,
    edited_suffix: str | None,
    exiftool: bool,
    exiftool_path: str,
    exportdb: str | None,
    exportdir: str | None,
    favorite_rating: int | None,
    sidecar: bool,
    sidecar_ignore_date: bool,
    sidecar_filename_template: str,
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
    post_function: tuple[Callable[..., None], ...],
    skip_dups: bool,
    dup_check: bool,
    dry_run: bool,
    report_data: dict[pathlib.Path, ReportRecord],
    relative_to: pathlib.Path | None,
    import_db: SQLiteKVStore,
    verbose: Callable[..., None],
    auto_live: bool,
    stop_on_error: int | None,
    signature: str | None,
) -> tuple[int, int, int]:
    """Import files into Photos library

    Returns: tuple of imported_count, skipped_count, error_count
    """
    # initialize FingerprintQuery to be able to find duplicates
    if signature:
        fq = SignatureQuery(
            last_library,
            signature,
            sidecar,
            sidecar_filename_template,
            edited_suffix,
            exiftool_path,
        )
    else:
        fq = FingerprintQuery(last_library)

    imported_count = 0
    error_count = 0
    skipped_count = 0
    filecount = len(list(itertools.chain.from_iterable(files)))
    groupcount = len(files)
    with rich_progress(console=get_verbose_console(), mock=no_progress) as progress:
        task = progress.add_task(
            f"Importing [num]{filecount}[/] {pluralize(filecount, 'file', 'files')} in [num]{groupcount}[/] {pluralize(groupcount, 'group', 'groups')}",
            total=groupcount,
        )
        try:
            for file_tuple in files:
                file_type = file_type_for_import_group(
                    file_tuple,
                    auto_live,
                    edited_suffix,
                    relative_to,
                    exiftool_path,
                    sidecar,
                    sidecar_filename_template,
                )
                noun = noun_for_file_type(file_type)
                if file_type & FILE_TYPE_HAS_NON_APPLE_AAE:
                    file_tuple = strip_non_apple_aae_file(file_tuple, verbose)
                verbose(
                    f"Processing {noun}: {', '.join([f'[filename]{f.name}[/]' for f in file_tuple])}"
                )
                filepath = pathlib.Path(file_tuple[0]).resolve().absolute()
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

                verbose(
                    f"Importing " + ", ".join(f"[filepath]{f}[/]" for f in file_tuple)
                )

                report_data[filepath] = ReportRecord(
                    filename=filepath.name,
                    filepath=filepath,
                    burst=bool(file_type & FILE_TYPE_IS_BURST_GROUP),
                    burst_images=(
                        len(file_tuple) if file_type & FILE_TYPE_IS_BURST_GROUP else 0
                    ),
                    live_photo=bool(file_type & FILE_TYPE_IS_LIVE_PAIR),
                    live_video=(
                        str(file_tuple[1])
                        if (file_type & FILE_TYPE_IS_LIVE_PAIR)
                        or (file_type & FILE_TYPE_AUTO_LIVE_PAIR)
                        else ""
                    ),
                    raw_pair=bool(file_type & FILE_TYPE_IS_RAW_JPEG_PAIR),
                    raw_image=(
                        str(file_tuple[1])
                        if file_type & FILE_TYPE_IS_RAW_JPEG_PAIR
                        else ""
                    ),
                    aae_file=bool(file_type & FILE_TYPE_HAS_AAE_FILE),
                    skipped_aae_file=bool(file_type & FILE_TYPE_HAS_NON_APPLE_AAE),
                )
                report_record = report_data[filepath]

                if sidecar or sidecar_filename_template:
                    sidecar_file = get_sidecar_file_with_template(
                        filepath=filepath,
                        sidecar=sidecar,
                        sidecar_filename_template=sidecar_filename_template,
                        edited_suffix=edited_suffix,
                        exiftool_path=exiftool_path,
                    )
                    if not sidecar_file:
                        verbose(f"No sidecar file found for [filepath]{filepath}[/]")
                else:
                    sidecar_file = None

                if duplicates := fq.possible_duplicates(filepath):
                    # duplicate of file already in Photos library
                    verbose(
                        f"File [filename]{filepath.name}[/] appears to be a duplicate of photos in the library: "
                        f"{', '.join([f'[filename]{f}[/] ([uuid]{u}[/]) added [datetime]{d}[/] ' for u, d, f in duplicates])}"
                    )

                    if skip_dups:
                        verbose(f"Skipping duplicate [filename]{filepath.name}[/]")
                        skipped_count += 1
                        report_record.imported = False

                        if not dup_albums:
                            continue

                        if album:
                            report_record.albums += add_duplicate_to_albums(
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

                        if exportdb:
                            report_record.albums += (
                                add_duplicate_to_albums_from_exportdb(
                                    duplicates,
                                    filepath,
                                    exportdb,
                                    exportdir,
                                    exiftool_path,
                                    verbose,
                                    dry_run,
                                )
                            )

                        continue

                if not dry_run:
                    with tempfile.TemporaryDirectory(
                        prefix="osxphotos_import_", ignore_cleanup_errors=True
                    ) as temp_dir:
                        if file_type & FILE_TYPE_SHOULD_STAGE_FILES:
                            verbose(
                                f"Staging files to [filepath]{temp_dir}[/] prior to import",
                                level=2,
                            )
                            files_to_import = stage_files(file_tuple, temp_dir)
                        else:
                            files_to_import = file_tuple
                        if file_type & FILE_TYPE_AUTO_LIVE_PAIR:
                            verbose(
                                f"Converting to live photo pair: [filename]{files_to_import[0].name}[/], [filename]{files_to_import[1].name}[/]"
                            )
                            try:
                                if not makelive:
                                    raise RuntimeError(
                                        "makelive not compatible with this version of macOS"
                                    )
                                makelive.make_live_photo(*files_to_import[:2])
                            except Exception as e:
                                echo(
                                    f"Error converting {files_to_import[0].name}, {files_to_import[1].name} to live photo pair: {e}",
                                    err=True,
                                )
                        if file_type & FILE_TYPE_SHOULD_RENAME_EDITED:
                            verbose(
                                f"Renaming edited group: {', '.join(f'[filename]{f.name}[/]' for f in files_to_import)}",
                                level=2,
                            )
                            files_to_import = rename_edited_group(
                                files_to_import,
                                edited_suffix,
                                relative_filepath,
                                exiftool_path,
                                sidecar,
                                sidecar_filename_template,
                            )
                            verbose(
                                f"Edited group renamed: {', '.join(f'[filename]{f.name}[/]' for f in files_to_import)}",
                                level=2,
                            )
                        photo, error = import_photo_group(
                            files_to_import, dup_check, verbose
                        )
                    if error:
                        error_count += 1
                        report_record.error = True

                        if stop_on_error and error_count >= stop_on_error:
                            rich_echo_error(
                                "[error]Error count exceeded limit, stopping! "
                                f"Last file: [filename]{filepath.name}[/], error count = [num]{error_count}[/]"
                            )
                            raise StopIteration
                        continue
                else:
                    photo = None
                report_record.imported = True
                imported_count += 1

                apply_photo_metadata(
                    clear_location=clear_location,
                    clear_metadata=clear_metadata,
                    description=description,
                    dry_run=dry_run,
                    exiftool=exiftool,
                    exiftool_path=exiftool_path,
                    exportdb=exportdb,
                    exportdir=exportdir,
                    favorite_rating=favorite_rating,
                    filepath=filepath,
                    keyword=keyword,
                    location=location,
                    merge_keywords=merge_keywords,
                    parse_date=parse_date,
                    parse_folder_date=parse_folder_date,
                    photo=photo,
                    relative_filepath=relative_filepath,
                    sidecar_file=sidecar_file,
                    sidecar_ignore_date=sidecar_ignore_date,
                    title=title,
                    verbose=verbose,
                )

                apply_photo_albums(
                    album=album,
                    dry_run=dry_run,
                    exiftool=exiftool,
                    exiftool_path=exiftool_path,
                    exportdb=exportdb,
                    exportdir=exportdir,
                    filepath=filepath,
                    photo=photo,
                    relative_filepath=relative_filepath,
                    report_record=report_record,
                    sidecar_file=sidecar_file,
                    split_folder=split_folder,
                    verbose=verbose,
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
                if photo and not dry_run:
                    update_report_record(report_record, photo, filepath)
                    import_db.set(str(filepath), report_record)

                progress.advance(task)
        except StopIteration:
            pass
    return imported_count, skipped_count, error_count


def check_imported_files(
    files: list[tuple[pathlib.Path, ...]],
    relative_to: pathlib.Path | None,
    library: str,
    signature: str,
    sidecar: bool,
    sidecar_filename_template: str | None,
    edited_suffix: str | None,
    exiftool_path: str | None,
    verbose: Callable[..., None],
):
    """Check if files have been previously imported and print results"""

    if not files:
        rich_echo_error("No files to check")
        return

    filecount = len(list(itertools.chain.from_iterable(files)))
    file_word = pluralize(filecount, "file", "files")
    group_word = pluralize(files, "group", "groups")
    verbose(
        f"Checking {filecount} {file_word} in {len(files)} {group_word} to see if previously imported"
    )
    if signature:
        fq = SignatureQuery(
            library,
            signature,
            sidecar,
            sidecar_filename_template,
            edited_suffix,
            exiftool_path,
        )
    else:
        fq = FingerprintQuery(library)
    for filegroup in files:
        filepaths, remainder = collect_filepaths_for_import_check(
            filegroup,
            edited_suffix,
            relative_to,
            exiftool_path,
            sidecar,
            sidecar_filename_template,
        )
        for filepath in filepaths:
            group_str = (
                f" ({', '.join([str(f) for f in remainder])})" if remainder else ""
            )
            if duplicates := fq.possible_duplicates(filepath):
                echo(
                    f"[filepath]:white_check_mark-emoji: {filepath}{group_str}[/], imported, "
                    + f"{', '.join([f'[filename]{f}[/] ([uuid]{u}[/]) added [datetime]{d}[/] ' for u, d, f in duplicates])}"
                )
            else:
                echo(f"[error]{filepath}{group_str}[/], not imported")


def check_not_imported_files(
    files: list[tuple[pathlib.Path, ...]],
    relative_to: pathlib.Path | None,
    library: str,
    signature: str,
    sidecar: bool,
    sidecar_filename_template: str | None,
    edited_suffix: str | None,
    exiftool_path: str | None,
    verbose: Callable[..., None],
):
    """Check if files have not been previously imported and print results"""

    if not files:
        rich_echo_error("No files to check")
        return

    filecount = len(list(itertools.chain.from_iterable(files)))
    file_word = pluralize(filecount, "file", "files")
    group_word = pluralize(files, "group", "groups")
    verbose(
        f"Checking {filecount} {file_word} in {len(files)} {group_word} to see if not previously imported"
    )
    if signature:
        fq = SignatureQuery(
            library,
            signature,
            sidecar,
            sidecar_filename_template,
            edited_suffix,
            exiftool_path,
        )
    else:
        fq = FingerprintQuery(library)
    for filegroup in files:
        filepaths, remainder = collect_filepaths_for_import_check(
            filegroup,
            edited_suffix,
            relative_to,
            exiftool_path,
            sidecar,
            sidecar_filename_template,
        )
        for filepath in filepaths:
            if fq.possible_duplicates(filepath):
                continue
            group_str = (
                f" ({', '.join([str(f) for f in remainder])})" if remainder else ""
            )
            echo(f"{filepath}{group_str}")


def has_aae(filepaths: Iterable[str | os.PathLike]) -> bool:
    """Return True if any file in the list is an AAE file"""
    for filepath in filepaths:
        filepath = (
            pathlib.Path(filepath)
            if not isinstance(filepath, pathlib.Path)
            else filepath
        )
        if filepath.name.lower().endswith(".aae"):
            return True
    return False


def has_non_apple_aae(filepaths: Iterable[str | os.PathLike]) -> str | None:
    """Return True value if any file in the list are an AAE file but not an Apple AAE file (external edits)"""
    for filepath in filepaths:
        filepath = (
            pathlib.Path(filepath)
            if not isinstance(filepath, pathlib.Path)
            else filepath
        )
        if filepath.name.lower().endswith(".aae"):
            if not is_apple_photos_aae_file(filepath):
                return str(filepath)
    return None


def has_original_and_edited_suffix(
    filepaths: Iterable[str | os.PathLike],
    edited_suffix: str,
    relative_filepath: pathlib.Path | None,
    exiftool_path: str | None,
    sidecar: bool,
    sidecar_filename_template: str | None,
) -> bool:
    """Return True if any files in list appear to be an original and an edited version using _edited suffix"""

    if edited := edited_suffix_files(
        filepaths,
        edited_suffix,
        relative_filepath,
        exiftool_path,
        sidecar,
        sidecar_filename_template,
    ):
        return True
    return False


def has_original_and_edited(
    filepaths: Iterable[str | os.PathLike],
) -> bool:
    """Return True if any files in list appear to be an original and an edited version"""

    # see if there's a match in form "IMG_1234.jpg" and "IMG_E1234.jpg"
    for filepath1 in filepaths:
        if not re.match(ORIGINAL_RE, str(filepath1)):
            continue
        for filepath2 in filepaths:
            if not re.match(EDITED_RE, str(filepath2)):
                continue
            if is_edited_version_of_file(filepath1, filepath2):
                return True
    return False


def non_raw_file(filepaths: Iterable[str | os.PathLike]) -> str | os.PathLike:
    """Return the non-RAW file from a RAW+non-RAW pair or the first file if non-RAW file not found"""
    for filepath in filepaths:
        if not is_raw_image(filepath):
            return filepath
    return filepaths[0]


def non_edited_files(
    filepaths: Iterable[str | os.PathLike],
    edited_suffix: str,
    relative_filepath: pathlib.Path | None,
    exiftool_path: str | None,
    sidecar: pathlib.Path | None,
) -> list[os.PathLike]:
    """Return only the non-edited files from a file group"""

    edited_files = set(
        edited_filename_from_template(
            pathlib.Path(fp), relative_filepath, edited_suffix, exiftool_path, sidecar
        )
        for fp in filepaths
    )
    non_edited = [fp for fp in filepaths if pathlib.Path(fp) not in edited_files]

    # Also exclude any files that match EDITED_RE if a file in the filepaths matches ORIGINAL_RE
    for filepath1 in filepaths:
        if not re.match(ORIGINAL_RE, str(filepath1)):
            continue
        for filepath2 in filepaths:
            if not re.match(EDITED_RE, str(filepath2)):
                continue
            if is_edited_version_of_file(filepath1, filepath2):
                non_edited = [fp for fp in non_edited if fp != filepath2]
    return non_edited


def edited_suffix_files(
    filepaths: Iterable[pathlib.Path],
    edited_suffix: str,
    relative_filepath: pathlib.Path | None,
    exiftool_path: str | None,
    sidecar: bool,
    sidecar_filename_template: str | None,
) -> list[os.PathLike]:
    """Return filepaths in filepaths that are the same as another file in filepaths but with edited_suffix otherwise empty list"""

    edited_files = set()
    for file in filepaths:
        sidecar_filename = get_sidecar_file_with_template(
            filepath=file,
            sidecar=sidecar,
            sidecar_filename_template=sidecar_filename_template,
            edited_suffix=edited_suffix,
            exiftool_path=exiftool_path,
        )
        edited_files.add(
            edited_filename_from_template(
                pathlib.Path(file),
                relative_filepath,
                edited_suffix,
                exiftool_path,
                sidecar_filename,
            ).stem
        )
    return [fp for fp in filepaths if fp.stem in edited_files]


def filepath_with_edited_suffix(
    filepath: pathlib.Path,
    edited_suffix: str,
    relative_filepath: pathlib.Path | None,
    exiftool_path: str | None,
    sidecar: bool,
    sidecar_filename_template: str | None,
) -> os.PathLike:
    """Return the file name of the filepath with the given edited_suffix rendered"""

    sidecar_filename = get_sidecar_file_with_template(
        filepath=filepath,
        sidecar=sidecar,
        sidecar_filename_template=sidecar_filename_template,
        edited_suffix=edited_suffix,
        exiftool_path=exiftool_path,
    )
    edited_file = edited_filename_from_template(
        filepath, relative_filepath, edited_suffix, exiftool_path, sidecar_filename
    )
    return edited_file


def edited_filename_from_template(
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path | None,
    template: str,
    exiftool_path: str | None,
    sidecar: pathlib.Path | None,
) -> pathlib.Path:
    """Given an edited suffix template, return the filename of the edited file for a given path"""

    edited_name = render_photo_template_from_filepath(
        filepath=filepath,
        relative_filepath=relative_filepath,
        template=template or DEFAULT_EDITED_SUFFIX,
        exiftool_path=exiftool_path,
        sidecar=sidecar,
    )

    if not edited_name:
        raise ValueError(
            f"Could not get edited path for {filepath} from template {template}"
        )
    return (
        pathlib.Path(filepath.parent)
        / f"{filepath.stem}{edited_name[0]}{filepath.suffix}"
    )


def stage_files(
    filepaths: Iterable[str | os.PathLike], temp_dir: str | os.PathLike
) -> tuple[pathlib.Path]:
    """Stage files for import to temp directory"""
    staged = []
    for source in filepaths:
        dest = os.path.join(temp_dir, pathlib.Path(source).name)
        FileUtilMacOS.copy(str(source), dest)
        staged.append(pathlib.Path(dest))
    return tuple(staged)


def rename_edited_group(
    filepaths: list[pathlib.Path],
    edited_suffix: str | None,
    relative_filepath: pathlib.Path | None,
    exiftool_path: str | None,
    sidecar: bool,
    sidecar_filename_template: str | None,
) -> list[pathlib.Path]:
    """Rename files if necessary so originals+edited+aae are correctly imported by Photos"""
    original_regex = re.compile(r"^(.*\/?)([A-Za-z]{3})_(\d{4})(.*)\.([a-zA-Z0-9]+)$")
    edited_regex = re.compile(r"^.*\/?(.*_E\d{4}).*$")

    edited_files = []
    original_files = list(filepaths)

    for filepath in filepaths:
        if edited_regex.match(str(filepath)):
            edited_files.append(filepath)
            original_files.remove(filepath)

    if not edited_files:
        # look for edited file using template
        if edited_files := edited_suffix_files(
            filepaths,
            edited_suffix,
            relative_filepath,
            exiftool_path,
            sidecar,
            sidecar_filename_template,
        ):
            for e in edited_files:
                original_files.remove(e)

    if not edited_files:
        return filepaths

    original_match = original_regex.match(str(original_files[0]))
    if original_match:
        # second format: ABC_1234.jpg, ABC_1234_suffix.jpg
        new_edited_files = []
        prefix = original_match.group(2)
        counter_value = original_match.group(3)
        postfix = original_match.group(4)
        for edited_file in edited_files:
            new_edited_filepath = pathlib.Path(
                edited_file.parent,
                f"{prefix}_E{counter_value}{postfix}{edited_file.suffix}",
            )
            edited_file.rename(new_edited_filepath)
            new_edited_files.append(new_edited_filepath)

        return original_files + new_edited_files
    else:
        # third format: ImageName.jpg, ImageName_edited.jpg
        prefix = "IMG"
        counter_value = _increment_image_counter()
        new_filepaths = []

        for filepath in original_files:
            new_filepath = pathlib.Path(
                filepath.parent,
                f"{prefix}_{counter_value}_{filepath.stem}{filepath.suffix}",
            )
            filepath.rename(new_filepath)
            new_filepaths.append(new_filepath)

        # edited version needs to be renamed in format: ABC_E0001_ImageName.jpg
        original_stem = original_files[0].stem
        for edited_file in edited_files:
            edited_suffix = edited_file.suffix
            new_edited_filepath = pathlib.Path(
                edited_file.parent,
                f"{prefix}_E{counter_value}_{original_stem}{edited_suffix}",
            )
            edited_file.rename(new_edited_filepath)
            new_filepaths.append(new_edited_filepath)

        return new_filepaths
