"""Recover person names from one library and add them to photos in another library as keywords and/or captions.

When a library is migrated (for example, from iPhoto to Photos, or from one Photos library to another
by exporting and re-importing), the names of the people identified in each photo are sometimes lost.
Photos does not allow person names to be set via AppleScript, but they can be preserved as keywords
or in the caption (description) so they're still searchable.

This script reads the person names from a source library (either a Photos library or an iPhoto library)
and adds them to the matching photos in the destination Photos library (the library currently open in Photos).

Photos are matched between the two libraries by original filename (case-insensitive, ignoring any
collision suffix Photos may have added, e.g. "IMG_1234 2.jpg" is matched to "IMG_1234.jpg") plus,
in order of preference:

    1. the fingerprint of the original file (the same approach used by `osxphotos sync`)
    2. the size of the original file
    3. the date/time the photo was taken (local time, to the second)

The first two only match if the original file is byte-for-byte identical in both libraries.
That is often not the case after a migration: for example, if the photos were exported from the
old library and imported into the new one, the exported files may have had metadata written to them.
The date/time match handles this case. Use --verbose to see how each photo was matched and
which source photos could not be matched.

Matching is done by this script rather than with `osxphotos sync --export` so that it works
with versions of osxphotos where `sync` cannot read iPhoto libraries.

Run with `osxphotos run recover_person_names.py --help` to see all options. For example:

    # see what would be done without changing anything
    osxphotos run recover_person_names.py --library "/Volumes/Backup/iPhoto Library" --keyword --dry-run --verbose

    # add keywords like "Person:Rhet Turnbull" to the matching photos in the library currently open in Photos
    osxphotos run recover_person_names.py --library "/Volumes/Backup/iPhoto Library" --keyword --prefix "Person:"

    # add the names to the caption as "Person:Rhet Turnbull; Person:Sarah"
    osxphotos run recover_person_names.py --library ~/Pictures/Old.photoslibrary --caption --prefix "Person:"

Notes:
    - Changes are made via AppleScript to the library currently open in Photos. If you use --db to
      specify the destination library, it must be the library currently open in Photos.
    - Photos must be running; the script will launch it if needed.
    - Running the script more than once is safe: keywords and caption text that are already present
      are not added again.
    - Shared photos (iCloud Shared Albums) are skipped as their metadata cannot be changed.
"""

from __future__ import annotations

import datetime
import os
import pathlib
from collections.abc import Iterable
from typing import Protocol

import click
import photoscript

from osxphotos import PhotosDB
from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.cli.sync import set_photo_property
from osxphotos.iphoto import iPhotoDB, is_iphoto_library
from osxphotos.signature_utils import normalize_collision_filename
from osxphotos.utils import pluralize


class PhotoLike(Protocol):
    """The subset of PhotoInfo / iPhotoPhotoInfo used for matching photos"""

    uuid: str
    original_filename: str
    original_filesize: int
    fingerprint: str | None
    date: datetime.datetime
    persons: list[str]
    shared: bool | None


def local_date_key(date: datetime.datetime | None) -> str | None:
    """Return the local ("wall clock") date/time of a photo, to the second, as a string

    The timezone is ignored: iPhoto stores the local time a photo was taken but may
    label it as GMT whereas Photos stores the local time with the correct timezone offset,
    so the same photo can have different UTC times in the two libraries.
    """
    if not date:
        return None
    return date.replace(tzinfo=None, microsecond=0).isoformat()


def match_keys(photo: PhotoLike) -> list[tuple[str, str]]:
    """Return the keys used to match a photo between libraries, most specific first.

    Returns: list of (match method, key) tuples

    The fingerprint key uses the same "filename:fingerprint" form as
    osxphotos.photo_signature.photo_signature() (which is what `osxphotos sync` uses)
    but is computed here so that it works with iPhoto photos in versions of osxphotos
    where photo_signature() does not support them.
    Keys are also generated with any Photos collision suffix (" 2", " 3", ...) removed
    from the filename.
    """
    filename = (photo.original_filename or "").lower()
    names = [filename]
    normalized = normalize_collision_filename(filename).lower()
    if normalized != filename:
        names.append(normalized)

    keys = []
    if fingerprint := photo.fingerprint:
        keys.extend(("fingerprint", f"{name}:{fingerprint}") for name in names)
    if filesize := photo.original_filesize:
        keys.extend(("file size", f"{name}:size:{filesize}") for name in names)
    if date := local_date_key(photo.date):
        keys.extend(("date", f"{name}:date:{date}") for name in names)
    return keys


def named_persons(photo: PhotoLike) -> set[str]:
    """Return the set of named persons in a photo (unnamed faces are excluded)"""
    return {p for p in photo.persons if p and p != _UNKNOWN_PERSON}


def open_source_library(library: str) -> PhotosDB | iPhotoDB:
    """Open the source library which may be a Photos library or an iPhoto library"""
    if is_iphoto_library(library):
        click.echo(f"Reading iPhoto library: {library}")
        return iPhotoDB(dbfile=library)
    click.echo(f"Reading Photos library: {library}")
    return PhotosDB(dbfile=library)


class PersonIndex:
    """Index of person names in the source library keyed by match key"""

    def __init__(self, photos: Iterable[PhotoLike]):
        self.persons: dict[str, set[str]] = {}  # source uuid -> person names
        self.descriptions: dict[str, str] = {}  # source uuid -> description for output
        self.keys: dict[str, set[str]] = {}  # match key -> source uuids
        for photo in photos:
            if photo.shared:
                continue
            if not (names := named_persons(photo)):
                continue
            self.persons[photo.uuid] = names
            self.descriptions[photo.uuid] = (
                f"{photo.original_filename} ({photo.uuid}, "
                f"{local_date_key(photo.date)}): {', '.join(sorted(names))}"
            )
            for _, key in match_keys(photo):
                self.keys.setdefault(key, set()).add(photo.uuid)

    def __len__(self) -> int:
        """Number of source photos with named persons"""
        return len(self.persons)

    def find(self, photo: PhotoLike) -> tuple[set[str], str] | tuple[None, None]:
        """Find the source photos matching photo

        Returns: tuple of (uuids of matching source photos, match method)
            or (None, None) if no match

        More than one source photo may match if the same photo was in
        the source library more than once (e.g. imported twice).
        """
        for method, key in match_keys(photo):
            if key in self.keys:
                return self.keys[key], method
        return None, None

    def names(self, uuids: Iterable[str]) -> set[str]:
        """Return the merged person names for source photos"""
        return set().union(*(self.persons[uuid] for uuid in uuids))


def add_keywords(existing: list[str], tags: list[str]) -> list[str] | None:
    """Return the new keyword list or None if no change is needed"""
    if new := [t for t in tags if t not in existing]:
        return sorted(existing + new)
    return None


def add_caption(existing: str | None, tags: list[str], delimiter: str) -> str | None:
    """Return the new caption or None if no change is needed"""
    existing = existing or ""
    new = [t for t in tags if t not in existing]
    if not new:
        return None
    text = delimiter.join(new)
    return f"{existing}{delimiter}{text}" if existing else text


def same_library(path1: str | os.PathLike, path2: str | os.PathLike) -> bool:
    """Return True if path1 and path2 point to the same library"""
    try:
        return pathlib.Path(path1).resolve() == pathlib.Path(path2).resolve()
    except OSError:
        return False


@click.command()
@click.option(
    "--library",
    "source_library",
    metavar="LIBRARY_PATH",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Path to the source Photos or iPhoto library to read person names from. "
    "The library may be in any location, e.g. on an external drive.",
)
@click.option(
    "--db",
    "dest_library",
    metavar="PHOTOS_LIBRARY_PATH",
    type=click.Path(exists=True),
    help="Path to the destination Photos library. "
    "If not provided, the last opened Photos library is used. "
    "This must be the library currently open in Photos.",
)
@click.option(
    "--keyword",
    "add_as_keyword",
    is_flag=True,
    help="Add person names to matching photos as keywords.",
)
@click.option(
    "--caption",
    "add_as_caption",
    is_flag=True,
    help="Add person names to the caption (description) of matching photos. "
    "Names are appended to any existing caption.",
)
@click.option(
    "--prefix",
    metavar="PREFIX",
    default="",
    help="Optional prefix to add to each person name, e.g. --prefix 'Person:' "
    "results in 'Person:Rhet Turnbull'.",
)
@click.option(
    "--delimiter",
    metavar="DELIMITER",
    default="; ",
    show_default=True,
    help="Delimiter used to separate person names in the caption (and the names from any existing caption text).",
)
@click.option(
    "--missing-only",
    is_flag=True,
    help="Only add person names that are not already a named person "
    "for the photo in the destination library.",
)
@click.option(
    "--selected",
    is_flag=True,
    help="Only process photos currently selected in Photos.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without changing any photos.",
)
@click.option("--verbose", "-V", is_flag=True, help="Print verbose output.")
def recover_person_names(
    source_library: str,
    dest_library: str | None,
    add_as_keyword: bool,
    add_as_caption: bool,
    prefix: str,
    delimiter: str,
    missing_only: bool,
    selected: bool,
    dry_run: bool,
    verbose: bool,
):
    """Recover person names from a source Photos or iPhoto library and add them
    to the matching photos in the current Photos library as keywords and/or captions."""

    def vprint(msg: str):
        if verbose:
            click.echo(msg)

    if not add_as_keyword and not add_as_caption:
        raise click.UsageError("At least one of --keyword or --caption is required.")

    # read person names from source library
    source_db = open_source_library(source_library)
    index = PersonIndex(source_db.photos())
    click.echo(
        f"Found {len(index)} {pluralize(len(index), 'photo', 'photos')} "
        "with named persons in source library"
    )
    if not index:
        click.echo("Nothing to do")
        return

    # read destination library
    dest_db = PhotosDB(dbfile=dest_library)
    if same_library(dest_db.library_path, source_library):
        raise click.UsageError(
            "The source library (--library) and destination library are the same library."
        )
    click.echo(f"Reading destination Photos library: {dest_db.library_path}")

    if selected:
        selected_uuids = {p.uuid for p in photoscript.PhotosLibrary().selection}
        if not selected_uuids:
            raise click.UsageError("--selected specified but no photos are selected.")
        dest_photos = dest_db.photos(uuid=list(selected_uuids))
    else:
        dest_photos = dest_db.photos()
    dest_photos = [p for p in dest_photos if not p.shared]

    if dry_run:
        click.echo("Dry run: no photos will be changed")

    matched = updated = 0
    matched_source_uuids: set[str] = set()
    for photo in dest_photos:
        source_uuids, method = index.find(photo)
        if source_uuids is None:
            continue
        matched += 1
        matched_source_uuids.update(source_uuids)
        persons = index.names(source_uuids)
        vprint(
            f"Matched {photo.original_filename} ({photo.uuid}) by {method}: "
            f"{', '.join(sorted(persons))}"
        )

        if missing_only:
            persons = persons - named_persons(photo)
        if not persons:
            vprint(f"{photo.original_filename} ({photo.uuid}): no names to add")
            continue

        tags = [f"{prefix}{name}" for name in sorted(persons)]
        new_keywords = add_keywords(photo.keywords, tags) if add_as_keyword else None
        new_caption = (
            add_caption(photo.description, tags, delimiter) if add_as_caption else None
        )
        if new_keywords is None and new_caption is None:
            vprint(f"{photo.original_filename} ({photo.uuid}): already up to date")
            continue

        click.echo(f"Updating {photo.original_filename} ({photo.uuid})")
        if new_keywords is not None:
            vprint(f"  keywords: {photo.keywords} -> {new_keywords}")
        if new_caption is not None:
            vprint(f"  caption: {photo.description!r} -> {new_caption!r}")

        if not dry_run:
            try:
                photo_ = photoscript.Photo(photo.uuid)
            except ValueError:
                click.echo(
                    f"Unable to access {photo.original_filename} ({photo.uuid}) via AppleScript, skipping. "
                    "Is the destination library open in Photos?",
                    err=True,
                )
                continue
            if new_keywords is not None:
                set_photo_property(photo_, "keywords", new_keywords)
            if new_caption is not None:
                set_photo_property(photo_, "description", new_caption)
        updated += 1

    unmatched_uuids = [u for u in index.persons if u not in matched_source_uuids]
    unmatched = len(unmatched_uuids)
    click.echo(
        f"Done: matched {matched} {pluralize(matched, 'photo', 'photos')} in destination library, "
        f"{'would update' if dry_run else 'updated'} {updated} {pluralize(updated, 'photo', 'photos')}"
    )
    if unmatched > 0 and not selected:
        click.echo(
            f"{unmatched} source {pluralize(unmatched, 'photo', 'photos')} "
            "with named persons did not match any photo in the destination library"
            + ("" if verbose else " (use --verbose to list them)")
        )
        for uuid in unmatched_uuids:
            vprint(f"  Unmatched: {index.descriptions[uuid]}")


if __name__ == "__main__":
    recover_person_names()
