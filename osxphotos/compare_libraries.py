"""Compare two Photos libraries"""

from __future__ import annotations

import csv
import dataclasses
import datetime
import json
from io import StringIO
from typing import Any, Callable

from .dictdiff import dictdiff
from .photo_signature import photo_signature
from .photoinfo import PhotoInfo
from .photosdb import PhotosDB
from .utils import noop, pluralize

__all__ = ["PhotosDBDiff", "compare_photos_libraries"]


def pluralize_assets(photolist: list[PhotoInfo]) -> str:
    """Return pluralized form of '1 asset', '2 assets', etc based on number of photos in list"""
    length = len(photolist)
    photo_word = pluralize(length, "asset", "assets")
    return f"{length} {photo_word}"


@dataclasses.dataclass
class PhotosDBDiff:
    """Class to hold differences between two PhotosDB objects"""

    library_a: PhotosDB
    library_b: PhotosDB
    in_a_not_b: list[PhotoInfo]
    in_b_not_a: list[PhotoInfo]
    in_both_same: list[tuple[PhotoInfo, PhotoInfo]]
    in_both_different: list[tuple[PhotoInfo, PhotoInfo, Any]]
    signature: Callable[[PhotoInfo], Any] = photo_signature

    def asdict(self) -> dict:
        """Return PhotosDBDiff as a dict"""
        in_a_not_b = [
            {
                "original_filename": photo.original_filename,
                "signature": self.signature(photo),
                "uuid": photo.uuid,
            }
            for photo in self.in_a_not_b
        ]
        in_b_not_a = [
            {
                "original_filename": photo.original_filename,
                "signature": self.signature(photo),
                "uuid": photo.uuid,
            }
            for photo in self.in_b_not_a
        ]
        in_a_and_b_same = [
            {
                "original_filename": photo_a.original_filename,
                "signature": self.signature(photo_a),
                "uuid_a": photo_a.uuid,
                "uuid_b": photo_b.uuid,
            }
            for photo_a, photo_b in self.in_both_same
        ]
        in_a_and_b_different = [
            {
                "original_filename": photo_a.original_filename,
                "signature": self.signature(photo_a),
                "uuid_a": photo_a.uuid,
                "uuid_b": photo_b.uuid,
                "difference": diff,
            }
            for photo_a, photo_b, diff in self.in_both_different
        ]

        return {
            "library_a": self.library_a.library_path,
            "library_b": self.library_b.library_path,
            "in_a_not_b": in_a_not_b,
            "in_b_not_a": in_b_not_a,
            "in_a_and_b_same": in_a_and_b_same,
            "in_a_and_b_different": in_a_and_b_different,
        }

    def json(self, indent=2) -> str:
        """Return PhotosDBDiff as a JSON string"""
        d = self.asdict()

        def _default(o):
            if isinstance(o, datetime.datetime):
                return o.isoformat()
            return o

        return json.dumps(d, indent=indent, default=_default)

    def csv(self, delimiter=",") -> str:
        """Return PhotosDBDiff as a CSV string"""
        headers = [
            "original_filename",
            "signature",
            "uuid_a",
            "uuid_b",
            "in_a_not_b",
            "in_b_not_a",
            "in_a_and_b_same",
            "in_a_and_b_different",
            "difference",
        ]
        rows = []

        for photo_a in self.in_a_not_b:
            rows.append(
                [
                    photo_a.original_filename,
                    self.signature(photo_a),
                    photo_a.uuid,
                    "",
                    1,
                    0,
                    0,
                    0,
                    "",
                ]
            )
        for photo_b in self.in_b_not_a:
            rows.append(
                [
                    photo_b.original_filename,
                    self.signature(photo_b),
                    "",
                    photo_b.uuid,
                    0,
                    1,
                    0,
                    0,
                    "",
                ]
            )
        for photo_a, photo_b in self.in_both_same:
            rows.append(
                [
                    photo_a.original_filename,
                    self.signature(photo_a),
                    photo_a.uuid,
                    photo_b.uuid,
                    0,
                    0,
                    1,
                    0,
                    "",
                ]
            )
        for photo_a, photo_b, diff in self.in_both_different:
            rows.append(
                [
                    photo_a.original_filename,
                    self.signature(photo_a),
                    photo_a.uuid,
                    photo_b.uuid,
                    0,
                    0,
                    0,
                    1,
                    str(diff),
                ]
            )

        with StringIO(newline="") as csvfile:
            writer = csv.writer(csvfile, delimiter=delimiter)
            writer.writerow(headers)
            writer.writerows(rows)
            csvfile.flush()
            return csvfile.getvalue()

    def __len__(self) -> int:
        """Return total number of different photos or photos in only one library"""
        return len(self.in_a_not_b) + len(self.in_b_not_a) + len(self.in_both_different)

    def __bool__(self) -> bool:
        """Return True if there are any differences, False otherwise"""
        return bool(len(self))

    def __str__(self) -> str:
        """Return PhotosDBDiff as a string"""
        with StringIO(newline="") as strfile:
            print(f"library_a = {self.library_a.library_path}", file=strfile)
            print(f"library_b = {self.library_b.library_path}", file=strfile)
            print(f"in_a_not_b = {pluralize_assets(self.in_a_not_b)}", file=strfile)
            print(f"in_b_not_a = {pluralize_assets(self.in_b_not_a)}", file=strfile)
            print(
                f"in_a_and_b_same = {pluralize_assets(self.in_both_same)}", file=strfile
            )
            print(
                f"in_a_and_b_different = {pluralize_assets(self.in_both_different)}",
                file=strfile,
            )
            strfile.flush()
            return strfile.getvalue()


def photo_diff(photo_a: PhotoInfo, photo_b: PhotoInfo) -> list[list[Any]]:
    """Compare two PhotoInfo objects and return the differences if any or empty list if no differences"""
    diffs = dictdiff(photo_b.asdict(shallow=True), photo_a.asdict(shallow=True))

    # remove some keys that are not relevant for comparison or will always be different
    diffs = [
        diff
        for diff in diffs
        if not diff[0] in ("library", "face_info", "labels", "filename", "uuid")
        and not diff[0].startswith("path")
        and not diff[0].startswith("score")
    ]

    return diffs


def compare_photos_libraries(
    library_a: PhotosDB,
    library_b: PhotosDB,
    verbose: Callable[[Any], bool] | None = None,
    signature_function: Callable[[PhotoInfo], Any] | None = None,
    diff_function: Callable[[PhotoInfo, PhotoInfo], Any] | None = None,
) -> PhotosDBDiff:
    """Compare two Photos libraries and return a PhotosDBDiff object

    Args:
        library_a: PhotosDB object for first library
        library_b: PhotosDB object for second library
        verbose: function to print verbose output, defaults to None
        signature_function: function to compute signature for a PhotoInfo object, defaults to None
        diff_function: function to compare two PhotoInfo objects, defaults to None

    Returns: PhotosDBDiff object

    Note: signature_function should take a PhotoInfo object as input and return a unique
        signature for the photo; if signature_function is None, the default signature
        function will be used which computes a signature based on the photo's fingerprint
        diff_function should take two PhotoInfo objects as input and return a truthy value
        if the objects are different or a falsy value if they are the same; if diff_function
        is None, the default diff function will be used which compares the dictionary
        representation of the PhotoInfo objects.
    """
    verbose = verbose or noop
    signature_function = signature_function or photo_signature
    diff_function = diff_function or photo_diff

    verbose(f"Comparing libraries:")
    verbose(f"library_a = {library_a.library_path}")
    verbose(f"library_b = {library_b.library_path}")

    # map signatures for all photos in each library
    verbose("Scanning library_a for signatures")
    mapping_a = _map_signatures(library_a, signature_function)
    verbose("Scanning library_b for signatures")
    mapping_b = _map_signatures(library_b, signature_function)

    in_a_not_b, in_b_not_a, in_a_and_b_same, in_a_and_b_different = _compare_mappings(
        mapping_a, mapping_b, diff_function
    )

    return PhotosDBDiff(
        library_a,
        library_b,
        in_a_not_b,
        in_b_not_a,
        in_a_and_b_same,
        in_a_and_b_different,
        signature_function,
    )


def _map_signatures(
    photosdb: PhotosDB, signature: Callable[[PhotoInfo], Any]
) -> dict[Any, list[PhotoInfo]]:
    """Return dictionary of signatures for all photos in library"""
    mapping = {}
    for photo in photosdb.photos():
        sig = signature(photo)
        if sig in mapping:
            mapping[sig].append(photo)
        else:
            mapping[sig] = [photo]
    return mapping


def _compare_mappings(
    mapping_a: dict[Any, list[PhotoInfo]],
    mapping_b: dict[Any, list[PhotoInfo]],
    diff_function: Callable[[PhotoInfo, PhotoInfo], Any],
) -> tuple[
    list[tuple[PhotoInfo, PhotoInfo]],
    list[tuple[PhotoInfo, PhotoInfo, Any]],
    list[PhotoInfo],
    list[PhotoInfo],
]:
    """Compare two mappings of photo signatures and return differences

    Args:
        mapping_a: dictionary of photo signatures where the value is a list of PhotoInfo objects
        mapping_b: dictionary of photo signatures where the value is a list of PhotoInfo objects
        diff_function: function to compare two PhotoInfo objects

    Returns: tuple of:
        list of tuples of PhotoInfo objects in both mapping_a and mapping_b that are the same
        list of tuples of PhotoInfo objects in both mapping_a and mapping_b that are different
        list of PhotoInfo objects in only mapping_a
        list of PhotoInfo objects in only mapping_b
    """

    in_a_and_b_same = []
    in_a_and_b_diff = []
    in_a_not_b = []
    in_b_not_a = []

    keys_a = set(mapping_a.keys())
    keys_b = set(mapping_b.keys())

    only_in_a = keys_a - keys_b
    only_in_b = keys_b - keys_a
    in_both = keys_a & keys_b

    for signature in only_in_a:
        in_a_not_b.extend(mapping_a[signature])

    for signature in only_in_b:
        in_b_not_a.extend(mapping_b[signature])

    # for signatures in both mappings, need to determine if any pair from each mapping are the same
    # first, check if any photos have the same UUID
    # if not, check if any photos have the same date_added
    # (UUID may change if photo library repaired but date_added would not)
    # if not, compare all photos in both mappings
    # any photos left over in either mapping are added to the in_a_not_b or in_b_not_a lists
    # this multi-pass approach is necessary to deal with duplicate photos in each library
    # the most common case will be a 1:1 mapping of photos, in which case the second and third pass will be skipped
    for signature in in_both:
        a_photos = mapping_a[signature].copy()
        b_photos = mapping_b[signature].copy()

        b_uuids = [photo.uuid for photo in b_photos]

        for photo_a in a_photos.copy():
            if photo_a.uuid in b_uuids:
                matched_photo = next(
                    photo for photo in b_photos if photo.uuid == photo_a.uuid
                )

                if diff_function(photo_a, matched_photo):
                    in_a_and_b_diff.append(
                        (photo_a, matched_photo, diff_function(photo_a, matched_photo))
                    )
                else:
                    in_a_and_b_same.append((photo_a, matched_photo))

                a_photos.remove(photo_a)
                b_photos.remove(matched_photo)
                b_uuids.remove(photo_a.uuid)

        for photo_a in a_photos.copy():
            for photo_b in b_photos.copy():
                if photo_a.date_added == photo_b.date_added:
                    if diff := diff_function(photo_a, photo_b):
                        in_a_and_b_diff.append((photo_a, photo_b, diff))
                    else:
                        in_a_and_b_same.append((photo_a, photo_b))

                    a_photos.remove(photo_a)
                    b_photos.remove(photo_b)
                    break

        if b_photos and a_photos:
            for photo_a, photo_b in zip(a_photos, b_photos):
                if diff_function(photo_a, photo_b):
                    in_a_and_b_diff.append(
                        (photo_a, photo_b, diff_function(photo_a, photo_b))
                    )
                else:
                    in_a_and_b_same.append((photo_a, photo_b))

        if len(a_photos) > len(b_photos):
            in_a_not_b.extend(a_photos[len(b_photos) :])
        elif len(b_photos) > len(a_photos):
            in_b_not_a.extend(b_photos[len(a_photos) :])

    return in_a_not_b, in_b_not_a, in_a_and_b_same, in_a_and_b_diff
