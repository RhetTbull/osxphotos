"""Add Photos keywords for any Finder tags found on imported photos.

Reference: https://www.reddit.com/r/ApplePhotos/comments/16e9quq/finder_tags_do_not_become_photos_keywords_help/

This script can be run with osxphotos via: `osxphotos run finder_tags_to_keywords.py`

Running this script will scan all photos in your Photos library and for any photos that have Finder tags,
add the Finder tags as keywords in Photos.
"""

import osxmetadata
import photoscript
from rich.progress import Progress

import osxphotos
from osxphotos.cli import echo
from osxphotos.cli.verbose import get_verbose_console, verbose_print
from osxphotos.utils import pluralize


def main():
    """Add Photos keywords for any Finder tags found on imported photos."""
    verbose_print()

    echo("Loading Photos library...")
    photosdb = osxphotos.PhotosDB()
    photos = photosdb.photos()
    echo(f"Found {len(photos)} {pluralize(len(photos), 'photo', 'photos')} in library")

    total = len(photos)
    updated = 0
    missing = 0
    with Progress(console=get_verbose_console()) as progress:
        task = progress.add_task("Processing", total=len(photos))
        for photo in photos:
            if not photo.path:
                missing += 1
            else:
                md = osxmetadata.OSXMetaData(photo.path)
                if md.tags and sorted(t.name for t in md.tags) != sorted(
                    photo.keywords
                ):
                    progress.print(
                        f"Adding keywords to {photo.original_filename} ({photo.uuid}): {list(t.name for t in md.tags)}"
                    )
                    new_keywords = list(
                        set(photo.keywords + list(t.name for t in md.tags))
                    )
                    photoscript.Photo(photo.uuid).keywords = new_keywords
                    updated += 1
            progress.advance(task)
    echo(
        f"Done. Processed {total} {pluralize(total, 'photo', 'photos')}, updated {updated} and skipped {missing} missing."
    )


if __name__ == "__main__":
    main()
