""" Example function for use with osxphotos export --post-function option to set custom XMP:Rating value"""

# See this Reddit post for context: https://www.reddit.com/r/osxphotos/comments/wo4xra/can_i_set_xmprating_based_on_keywords/

import sys
from typing import Callable

from osxphotos import ExportResults, PhotoInfo
from osxphotos.exiftool import ExifTool
from osxphotos.utils import normalize_unicode

# Update this for your custom keyword to rating mapping
RATINGS = {
    "★⭐︎⭐︎⭐︎⭐︎": 1,
    "★★︎⭐︎⭐︎⭐︎": 2,
    "★★★︎⭐︎⭐︎": 3,
    "★★★★︎⭐︎": 4,
    "★★★★★︎": 5,
}

# normalize the unicode to match what osxphotos uses internally
RATINGS = {normalize_unicode(k): v for k, v in RATINGS.items()}


def rating(photo: PhotoInfo, results: ExportResults, verbose: Callable, **kwargs):
    """Call this with `osxphotos export /path/to/export --post-function xmp_rating.py::rating`
        This will get called immediately after the photo has been exported

    Args:
        photo: PhotoInfo instance for the photo that's just been exported
        results: ExportResults instance with information about the files associated with the exported photo
        verbose: A function to print verbose output if --verbose is set; if --verbose is not set, acts as a no-op (nothing gets printed)
        **kwargs: reserved for future use; recommend you include **kwargs so your function still works if additional arguments are added in future versions

    Notes:
        Use verbose(str) instead of print if you want your function to conditionally output text depending on --verbose flag
        Any string printed with verbose that contains "warning" or "error" (case-insensitive) will be printed with the appropriate warning or error color
        Will not be called if --dry-run flag is enabled
        Will be called immediately after export and before any --post-command commands are executed
    """

    # ExportResults has the following properties
    # fields with filenames contain the full path to the file
    # exported: list of all files exported
    # new: list of all new files exported (--update)
    # updated: list of all files updated (--update)
    # skipped: list of all files skipped (--update)
    # exif_updated: list of all files that were updated with --exiftool
    # touched: list of all files that had date updated with --touch-file
    # converted_to_jpeg: list of files converted to jpeg with --convert-to-jpeg
    # sidecar_json_written: list of all JSON sidecar files written
    # sidecar_json_skipped: list of all JSON sidecar files skipped (--update)
    # sidecar_exiftool_written: list of all exiftool sidecar files written
    # sidecar_exiftool_skipped: list of all exiftool sidecar files skipped (--update)
    # sidecar_xmp_written: list of all XMP sidecar files written
    # sidecar_xmp_skipped: list of all XMP sidecar files skipped (--update)
    # missing: list of all missing files
    # error: list tuples of (filename, error) for any errors generated during export
    # exiftool_warning: list of tuples of (filename, warning) for any warnings generated by exiftool with --exiftool
    # exiftool_error: list of tuples of (filename, error) for any errors generated by exiftool with --exiftool
    # xattr_written: list of files that had extended attributes written
    # xattr_skipped: list of files that where extended attributes were skipped (--update)
    # deleted_files: list of deleted files
    # deleted_directories: list of deleted directories
    # exported_album: list of tuples of (filename, album_name) for exported files added to album with --add-exported-to-album
    # skipped_album: list of tuples of (filename, album_name) for skipped files added to album with --add-skipped-to-album
    # missing_album: list of tuples of (filename, album_name) for missing files added to album with --add-missing-to-album
    # metadata_changed: list of filenames that had metadata changes since last export

    xmp_rating = None

    # check to see if there's a rating to apply
    for rating in RATINGS:
        if rating in photo.keywords:
            xmp_rating = RATINGS[rating]
            break

    if not xmp_rating:
        # nothing to do
        verbose("No XMP:Rating to set")
        return

    # update each exported file with the new rating
    for filename in results.exported:
        verbose(
            f"Updating [filepath]{filename}[/] with XMP:Rating=[num]{xmp_rating}[/]"
        )
        with ExifTool(filename) as exiftool:
            if not exiftool.setvalue("XMP:Rating", xmp_rating):
                print(
                    f"Error updating XMP:Rating for file {filename}: {exiftool.error}",
                    file=sys.stderr,
                )