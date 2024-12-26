""" Generate XMP sidecar files for selected photos.

Run with `osxphotos run sidecars.py` or `osxphotos run https://raw.githubusercontent.com/RhetTbull/osxphotos/refs/heads/main/examples/sidecars.py` to run without saving to your computer.
"""

from __future__ import annotations

import pathlib

import osxphotos
from osxphotos._constants import SIDECAR_XMP
from osxphotos.cli import echo, selection_command, verbose
from osxphotos.exportoptions import ExportOptions
from osxphotos.sidecars import SidecarWriter


@selection_command
def sidecars(photos: list[osxphotos.PhotoInfo], **kwargs):
    """Generate XMP sidecars for currently selected photos.

    Select one or more photos in Photos then run the script to generate XMP sidecars which will be saved to the current directory.
    """

    echo(f"Processing {len(photos)} photo(s)")

    options = ExportOptions(sidecar=SIDECAR_XMP)

    for photo in photos:
        # photos is a list of PhotoInfo objects
        # see: https://rhettbull.github.io/osxphotos/reference.html#osxphotos.PhotoInfo
        echo(f"Processing {photo.original_filename} ({photo.uuid})")
        path = pathlib.Path(f"{photo.original_filename}")
        writer = SidecarWriter(photo)
        files = writer.write_sidecar_files(path, options)
        if files.sidecar_xmp_written:
            echo(f"Wrote sidecar file {files.sidecar_xmp_written[0]}")
        else:
            echo("No sidecar file written")


if __name__ == "__main__":
    # call your function here
    # you do not need to pass any arguments to the function
    # as the decorator will handle parsing the command line arguments
    sidecars()
