"""Add keywords to photos in Photos app from Finder tags on the original file.

Run with: osxphotos run add_finder_tags.py FILES_OR_DIRS
"""

from __future__ import annotations

import fnmatch
import os
import pathlib

import click
import osxmetadata
import photoscript

from osxphotos.cli.click_rich_echo import rich_echo as echo
from osxphotos.cli.click_rich_echo import rich_echo_error
from osxphotos.fingerprintquery import FingerprintQuery
from osxphotos.image_file_utils import is_image_file, is_video_file
from osxphotos.utils import get_last_library_path


@click.command()
@click.option(
    "--include",
    "-i",
    multiple=True,
    help="Include only these Finder tags; repeat --include/-i to include multiple tags",
)
@click.option(
    "--exclude",
    "-x",
    multiple=True,
    help="Exclude these Finder tags; repeat --exclude/-x to exclude multiple tags",
)
@click.option("--caption", is_flag=True, help="Set photo caption from Finder comment")
@click.option("--dry-run", is_flag=True, help="Dry run; don't actually change anything")
@click.option("--walk", is_flag=True, help="Recursively walk directories")
@click.option(
    "--library",
    metavar="LIBRARY_PATH",
    type=click.Path(exists=True),
    help="Path to the Photos library. This is not usually needed. "
    "You will only need to specify this if osxphotos cannot determine the path to the library "
    "in which case osxphotos will tell you to use the --library option when you run the command.",
)
@click.argument("files_or_dirs", nargs=-1, type=click.Path(exists=True))
def add_finder_tags(
    include: tuple[str],
    exclude: tuple[str],
    walk: bool,
    caption: bool,
    dry_run: bool,
    library: str,
    files_or_dirs: list[str],
):
    """Add Finder tags to matching photos in Photos library as keywords.

    This command will scan FILES_OR_DIRS for image and video files and will attempt to
    find the matching assets in the Photos library. If a matching asset is found, the Finder tags
    from the file will be added as keywords to the asset in Photos. If --caption is specified,
    the Finder comment will be added as the caption to the asset in Photos; any existing caption
    will be replaced.

    Use --exclude and --include to filter which Finder tags are added as keywords; if one of these is
    not specified, all Finder tags will be added as keywords. Use --exclude to exclude specific tags,
    for example, --exclude "tag1" --exclude "tag2" will exclude tags "tag1" and "tag2" from being added.
    Use --include to include only specific tags, for example, --include "tag1" --include "tag2" will only
    include tags "tag1" and "tag2" (if they are found in the file) and exclude all other tags.

    Use --dry-run to see what changes would be made without actually making the changes.

    If you specify a directory, all files in the directory will be processed. If you specify a file,
    only that file will be processed. You can specify multiple files and directories as the arguments
    to the command. Use --walk to recursively walk directories passed as arguments.

    Files are matched to Photos library assets using the fingerprint of the file. If the file has been
    edited or modified since it was imported to Photos, the fingerprint may not match and the file will
    not be processed. In this case, you will need to manually add the Finder tags to the photo in Photos.

    If you no longer have the original files, you can use the script to walk the Photos library originals
    folder. In my tests, the Finder tags are preserved on originals when importing to Photos but Finder
    comments are not. For example:

        osxphotos run add_finder_tags.py --walk ~/Pictures/Photos\ Library.photoslibrary/originals

    Note that this may take a long while to process if you have a large library. I do not know if Finder
    tags are preserved in images downloaded from iCloud but I suspect they are not.
    """
    if not files_or_dirs:
        echo("Nothing to import", err=True)
        return
    echo("Collecting files to process...")
    files_or_dirs = collect_files(files_or_dirs, walk=walk, glob=("*",))
    echo(f"Processing [num]{len(files_or_dirs)}[/] file(s).")

    # need to get the library path to initialize FingerprintQuery
    last_library = library or get_last_library_path()
    if not last_library:
        rich_echo_error(
            "[error]Could not determine path to Photos library. "
            "Please specify path to library with --library option."
        )
        raise click.Abort()

    fq = FingerprintQuery(last_library)
    for filepath in files_or_dirs:
        add_metadata_to_photo(filepath, fq, include, exclude, caption, dry_run)


def add_metadata_to_photo(
    filepath: str,
    fq: FingerprintQuery,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    caption: bool,
    dry_run: bool,
):
    """Add Finder tags to matching photo in Photos library as keywords."""
    tags = get_finder_tags(filepath, include, exclude)
    echo(
        f"Finder tags for [filepath]{filepath}[/]: [i]{', '.join(tags) if tags else None}[/]"
    )
    if matches := fq.possible_duplicates(filepath):
        echo(
            f"Adding Finder tags to [num]{len(matches)}[/] matching photo(s) in Photos library..."
        )
        for match in matches:
            photo = photoscript.Photo(uuid=match[0])
            if not photo:
                echo(f"Could not find photo with UUID [uuid]{match[0]}[/]", err=True)
                continue
            echo(
                f"Processing photo [filename]{photo.filename}[/] ([uuid]{photo.uuid}[/])"
            )
            add_keywords_to_photo(photo, tags, dry_run)
            if caption:
                add_comment_to_photo(photo, filepath, dry_run)


def add_comment_to_photo(photo: photoscript.Photo, filepath: str, dry_run: bool):
    """Add Finder comment as photo caption"""
    md = osxmetadata.OSXMetaData(filepath)
    if comment := md.findercomment:
        echo(f"Setting photo caption to Finder comment: [i]{comment}[/]")
        if not dry_run:
            photo.description = comment
    else:
        echo("No Finder comment found; skipping caption update")


def add_keywords_to_photo(photo: photoscript.Photo, tags: list[str], dry_run: bool):
    """Add keywords to photo"""
    keywords = photo.keywords
    keywords_before = keywords.copy()
    for tag in tags:
        if tag not in keywords:
            keywords.append(tag)
    if not keywords or keywords == keywords_before:
        echo("Skipping keywords update; nothing to do")
        return
    echo(
        f"Setting keywords on photo from: [i]{', '.join(keywords_before) if keywords_before else None}[/] to: [i]{', '.join(keywords)}[/]"
    )
    if not dry_run:
        photo.keywords = keywords


def get_finder_tags(
    filepath: str, include: tuple[str, ...], exclude: tuple[str, ...]
) -> list[str]:
    """Get Finder tags from file"""
    md = osxmetadata.OSXMetaData(filepath)
    tags = [tag.name for tag in md.tags]
    if include:
        include = [tag.lower() for tag in include]
        tags = [tag for tag in tags if tag.lower() in include]
    if exclude:
        exclude = [tag.lower() for tag in exclude]
        tags = [tag for tag in tags if tag.lower() not in exclude]
    return tags


def collect_files(
    files: tuple[str, ...],
    walk: bool,
    glob: tuple[str, ...],
) -> list[pathlib.Path]:
    """Collect files to process, recursively if necessary

    Args:
        files: list of initial files or directories to process
        walk: whether to walk directories
        glob: glob patterns to match files or empty tuple if none
    """

    files_list = []
    for file in files:
        if os.path.isfile(file):
            files_list.append(file)
        elif os.path.isdir(file):
            if not walk:
                # don't recurse but do collect all files in the directory
                dir_files = [
                    os.path.join(file, f)
                    for f in os.listdir(file)
                    if os.path.isfile(os.path.join(file, f))
                ]
                files_list.extend(dir_files)
            else:
                for root, dirs, filenames in os.walk(file):
                    for file in filenames:
                        files_list.append(os.path.join(root, file))
        else:
            continue

    # if glob:
    #     echo("Filtering files with glob...")
    #     files_list = [
    #         f
    #         for f in files_list
    #         if filename_matches_patterns(os.path.basename(f), glob)
    #     ]

    echo(f"Getting absolute path of each file...")
    files_list = [pathlib.Path(f).absolute() for f in files_list]

    # keep only image files, video files, and .aae files
    filtered_file_list = []
    echo("Filtering file list for image & video files...")
    for f in files_list:
        if is_image_file(f) or is_video_file(f):
            filtered_file_list.append(f)

    # there may be duplicates if user passed both a directory and files in that directory
    # e.g. /Volumes/import /Volumes/import/IMG_1234.*
    # so strip duplicates before returning the list
    return list(set(filtered_file_list))


def filename_matches_patterns(filename: str, patterns: tuple[str, ...]) -> bool:
    """Return True if filename matches any pattern in patterns"""
    return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)


if __name__ == "__main__":
    add_finder_tags()
