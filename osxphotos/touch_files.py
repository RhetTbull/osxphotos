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
        ExportResults object with 'touched' set to list of files that were touched

    Note:
        Does not touch files if options.dry_run is True
    """
    fileutil = options.fileutil
    stat_cache = options.stat_cache
    touch_results = []
    for touch_file in set(touch_files):
        ts = int(photo.date.timestamp())
        try:
            # Use stat_cache if available to avoid network stat() calls
            if stat_cache is not None:
                cached_stat = stat_cache.stat(touch_file)
                if cached_stat is not None:
                    current_mtime = int(cached_stat.st_mtime)
                else:
                    # Not in cache, fall back to direct stat
                    current_mtime = int(os.stat(touch_file).st_mtime)
            else:
                current_mtime = int(os.stat(touch_file).st_mtime)

            if current_mtime != ts:
                fileutil.utime(touch_file, (ts, ts))
                # Update stat cache with new mtime (avoids extra stat call)
                if stat_cache is not None:
                    stat_cache.update_file(touch_file, mtime=ts)
                touch_results.append(touch_file)
        except FileNotFoundError as e:
            # ignore errors if in dry_run as file may not be present
            if not options.dry_run:
                raise e from e
    return ExportResults(touched=touch_results)
