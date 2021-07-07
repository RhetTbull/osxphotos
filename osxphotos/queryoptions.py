""" QueryOptions class for PhotosDB.query """

import datetime
from dataclasses import asdict, dataclass
from typing import Iterable, List, Optional, Tuple

import bitmath


@dataclass
class QueryOptions:

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

    def asdict(self):
        return asdict(self)
