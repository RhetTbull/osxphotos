""" QueryOptions class for PhotosDB.query """

import datetime
from dataclasses import asdict, dataclass
from typing import Iterable, List, Optional, Tuple

import bitmath

__all__ = ["QueryOptions"]


@dataclass
class QueryOptions:

    """QueryOptions class for PhotosDB.query

    Attributes:
        keyword: list of keywords to search for
        person: list of person names to search for
        album: list of album names to search for
        folder: list of folder names to search for
        uuid: list of uuids to search for
        title: list of titles to search for
        no_title: search for photos with no title
        description: list of descriptions to search for
        no_description: search for photos with no description
        ignore_case: ignore case when searching
        edited: search for edited photos
        external_edit: search for photos edited in external apps
        favorite: search for favorite photos
        not_favorite: search for non-favorite photos
        hidden: search for hidden photos
        not_hidden: search for non-hidden photos
        missing: search for missing photos
        not_missing: search for non-missing photos
        shared: search for shared photos
        not_shared: search for non-shared photos
        photos: search for photos
        movies: search for movies
        uti: list of UTIs to search for
        burst: search for burst photos
        not_burst: search for non-burst photos
        live: search for live photos
        not_live: search for non-live photos
        cloudasset: search for photos that are managed by iCloud
        not_cloudasset: search for photos that are not managed by iCloud
        incloud: search for cloud assets that are synched to iCloud
        not_incloud: search for cloud asset photos that are not yet synched to iCloud
        from_date: search for photos taken on or after this date
        to_date: search for photos taken on or before this date
        portrait: search for portrait photos
        not_portrait: search for non-portrait photos
        screenshot: search for screenshot photos
        not_screenshot: search for non-screenshot photos
        slow_mo: search for slow-mo photos
        not_slow_mo: search for non-slow-mo photos
        time_lapse: search for time-lapse photos
        not_time_lapse: search for non-time-lapse photos
        hdr: search for HDR photos
        not_hdr: search for non-HDR photos
        selfie: search for selfie photos
        not_selfie: search for non-selfie photos
        panorama: search for panorama photos
        not_panorama: search for non-panorama photos
        has_raw: search for photos with associated raw files
        place: list of place names to search for
        no_place: search for photos with no place
        label: list of labels to search for
        deleted: also include deleted photos
        deleted_only: search only for deleted photos
        has_comment: search for photos with comments
        no_comment: search for photos with no comments
        has_likes: search for shared photos with likes
        no_likes: search for shared photos with no likes
        is_reference: search for photos stored by reference (that is, they are not managed by Photos)
        in_album: search for photos in an album
        not_in_album: search for photos not in an album
        burst_photos: search for burst photos
        missing_bursts: for burst photos, also include burst photos that are missing
        name: list of names to search for
        min_size: minimum size of photos to search for
        max_size: maximum size of photos to search for
        regex: list of regular expressions to search for
        query_eval: list of query expressions to evaluate
        duplicate: search for duplicate photos
        location: search for photos with a location
        no_location: search for photos with no location
        function: list of query functions to evaluate
        selected: search for selected photos
        exif: search for photos with EXIF tags that matches the given data
        year: search for photos taken in a given year

    """

    keyword: Optional[Iterable[str]] = None
    person: Optional[Iterable[str]] = None
    album: Optional[Iterable[str]] = None
    folder: Optional[Iterable[str]] = None
    uuid: Optional[Iterable[str]] = None
    title: Optional[Iterable[str]] = None
    no_title: Optional[bool] = None
    description: Optional[Iterable[str]] = None
    no_description: Optional[bool] = None
    ignore_case: Optional[bool] = None
    edited: Optional[bool] = None
    external_edit: Optional[bool] = None
    favorite: Optional[bool] = None
    not_favorite: Optional[bool] = None
    hidden: Optional[bool] = None
    not_hidden: Optional[bool] = None
    missing: Optional[bool] = None
    not_missing: Optional[bool] = None
    shared: Optional[bool] = None
    not_shared: Optional[bool] = None
    photos: Optional[bool] = True
    movies: Optional[bool] = True
    uti: Optional[Iterable[str]] = None
    burst: Optional[bool] = None
    not_burst: Optional[bool] = None
    live: Optional[bool] = None
    not_live: Optional[bool] = None
    cloudasset: Optional[bool] = None
    not_cloudasset: Optional[bool] = None
    incloud: Optional[bool] = None
    not_incloud: Optional[bool] = None
    from_date: Optional[datetime.datetime] = None
    to_date: Optional[datetime.datetime] = None
    from_time: Optional[datetime.time] = None
    to_time: Optional[datetime.time] = None
    portrait: Optional[bool] = None
    not_portrait: Optional[bool] = None
    screenshot: Optional[bool] = None
    not_screenshot: Optional[bool] = None
    slow_mo: Optional[bool] = None
    not_slow_mo: Optional[bool] = None
    time_lapse: Optional[bool] = None
    not_time_lapse: Optional[bool] = None
    hdr: Optional[bool] = None
    not_hdr: Optional[bool] = None
    selfie: Optional[bool] = None
    not_selfie: Optional[bool] = None
    panorama: Optional[bool] = None
    not_panorama: Optional[bool] = None
    has_raw: Optional[bool] = None
    place: Optional[Iterable[str]] = None
    no_place: Optional[bool] = None
    label: Optional[Iterable[str]] = None
    deleted: Optional[bool] = None
    deleted_only: Optional[bool] = None
    has_comment: Optional[bool] = None
    no_comment: Optional[bool] = None
    has_likes: Optional[bool] = None
    no_likes: Optional[bool] = None
    is_reference: Optional[bool] = None
    in_album: Optional[bool] = None
    not_in_album: Optional[bool] = None
    burst_photos: Optional[bool] = None
    missing_bursts: Optional[bool] = None
    name: Optional[Iterable[str]] = None
    min_size: Optional[bitmath.Byte] = None
    max_size: Optional[bitmath.Byte] = None
    regex: Optional[Iterable[Tuple[str, str]]] = None
    query_eval: Optional[Iterable[str]] = None
    duplicate: Optional[bool] = None
    location: Optional[bool] = None
    no_location: Optional[bool] = None
    function: Optional[List[Tuple[callable, str]]] = None
    selected: Optional[bool] = None
    exif: Optional[Iterable[Tuple[str, str]]] = None
    year: Optional[Iterable[int]] = None

    def asdict(self):
        return asdict(self)
