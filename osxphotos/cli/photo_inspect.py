"""Inspect photos selected in Photos """

import functools
import re
from fractions import Fraction
from multiprocessing import Process, Queue
from queue import Empty
from time import gmtime, sleep, strftime
from typing import List, Optional, Tuple
import pathlib

import bitmath
import click
from applescript import ScriptError
from photoscript import PhotosLibrary
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel

from osxphotos import PhotoInfo, PhotosDB
from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.rich_utils import add_rich_markup_tag
from osxphotos.text_detection import detect_text as detect_text_in_photo
from osxphotos.utils import dd_to_dms_str

from .color_themes import get_theme
from .common import DB_OPTION, THEME_OPTION, get_photos_db

# global that tracks UUID being inspected
CURRENT_UUID = None

# helpers for markup
bold = add_rich_markup_tag("bold")
dim = add_rich_markup_tag("dim")


def extract_uuid(text: str) -> str:
    """Extract a UUID from a string"""
    if match := re.search(
        r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
        text,
    ):
        return match[1]
    return None


def trim(text: str, pad: str = "") -> str:
    """Truncate a string to a fit in console, - len(pad) - 4; also removes new lines"""
    width = Console().width - len(pad) - 4
    text = text.replace("\n", " ")
    return text if len(text) <= width else f"{text[: width- 3]}..."


def inspect_photo(photo: PhotoInfo, detected_text: Optional[str] = None) -> str:
    """Get info about an osxphotos PhotoInfo object formatted for printing"""

    properties = [
        bold("Filename: ") + f"[filename]{photo.original_filename}[/]",
        bold("Type: ") + get_photo_type(photo),
        bold("UUID: ") + f"[uuid]{photo.uuid}[/]",
        bold("Date: ") + f"[time]{photo.date.isoformat()}[/]",
        bold("Date added: ") + f"[time]{photo.date_added.isoformat()}[/]",
    ]
    if photo.date_modified:
        properties.append(
            bold("Date modified: ") + f"[time]{photo.date_modified.isoformat()}[/]"
        )

    if photo.intrash and photo.date_trashed:
        properties.append(
            bold("Date deleted: ") + f"[time]{photo.date_trashed.isoformat()}[/]"
        )

    if photo.import_info and photo.import_info.creation_date:
        properties.append(
            bold("Date imported: ")
            + f"[time]{photo.import_info.creation_date.isoformat()}[/]"
        )

    properties.extend(
        [
            bold("Dimensions: ")
            + f"[num]{photo.width}[/] x [num]{photo.height}[/] "
            + bold("Orientation: ")
            + f"[num]{photo.orientation}[/]",
            bold("File size: ")
            + f"[num]{float(bitmath.Byte(photo.original_filesize).to_MB()):.2f} MB[/]",
            bold("Title: ") + f"{photo.title or '-'}",
            bold("Description: ")
            + f"{trim(photo.description or '-', 'Description: ')}",
            bold("Edited: ")
            + f"{'✔' if photo.hasadjustments else '-'} "
            + bold("External edits: ")
            + f"{'✔' if photo.external_edit else '-'}",
            bold("Keywords: ") + f"{', '.join(photo.keywords) or '-'}",
            bold("Persons: ")
            + f"{', '.join(p for p in photo.persons if p != _UNKNOWN_PERSON) or '-'}",
            bold("Location: ")
            + f"{', '.join(dd_to_dms_str(*photo.location)) if photo.location[0] else '-'}",
            bold("Place: ") + f"{photo.place.name if photo.place else '-'}",
            bold("Categories: ") + f"{', '.join(photo.labels) or '-'}",
        ]
    )
    properties.append(format_flags(photo))
    properties.append(format_albums(photo))

    if photo.project_info:
        properties.append(
            bold("Projects: ")
            + f"{', '.join(p.title for p in photo.project_info) or '-'}"
        )

    if photo.moment_info:
        properties.append(bold("Moment: ") + f"{photo.moment_info.title or '-'}")

    if photo.comments:
        comments = [f"{c.user}: {c.text}" for c in photo.comments]
        properties.append(
            bold("Comments: ") + trim(f"{', '.join(comments)}", "Comments: ")
        )

    if photo.likes:
        properties.append(
            bold("Likes: ")
            + trim(f"{', '.join(l.user for l in photo.likes)}", "Likes: ")
        )

    properties.append(format_exif_info(photo))
    properties.append(format_score_info(photo))

    if detected_text:
        # have detected text for this photo
        properties.append(
            bold("Detected text: ") + trim(detected_text, "Detected text: ")
        )

    properties.append(format_paths(photo))

    return "\n".join(properties)


def format_score_info(photo: PhotoInfo) -> str:
    """Format score_info"""
    score_str = bold("Score: ")
    if photo.score:
        score_str += f"[num]{photo.score.overall}[/]" if photo.score else "-"
    return score_str


def format_flags(photo: PhotoInfo) -> str:
    """Format special properties"""
    flag_str = bold("Flags: ")
    flags = []
    if photo.favorite:
        flags.append("favorite")
    if photo.visible:
        flags.append("visible")
    if photo.hidden:
        flags.append("hidden")
    if photo.ismissing:
        flags.append("missing")
    if photo.intrash:
        flags.append("in trash")
    if photo.iscloudasset:
        flags.append("cloud asset")
    if photo.incloud:
        flags.append("in cloud")
    if photo.shared:
        flags.append("shared")

    flag_str += f"{', '.join(flags) or '-'}"
    return flag_str


def format_albums(photo: PhotoInfo) -> str:
    """Format albums for inspect_photo"""
    album_str = bold("Albums: ")
    album_names = []
    for album in photo.album_info:
        if album.folder_names:
            folder_str = "/".join(album.folder_names)
            album_names.append(f"{folder_str}/{album.title}")
        else:
            album_names.append(album.title)
    album_str += f"{', '.join(album_names) or '-'}"
    return album_str


def format_path_link(path: str) -> str:
    """Format a path as URI for display in terminal"""
    return f"[link={pathlib.Path(path).as_uri()}]{path}[/link]"


def format_paths(photo: PhotoInfo) -> str:
    """format photo paths for inspect_photo"""
    path_str = bold("Path original: ")
    path_str += f"[filepath]{format_path_link(photo.path)}[/]" if photo.path else "-"
    if photo.path_edited:
        path_str += "\n"
        path_str += bold("Path edited: ")
        path_str += f"[filepath]{format_path_link(photo.path_edited)}[/]"
    if photo.path_raw:
        path_str += "\n"
        path_str += bold("Path raw: ")
        path_str += f"[filepath]{format_path_link(photo.path_raw)}[/]"
    if photo.path_derivatives:
        path_str += "\n"
        path_str += bold("Path preview: ")
        path_str += f"[filepath]{format_path_link(photo.path_derivatives[0])}[/]"
    return path_str


def format_exif_info(photo: PhotoInfo) -> str:
    """Format exif_info for inspect_photo"""
    exif_str = bold("EXIF: ")
    exif = photo.exif_info
    if not exif:
        return f"{exif_str}-"

    if exif.camera_make:
        exif_str += f"{exif.camera_make} "
    if exif.camera_model:
        exif_str += f"{exif.camera_model} "
    if exif.focal_length:
        exif_str += f"{exif.focal_length:.2f}mm "
    if exif.iso:
        exif_str += f"ISO {exif.iso} "
    if exif.flash_fired:
        exif_str += "Flash "
    if exif.exposure_bias is not None:
        exif_str += (
            f"{int(exif.exposure_bias)} ev "
            if exif.exposure_bias == int(exif.exposure_bias)
            else f"{exif.exposure_bias} ev "
        )
    if exif.aperture:
        exif_str += (
            f"ƒ{int(exif.aperture)} "
            if exif.aperture == int(exif.aperture)
            else f"ƒ{exif.aperture:.1f} "
        )
    if exif.shutter_speed:
        exif_str += f"{Fraction(exif.shutter_speed).limit_denominator(100_000)}s "
    if exif.bit_rate:
        exif_str += f"{exif.bit_rate} bit rate"
    if exif.sample_rate:
        exif_str += f"{exif.sample_rate} sample rate"
    if exif.fps:
        exif_str += f"{exif.fps or 0:.1f}FPS "
    if exif.duration:
        exif_str += f"{strftime('%H:%M:%S', gmtime(exif.duration or 0))} "
    if exif.codec:
        exif_str += f"{exif.codec}"
    if exif.track_format:
        exif_str += f"{exif.track_format}"
    return exif_str


def get_photo_type(photo: PhotoInfo) -> str:
    """Return a string describing the type of photo"""
    photo_type = "video" if photo.ismovie else "photo"
    if photo.has_raw:
        photo_type += " RAW+JPEG"
    if photo.israw:
        photo_type += " RAW"
    if photo.burst:
        photo_type += " burst"
    if photo.live_photo:
        photo_type += " live"
    if photo.selfie:
        photo_type += " selfie"
    if photo.panorama:
        photo_type += " panorama"
    if photo.hdr:
        photo_type += " HDR"
    if photo.screenshot:
        photo_type += " screenshot"
    if photo.slow_mo:
        photo_type += " slow-mo"
    if photo.time_lapse:
        photo_type += " time-lapse"
    if photo.portrait:
        photo_type += " portrait"
    return photo_type


def start_text_detection(photo: PhotoInfo) -> Tuple[Process, Queue]:
    """Start text detection process for a photo"""
    path_preview = photo.path_derivatives[0] if photo.path_derivatives else None
    path = photo.path_edited or photo.path or path_preview
    if not path:
        raise ValueError("No path to photo")
    queue = Queue()
    p = Process(
        target=_get_detected_text,
        args=(photo.uuid, path, photo.orientation, queue),
    )
    p.start()
    return (p, queue)


def _get_detected_text(uuid: str, path: str, orientation: int, queue: Queue) -> None:
    """Called by start_text_detection to run text detection in separate process"""
    try:
        if text := detect_text_in_photo(path, orientation):
            queue.put([uuid, " ".join(t[0] for t in text if t[1] > 0.5)])
    except Exception as e:
        queue.put([uuid, str(e)])


def get_uuid_for_photos_selection() -> List[str]:
    """Get the uuid for the first photo selected in Photos

    Returns: tuple of (uuid, total_selected_photos)"""
    photoslib = PhotosLibrary()
    try:
        if photos := photoslib.selection:
            return photos[0].uuid, len(photos)
    except (ValueError, ScriptError) as e:
        if uuid := extract_uuid(str(e)):
            return uuid, 1
        else:
            raise e
    return None, 0


def make_layout() -> Layout:
    """Define the layout."""
    layout = Layout(name="root")

    layout.split(
        Layout(name="main", ratio=1),
        Layout(name="status", size=1),
        Layout(name="footer", size=1),
    )
    return layout


@click.command(name="inspect")
@click.option("--detect-text", "-t", is_flag=True, help="Detect text in photos")
@THEME_OPTION
@DB_OPTION
def photo_inspect(db, theme, detect_text):
    """Interactively inspect photos selected in Photos.

    Open Photos then run `osxphotos inspect` in the terminal.
    As you select a photo in Photos, inspect will display metadata about the photo. 
    Press Ctrl+C to exit when done.
    Works best with a modern terminal like iTerm2 or Kitty.
    """
    db = get_photos_db(db)
    if not db:
        raise click.UsageError(
            "Did not locate Photos database. Try running with --db option."
        )

    theme = get_theme(theme)
    console = Console(theme=theme)

    layout = make_layout()
    layout["footer"].update("Press Ctrl+C to quit")
    layout["main"].update(
        Panel("Loading Photos database, hold on...", title="Loading...")
    )

    def loading_status(status: str):
        layout["status"].update(f"Loading database: {status}")

    def update_status(status: str):
        layout["status"].update(status)

    def update_detected_text(photo: PhotoInfo, uuid: str, text: str):
        global CURRENT_UUID
        if uuid == CURRENT_UUID:
            layout["main"].update(
                Panel(
                    inspect_photo(photo, text),
                    title=photo.title or photo.original_filename,
                )
            )

    with Live(layout, console=console, refresh_per_second=10, screen=True):
        photosdb = PhotosDB(dbfile=db, verbose=loading_status)
        layout["main"].update(
            Panel("Select a photo in Photos to inspect", title="Select a photo")
        )
        processes = []
        global CURRENT_UUID
        detected_text_cache = {}
        last_uuid = None
        uuid = None
        total = 0
        while True:
            try:
                uuid, total = get_uuid_for_photos_selection()
            except Exception as e:
                layout["main"].update(Panel(f"Error: {e}", title="Error"))
            except KeyboardInterrupt:
                # allow Ctrl+C to quit
                break
            finally:
                if uuid and uuid != last_uuid:
                    if total > 1:
                        update_status(
                            f"{total} photos selected; inspecting uuid={uuid}"
                        )
                    else:
                        update_status(f"Inspecting uuid={uuid}")
                        CURRENT_UUID = uuid
                    if photo := photosdb.get_photo(uuid):
                        layout["main"].update(
                            Panel(
                                inspect_photo(
                                    photo,
                                    detected_text=detected_text_cache.get(uuid, None),
                                ),
                                title=photo.title or photo.original_filename,
                            )
                        )

                        # start text detection if requested
                        if (
                            detect_text
                            and (
                                photo.path
                                or photo.path_edited
                                or photo.path_derivatives
                            )
                            and uuid not in detected_text_cache
                        ):
                            # can only detect text on photos if on disk
                            # start text detection in separate process as it can take a few seconds
                            update_detected_text_callback = functools.partial(
                                update_detected_text, photo
                            )
                            process, queue = start_text_detection(photo)
                            processes.append(
                                [True, process, queue, update_detected_text_callback]
                            )
                    else:
                        layout["main"].update(
                            Panel(
                                f"No photo found in database for uuid={uuid}",
                                title="Error",
                            )
                        )
                    last_uuid = uuid
            if not uuid:
                last_uuid = None
                layout["main"].update(
                    Panel("Select a photo in Photos to inspect", title="Select a photo")
                )
                update_status("Select a photo in Photos to inspect")
            if detect_text:
                # check on text detection processes
                for _, values in enumerate(processes):
                    alive, process, queue, update_detected_text_callback = values
                    if alive:
                        # process hasn't been marked as dead yet
                        try:
                            uuid, text = queue.get(False)
                            update_detected_text_callback(uuid, text)
                            detected_text_cache[uuid] = text
                            process.join()
                            # set alive = False
                            values[0] = False
                        except Empty:
                            if not process.is_alive():
                                # process has finished, nothing in the queue
                                process.join()
                                # set alive = False
                                values[0] = False
            sleep(0.100)
