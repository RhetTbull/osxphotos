"""Common options & parameters for osxphotos CLI commands"""


from __future__ import annotations

import contextlib
import functools
from textwrap import dedent
from typing import Any, Callable

import click

from ..platform import is_macos
from .common import OSXPHOTOS_HIDDEN, print_version
from .param_types import *

__all__ = [
    "DB_ARGUMENT",
    "DB_OPTION",
    "DEBUG_OPTIONS",
    "DELETED_OPTIONS",
    "FIELD_OPTION",
    "JSON_OPTION",
    "QUERY_OPTIONS",
    "THEME_OPTION",
    "TIMESTAMP_OPTION",
    "VERBOSE_OPTION",
    "VERSION_OPTION",
]


def validate_selected(ctx, param, value):
    """ "Validate photos are actually selected when --selected is used"""

    if not value:
        # --selected not used, just return
        return value

    # imports here to avoid conflict with linux port
    # TODO: fix this once linux port is complete
    import photoscript
    from applescript import ScriptError

    selection = None
    with contextlib.suppress(ScriptError):
        # ScriptError raised if selection made in edit mode or Smart Albums (on older versions of Photos)
        selection = photoscript.PhotosLibrary().selection

    if not selection:
        click.echo(
            dedent(
                """
                --selected option used but no photos selected in Photos.

                To select photos in Photos use one of the following methods:
    
                - Select a single photo: Click the photo, or press the arrow keys to quickly navigate to and select the photo.

                - Select a group of adjacent photos in a day: Click the first photo, then hold down the Shift key while you click the last photo.
                You can also hold down Shift and press the arrow keys, or simply drag to enclose the photos within the selection rectangle.

                - Select photos in a day that are not adjacent to each other: Hold down the Command key as you click each photo.

                - Deselect specific photos: Hold down the Command key and click the photos you want to deselect.

                - Deselect all photos: Click an empty space in the window (not a photo).
            """
            ),
            err=True,
        )
        ctx.exit(1)
    return value


def _param_memo(f: Callable[..., Any], param: click.Parameter) -> None:
    """Add param to the list of params for a click.Command
    This is directly from the click source code and
    the implementation is thus tightly coupled to click internals
    """
    if isinstance(f, click.Command):
        f.params.append(param)
    else:
        if not hasattr(f, "__click_params__"):
            f.__click_params__ = []  # type: ignore

        f.__click_params__.append(param)  # type: ignore


def make_click_option_decorator(*params: click.Parameter) -> Callable[..., Any]:
    """Make a decorator for a click option from one or more click Parameter objects"""

    def decorator(wrapped=None) -> Callable[..., Any]:
        """Function decorator to add option to a click command.

        Args:
            wrapped: function to decorate (this is normally passed automatically
        """

        if wrapped is None:
            return decorator

        def _add_options(wrapped):
            """Add query options to wrapped function"""
            for param in params:
                _param_memo(wrapped, param)
            return wrapped

        return _add_options(wrapped)

    return decorator


VERSION_CHECK_OPTION = click.option("--no-version-check", required=False, is_flag=True)

_DB_PARAMETER = click.Option(
    ["--library", "--db", "db"],
    required=False,
    metavar="PHOTOS_LIBRARY_PATH",
    default=None,
    help=(
        "Specify path to Photos library. "
        "If not provided, will attempt to find the library to use in the following order: "
        "1. last opened library, 2. system library, 3. ~/Pictures/Photos Library.photoslibrary"
    ),
    type=click.Path(exists=True),
)

DB_OPTION = make_click_option_decorator(_DB_PARAMETER)

DB_ARGUMENT = click.argument(
    "photos_library",
    nargs=-1,
    type=DeprecatedPath(
        exists=True,
        deprecation_warning="The PHOTOS_LIBRARY argument is deprecated and "
        "will be removed in a future version of osxphotos. "
        "Use --library instead to specify the Photos Library path.",
    ),
)

_JSON_PARAMETER = click.Option(
    ["--json", "json_"],
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format.",
)

JSON_OPTION = make_click_option_decorator(_JSON_PARAMETER)

_FIELD_PARAMETER = click.Option(
    ["--field", "-f"],
    metavar="FIELD TEMPLATE",
    multiple=True,
    nargs=2,
    help="Output only specified custom fields. "
    "FIELD is the name of the field and TEMPLATE is the template to use as the field value. "
    "May be repeated to output multiple fields. "
    "For example, to output photo uuid, name, and title: "
    '`--field uuid "{uuid}" --field name "{original_name}" --field title "{title}"`.',
)

FIELD_OPTION = make_click_option_decorator(_FIELD_PARAMETER)

_DELETED_PARAMETERS = [
    click.Option(
        ["--deleted"],
        is_flag=True,
        help="Include photos from the 'Recently Deleted' folder.",
    ),
    click.Option(
        ["--deleted-only"],
        is_flag=True,
        help="Include only photos from the 'Recently Deleted' folder.",
    ),
]

DELETED_OPTIONS = make_click_option_decorator(*_DELETED_PARAMETERS)

# The following are used by the query command and by
# QUERY_OPTIONS to add the query options to other commands
# To add new query options, add them to _QUERY_OPTIONS as
# a click.Option, add them to osxphotos/photosdb/photosdb.py::PhotosDB.query(),
# and to osxphotos/query_options.py::QueryOptions
_QUERY_PARAMETERS_DICT = {
    "--keyword": click.Option(
        ["--keyword"],
        metavar="KEYWORD",
        default=None,
        multiple=True,
        help="Search for photos with keyword KEYWORD. "
        'If more than one keyword, treated as "OR", e.g. find photos matching any keyword',
    ),
    "--no-keyword": click.Option(
        ["--no-keyword"],
        is_flag=True,
        help="Search for photos with no keyword.",
    ),
    "--person": click.Option(
        ["--person"],
        metavar="PERSON",
        default=None,
        multiple=True,
        help="Search for photos with person PERSON. "
        'If more than one person, treated as "OR", e.g. find photos matching any person',
    ),
    "--album": click.Option(
        ["--album"],
        metavar="ALBUM",
        default=None,
        multiple=True,
        help="Search for photos in album ALBUM. "
        'If more than one album, treated as "OR", e.g. find photos matching any album',
    ),
    "--folder": click.Option(
        ["--folder"],
        metavar="FOLDER",
        default=None,
        multiple=True,
        help="Search for photos in an album in folder FOLDER. "
        'If more than one folder, treated as "OR", e.g. find photos in any FOLDER.  '
        "Only searches top level folders (e.g. does not look at subfolders)",
    ),
    "--name": click.Option(
        ["--name"],
        metavar="FILENAME",
        default=None,
        multiple=True,
        help="Search for photos with filename matching FILENAME. "
        'If more than one --name options is specified, they are treated as "OR", '
        "e.g. find photos matching any FILENAME. ",
    ),
    "--uuid": click.Option(
        ["--uuid"],
        metavar="UUID",
        default=None,
        multiple=True,
        help="Search for photos with UUID(s). "
        "May be repeated to include multiple UUIDs.",
    ),
    "--uuid-from-file": click.Option(
        ["--uuid-from-file"],
        metavar="FILE",
        default=None,
        multiple=False,
        help="Search for photos with UUID(s) loaded from FILE. "
        "Format is a single UUID per line. Lines preceded with # are ignored. "
        "If FILE is '-', read UUIDs from stdin.",
        type=PathOrStdin(exists=True),
    ),
    "--title": click.Option(
        ["--title"],
        metavar="TITLE",
        default=None,
        multiple=True,
        help="Search for TITLE in title of photo.",
    ),
    "--no-title": click.Option(
        ["--no-title"], is_flag=True, help="Search for photos with no title."
    ),
    "--description": click.Option(
        ["--description"],
        metavar="DESC",
        default=None,
        multiple=True,
        help="Search for DESC in description of photo.",
    ),
    "--no-description": click.Option(
        ["--no-description"],
        is_flag=True,
        help="Search for photos with no description.",
    ),
    "--place": click.Option(
        ["--place"],
        metavar="PLACE",
        default=None,
        multiple=True,
        help="Search for PLACE in photo's reverse geolocation info",
    ),
    "--no-place": click.Option(
        ["--no-place"],
        is_flag=True,
        help="Search for photos with no associated place name info (no reverse geolocation info)",
    ),
    "--location": click.Option(
        ["--location"],
        is_flag=True,
        help="Search for photos with associated location info (e.g. GPS coordinates)",
    ),
    "--no-location": click.Option(
        ["--no-location"],
        is_flag=True,
        help="Search for photos with no associated location info (e.g. no GPS coordinates)",
    ),
    "--label": click.Option(
        ["--label"],
        metavar="LABEL",
        multiple=True,
        help="Search for photos with image classification label LABEL (Photos 5+ only). "
        'If more than one label, treated as "OR", e.g. find photos matching any label',
    ),
    "--uti": click.Option(
        ["--uti"],
        metavar="UTI",
        default=None,
        multiple=False,
        help="Search for photos whose uniform type identifier (UTI) matches UTI",
    ),
    "--ignore_case": click.Option(
        ["-i", "--ignore-case"],
        is_flag=True,
        help="Case insensitive search for title, description, place, keyword, person, or album.",
    ),
    "--edited": click.Option(
        ["--edited"],
        is_flag=True,
        help="Search for photos that have been edited.",
    ),
    "--not-edited": click.Option(
        ["--not-edited"],
        is_flag=True,
        help="Search for photos that have not been edited.",
    ),
    "--external-edit": click.Option(
        ["--external-edit"],
        is_flag=True,
        help="Search for photos edited in external editor.",
    ),
    "--favorite": click.Option(
        ["--favorite"], is_flag=True, help="Search for photos marked favorite."
    ),
    "--not-favorite": click.Option(
        ["--not-favorite"],
        is_flag=True,
        help="Search for photos not marked favorite.",
    ),
    "--hidden": click.Option(
        ["--hidden"], is_flag=True, help="Search for photos marked hidden."
    ),
    "--not-hidden": click.Option(
        ["--not-hidden"],
        is_flag=True,
        help="Search for photos not marked hidden.",
    ),
    "--shared": click.Option(
        ["--shared"],
        is_flag=True,
        help="Search for photos in shared iCloud album (Photos 5+ only).",
    ),
    "--not-shared": click.Option(
        ["--not-shared"],
        is_flag=True,
        help="Search for photos not in shared iCloud album (Photos 5+ only).",
    ),
    "--burst": click.Option(
        ["--burst"],
        is_flag=True,
        help="Search for photos that were taken in a burst.",
    ),
    "--not-burst": click.Option(
        ["--not-burst"],
        is_flag=True,
        help="Search for photos that are not part of a burst.",
    ),
    "--live": click.Option(
        ["--live"], is_flag=True, help="Search for Apple live photos"
    ),
    "--not-live": click.Option(
        ["--not-live"],
        is_flag=True,
        help="Search for photos that are not Apple live photos.",
    ),
    "--portrait": click.Option(
        ["--portrait"],
        is_flag=True,
        help="Search for Apple portrait mode photos.",
    ),
    "--not-portrait": click.Option(
        ["--not-portrait"],
        is_flag=True,
        help="Search for photos that are not Apple portrait mode photos.",
    ),
    "--screenshot": click.Option(
        ["--screenshot"], is_flag=True, help="Search for screenshot photos."
    ),
    "--not-screenshot": click.Option(
        ["--not-screenshot"],
        is_flag=True,
        help="Search for photos that are not screenshot photos.",
    ),
    "--slow-mo": click.Option(
        ["--slow-mo"], is_flag=True, help="Search for slow motion videos."
    ),
    "--not-slow-mo": click.Option(
        ["--not-slow-mo"],
        is_flag=True,
        help="Search for photos that are not slow motion videos.",
    ),
    "--time-lapse": click.Option(
        ["--time-lapse"], is_flag=True, help="Search for time lapse videos."
    ),
    "--not-time-lapse": click.Option(
        ["--not-time-lapse"],
        is_flag=True,
        help="Search for photos that are not time lapse videos.",
    ),
    "--hdr": click.Option(
        ["--hdr"],
        is_flag=True,
        help="Search for high dynamic range (HDR) photos.",
    ),
    "--not-hdr": click.Option(
        ["--not-hdr"],
        is_flag=True,
        help="Search for photos that are not HDR photos.",
    ),
    "--selfie": click.Option(
        ["--selfie"],
        is_flag=True,
        help="Search for selfies (photos taken with front-facing cameras).",
    ),
    "--not-selfie": click.Option(
        ["--not-selfie"],
        is_flag=True,
        help="Search for photos that are not selfies.",
    ),
    "--panorama": click.Option(
        ["--panorama"], is_flag=True, help="Search for panorama photos."
    ),
    "--not-panorama": click.Option(
        ["--not-panorama"],
        is_flag=True,
        help="Search for photos that are not panoramas.",
    ),
    "--has-raw": click.Option(
        ["--has-raw"],
        is_flag=True,
        help="Search for photos with both a jpeg and raw version",
    ),
    "--only-movies": click.Option(
        ["--only-movies"],
        is_flag=True,
        help="Search only for movies (default searches both images and movies).",
    ),
    "--only-photos": click.Option(
        ["--only-photos"],
        is_flag=True,
        help="Search only for photos/images (default searches both images and movies).",
    ),
    "--from-date": click.Option(
        ["--from-date"],
        metavar="DATE",
        help="Search for items created on or after DATE, e.g. 2000-01-12T12:00:00, 2001-01-12T12:00:00-07:00, or 2000-12-31 (ISO 8601 with/without timezone).",
        type=DateTimeISO8601(),
    ),
    "--to-date": click.Option(
        ["--to-date"],
        metavar="DATE",
        help="Search for items created before DATE, e.g. 2000-01-12T12:00:00, 2001-01-12T12:00:00-07:00, or 2000-12-31 (ISO 8601 with/without timezone).",
        type=DateTimeISO8601(),
    ),
    "--from-time": click.Option(
        ["--from-time"],
        metavar="TIME",
        help="Search for items created on or after TIME of day, e.g. 12:00, or 12:00:00.",
        type=TimeISO8601(),
    ),
    "--to-time": click.Option(
        ["--to-time"],
        help="Search for items created before TIME of day, e.g. 12:00 or 12:00:00.",
        type=TimeISO8601(),
    ),
    "--year": click.Option(
        ["--year"],
        metavar="YEAR",
        help="Search for items from a specific year, e.g. --year 2022 to find all photos from the year 2022. "
        "May be repeated to search multiple years.",
        multiple=True,
        type=int,
    ),
    "--added-before": click.Option(
        ["--added-before"],
        metavar="DATE",
        help="Search for items added to the library before a specific date/time, "
        "e.g. --added-before e.g. 2000-01-12T12:00:00, 2001-01-12T12:00:00-07:00, or 2000-12-31 (ISO 8601 with/without timezone).",
        type=DateTimeISO8601(),
    ),
    "--added-after": click.Option(
        ["--added-after"],
        metavar="DATE",
        help="Search for items added to the library on or after a specific date/time, "
        "e.g. --added-after e.g. 2000-01-12T12:00:00, 2001-01-12T12:00:00-07:00, or 2000-12-31 (ISO 8601 with/without timezone).",
        type=DateTimeISO8601(),
    ),
    "--added-in-last": click.Option(
        ["--added-in-last"],
        metavar="TIME_DELTA",
        help="Search for items added to the library in the last TIME_DELTA, "
        "where TIME_DELTA is a string like "
        "'12 hrs', '1 day', '1d', '1 week', '2weeks', '1 month', '1 year'. "
        "for example, `--added-in-last 7d` and `--added-in-last '1 week'` are equivalent. "
        "months are assumed to be 30 days and years are assumed to be 365 days. "
        "Common English abbreviations are accepted, e.g. d, day, days or m, min, minutes.",
        type=TimeOffset(),
    ),
    "--has-comment": click.Option(
        ["--has-comment"],
        is_flag=True,
        help="Search for photos that have comments.",
    ),
    "--no-comment": click.Option(
        ["--no-comment"],
        is_flag=True,
        help="Search for photos with no comments.",
    ),
    "--has-likes": click.Option(
        ["--has-likes"], is_flag=True, help="Search for photos that have likes."
    ),
    "--no-likes": click.Option(
        ["--no-likes"], is_flag=True, help="Search for photos with no likes."
    ),
    "--is-reference": click.Option(
        ["--is-reference"],
        is_flag=True,
        help="Search for photos that were imported as referenced files (not copied into Photos library).",
    ),
    "--not-reference": click.Option(
        ["--not-reference"],
        is_flag=True,
        help="Search for photos that are not references, that is, they were copied into the Photos library "
        "and are managed by Photos.",
    ),
    "--in-album": click.Option(
        ["--in-album"],
        is_flag=True,
        help="Search for photos that are in one or more albums.",
    ),
    "--not-in-album": click.Option(
        ["--not-in-album"],
        is_flag=True,
        help="Search for photos that are not in any albums.",
    ),
    "--duplicate": click.Option(
        ["--duplicate"],
        is_flag=True,
        help="Search for photos with possible duplicates. osxphotos will compare signatures of photos, "
        "evaluating date created, size, height, width, and edited status to find *possible* duplicates. "
        "This does not compare images byte-for-byte nor compare hashes but should find photos imported multiple "
        "times or duplicated within Photos.",
    ),
    "--min-size": click.Option(
        ["--min-size"],
        metavar="SIZE",
        type=BitMathSize(),
        help="Search for photos with size >= SIZE bytes. "
        "The size evaluated is the photo's original size (when imported to Photos). "
        "Size may be specified as integer bytes or using SI or NIST units. "
        "For example, the following are all valid and equivalent sizes: '1048576' '1.048576MB', '1 MiB'.",
    ),
    "--max-size": click.Option(
        ["--max-size"],
        metavar="SIZE",
        type=BitMathSize(),
        help="Search for photos with size <= SIZE bytes. "
        "The size evaluated is the photo's original size (when imported to Photos). "
        "Size may be specified as integer bytes or using SI or NIST units. "
        "For example, the following are all valid and equivalent sizes: '1048576' '1.048576MB', '1 MiB'.",
    ),
    "--missing": click.Option(
        ["--missing"], is_flag=True, help="Search for photos missing from disk."
    ),
    "--not-missing": click.Option(
        ["--not-missing"],
        is_flag=True,
        help="Search for photos present on disk (e.g. not missing).",
    ),
    "--cloudasset": click.Option(
        ["--cloudasset"],
        is_flag=True,
        help="Search for photos that are part of an iCloud library",
    ),
    "--not-cloudasset": click.Option(
        ["--not-cloudasset"],
        is_flag=True,
        help="Search for photos that are not part of an iCloud library",
    ),
    "--incloud": click.Option(
        ["--incloud"],
        is_flag=True,
        help="Search for photos that are in iCloud (have been synched)",
    ),
    "--not-incloud": click.Option(
        ["--not-incloud"],
        is_flag=True,
        help="Search for photos that are not in iCloud (have not been synched)",
    ),
    "--syndicated": click.Option(
        ["--syndicated"],
        is_flag=True,
        help="Search for photos that have been shared via syndication ('Shared with You' album via Messages, etc.)",
    ),
    "--not-syndicated": click.Option(
        ["--not-syndicated"],
        is_flag=True,
        help="Search for photos that have not been shared via syndication ('Shared with You' album via Messages, etc.)",
    ),
    "--saved-to-library": click.Option(
        ["--saved-to-library"],
        is_flag=True,
        help="Search for syndicated photos that have saved to the library",
    ),
    "--not-saved-to-library": click.Option(
        ["--not-saved-to-library"],
        is_flag=True,
        help="Search for syndicated photos that have not saved to the library",
    ),
    "--shared-moment": click.Option(
        ["--shared-moment"],
        is_flag=True,
        help="Search for photos that are part of a shared moment",
    ),
    "--not-shared-moment": click.Option(
        ["--not-shared-moment"],
        is_flag=True,
        help="Search for photos that are not part of a shared moment",
    ),
    "--shared-library": click.Option(
        ["--shared-library"],
        is_flag=True,
        help="Search for photos that are part of a shared library",
    ),
    "--not-shared-library": click.Option(
        ["--not-shared-library"],
        is_flag=True,
        help="Search for photos that are not part of a shared library",
    ),
    "--regex": click.Option(
        ["--regex"],
        metavar="REGEX TEMPLATE",
        nargs=2,
        multiple=True,
        help="Search for photos where TEMPLATE matches regular expression REGEX. "
        "For example, to find photos in an album that begins with 'Beach': '--regex \"^Beach\" \"{album}\"'. "
        "You may specify more than one regular expression match by repeating '--regex' with different arguments.",
    ),
    "--selected": click.Option(
        ["--selected"],
        is_flag=True,
        help="Filter for photos that are currently selected in Photos.",
        callback=validate_selected,
    ),
    "--exif": click.Option(
        ["--exif"],
        metavar="EXIF_TAG VALUE",
        nargs=2,
        multiple=True,
        help="Search for photos where EXIF_TAG exists in photo's EXIF data and contains VALUE. "
        "For example, to find photos created by Adobe Photoshop: `--exif Software 'Adobe Photoshop' `"
        "or to find all photos shot on a Canon camera: `--exif Make Canon`. "
        "EXIF_TAG can be any valid exiftool tag, with or without group name, e.g. `EXIF:Make` or `Make`. "
        "To use --exif, exiftool must be installed and in the path.",
    ),
    "--query-eval": click.Option(
        ["--query-eval"],
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
    "--query-function": click.Option(
        ["--query-function"],
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
}

if not is_macos:
    del _QUERY_PARAMETERS_DICT["--selected"]


def QUERY_OPTIONS(
    wrapped=None, *, exclude: list[str] | None = None
) -> Callable[..., Any]:
    """Function decorator to add query options to a click command.

    Args:
        wrapped: function to decorate (this is normally passed automatically
        exclude: list of query options to exclude from the command, for example `exclude=["--shared"]
    """
    if wrapped is None:
        return functools.partial(QUERY_OPTIONS, exclude=exclude)

    exclude = exclude or []

    def _add_options(wrapped):
        """Add query options to wrapped function"""
        for option in reversed(_QUERY_PARAMETERS_DICT.keys()):
            if option in exclude:
                continue
            click_opt = _QUERY_PARAMETERS_DICT[option]
            _param_memo(wrapped, click_opt)
        return wrapped

    return _add_options(wrapped)


_DEBUG_PARAMETERS = [
    click.Option(
        ["--debug"],
        is_flag=True,
        help="Enable debug output.",
        hidden=OSXPHOTOS_HIDDEN,
    ),
    click.Option(
        ["--watch"],
        metavar="MODULE::NAME",
        multiple=True,
        help="Watch function or method calls. The function to watch must be in the form "
        "MODULE::NAME where MODULE is the module path and NAME is the function or method name "
        "contained in the module. For example, to watch all calls to FileUtil.copy() which is in "
        "osxphotos.fileutil, use: "
        "'--watch osxphotos.fileutil::FileUtil.copy'.  More than one --watch option can be specified.",
        hidden=OSXPHOTOS_HIDDEN,
    ),
    click.Option(
        ["--breakpoint"],
        metavar="MODULE::NAME",
        multiple=True,
        help="Add breakpoint to function calls. The function to watch must be in the form "
        "MODULE::NAME where MODULE is the module path and NAME is the function or method name "
        "contained in the module. For example, to set a breakpoint for calls to "
        "FileUtil.copy() which is in osxphotos.fileutil, use: "
        "'--breakpoint osxphotos.fileutil::FileUtil.copy'.  More than one --breakpoint option can be specified.",
        hidden=OSXPHOTOS_HIDDEN,
    ),
]
DEBUG_OPTIONS = make_click_option_decorator(*_DEBUG_PARAMETERS)

_THEME_PARAMETER = click.Option(
    ["--theme"],
    metavar="THEME",
    type=click.Choice(["dark", "light", "mono", "plain"], case_sensitive=False),
    help="Specify the color theme to use for output. "
    "Valid themes are 'dark', 'light', 'mono', and 'plain'. "
    "Defaults to 'dark' or 'light' depending on system dark mode setting.",
)
THEME_OPTION = make_click_option_decorator(_THEME_PARAMETER)

_VERBOSE_PARAMETER = click.Option(
    ["--verbose", "-V", "verbose_flag"],
    count=True,
    help="Print verbose output; may be specified multiple times for more verbose output.",
)
VERBOSE_OPTION = make_click_option_decorator(_VERBOSE_PARAMETER)

_TIMESTAMP_PARAMETER = click.Option(
    ["--timestamp"], is_flag=True, help="Add time stamp to verbose output"
)
TIMESTAMP_OPTION = make_click_option_decorator(_TIMESTAMP_PARAMETER)

_VERSION_PARAMETER = click.Option(
    ["--version", "-v", "_version_flag"],
    is_flag=True,
    help="Show the version and exit.",
    callback=print_version,
)

VERSION_OPTION = make_click_option_decorator(_VERSION_PARAMETER)
