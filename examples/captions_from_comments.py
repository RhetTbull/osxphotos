"""Generate captions in Photos from Finder comments

Run with `osxphotos run captions_from_comments.py /path/to/photos/* [--walk] [--dry-run]
"""

import os

import click
import osxmetadata
import photoscript

from osxphotos.cli import echo
from osxphotos.fingerprint import fingerprint
from osxphotos.fingerprintquery import FingerprintQuery
from osxphotos.image_file_utils import is_image_file, is_video_file
from osxphotos.utils import get_last_library_path


@click.command()
@click.option("--walk", is_flag=True, help="Walk directories recursively")
@click.option("--dry-run", is_flag=True, help="Dry run: Do not modify Photos library")
@click.argument("paths", nargs=-1)
def main(walk: bool, dry_run: bool, paths: tuple[str]):
    """
    Generate captions in Photos from Finder comments.

    Scans one or more files, finds the matching photo in Photos, then sets the photo's caption from the Finder comment, if available.
    """

    if not paths:
        print("No paths provided")
        return

    echo("Collecting files to check...")
    files = scan_files(paths, walk=walk)
    echo(f"Found [num]{len(files)}[/] file{'s' if len(files) != 1 else ''} to check")

    library = get_last_library_path()
    fq = FingerprintQuery(library)
    for file in files:
        try:
            md = osxmetadata.OSXMetaData(file)
        except Exception as e:
            echo(f"Error reading metadata for file [filename]{file}[/]: {e}")
            continue
        if not md.findercomment:
            echo(f"Skipping file [filename]{file}[/] because it has no Finder comment")
            continue
        fp = fingerprint(file)
        if matches := fq.photos_by_fingerprint(fp):
            for uuid, date, filename in matches:
                echo(
                    f"Found match for file [filename]{file}[/] in Photos: [filename]{filename}[/] ([uuid]{uuid}[/])"
                )
                echo(f"Setting caption to [filepath]{md.findercomment}[/]")
                if not dry_run:
                    set_caption(uuid, md.findercomment)
            else:
                echo(f"No match found for file [filename]{file}[/] in Photos")


def set_caption(uuid: str, caption: str) -> None:
    """Set the caption for a photo in Photos"""
    try:
        photo = photoscript.Photo(uuid)
        photo.description = caption
    except Exception as e:
        echo(f"Error setting caption for photo [uuid]{uuid}[/]: {e}")


def scan_files(paths: tuple[str], walk: bool) -> list[str]:
    """Scan files and return a list of file paths"""
    files = []
    for path in paths:
        if os.path.isdir(path):
            if walk:
                for root, dirs, filenames in os.walk(path):
                    for filename in filenames:
                        files.append(os.path.join(root, filename))
            else:
                files.extend(os.listdir(path))
        else:
            files.append(os.path.abspath(path))

    files = [file for file in files if is_image_file(file) or is_video_file(file)]
    return files


if __name__ == "__main__":
    main()
