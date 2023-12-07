"""Use osxphotos to delete empty albums and folders from Photos

Usage:
    osxphotos run delete-empty-albums.py [options]
"""

from __future__ import annotations

import sys

import click
import photoscript

from osxphotos.cli.cli_commands import echo, echo_error
from osxphotos.utils import pluralize


@click.command()
@click.option(
    "--folders",
    "prune_folders",
    is_flag=True,
    help="In addition to empty albums, also delete empty folders",
)
@click.option("--dry-run", is_flag=True, help="Dry run, don't delete anything")
def main(prune_folders: bool, dry_run: bool) -> None:
    """Delete empty albums and folders from Photos library.

    This script uses osxphotos to find empty albums and folders and then
    deletes them. It does not delete any photos or videos.

    This script will only operate on the last-opened Photos library--that is, the library
    that opens if you clicked on the Photos icon in the Dock right now. If you want to use
    this on a different library, close Photos then hold down the Option key while clicking
    on the Photos icon in the Dock. You will be prompted to choose a library. Select the
    library you want to use and then run this script.
    """

    message = (
        "This script will delete empty albums"
        + (" and folders " if prune_folders else " ")
        + "from your Photos library. "
        + "Are you sure you want to continue?"
    )
    if not click.confirm(message):
        echo("Aborting")
        sys.exit(1)

    photoslib = photoscript.PhotosLibrary()
    echo("Finding empty albums...")
    albums = photoslib.albums()
    empty_albums = [album for album in albums if not len(album)]

    echo(
        f"Found [num]{len(empty_albums)}[/] empty {pluralize(len(empty_albums), 'album', 'albums')}"
    )

    for album in empty_albums:
        echo(f"Deleting empty album: [filename]{album.title}")
        if not dry_run:
            photoslib.delete_album(photoscript.Album(uuid=album.uuid))

    if prune_folders:
        echo("Pruning empty folders...")
        if dry_run:
            echo(
                "[warning]Dry run mode: when using --dry-run, "
                "folders that would be empty after deleting albums will not be listed "
                "as they are not currently empty."
            )
        for folder in photoslib.folders(top_level=True):
            remove_empty_folders(folder, dry_run=dry_run)
    else:
        echo(
            "Skipping folder pruning "
            "([uuid]--folders[/] not specified, see [uuid]--help[/]; "
            "run again with [uuid]--folders[/] to prune empty folders)"
        )

    echo("Done!")


def remove_empty_folders(folder: photoscript.Folder, dry_run: bool, path: str = ""):
    """Recursively remove empty folders from the folder hierarchy"""
    for subfolder in folder.subfolders:
        remove_empty_folders(subfolder, dry_run=dry_run, path=f"{path}/{folder.title}")

    if not folder.albums and not folder.subfolders:
        # If it's empty, remove it
        if folder.parent:
            # bug in Photos AppleScript since Catalina that prevents deleting sub-folder
            echo(
                f"Empty sub-folder: [filepath]{path}/{folder.title}[/], "
                "cannot be deleted by this script"
            )
            return
        echo(f"Removing empty folder: [filepath]{path}/{folder.title}")
        if not dry_run:
            photoscript.PhotosLibrary().delete_folder(folder)


if __name__ == "__main__":
    main()
