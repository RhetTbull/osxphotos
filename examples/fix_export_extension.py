""" Example function for use with osxphotos export --post-function option """

import pathlib
from typing import Callable

from osxphotos import ExportResults, PhotoInfo
from osxphotos.exiftool import ExifTool


def fix_extension(
    photo: PhotoInfo, results: ExportResults, verbose: Callable, **kwargs
):
    """Call this with osxphotos export /path/to/export --post-function fix_export_extension.py::fix_extension
        This will get called immediately after the photo has been exported

    See full example here: https://github.com/RhetTbull/osxphotos/blob/master/examples/post_function.py

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

    for filepath in results.exported:
        filepath = pathlib.Path(filepath)
        ext = filepath.suffix.lower()
        if not ext:
            continue
        ext = ext[1:]  # remove leading dot
        exiftool = ExifTool(filepath)
        actual_ext = exiftool.asdict().get("File:FileTypeExtension").lower()
        if ext != actual_ext and (ext not in ("jpg", "jpeg") or actual_ext != "jpg"):
            # WARNING: Does not check for name collisions; left as an exercise for the reader
            verbose(f"Fixing extension for {filepath} from {ext} to {actual_ext}")
            new_filepath = filepath.with_suffix(f".{actual_ext}")
            verbose(f"Renaming {filepath} to {new_filepath}")
            filepath.rename(new_filepath)
