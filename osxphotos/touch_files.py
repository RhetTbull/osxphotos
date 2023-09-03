"""Touch files to update their modification time to match a photo's date/time"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .exportoptions import ExportOptions, ExportResults

if TYPE_CHECKING:
    from .photoinfo import PhotoInfo

__all__ = ["touch_files"]


def touch_files(
    photo: PhotoInfo, touch_files: list[str], options: ExportOptions
) -> ExportResults:
    """Touch file date/time to match photo creation date/time; only touches files if needed

    Args:
        photo: PhotoInfo object
        touch_files: list of file paths to touch
        options: ExportOptions object

    Returns:
        ExportResults object with `touched` set to list of files that were touched

    Note:
        Does not touch files if options.dry_run is True
    """
    fileutil = options.fileutil
    touch_results = []
    for touch_file in set(touch_files):
        ts = int(photo.date.timestamp())
        try:
            stat = os.stat(touch_file)
            if stat.st_mtime != ts:
                fileutil.utime(touch_file, (ts, ts))
                touch_results.append(touch_file)
        except FileNotFoundError as e:
            # ignore errors if in dry_run as file may not be present
            if not options.dry_run:
                raise e from e
    return ExportResults(touched=touch_results)
