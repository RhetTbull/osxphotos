"""Globals and constants use by the CLI commands"""


import os
import pathlib
from datetime import datetime

import click

import osxphotos
from osxphotos._version import __version__

from .param_types import *

# used to show/hide hidden commands
OSXPHOTOS_HIDDEN = not bool(os.getenv("OSXPHOTOS_SHOW_HIDDEN", default=False))

# used by snap and diff commands
OSXPHOTOS_SNAPSHOT_DIR = "/private/tmp/osxphotos_snapshots"

# where to write the crash report if osxphotos crashes
OSXPHOTOS_CRASH_LOG = f"{os.getcwd()}/osxphotos_crash.log"

CLI_COLOR_ERROR = "red"
CLI_COLOR_WARNING = "yellow"

__all__ = [
    "CLI_COLOR_ERROR",
    "CLI_COLOR_WARNING",
    "DB_ARGUMENT",
    "DB_OPTION",
    "DEBUG_OPTIONS",
    "DELETED_OPTIONS",
    "JSON_OPTION",
    "QUERY_OPTIONS",
    "get_photos_db",
    "load_uuid_from_file",
    "noop",
    "time_stamp",
]


def noop(*args, **kwargs):
    """no-op function"""
    pass


def time_stamp() -> str:
    """return timestamp"""
    return f"[time]{str(datetime.now())}[/time] -- "


def get_photos_db(*db_options):
    """Return path to photos db, select first non-None db_options
    If no db_options are non-None, try to find library to use in
    the following order:
    - last library opened
    - system library
    - ~/Pictures/Photos Library.photoslibrary
    - failing above, returns None
    """
    if db_options:
        for db in db_options:
            if db is not None:
                return db

    # if get here, no valid database paths passed, so try to figure out which to use
    db = osxphotos.utils.get_last_library_path()
    if db is not None:
        click.echo(f"Using last opened Photos library: {db}", err=True)
        return db

    db = osxphotos.utils.get_system_library_path()
    if db is not None:
        click.echo(f"Using system Photos library: {db}", err=True)
        return db

    db = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")
    if os.path.isdir(db):
        click.echo(f"Using Photos library: {db}", err=True)
        return db
    else:
        return None


DB_OPTION = click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help=(
        "Specify Photos database path. "
        "Path to Photos library/database can be specified using either --db "
        "or directly as PHOTOS_LIBRARY positional argument. "
        "If neither --db or PHOTOS_LIBRARY provided, will attempt to find the library "
        "to use in the following order: 1. last opened library, 2. system library, 3. ~/Pictures/Photos Library.photoslibrary"
    ),
    type=click.Path(exists=True),
)

DB_ARGUMENT = click.argument("photos_library", nargs=-1, type=click.Path(exists=True))

JSON_OPTION = click.option(
    "--json",
    "json_",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)


def DELETED_OPTIONS(f):
    o = click.option
    options = [
        o(
            "--deleted",
            is_flag=True,
            help="Include photos from the 'Recently Deleted' folder.",
        ),
        o(
            "--deleted-only",
            is_flag=True,
            help="Include only photos from the 'Recently Deleted' folder.",
        ),
    ]
    for o in options[::-1]:
        f = o(f)
    return f


def QUERY_OPTIONS(f):
    o = click.option
    options = [
        o(
            "--keyword",
            metavar="KEYWORD",
            default=None,
            multiple=True,
            help="Search for photos with keyword KEYWORD. "
            'If more than one keyword, treated as "OR", e.g. find photos matching any keyword',
        ),
        o(
            "--person",
            metavar="PERSON",
            default=None,
            multiple=True,
            help="Search for photos with person PERSON. "
            'If more than one person, treated as "OR", e.g. find photos matching any person',
        ),
        o(
            "--album",
            metavar="ALBUM",
            default=None,
            multiple=True,
            help="Search for photos in album ALBUM. "
            'If more than one album, treated as "OR", e.g. find photos matching any album',
        ),
        o(
            "--folder",
            metavar="FOLDER",
            default=None,
            multiple=True,
            help="Search for photos in an album in folder FOLDER. "
            'If more than one folder, treated as "OR", e.g. find photos in any FOLDER.  '
            "Only searches top level folders (e.g. does not look at subfolders)",
        ),
        o(
            "--name",
            metavar="FILENAME",
            default=None,
            multiple=True,
            help="Search for photos with filename matching FILENAME. "
            'If more than one --name options is specified, they are treated as "OR", '
            "e.g. find photos matching any FILENAME. ",
        ),
        o(
            "--uuid",
            metavar="UUID",
            default=None,
            multiple=True,
            help="Search for photos with UUID(s). "
            "May be repeated to include multiple UUIDs.",
        ),
        o(
            "--uuid-from-file",
            metavar="FILE",
            default=None,
            multiple=False,
            help="Search for photos with UUID(s) loaded from FILE. "
            "Format is a single UUID per line.  Lines preceded with # are ignored.",
            type=click.Path(exists=True),
        ),
        o(
            "--title",
            metavar="TITLE",
            default=None,
            multiple=True,
            help="Search for TITLE in title of photo.",
        ),
        o("--no-title", is_flag=True, help="Search for photos with no title."),
        o(
            "--description",
            metavar="DESC",
            default=None,
            multiple=True,
            help="Search for DESC in description of photo.",
        ),
        o(
            "--no-description",
            is_flag=True,
            help="Search for photos with no description.",
        ),
        o(
            "--place",
            metavar="PLACE",
            default=None,
            multiple=True,
            help="Search for PLACE in photo's reverse geolocation info",
        ),
        o(
            "--no-place",
            is_flag=True,
            help="Search for photos with no associated place name info (no reverse geolocation info)",
        ),
        o(
            "--location",
            is_flag=True,
            help="Search for photos with associated location info (e.g. GPS coordinates)",
        ),
        o(
            "--no-location",
            is_flag=True,
            help="Search for photos with no associated location info (e.g. no GPS coordinates)",
        ),
        o(
            "--label",
            metavar="LABEL",
            multiple=True,
            help="Search for photos with image classification label LABEL (Photos 5 only). "
            'If more than one label, treated as "OR", e.g. find photos matching any label',
        ),
        o(
            "--uti",
            metavar="UTI",
            default=None,
            multiple=False,
            help="Search for photos whose uniform type identifier (UTI) matches UTI",
        ),
        o(
            "-i",
            "--ignore-case",
            is_flag=True,
            help="Case insensitive search for title, description, place, keyword, person, or album.",
        ),
        o("--edited", is_flag=True, help="Search for photos that have been edited."),
        o(
            "--external-edit",
            is_flag=True,
            help="Search for photos edited in external editor.",
        ),
        o("--favorite", is_flag=True, help="Search for photos marked favorite."),
        o(
            "--not-favorite",
            is_flag=True,
            help="Search for photos not marked favorite.",
        ),
        o("--hidden", is_flag=True, help="Search for photos marked hidden."),
        o("--not-hidden", is_flag=True, help="Search for photos not marked hidden."),
        o(
            "--shared",
            is_flag=True,
            help="Search for photos in shared iCloud album (Photos 5 only).",
        ),
        o(
            "--not-shared",
            is_flag=True,
            help="Search for photos not in shared iCloud album (Photos 5 only).",
        ),
        o(
            "--burst",
            is_flag=True,
            help="Search for photos that were taken in a burst.",
        ),
        o(
            "--not-burst",
            is_flag=True,
            help="Search for photos that are not part of a burst.",
        ),
        o("--live", is_flag=True, help="Search for Apple live photos"),
        o(
            "--not-live",
            is_flag=True,
            help="Search for photos that are not Apple live photos.",
        ),
        o("--portrait", is_flag=True, help="Search for Apple portrait mode photos."),
        o(
            "--not-portrait",
            is_flag=True,
            help="Search for photos that are not Apple portrait mode photos.",
        ),
        o("--screenshot", is_flag=True, help="Search for screenshot photos."),
        o(
            "--not-screenshot",
            is_flag=True,
            help="Search for photos that are not screenshot photos.",
        ),
        o("--slow-mo", is_flag=True, help="Search for slow motion videos."),
        o(
            "--not-slow-mo",
            is_flag=True,
            help="Search for photos that are not slow motion videos.",
        ),
        o("--time-lapse", is_flag=True, help="Search for time lapse videos."),
        o(
            "--not-time-lapse",
            is_flag=True,
            help="Search for photos that are not time lapse videos.",
        ),
        o("--hdr", is_flag=True, help="Search for high dynamic range (HDR) photos."),
        o("--not-hdr", is_flag=True, help="Search for photos that are not HDR photos."),
        o(
            "--selfie",
            is_flag=True,
            help="Search for selfies (photos taken with front-facing cameras).",
        ),
        o("--not-selfie", is_flag=True, help="Search for photos that are not selfies."),
        o("--panorama", is_flag=True, help="Search for panorama photos."),
        o(
            "--not-panorama",
            is_flag=True,
            help="Search for photos that are not panoramas.",
        ),
        o(
            "--has-raw",
            is_flag=True,
            help="Search for photos with both a jpeg and raw version",
        ),
        o(
            "--only-movies",
            is_flag=True,
            help="Search only for movies (default searches both images and movies).",
        ),
        o(
            "--only-photos",
            is_flag=True,
            help="Search only for photos/images (default searches both images and movies).",
        ),
        o(
            "--from-date",
            help="Search by item start date, e.g. 2000-01-12T12:00:00, 2001-01-12T12:00:00-07:00, or 2000-12-31 (ISO 8601 with/without timezone).",
            type=DateTimeISO8601(),
        ),
        o(
            "--to-date",
            help="Search by item end date, e.g. 2000-01-12T12:00:00, 2001-01-12T12:00:00-07:00, or 2000-12-31 (ISO 8601 with/without timezone).",
            type=DateTimeISO8601(),
        ),
        o(
            "--from-time",
            help="Search by item start time of day, e.g. 12:00, or 12:00:00.",
            type=TimeISO8601(),
        ),
        o(
            "--to-time",
            help="Search by item end time of day, e.g. 12:00 or 12:00:00.",
            type=TimeISO8601(),
        ),
        o("--has-comment", is_flag=True, help="Search for photos that have comments."),
        o("--no-comment", is_flag=True, help="Search for photos with no comments."),
        o("--has-likes", is_flag=True, help="Search for photos that have likes."),
        o("--no-likes", is_flag=True, help="Search for photos with no likes."),
        o(
            "--is-reference",
            is_flag=True,
            help="Search for photos that were imported as referenced files (not copied into Photos library).",
        ),
        o(
            "--in-album",
            is_flag=True,
            help="Search for photos that are in one or more albums.",
        ),
        o(
            "--not-in-album",
            is_flag=True,
            help="Search for photos that are not in any albums.",
        ),
        o(
            "--duplicate",
            is_flag=True,
            help="Search for photos with possible duplicates. osxphotos will compare signatures of photos, "
            "evaluating date created, size, height, width, and edited status to find *possible* duplicates. "
            "This does not compare images byte-for-byte nor compare hashes but should find photos imported multiple "
            "times or duplicated within Photos.",
        ),
        o(
            "--min-size",
            metavar="SIZE",
            type=BitMathSize(),
            help="Search for photos with size >= SIZE bytes. "
            "The size evaluated is the photo's original size (when imported to Photos). "
            "Size may be specified as integer bytes or using SI or NIST units. "
            "For example, the following are all valid and equivalent sizes: '1048576' '1.048576MB', '1 MiB'.",
        ),
        o(
            "--max-size",
            metavar="SIZE",
            type=BitMathSize(),
            help="Search for photos with size <= SIZE bytes. "
            "The size evaluated is the photo's original size (when imported to Photos). "
            "Size may be specified as integer bytes or using SI or NIST units. "
            "For example, the following are all valid and equivalent sizes: '1048576' '1.048576MB', '1 MiB'.",
        ),
        o(
            "--regex",
            metavar="REGEX TEMPLATE",
            nargs=2,
            multiple=True,
            help="Search for photos where TEMPLATE matches regular expression REGEX. "
            "For example, to find photos in an album that begins with 'Beach': '--regex \"^Beach\" \"{album}\"'. "
            "You may specify more than one regular expression match by repeating '--regex' with different arguments.",
        ),
        o(
            "--selected",
            is_flag=True,
            help="Filter for photos that are currently selected in Photos.",
        ),
        o(
            "--exif",
            metavar="EXIF_TAG VALUE",
            nargs=2,
            multiple=True,
            help="Search for photos where EXIF_TAG exists in photo's EXIF data and contains VALUE. "
            "For example, to find photos created by Adobe Photoshop: `--exif Software 'Adobe Photoshop' `"
            "or to find all photos shot on a Canon camera: `--exif Make Canon`. "
            "EXIF_TAG can be any valid exiftool tag, with or without group name, e.g. `EXIF:Make` or `Make`. "
            "To use --exif, exiftool must be installed and in the path.",
        ),
        o(
            "--query-eval",
            metavar="CRITERIA",
            multiple=True,
            help="Evaluate CRITERIA to filter photos. "
            "CRITERIA will be evaluated in context of the following python list comprehension: "
            "`photos = [photo for photo in photos if CRITERIA]` "
            "where photo represents a PhotoInfo object. "
            "For example: `--query-eval photo.favorite` returns all photos that have been "
            "favorited and is equivalent to --favorite. "
            "You may specify more than one CRITERIA by using --query-eval multiple times. "
            "CRITERIA must be a valid python expression. "
            "See https://rhettbull.github.io/osxphotos/ for additional documentation on the PhotoInfo class.",
        ),
        o(
            "--query-function",
            metavar="filename.py::function",
            multiple=True,
            type=FunctionCall(),
            help="Run function to filter photos. Use this in format: --query-function filename.py::function where filename.py is a python "
            + "file you've created and function is the name of the function in the python file you want to call. "
            + "Your function will be passed a list of PhotoInfo objects and is expected to return a filtered list of PhotoInfo objects. "
            + "You may use more than one function by repeating the --query-function option with a different value. "
            + "Your query function will be called after all other query options have been evaluated. "
            + "See https://github.com/RhetTbull/osxphotos/blob/master/examples/query_function.py for example of how to use this option.",
        ),
    ]
    for o in options[::-1]:
        f = o(f)
    return f


def DEBUG_OPTIONS(f):
    o = click.option
    options = [
        o(
            "--debug",
            is_flag=True,
            help="Enable debug output.",
            hidden=OSXPHOTOS_HIDDEN,
        ),
        o(
            "--watch",
            metavar="FUNCTION_PATH",
            multiple=True,
            help="Watch function calls.  For example, to watch all calls to FileUtil.copy: "
            "'--watch osxphotos.fileutil.FileUtil.copy'.  More than one --watch option can be specified.",
            hidden=OSXPHOTOS_HIDDEN,
        ),
        o(
            "--breakpoint",
            metavar="FUNCTION_PATH",
            multiple=True,
            help="Add breakpoint to function calls.  For example, to add breakpoint to FileUtil.copy: "
            "'--breakpoint osxphotos.fileutil.FileUtil.copy'.  More than one --breakpoint option can be specified.",
            hidden=OSXPHOTOS_HIDDEN,
        ),
    ]
    for o in options[::-1]:
        f = o(f)
    return f


def load_uuid_from_file(filename):
    """Load UUIDs from file.  Does not validate UUIDs.
        Format is 1 UUID per line, any line beginning with # is ignored.
        Whitespace is stripped.

    Arguments:
        filename: file name of the file containing UUIDs

    Returns:
        list of UUIDs or empty list of no UUIDs in file

    Raises:
        FileNotFoundError if file does not exist
    """

    if not pathlib.Path(filename).is_file():
        raise FileNotFoundError(f"Could not find file {filename}")

    uuid = []
    with open(filename, "r") as uuid_file:
        for line in uuid_file:
            line = line.strip()
            if len(line) and line[0] != "#":
                uuid.append(line)
    return uuid
