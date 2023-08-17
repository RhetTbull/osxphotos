""" Fix time / date / timezone for photos in Apple Photos """

from __future__ import annotations

import sys
from functools import partial
from textwrap import dedent

import click
from rich.console import Console

from osxphotos._constants import APP_NAME
from osxphotos._version import __version__
from osxphotos.compare_exif import PhotoCompare
from osxphotos.crash_reporter import crash_reporter, set_crash_data
from osxphotos.datetime_utils import datetime_naive_to_local, datetime_to_new_tz
from osxphotos.exif_datetime_updater import ExifDateTimeUpdater
from osxphotos.exiftool import get_exiftool_path
from osxphotos.photodates import (
    get_photo_date_added,
    set_photo_date_added,
    set_photo_date_from_filename,
    update_photo_date_time,
    update_photo_from_function,
    update_photo_time_for_new_timezone,
)
from osxphotos.phototz import PhotoTimeZone, PhotoTimeZoneUpdater
from osxphotos.platform import assert_macos
from osxphotos.utils import noop, pluralize

assert_macos()

from photoscript import PhotosLibrary

from osxphotos.photosalbum import PhotosAlbumPhotoScript

from .cli_params import THEME_OPTION, TIMESTAMP_OPTION, VERBOSE_OPTION
from .click_rich_echo import rich_click_echo as echo
from .click_rich_echo import rich_echo_error as echo_error
from .color_themes import get_theme
from .common import OSXPHOTOS_CRASH_LOG
from .darkmode import is_dark_mode
from .help import HELP_WIDTH, rich_text
from .param_types import (
    DateOffset,
    DateTimeISO8601,
    FunctionCall,
    StrpDateTimePattern,
    TimeOffset,
    TimeString,
    UTCOffset,
)
from .rich_progress import rich_progress
from .verbose import get_verbose_console, verbose_print

# format for pretty printing date/times
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"


class TimeWarpCommand(click.Command):
    """Custom click.Command that overrides get_help() to show additional help info for export"""

    def get_help(self, ctx):
        help_text = super().get_help(ctx)
        formatter = click.HelpFormatter(width=HELP_WIDTH)
        formatter.write("\n\n")
        formatter.write(
            rich_text(
                dedent(
                    """
# Timewarp Overview

Timewarp operates on photos selected in Apple Photos.  To use it, open Photos, select the photos for which you'd like to adjust the date/time/timezone, then run osxphotos timewarp from the command line:

`osxphotos timewarp --date 2021-09-10 --time-delta "-1 hour" --timezone -0700 --verbose`

This example sets the date for all selected photos to `2021-09-10`, subtracts 1 hour from the time of each photo, and sets the timezone of each photo to `GMT -07:00` (Pacific Daylight Time).

osxphotos timewarp has been well tested on macOS Catalina (10.15).  It should work on macOS Big Sur (11.0) and macOS Monterey (12.0) but I have not been able to test this.  It will not work on macOS Mojave (10.14) or earlier as the Photos database format is different.

**Caution**: This app directly modifies your Photos library database using undocumented features.  It may corrupt, damage, or destroy your Photos library.  Use at your own caution.  I strongly recommend you make a backup of your Photos library before using this script (e.g. use Time Machine).

## Examples 

**Add 1 day to the date of each photo**

`osxphotos timewarp --date-delta 1`

or

`osxphotos timewarp --date-delta "+1 day"`

**Set the date of each photo to 23 April 2020 and add 3 hours to the time**

`osxphotos timewarp --date 2020-04-23 --time-delta "+3 hours"`

or

`osxphotos timewarp --date 2020-04-23 --time-delta "+03:00:00"`

**Set the time of each photo to 14:30 and set the timezone to UTC +1:00 (Central European Time)**

`osxphotos timewarp --time 14:30 --timezone +01:00`

or

`osxphotos timewarp --time 14:30 --timezone +0100`

**Subtract 1 week from the date for each photo, add 3 hours to the time, set the timezone to UTC -07:00 (Pacific Daylight Time) and also use exiftool to update the EXIF metadata accordingly in the original file; use --verbose to print additional details**

`osxphotos timewarp --date-delta "-1 week" --time-delta "+3 hours" --timezone -0700 --push-exif --verbose`

For this to work, you'll need to install the third-party exiftool (https://exiftool.org/) utility.  If you use  homebrew (https://brew.sh/) you can do this with `brew install exiftool`.

**Set the timezone to UTC +03:00 for each photo but keep the time the same (that is, don't adjust time for the new timezone)**

`osxphotos timewarp --timezone 0300 --match-time`

*Note on timezones and times*: In Photos, when you change the timezone, Photos assumes the time itself was correct for the previous timezone and adjusts the time accordingly to the new timezone.  E.g. if the photo's time is `13:00` and the timezone is `GMT -07:00` and you adjust the timezone one hour east to `GMT -06:00`, Photos will change the time of the photo to `14:00`.  osxphotos timewarp follows this behavior.  Using `--match-time` allows you to adjust the timezone but keep the same time without adjustment. For example, if your camera clock was correct but lacked timezone information and you took photos in one timezone but imported them to photos in another, Photos will add the timezone of the computer at time of import.  You can use osxphotos timewarp to adjust the timezone but keep the time using `--match-time`.

**Update the date the photos were added to Photos**

`osxphotos timewarp --date-added 2021-09-10`

**Update the date the photos were added to Photos to match the date of the photo**

`osxphotos timewarp --date-added-from-photo`

**Compare the date/time/timezone of selected photos with the date/time/timezone in the photos' original EXIF metadata**

`osxphotos timewarp --compare-exif`

**Read the date/time/timezone from the photos' original EXIF metadata to update the photos' date/time/timezone; 
if the EXIF data is missing, use the file modification date/time; show verbose output**

`osxphotos timewarp --pull-exif --use-file-time --verbose`

## Parsing Dates/Times from Filenames

The --parse-date option allows you to parse dates/times from the original filename of the photo.
This is useful if you files with dates/times embedded in the filename but not in the metadata.


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


"""  # noqa: E501
                ),
                width=formatter.width,
                markdown=True,
            )
        )
        help_text += formatter.getvalue()
        return help_text


@click.command(cls=TimeWarpCommand, name="timewarp")
@click.option(
    "--date",
    "-d",
    metavar="DATE",
    type=DateTimeISO8601(),
    help="Set date for selected photos. Format is 'YYYY-MM-DD'.",
)
@click.option(
    "--date-delta",
    "-D",
    metavar="DELTA",
    type=DateOffset(),
    help="Adjust date for selected photos by DELTA. "
    "Format is one of: '±D days', '±W weeks', '±D' where D is days",
)
@click.option(
    "--time",
    "-t",
    metavar="TIME",
    type=TimeString(),
    help="Set time for selected photos. Format is one of 'HH:MM:SS', 'HH:MM:SS.fff', 'HH:MM'.",
)
@click.option(
    "--time-delta",
    "-T",
    metavar="DELTA",
    type=TimeOffset(),
    help="Adjust time for selected photos by DELTA time. "
    "Format is one of '±HH:MM:SS', '±H hours' (or hr), '±M minutes' (or min), '±S seconds' (or sec), '±S' (where S is seconds)",
)
@click.option(
    "--timezone",
    "-z",
    metavar="TIMEZONE",
    type=UTCOffset(),
    help="Set timezone for selected photos as offset from UTC. "
    "Format is one of '±HH:MM', '±H:MM', or '±HHMM'. "
    "The actual time of the photo is not adjusted which means, somewhat counterintuitively, "
    "that the time in the new timezone will be different. "
    "For example, if photo has time of 12:00 and timezone of GMT+01:00 and new timezone is specified as "
    "'--timezone +02:00' (one hour ahead of current GMT+01:00 timezone), the photo's new time will be 13:00 GMT+02:00, "
    "which is equivalent to the old time of 12:00+01:00. "
    "This is the same behavior exhibited by Photos when manually adjusting timezone in the Get Info window. "
    "See also --match-time. ",
)
@click.option(
    "--date-added",
    metavar="DATE",
    type=DateTimeISO8601(),
    help="Set date/time added for selected photos. "
    "This changes the date added or imported date in Photos but "
    "does not change the date/time/timezone of the photo itself. "
    "This is useful for removing photos from the Recents album, "
    "for example if you have imported old scanned photos. "
    "Format is 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'. "
    "If time is not included, midnight is assumed.",
)
@click.option(
    "--date-added-from-photo",
    is_flag=True,
    help="Set date/time added for selected photos to the date/time the photo was taken. "
    "This changes the date added or imported date in Photos but "
    "does not change the date/time/timezone of the photo itself. ",
)
@click.option(
    "--inspect",
    "-i",
    is_flag=True,
    help="Print out the date/time/timezone for each selected photo without changing any information.",
)
@click.option(
    "--compare-exif",
    "-c",
    is_flag=True,
    help="Compare the EXIF date/time/timezone for each selected photo to the same data in Photos. "
    "Requires the third-party exiftool utility be installed (see https://exiftool.org/). "
    "See also --add-to-album.",
)
@click.option(
    "--push-exif",
    "-p",
    is_flag=True,
    help="Push date/time and timezone for selected photos from Photos to the "
    "EXIF metadata in the original file in the Photos library. "
    "Requires the third-party exiftool utility be installed (see https://exiftool.org/). "
    "Using this option modifies the *original* file of the image in your Photos library. "
    "--push-exif will be executed after any other updates are performed on the photo. "
    "Note that if the Photos library is synced to iCloud, the updated EXIF data will not be"
    "synced to iCloud and thus exporting the photo on any other device will not show the updated EXIF data. "
    "This option is most useful for libraries that are not synced to iCloud. "
    "See also --pull-exif.",
)
@click.option(
    "--pull-exif",
    "-P",
    is_flag=True,
    help="Pull date/time and timezone for selected photos from EXIF metadata in the original file "
    "into Photos and update the associated data in Photos to match the EXIF data. "
    "--pull-exif will be executed before any other updates are performed on the photo. "
    "It is possible for images to have missing EXIF data, for example the date/time could be set but there might be "
    "no timezone set in the EXIF metadata. "
    "Missing data will be handled thusly: if date/time/timezone are all present in the EXIF data, "
    "the photo's date/time/timezone will be updated. If timezone is missing but date/time is present, "
    "only the photo's date/time will be updated.  If date/time is missing but the timezone is present, only the "
    "photo's timezone will be updated unless --use-file-time is set in which case, "
    "the photo's file modification date/time will be used in place of EXIF date/time. "
    "If the date is present but the time is missing, the time will be set to 00:00:00. "
    "Requires the third-party exiftool utility be installed (see https://exiftool.org/). "
    "See also --push-exif.",
)
@click.option(
    "--parse-date",
    "-M",
    metavar="DATE_PATTERN",
    type=StrpDateTimePattern(),
    help="Parse date from filename using DATE_PATTERN and set photo's date to match. "
    "If file does not match DATE_PATTERN, the date will not be changed. "
    "DATE_PATTERN is a strptime-compatible pattern with extensions as pattern described below. "
    "If DATE_PATTERN matches time zone information, the photo's timezone will be set to match. "
    "For example, if your photos are named 'IMG_1234_2022_11_23_12_34_56.jpg' where the date/time is "
    "'2022-11-23 12:34:56', you could use the pattern '%Y_%m_%d_%H_%M_%S' or "
    "'IMG_*_%Y_%m_%d_%H_%M_%S' to further narrow the pattern to only match files with 'IMG_xxxx_' in the name.",
)
@click.option(
    "--function",
    "-F",
    metavar="filename.py::function",
    nargs=1,
    type=FunctionCall(),
    multiple=False,
    help="Run python function to determine the date/time/timezone to apply to a photo. "
    "Use this in format: --function filename.py::function where filename.py is a python "
    "file you've created and function is the name of the function in the python file you want to call.  The function will be "
    "passed information about the photo being processed and is expected to return "
    "a naive datetime.datetime object with time in local time and UTC timezone offset in seconds. "
    "See example function at https://github.com/RhetTbull/osxphotos/blob/master/examples/timewarp_function_example.py",
)
@click.option(
    "--match-time",
    "-m",
    is_flag=True,
    help="When used with --timezone, adjusts the photo time so that the timestamp in the new timezone matches "
    "the timestamp in the old timezone. "
    "For example, if photo has time of 12:00 and timezone of GMT+01:00 and new timezone is specified as "
    "'--timezone +02:00' (one hour ahead of current GMT+01:00 timezone), the photo's new time will be 12:00 GMT+02:00. "
    "That is, the timezone will have changed but the timestamp of the photo will match the previous timestamp. "
    "Use --match-time when the camera's time was correct for the time the photo was taken but the "
    "timezone was missing or wrong and you want to adjust the timezone while preserving the photo's time. "
    "See also --timezone.",
)
@click.option(
    "--use-file-time",
    "-f",
    is_flag=True,
    help="When used with --pull-exif, the file modification date/time will be used if date/time "
    "is missing from the EXIF data. ",
)
@click.option(
    "--add-to-album",
    "-a",
    metavar="ALBUM",
    help="When used with --compare-exif, adds any photos with date/time/timezone differences "
    "between Photos/EXIF to album ALBUM.  If ALBUM does not exist, it will be created.",
)
@VERBOSE_OPTION
@TIMESTAMP_OPTION
@click.option(
    "--library",
    "-L",
    metavar="PHOTOS_LIBRARY_PATH",
    type=click.Path(),
    help=r"Path to Photos library (e.g. '~/Pictures/Photos\ Library.photoslibrary'). "
    f"This is not likely needed as {APP_NAME} will usually be able to locate the path to the open Photos library. "
    "Use --library only if you get an error that the Photos library cannot be located.",
)
@click.option(
    "--exiftool-path",
    "-e",
    type=click.Path(exists=True),
    help="Optional path to exiftool executable (will look in $PATH if not specified) for those options which require exiftool.",
)
@click.option("--timestamp", is_flag=True, help="Add time stamp to verbose output")
@THEME_OPTION
@click.option(
    "--plain",
    is_flag=True,
    help="Plain text mode.  Do not use rich output.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Bypass confirmation prompt.  Use with caution.",
)
@crash_reporter(
    OSXPHOTOS_CRASH_LOG,
    "[red]Something went wrong and osxphotos encountered an error:[/red]",
    "osxphotos crash log",
    "Please file a bug report at https://github.com/RhetTbull/osxphotos/issues with the crash log attached.",
    f"osxphotos version: {__version__}",
)
def timewarp(
    date,
    date_delta,
    time,
    time_delta,
    timezone,
    date_added,
    date_added_from_photo,
    inspect,
    compare_exif,
    push_exif,
    pull_exif,
    function,
    match_time,
    use_file_time,
    add_to_album,
    exiftool_path,
    verbose_flag,
    library,
    theme,
    parse_date,
    plain,
    timestamp,
    force,
):
    """Adjust date/time/timezone of photos in Apple Photos.

    Changes will be applied to all photos currently selected in Photos.
    timewarp cannot operate on photos selected in a Smart Album;
    select photos in a regular album or in the 'All Photos' view.
    See Timewarp Overview below for additional information.
    """

    set_crash_data("locals", locals())

    # check constraints
    if not any(
        [
            compare_exif,
            date_added_from_photo,
            date_added,
            date_delta,
            date,
            function,
            inspect,
            parse_date,
            pull_exif,
            push_exif,
            time_delta,
            time,
            timezone,
        ]
    ):
        raise click.UsageError(
            "At least one of --date, --date-delta, --time, --time-delta, "
            "--timezone, --inspect, --compare-exif, --push-exif, --pull-exif, "
            "--parse-date, --function, --date-added, or --date-added-from-photo "
            "must be specified."
        )

    if date and date_delta:
        raise click.UsageError("--date and --date-delta are mutually exclusive.")

    if time and time_delta:
        raise click.UsageError("--time and --time-delta are mutually exclusive.")

    if match_time and not timezone:
        raise click.UsageError("--match-time must be used with --timezone.")

    if add_to_album and not compare_exif:
        raise click.UsageError("--add-to-album must be used with --compare-exif.")

    verbose = verbose_print(verbose=verbose_flag, timestamp=timestamp, theme=theme)

    if any([compare_exif, push_exif, pull_exif]):
        exiftool_path = exiftool_path or get_exiftool_path()
        verbose(f"exiftool path: [filename]{exiftool_path}[/filename]")

    try:
        photos = PhotosLibrary().selection
        if not photos:
            echo_error("[warning]No photos selected[/]")
            sys.exit(0)
    except Exception as e:
        # AppleScript error -1728 occurs if user attempts to get selected photos in a Smart Album
        if "(-1728)" in str(e):
            echo_error(
                "[error]Could not get selected photos. Ensure photos is open and photos are selected. "
                "If you have selected photos and you see this message, it may be because the selected photos are in a Photos Smart Album. "
                f"{APP_NAME} cannot access photos in a Smart Album.  Select the photos in a regular album or in 'All Photos' view. "
                "Another option is to create a new album using 'File | New Album With Selection' then select the photos in the new album.[/]",
            )
        else:
            echo_error(
                f"[error]Could not get selected photos. Ensure Photos is open and photos to process are selected. {e}[/]",
            )
        sys.exit(1)

    # confirm with user before proceeding
    if (
        any(
            [
                date_added_from_photo,
                date_added,
                date_delta,
                date,
                function,
                parse_date,
                pull_exif,
                push_exif,
                time_delta,
                time,
                timezone,
            ]
        )
        and not force
    ):
        click.confirm(
            rich_text(
                f":warning-emoji:  About to process [num]{len(photos)}[/] {pluralize(len(photos), 'photo', 'photos')} with timewarp. "
                "This will directly modify your Photos library database using undocumented features. "
                "While this functionality has been well tested, it is possible this may "
                "corrupt, damage, or destroy your Photos library. [bold]Use at your own caution. No warranty is implied or provided.[/] "
                "It is strongly recommended you make a backup of your Photos library before using the timewarp command "
                "(for example, using Time Machine).\n\n"
                "Proceed with timewarp?"
            ),
            abort=True,
        )

    update_photo_date_time_ = partial(
        update_photo_date_time,
        date=date,
        time=time,
        date_delta=date_delta,
        time_delta=time_delta,
        verbose=verbose,
    )

    update_photo_time_for_new_timezone_ = partial(
        update_photo_time_for_new_timezone,
        library_path=library,
        verbose=verbose,
    )

    set_photo_date_from_filename_ = partial(
        set_photo_date_from_filename,
        library_path=library,
        verbose=verbose,
    )

    set_photo_date_added_ = partial(
        set_photo_date_added,
        library_path=library,
        verbose=verbose,
        date_added=date_added,
    )

    set_photo_date_added_from_photo_ = partial(
        set_photo_date_added,
        library_path=library,
        verbose=verbose,
    )

    get_photo_date_added_ = partial(
        get_photo_date_added,
        library_path=library,
    )

    if function:
        update_photo_from_function_ = partial(
            update_photo_from_function,
            library_path=library,
            function=function[0],
            verbose=verbose,
        )
    else:
        update_photo_from_function_ = noop

    if inspect:
        tzinfo = PhotoTimeZone(library_path=library)
        if photos:
            echo(
                "[filename]filename[/filename], [uuid]uuid[/uuid], "
                "[time]photo time (local)[/time], "
                "[time]photo time[/time], "
                "[tz]timezone offset[/tz], [tz]timezone name[/tz], "
                "[time]date added (local)[/time]"
            )
        for photo in photos:
            set_crash_data("photo", f"{photo.uuid} {photo.filename}")
            tz_seconds, tz_str, tz_name = tzinfo.get_timezone(photo)
            photo_date_local = datetime_naive_to_local(photo.date)
            photo_date_tz = datetime_to_new_tz(photo_date_local, tz_seconds)
            date_added = datetime_naive_to_local(get_photo_date_added_(photo))
            echo(
                f"[filename]{photo.filename}[/filename], [uuid]{photo.uuid}[/uuid], "
                f"[time]{photo_date_local.strftime(DATETIME_FORMAT)}[/time], "
                f"[time]{photo_date_tz.strftime(DATETIME_FORMAT)}[/time], "
                f"[tz]{tz_str}[/tz], [tz]{tz_name}[/tz], "
                f"[time]{date_added.strftime(DATETIME_FORMAT)}[/time]"
            )
        sys.exit(0)

    if compare_exif:
        album = PhotosAlbumPhotoScript(add_to_album) if add_to_album else None
        different_photos = 0
        if photos:
            photocomp = PhotoCompare(
                library_path=library,
                verbose=verbose,
                exiftool_path=exiftool_path,
            )
            if not album:
                echo(
                    "filename, uuid, photo time (Photos), photo time (EXIF), timezone offset (Photos), timezone offset (EXIF)"
                )
        for photo in photos:
            set_crash_data("photo", f"{photo.uuid} {photo.filename}")
            diff_results = (
                photocomp.compare_exif_no_markup(photo)
                if plain
                else photocomp.compare_exif_with_markup(photo)
            )

            if not plain:
                filename = (
                    f"[change]{photo.filename}[/change]"
                    if diff_results.diff
                    else f"[no_change]{photo.filename}[/no_change]"
                )
            else:
                filename = photo.filename
            uuid = f"[uuid]{photo.uuid}[/uuid]"
            if album:
                if diff_results.diff:
                    different_photos += 1
                    verbose(
                        f"Photo {filename} ({uuid}) has different date/time/timezone, adding to album '{album.name}'"
                    )
                    album.add(photo)
                else:
                    verbose(f"Photo {filename} ({uuid}) has same date/time/timezone")
            else:
                echo(
                    f"{filename}, {uuid}, "
                    f"{diff_results.photos_date} {diff_results.photos_time}, {diff_results.exif_date} {diff_results.exif_time}, "
                    f"{diff_results.photos_tz}, {diff_results.exif_tz}"
                )
        if album:
            echo(
                f"Compared {len(photos)} photos, found {different_photos} "
                f"that {pluralize(different_photos, 'is', 'are')} different and "
                f"added {pluralize(different_photos, 'it', 'them')} to album '{album.name}'."
            )
        sys.exit(0)

    if timezone:
        tz_updater = PhotoTimeZoneUpdater(
            timezone, verbose=verbose, library_path=library
        )

    if any([push_exif, pull_exif, function]):
        # ExifDateTimeUpdater used to get photo path for --function
        exif_updater = ExifDateTimeUpdater(
            library_path=library,
            verbose=verbose,
            exiftool_path=exiftool_path,
            plain=plain,
        )

    num_photos = len(photos)
    with rich_progress(console=get_verbose_console(), mock=verbose) as progress:
        task = progress.add_task(
            f"Processing [num]{num_photos}[/] {pluralize(len(photos), 'photo', 'photos')}",
            total=num_photos,
        )
        for photo in photos:
            set_crash_data("photo", f"{photo.uuid} {photo.filename}")
            if parse_date:
                set_photo_date_from_filename_(photo, photo.filename, parse_date)
            if pull_exif:
                exif_updater.update_photos_from_exif(
                    photo, use_file_modify_date=use_file_time
                )
            if any([date, time, date_delta, time_delta]):
                update_photo_date_time_(photo)
            if match_time:
                # need to adjust time before the timezone is updated
                # or the old timezone will be overwritten in the database
                update_photo_time_for_new_timezone_(photo=photo, new_timezone=timezone)
            if timezone:
                tz_updater.update_photo(photo)
            if date_added:
                set_photo_date_added_(photo)
            if date_added_from_photo:
                set_photo_date_added_from_photo_(photo, date_added=photo.date)
            if function:
                verbose(f"Calling function [bold]{function[1]}")
                photo_path = exif_updater.get_photo_path(photo)
                update_photo_from_function_(photo=photo, path=photo_path)
            if push_exif:
                # this should be the last step in the if chain to ensure all Photos data is updated
                # before exiftool is run
                exif_warn, exif_error = exif_updater.update_exif_from_photos(photo)
                if exif_warn:
                    echo_error(f"[warning]Warning running exiftool: {exif_warn}[/]")
                if exif_error:
                    echo_error(f"[error]Error running exiftool: {exif_error}[/]")

            progress.advance(task)

    echo("Done.")
