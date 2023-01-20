""" Example function for use with osxphotos import --post-function option """

import typing as t
import photoscript
import pathlib
from osxphotos.cli.import_cli import ReportRecord


def post_function(
    photo: photoscript.Photo,
    filepath: pathlib.Path,
    verbose: t.Callable,
    report_record: ReportRecord,
    **kwargs,
):
    """Call this with osxphotos import /file/to/import --post-function post_function.py::post_function
        This will get called immediately after the photo has been imported into Photos
        and all metadata been set (e.g. --exiftool, --title, etc.)

    Args:
        photo: photoscript.Photo instance for the photo that's just been imported
        filepath: pathlib.Path to the file that was imported (this is the path to the source file, not the path inside the Photos library)
        verbose: A function to print verbose output if --verbose is set; if --verbose is not set, acts as a no-op (nothing gets printed)
        report_record: ReportRecord instance for the photo that's just been imported; update this if you want to change the report output
        **kwargs: reserved for future use; recommend you include **kwargs so your function still works if additional arguments are added in future versions

    Notes:
        Use verbose(str) instead of print if you want your function to conditionally output text depending on --verbose flag
        Any string printed with verbose that contains "warning" or "error" (case-insensitive) will be printed with the appropriate warning or error color
        See https://rhettbull.github.io/PhotoScript/ for documentation on photoscript
    """

    # add a note to the photo's description
    verbose("Adding note to description")
    description = photo.description
    description = (
        f"{description} (imported with osxphotos)"
        if description
        else "(imported with osxphotos)"
    )

    # update report_record if you modify the photo and want the report to reflect the change
    # the report_record object passed to the function is mutable so you can update it directly
    report_record.description = description

    # update the photo's description via the Photo object
    photo.description = description
