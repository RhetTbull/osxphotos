""" photo_query and QueryOptions class for PhotosDB.query """

from __future__ import annotations

import dataclasses
import io
import pathlib
import re
import sys
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, List, Optional, Tuple

import bitmath

from ._constants import _PHOTOS_5_VERSION, UUID_PATTERN
from .datetime_utils import datetime_has_tz, datetime_naive_to_local
from .photoinfo import PhotoInfo
from .phototemplate import RenderOptions
from .platform import is_macos
from .unicode import normalize_unicode

if TYPE_CHECKING:
    from .iphoto import iPhotoDB
    from .photosdb import PhotosDB

if is_macos:
    import photoscript

__all__ = [
    "IncompatibleQueryOptions",
    "QueryOptions",
    "photo_query",
    "query_options_from_kwargs",
]


class IncompatibleQueryOptions(Exception):
    """Incompatible query options"""

    pass


@dataclass
class QueryOptions:

    """QueryOptions class for PhotosDB.query

    Attributes:
        added_after: search for photos added on or after a given date
        added_before: search for photos added before a given date
        added_in_last: search for photos added in last X datetime.timedelta
        album: list of album names to search for
        burst_photos: include all associated burst photos for photos in query results
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
        from_time: search for photos taken on or after this time of day
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
        to_date: search for photos taken before this date
        to_time: search for photos taken before this time of day
        uti: list of UTIs to search for
        uuid: list of uuids to search for
        year: search for photos taken in a given year
        syndicated: search for photos that have been shared via syndication ("Shared with You" album via Messages, etc.)
        not_syndicated: search for photos that have not been shared via syndication ("Shared with You" album via Messages, etc.)
        saved_to_library: search for syndicated photos that have been saved to the Photos library
        not_saved_to_library: search for syndicated photos that have not been saved to the Photos library
        shared_moment: search for photos that have been shared via a shared moment
        not_shared_moment: search for photos that have not been shared via a shared moment
        shared_library: search for photos that are part of a shared iCloud library
        not_shared_library: search for photos that are not part of a shared iCloud library
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
    syndicated: Optional[bool] = None
    not_syndicated: Optional[bool] = None
    saved_to_library: Optional[bool] = None
    not_saved_to_library: Optional[bool] = None
    shared_moment: Optional[bool] = None
    not_shared_moment: Optional[bool] = None
    shared_library: Optional[bool] = None
    not_shared_library: Optional[bool] = None

    def asdict(self):
        return asdict(self)


def query_options_from_kwargs(**kwargs) -> QueryOptions:
    """Validate query options and create a QueryOptions instance.
    Note: this will block on stdin if uuid_from_file is set to "-"
    so it is best to call function before creating the PhotosDB instance
    so that the validation of query options can happen before the database
    is loaded.
    """
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
        ("deleted", "deleted_only"),
        ("deleted_only", "not_deleted"),
        ("syndicated", "not_syndicated"),
        ("saved_to_library", "not_saved_to_library"),
        ("shared_moment", "not_shared_moment"),
        ("shared_library", "not_shared_library"),
    ]

    # TODO: add option to validate requiring at least one query arg
    for arg, not_arg in exclusive:
        if kwargs.get(arg) and kwargs.get(not_arg):
            arg = arg.replace("_", "-")
            not_arg = not_arg.replace("_", "-")
            raise IncompatibleQueryOptions(
                f"Incompatible query options: --{arg} and --{not_arg} are mutually exclusive"
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
    uuids = list(kwargs.get("uuid", []))  # Click option is a tuple
    if uuid_from_file := kwargs.get("uuid_from_file"):
        uuids.extend(load_uuid_from_file(uuid_from_file))
        uuids = tuple(uuids)

    query_fields = [field.name for field in dataclasses.fields(QueryOptions)]
    query_dict = {field: kwargs.get(field) for field in query_fields}
    query_dict["photos"] = include_photos
    query_dict["movies"] = include_movies
    query_dict["uuid"] = uuids
    query_dict["function"] = kwargs.get("query_function")

    return QueryOptions(**query_dict)


def load_uuid_from_file(filename: str) -> list[str]:
    """
    Load UUIDs from file.
    Does not validate UUIDs but does validate that the UUIDs are in the correct format.
    Format is 1 UUID per line, any line beginning with # is ignored.
    Whitespace is stripped.

    Arguments:
        filename: file name of the file containing UUIDs

    Returns:
        list of UUIDs or empty list of no UUIDs in file

    Raises:
        FileNotFoundError if file does not exist
        ValueError if UUID is not in correct format
    """

    if filename == "-":
        return _load_uuid_from_stream(sys.stdin)

    if not pathlib.Path(filename).is_file():
        raise FileNotFoundError(f"Could not find file {filename}")

    with open(filename, "r") as f:
        return _load_uuid_from_stream(f)


def _load_uuid_from_stream(stream: io.IOBase) -> list[str]:
    """
    Load UUIDs from stream.
    Does not validate UUIDs but does validate that the UUIDs are in the correct format.
    Format is 1 UUID per line, any line beginning with # is ignored.
    Whitespace is stripped.

    Arguments:
        filename: file name of the file containing UUIDs

    Returns:
        list of UUIDs or empty list of no UUIDs in file

    Raises:
        ValueError if UUID is not in correct format
    """

    uuid = []
    for line in stream:
        line = line.strip()
        if len(line) and line[0] != "#":
            if not re.match(f"^{UUID_PATTERN}$", line):
                raise ValueError(f"Invalid UUID: {line}")
            line = line.upper()
            uuid.append(line)
    return uuid


def photo_query(
    photosdb: PhotosDB | iPhotoDB, options: QueryOptions
) -> list[PhotoInfo]:
    """Run a query against PhotosDB to extract the photos based on user supplied options

    Args:
        options: a QueryOptions instance
    """

    if options.deleted or options.deleted_only:
        photos = photosdb.photos(
            uuid=options.uuid,
            images=options.photos,
            movies=options.movies,
            from_date=options.from_date,
            to_date=options.to_date,
            intrash=True,
        )
    else:
        photos = []

    if not options.deleted_only:
        photos += photosdb.photos(
            uuid=options.uuid,
            images=options.photos,
            movies=options.movies,
            from_date=options.from_date,
            to_date=options.to_date,
        )

    person = normalize_unicode(options.person)
    keyword = normalize_unicode(options.keyword)
    album = normalize_unicode(options.album)
    folder = normalize_unicode(options.folder)
    title = normalize_unicode(options.title)
    description = normalize_unicode(options.description)
    place = normalize_unicode(options.place)
    label = normalize_unicode(options.label)
    name = normalize_unicode(options.name)

    if album:
        photos = _get_photos_by_attribute(photos, "albums", album, options.ignore_case)

    if keyword:
        photos = _get_photos_by_attribute(
            photos, "keywords", keyword, options.ignore_case
        )
    elif options.no_keyword:
        photos = [p for p in photos if not p.keywords]

    if person:
        photos = _get_photos_by_attribute(
            photos, "persons", person, options.ignore_case
        )

    if label:
        photos = _get_photos_by_attribute(photos, "labels", label, options.ignore_case)

    if folder:
        # search for photos in an album in folder
        # finds photos that have albums whose top level folder matches folder
        photo_list = []
        for f in folder:
            photo_list.extend(
                [
                    p
                    for p in photos
                    if p.album_info
                    and f in [a.folder_names[0] for a in p.album_info if a.folder_names]
                ]
            )
        photos = photo_list

    if title:
        # search title field for text
        # if more than one, find photos with all title values in title
        photo_list = []
        if options.ignore_case:
            # case-insensitive
            for t in title:
                t = t.lower()
                photo_list.extend(
                    [p for p in photos if p.title and t in p.title.lower()]
                )
        else:
            for t in title:
                photo_list.extend([p for p in photos if p.title and t in p.title])
        photos = photo_list
    elif options.no_title:
        photos = [p for p in photos if not p.title]

    if description:
        # search description field for text
        # if more than one, find photos with all description values in description
        photo_list = []
        if options.ignore_case:
            # case-insensitive
            for d in description:
                d = d.lower()
                photo_list.extend(
                    [p for p in photos if p.description and d in p.description.lower()]
                )
        else:
            for d in description:
                photo_list.extend(
                    [p for p in photos if p.description and d in p.description]
                )
        photos = photo_list
    elif options.no_description:
        photos = [p for p in photos if not p.description]

    if place:
        # search place.names for text matching place
        # if more than one place, find photos with all place values in description
        if options.ignore_case:
            # case-insensitive
            for place_name in place:
                place_name = place_name.lower()
                photos = [
                    p
                    for p in photos
                    if p.place
                    and any(
                        pname
                        for pname in p.place.names
                        if any(
                            pvalue for pvalue in pname if place_name in pvalue.lower()
                        )
                    )
                ]
        else:
            for place_name in place:
                photos = [
                    p
                    for p in photos
                    if p.place
                    and any(
                        pname
                        for pname in p.place.names
                        if any(pvalue for pvalue in pname if place_name in pvalue)
                    )
                ]
    elif options.no_place:
        photos = [p for p in photos if not p.place]

    if options.edited:
        photos = [p for p in photos if p.hasadjustments]
    elif options.not_edited:
        photos = [p for p in photos if not p.hasadjustments]

    if options.external_edit:
        photos = [p for p in photos if p.external_edit]

    if options.favorite:
        photos = [p for p in photos if p.favorite]
    elif options.not_favorite:
        photos = [p for p in photos if not p.favorite]

    if options.hidden:
        photos = [p for p in photos if p.hidden]
    elif options.not_hidden:
        photos = [p for p in photos if not p.hidden]

    if options.missing:
        photos = [p for p in photos if not p.path]
    elif options.not_missing:
        photos = [p for p in photos if p.path]

    if options.shared:
        photos = [p for p in photos if p.shared]
    elif options.not_shared:
        photos = [p for p in photos if not p.shared]

    if options.shared:
        photos = [p for p in photos if p.shared]
    elif options.not_shared:
        photos = [p for p in photos if not p.shared]

    if options.uti:
        photos = [p for p in photos if options.uti in p.uti_original]

    if options.burst:
        photos = [p for p in photos if p.burst]
    elif options.not_burst:
        photos = [p for p in photos if not p.burst]

    if options.live:
        photos = [p for p in photos if p.live_photo]
    elif options.not_live:
        photos = [p for p in photos if not p.live_photo]

    if options.portrait:
        photos = [p for p in photos if p.portrait]
    elif options.not_portrait:
        photos = [p for p in photos if not p.portrait]

    if options.screenshot:
        photos = [p for p in photos if p.screenshot]
    elif options.not_screenshot:
        photos = [p for p in photos if not p.screenshot]

    if options.slow_mo:
        photos = [p for p in photos if p.slow_mo]
    elif options.not_slow_mo:
        photos = [p for p in photos if not p.slow_mo]

    if options.time_lapse:
        photos = [p for p in photos if p.time_lapse]
    elif options.not_time_lapse:
        photos = [p for p in photos if not p.time_lapse]

    if options.hdr:
        photos = [p for p in photos if p.hdr]
    elif options.not_hdr:
        photos = [p for p in photos if not p.hdr]

    if options.selfie:
        photos = [p for p in photos if p.selfie]
    elif options.not_selfie:
        photos = [p for p in photos if not p.selfie]

    if options.panorama:
        photos = [p for p in photos if p.panorama]
    elif options.not_panorama:
        photos = [p for p in photos if not p.panorama]

    if options.cloudasset:
        photos = [p for p in photos if p.iscloudasset]
    elif options.not_cloudasset:
        photos = [p for p in photos if not p.iscloudasset]

    if options.incloud:
        photos = [p for p in photos if p.incloud]
    elif options.not_incloud:
        photos = [p for p in photos if not p.incloud]

    if options.has_raw:
        photos = [p for p in photos if p.has_raw]

    if options.has_comment:
        photos = [p for p in photos if p.comments]
    elif options.no_comment:
        photos = [p for p in photos if not p.comments]

    if options.has_likes:
        photos = [p for p in photos if p.likes]
    elif options.no_likes:
        photos = [p for p in photos if not p.likes]

    if options.is_reference:
        photos = [p for p in photos if p.isreference]
    elif options.not_reference:
        photos = [p for p in photos if not p.isreference]

    if options.in_album:
        photos = [p for p in photos if p.albums]
    elif options.not_in_album:
        photos = [p for p in photos if not p.albums]

    if options.from_time:
        photos = [p for p in photos if p.date.time() >= options.from_time]

    if options.to_time:
        photos = [p for p in photos if p.date.time() < options.to_time]

    if options.year:
        photos = [p for p in photos if p.date.year in options.year]

    if name:
        # search filename fields for text
        # if more than one, find photos with all title values in filename
        photo_list = []
        if options.ignore_case:
            # case-insensitive
            for n in name:
                n = n.lower()
                if photosdb._db_version >= _PHOTOS_5_VERSION:
                    # search only original_filename (#594)
                    photo_list.extend(
                        [p for p in photos if n in p.original_filename.lower()]
                    )
                else:
                    photo_list.extend(
                        [
                            p
                            for p in photos
                            if n in p.filename.lower()
                            or n in p.original_filename.lower()
                        ]
                    )
        else:
            for n in name:
                if photosdb._db_version >= _PHOTOS_5_VERSION:
                    # search only original_filename (#594)
                    photo_list.extend([p for p in photos if n in p.original_filename])
                else:
                    photo_list.extend(
                        [
                            p
                            for p in photos
                            if n in p.filename or n in p.original_filename
                        ]
                    )
        photos = list(set(photo_list))

    if options.min_size:
        photos = [
            p for p in photos if bitmath.Byte(p.original_filesize) >= options.min_size
        ]

    if options.max_size:
        photos = [
            p for p in photos if bitmath.Byte(p.original_filesize) <= options.max_size
        ]

    if options.regex:
        flags = re.IGNORECASE if options.ignore_case else 0
        render_options = RenderOptions(none_str="")
        photo_list = []
        for regex, template in options.regex:
            regex = re.compile(regex, flags)
            for p in photos:
                rendered, _ = p.render_template(template, render_options)
                for value in rendered:
                    if regex.search(value):
                        photo_list.append(p)
                        break
        photos = photo_list

    if options.query_eval:
        for q in options.query_eval:
            query_string = f"[photo for photo in photos if {q}]"
            try:
                photos = eval(query_string)
            except Exception as e:
                raise ValueError(f"Invalid query_eval CRITERIA: {e}")

    if options.duplicate:
        no_date = datetime(1970, 1, 1)
        tz = timezone(timedelta(0))
        no_date = no_date.astimezone(tz=tz)
        photos = sorted(
            [p for p in photos if p.duplicates],
            key=lambda x: x.date_added or no_date,
        )
        # gather all duplicates but ensure each uuid is only represented once
        photodict = OrderedDict()
        for p in photos:
            if p.uuid not in photodict:
                photodict[p.uuid] = p
                for d in sorted(p.duplicates, key=lambda x: x.date_added or no_date):
                    if d.uuid not in photodict:
                        photodict[d.uuid] = d
        photos = list(photodict.values())

        # filter for deleted as photo.duplicates will include photos in the trash
        if not (options.deleted or options.deleted_only):
            photos = [p for p in photos if not p.intrash]
        if options.deleted_only:
            photos = [p for p in photos if p.intrash]

    if options.location:
        photos = [p for p in photos if p.location != (None, None)]
    elif options.no_location:
        photos = [p for p in photos if p.location == (None, None)]

    if options.selected:
        # photos selected in Photos app
        if not is_macos:
            raise NotImplementedError(
                "Query option --selected is only available on macOS"
            )
        try:
            # catch AppleScript errors as the scripting interfce to Photos is flaky
            selected = photoscript.PhotosLibrary().selection
            selected_uuid = [p.uuid for p in selected]
            photos = [p for p in photos if p.uuid in selected_uuid]
        except Exception:
            # no photos selected or a selected photo was "open"
            # selection only works if photos selected in main media browser
            photos = []

    if options.exif:
        matching_photos = []
        for p in photos:
            if not p.exiftool:
                continue
            exifdata = p.exiftool.asdict(normalized=True)
            exifdata.update(p.exiftool.asdict(tag_groups=False, normalized=True))
            for exiftag, exifvalue in options.exif:
                if options.ignore_case:
                    exifvalue = exifvalue.lower()
                    exifdata_value = exifdata.get(exiftag.lower(), "")
                    if isinstance(exifdata_value, str):
                        exifdata_value = exifdata_value.lower()
                    elif isinstance(exifdata_value, Iterable):
                        exifdata_value = [v.lower() for v in exifdata_value]
                    else:
                        exifdata_value = str(exifdata_value)

                    if exifvalue in exifdata_value:
                        matching_photos.append(p)
                else:
                    exifdata_value = exifdata.get(exiftag.lower(), "")
                    if not isinstance(exifdata_value, (str, Iterable)):
                        exifdata_value = str(exifdata_value)
                    if exifvalue in exifdata_value:
                        matching_photos.append(p)
        photos = list(set(matching_photos))

    if options.added_after:
        added_after = options.added_after
        if not datetime_has_tz(added_after):
            added_after = datetime_naive_to_local(added_after)
        photos = [p for p in photos if p.date_added and p.date_added > added_after]

    if options.added_before:
        added_before = options.added_before
        if not datetime_has_tz(added_before):
            added_before = datetime_naive_to_local(added_before)
        photos = [p for p in photos if p.date_added and p.date_added < added_before]

    if options.added_in_last:
        added_after = datetime.now() - options.added_in_last
        added_after = datetime_naive_to_local(added_after)
        photos = [p for p in photos if p.date_added and p.date_added > added_after]

    if options.syndicated:
        photos = [p for p in photos if p.syndicated]
    elif options.not_syndicated:
        photos = [p for p in photos if not p.syndicated]

    if options.saved_to_library:
        photos = [p for p in photos if p.syndicated and p.saved_to_library]
    elif options.not_saved_to_library:
        photos = [p for p in photos if p.syndicated and not p.saved_to_library]

    if options.shared_moment:
        photos = [p for p in photos if p.shared_moment]
    elif options.not_shared_moment:
        photos = [p for p in photos if not p.shared_moment]

    if options.shared_library:
        photos = [p for p in photos if p.shared_library]
    elif options.not_shared_library:
        photos = [p for p in photos if not p.shared_library]

    if options.function:
        for function in options.function:
            photos = function[0](photos)

    # burst should be checked last, ref #640
    if options.burst_photos:
        # add the burst_photos to the export set
        photos_burst = [p for p in photos if p.burst]
        for burst in photos_burst:
            if options.missing_bursts:
                # include burst photos that are missing
                photos.extend(burst.burst_photos)
            else:
                # don't include missing burst images (these can't be downloaded with AppleScript)
                photos.extend([p for p in burst.burst_photos if not p.ismissing])

        # remove duplicates as each burst photo in the set that's selected would
        # result in the entire set being added above
        # can't use set() because PhotoInfo not hashable
        seen_uuids = {}
        for p in photos:
            if p.uuid in seen_uuids:
                continue
            seen_uuids[p.uuid] = p
        photos = list(seen_uuids.values())

    return photos


def _get_photos_by_attribute(photos, attribute, values, ignore_case):
    """Search for photos based on values being in PhotoInfo.attribute

    Args:
        photos: a list of PhotoInfo objects
        attribute: str, name of PhotoInfo attribute to search (e.g. keywords, persons, etc)
        values: list of values to search in property
        ignore_case: ignore case when searching

    Returns:
        list of PhotoInfo objects matching search criteria
    """
    photos_search = []
    if ignore_case:
        # case-insensitive
        for x in values:
            x = x.lower()
            photos_search.extend(
                p
                for p in photos
                if x in [attr.lower() for attr in getattr(p, attribute)]
            )
    else:
        for x in values:
            photos_search.extend(p for p in photos if x in getattr(p, attribute))
    return list(set(photos_search))
