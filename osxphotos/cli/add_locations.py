"""Add missing location data to photos in Photos.app using nearest neighbor."""

from __future__ import annotations

import datetime

import click

import osxphotos
from osxphotos.photoquery import IncompatibleQueryOptions, query_options_from_kwargs
from osxphotos.platform import assert_macos
from osxphotos.utils import pluralize

from .cli_params import QUERY_OPTIONS, THEME_OPTION, TIMESTAMP_OPTION, VERBOSE_OPTION
from .click_rich_echo import rich_click_echo as echo
from .click_rich_echo import rich_echo_error as echo_error
from .param_types import TimeOffset
from .rich_progress import rich_progress
from .verbose import get_verbose_console, verbose_print

assert_macos()

import photoscript


def get_location(
    photos: list[osxphotos.PhotoInfo], idx: int, window: datetime.timedelta
) -> osxphotos.PhotoInfo | None:
    """Find nearest neighbor with location data within window of time.

    Args:
        photo: PhotoInfo object
        idx: index of photo in list of photos
        window: window of time to search for nearest neighbor

    Returns:
        nearest neighbor PhotoInfo object or None if no neighbor found
    """
    idx_back = None
    idx_forward = None
    if idx > 0:
        # search backwards in time
        for i in range(idx - 1, -1, -1):
            if (
                photos[idx].date - photos[i].date <= window
                and None not in photos[i].location
            ):
                idx_back = i
                break

    if idx < len(photos) - 1:
        # search forwards in time
        for i in range(idx + 1, len(photos)):
            if (
                photos[i].date - photos[idx].date <= window
                and None not in photos[i].location
            ):
                idx_forward = i
                break

    if idx_back is not None and idx_forward is not None:
        # found location in both directions
        # use location closest in time
        if (
            photos[idx].date - photos[idx_back].date
            < photos[idx_forward].date - photos[idx].date
        ):
            return photos[idx_back]
        else:
            return photos[idx_forward]
    elif idx_back is not None:
        return photos[idx_back]
    elif idx_forward is not None:
        return photos[idx_forward]
    else:
        return None


@click.command(name="add-locations")
@click.option(
    "--window",
    "-w",
    type=TimeOffset(),
    default="1 hr",
    help="Window of time to search for nearest neighbor; "
    "searches +/- window of time.  Default is 1 hour. "
    "Format is one of 'HH:MM:SS', 'D days', 'H hours' (or hr), 'M minutes' (or min), "
    "'S seconds' (or sec), 'S' (where S is seconds).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Don't actually add location, just print what would be done. "
    "Most useful with --verbose.",
)
@VERBOSE_OPTION
@TIMESTAMP_OPTION
@QUERY_OPTIONS
@THEME_OPTION
@click.pass_obj
@click.pass_context
def add_locations(
    ctx, cli_ob, window, dry_run, verbose_flag, timestamp, theme, **kwargs
):
    """Add missing location data to photos in Photos.app using nearest neighbor.

    This command will search for photos that are missing location data and look
    for the nearest neighbor photo within a given window of time that contains
    location information. If a photo is found within the window of time, the
    location of the nearest neighbor will be used to update the location of the
    photo.

    For example, if you took pictures with your iPhone and also with a camera that
    doesn't have location information, you can use this command to add location
    information to the photos taken with the camera from those taken with the
    iPhone.

    If you have many photos with missing location information but no nearest neighbor
    within the window of time, you could add location information to some photos manually
    then run this command again to add location information to the remaining photos.

    You can specify a subset of photos to update using the query options.  For example,
    `--selected` to update only the selected photos, `--added-after 2020-01-01` to update
    only photos added after Jan 1, 2020, etc.

    Example:

    Add location data to all photos with missing location data within a ±2 hour window:

    `osxphotos add-locations --window "2 hr" --verbose`

    The add-locations command assumes that photos already have the correct date and time.
    If you have photos that are missing both location data and date/time information,
    you can use `osxphotos timewarp` to add date/time information to the photos and then
    use `osxphotos add-locations` to add location information.
    See `osxphotos help timewarp` for more information.
    """
    verbose = verbose_print(verbose_flag, timestamp, theme=theme)

    verbose("Searching for photos with missing location data...")

    try:
        query_options = query_options_from_kwargs(**kwargs)
    except IncompatibleQueryOptions as e:
        echo_error("Incompatible query options")
        echo_error(ctx.obj.group.commands["repl"].get_help(ctx))
        ctx.exit(1)

    photosdb = osxphotos.PhotosDB(verbose=verbose)
    photos = photosdb.query(query_options)

    # sort photos by date
    photos = sorted(photos, key=lambda p: p.date)

    num_photos = len(photos)
    missing_location = 0
    found_location = 0
    verbose(f"Processing {len(photos)} photos, window = ±{window}...")
    with rich_progress(console=get_verbose_console(), mock=verbose_flag) as progress:
        task = progress.add_task(
            f"Processing [num]{num_photos}[/] {pluralize(len(photos), 'photo', 'photos')}, window = ±{window}",
            total=num_photos,
        )
        for idx, photo in enumerate(photos):
            if None in photo.location:
                missing_location += 1
                verbose(
                    f"Processing [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
                )
                if neighbor := get_location(photos, idx, window):
                    verbose(
                        f"Adding location {neighbor.location} to [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
                        f" from [filename]{neighbor.original_filename}[/] ([uuid]{neighbor.uuid}[/])"
                    )
                    found_location += 1
                    if not dry_run:
                        photoscript.Photo(photo.uuid).location = neighbor.location
                else:
                    verbose(
                        f"No location found for [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
                    )
            progress.advance(task)
    echo(
        f"Done. Processed: [num]{num_photos}[/] photos, "
        f"missing location: [num]{missing_location}[/], "
        f"found location: [num]{found_location}[/] "
    )
