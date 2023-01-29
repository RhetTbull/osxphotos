""" QueryOptions class for PhotosDB.query """

import dataclasses
import datetime
import pathlib
from dataclasses import asdict, dataclass
from typing import Iterable, List, Optional, Tuple

import bitmath

__all__ = ["QueryOptions", "query_options_from_kwargs", "IncompatibleQueryOptions"]


class IncompatibleQueryOptions(Exception):
    """Incompatible query options"""

    pass


@dataclass
class QueryOptions:

    """QueryOptions class for PhotosDB.query

    Attributes:
        added_after: search for photos added after a given date
        added_before: search for photos added before a given date
        added_in_last: search for photos added in last X datetime.timedelta
        album: list of album names to search for
        burst_photos: search for burst photos
        burst: search for burst photos
        cloudasset: search for photos that are managed by iCloud
        deleted_only: search only for deleted photos
        deleted: also include deleted photos
        description: list of descriptions to search for
        duplicate: search for duplicate photos
        edited: search for edited photos
        exif: search for photos with EXIF tags that matches the given data
        external_edit: search for photos edited in external apps
        favorite: search for favorite photos
        folder: list of folder names to search for
        from_date: search for photos taken on or after this date
        function: list of query functions to evaluate
        has_comment: search for photos with comments
        has_likes: search for shared photos with likes
        has_raw: search for photos with associated raw files
        hdr: search for HDR photos
        hidden: search for hidden photos
        ignore_case: ignore case when searching
        in_album: search for photos in an album
        incloud: search for cloud assets that are synched to iCloud
        is_reference: search for photos stored by reference (that is, they are not managed by Photos)
        keyword: list of keywords to search for
        label: list of labels to search for
        live: search for live photos
        location: search for photos with a location
        max_size: maximum size of photos to search for
        min_size: minimum size of photos to search for
        missing_bursts: for burst photos, also include burst photos that are missing
        missing: search for missing photos
        movies: search for movies
        name: list of names to search for
        no_comment: search for photos with no comments
        no_description: search for photos with no description
        no_likes: search for shared photos with no likes
        no_location: search for photos with no location
        no_keyword: search for photos with no keywords
        no_place: search for photos with no place
        no_title: search for photos with no title
        not_burst: search for non-burst photos
        not_cloudasset: search for photos that are not managed by iCloud
        not_edited: search for photos that have not been edited
        not_favorite: search for non-favorite photos
        not_hdr: search for non-HDR photos
        not_hidden: search for non-hidden photos
        not_in_album: search for photos not in an album
        not_incloud: search for cloud asset photos that are not yet synched to iCloud
        not_live: search for non-live photos
        not_missing: search for non-missing photos
        not_panorama: search for non-panorama photos
        not_portrait: search for non-portrait photos
        not_reference: search for photos not stored by reference (that is, they are managed by Photos)
        not_screenshot: search for non-screenshot photos
        not_selfie: search for non-selfie photos
        not_shared: search for non-shared photos
        not_slow_mo: search for non-slow-mo photos
        not_time_lapse: search for non-time-lapse photos
        panorama: search for panorama photos
        person: list of person names to search for
        photos: search for photos
        place: list of place names to search for
        portrait: search for portrait photos
        query_eval: list of query expressions to evaluate
        regex: list of regular expressions to search for
        screenshot: search for screenshot photos
        selected: search for selected photos
        selfie: search for selfie photos
        shared: search for shared photos
        slow_mo: search for slow-mo photos
        time_lapse: search for time-lapse photos
        title: list of titles to search for
        to_date: search for photos taken on or before this date
        uti: list of UTIs to search for
        uuid: list of uuids to search for
        year: search for photos taken in a given year
    """

    added_after: Optional[datetime.datetime] = None
    added_before: Optional[datetime.datetime] = None
    added_in_last: Optional[datetime.timedelta] = None
    album: Optional[Iterable[str]] = None
    burst_photos: Optional[bool] = None
    burst: Optional[bool] = None
    cloudasset: Optional[bool] = None
    deleted_only: Optional[bool] = None
    deleted: Optional[bool] = None
    description: Optional[Iterable[str]] = None
    duplicate: Optional[bool] = None
    edited: Optional[bool] = None
    exif: Optional[Iterable[Tuple[str, str]]] = None
    external_edit: Optional[bool] = None
    favorite: Optional[bool] = None
    folder: Optional[Iterable[str]] = None
    from_date: Optional[datetime.datetime] = None
    from_time: Optional[datetime.time] = None
    function: Optional[List[Tuple[callable, str]]] = None
    has_comment: Optional[bool] = None
    has_likes: Optional[bool] = None
    has_raw: Optional[bool] = None
    hdr: Optional[bool] = None
    hidden: Optional[bool] = None
    ignore_case: Optional[bool] = None
    in_album: Optional[bool] = None
    incloud: Optional[bool] = None
    is_reference: Optional[bool] = None
    keyword: Optional[Iterable[str]] = None
    label: Optional[Iterable[str]] = None
    live: Optional[bool] = None
    location: Optional[bool] = None
    max_size: Optional[bitmath.Byte] = None
    min_size: Optional[bitmath.Byte] = None
    missing_bursts: Optional[bool] = None
    missing: Optional[bool] = None
    movies: Optional[bool] = True
    name: Optional[Iterable[str]] = None
    no_comment: Optional[bool] = None
    no_description: Optional[bool] = None
    no_likes: Optional[bool] = None
    no_location: Optional[bool] = None
    no_keyword: Optional[bool] = None
    no_place: Optional[bool] = None
    no_title: Optional[bool] = None
    not_burst: Optional[bool] = None
    not_cloudasset: Optional[bool] = None
    not_edited: Optional[bool] = None
    not_favorite: Optional[bool] = None
    not_hdr: Optional[bool] = None
    not_hidden: Optional[bool] = None
    not_in_album: Optional[bool] = None
    not_incloud: Optional[bool] = None
    not_live: Optional[bool] = None
    not_missing: Optional[bool] = None
    not_panorama: Optional[bool] = None
    not_portrait: Optional[bool] = None
    not_reference: Optional[bool] = None
    not_screenshot: Optional[bool] = None
    not_selfie: Optional[bool] = None
    not_shared: Optional[bool] = None
    not_slow_mo: Optional[bool] = None
    not_time_lapse: Optional[bool] = None
    panorama: Optional[bool] = None
    person: Optional[Iterable[str]] = None
    photos: Optional[bool] = True
    place: Optional[Iterable[str]] = None
    portrait: Optional[bool] = None
    query_eval: Optional[Iterable[str]] = None
    regex: Optional[Iterable[Tuple[str, str]]] = None
    screenshot: Optional[bool] = None
    selected: Optional[bool] = None
    selfie: Optional[bool] = None
    shared: Optional[bool] = None
    slow_mo: Optional[bool] = None
    time_lapse: Optional[bool] = None
    title: Optional[Iterable[str]] = None
    to_date: Optional[datetime.datetime] = None
    to_time: Optional[datetime.time] = None
    uti: Optional[Iterable[str]] = None
    uuid: Optional[Iterable[str]] = None
    year: Optional[Iterable[int]] = None

    def asdict(self):
        return asdict(self)


def query_options_from_kwargs(**kwargs) -> QueryOptions:
    """Validate query options and create a QueryOptions instance"""
    # sanity check input args
    nonexclusive = [
        "added_after",
        "added_before",
        "added_in_last",
        "album",
        "duplicate",
        "exif",
        "external_edit",
        "folder",
        "from_date",
        "from_time",
        "has_raw",
        "keyword",
        "label",
        "max_size",
        "min_size",
        "name",
        "person",
        "query_eval",
        "query_function",
        "regex",
        "selected",
        "to_date",
        "to_time",
        "uti",
        "uuid",
        "uuid_from_file",
        "year",
    ]
    exclusive = [
        ("burst", "not_burst"),
        ("cloudasset", "not_cloudasset"),
        ("edited", "not_edited"),
        ("favorite", "not_favorite"),
        ("has_comment", "no_comment"),
        ("has_likes", "no_likes"),
        ("hdr", "not_hdr"),
        ("hidden", "not_hidden"),
        ("in_album", "not_in_album"),
        ("incloud", "not_incloud"),
        ("is_reference", "not_reference"),
        ("keyword", "no_keyword"),
        ("live", "not_live"),
        ("location", "no_location"),
        ("missing", "not_missing"),
        ("only_photos", "only_movies"),
        ("panorama", "not_panorama"),
        ("portrait", "not_portrait"),
        ("screenshot", "not_screenshot"),
        ("selfie", "not_selfie"),
        ("shared", "not_shared"),
        ("slow_mo", "not_slow_mo"),
        ("time_lapse", "not_time_lapse"),
        ("deleted", "not_deleted"),
    ]
    # TODO: add option to validate requiring at least one query arg
    for arg, not_arg in exclusive:
        if kwargs.get(arg) and kwargs.get(not_arg):
            arg = arg.replace("_", "-")
            not_arg = not_arg.replace("_", "-")
            raise IncompatibleQueryOptions(
                f"--{arg} and --{not_arg} are mutually exclusive"
            )

    # some options like title can be specified multiple times
    # check if any of them are specified along with their no_ counterpart
    exclusive_multi_options = ["title", "description", "place", "keyword"]
    for option in exclusive_multi_options:
        if kwargs.get(option) and kwargs.get("no_{option}"):
            raise IncompatibleQueryOptions(
                f"--{option} and --no-{option} are mutually exclusive"
            )

    include_photos = True
    include_movies = True  # default searches for everything
    if kwargs.get("only_movies"):
        include_photos = False
    if kwargs.get("only_photos"):
        include_movies = False

    # load UUIDs if necessary and append to any uuids passed with --uuid
    uuid = None
    if uuid_from_file := kwargs.get("uuid_from_file"):
        uuid_list = list(kwargs.get("uuid", []))  # Click option is a tuple
        uuid_list.extend(load_uuid_from_file(uuid_from_file))
        uuid = tuple(uuid_list)

    query_fields = [field.name for field in dataclasses.fields(QueryOptions)]
    query_dict = {field: kwargs.get(field) for field in query_fields}
    query_dict["photos"] = include_photos
    query_dict["movies"] = include_movies
    query_dict["uuid"] = uuid
    return QueryOptions(**query_dict)


def load_uuid_from_file(filename):
    """Load UUIDs from file.  Does not validate UUIDs.
        Format is 1 UUID per line, any line beginning with # is ignored.
        Whitespace is stripped.

    Arguments:
        filename: file name of the file containing UUIDs

    Returns:
        list of UUIDs or empty list of no UUIDs in file

    Raises:
        FileNotFoundError if file does not exist
    """

    if not pathlib.Path(filename).is_file():
        raise FileNotFoundError(f"Could not find file {filename}")

    uuid = []
    with open(filename, "r") as uuid_file:
        for line in uuid_file:
            line = line.strip()
            if len(line) and line[0] != "#":
                uuid.append(line)
    return uuid
