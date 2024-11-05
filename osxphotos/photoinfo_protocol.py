"""Protocol for PhotoInfo class."""

from __future__ import annotations

import datetime
import pathlib
from typing import TYPE_CHECKING, Any, Protocol, Union, runtime_checkable

if TYPE_CHECKING:
    from .adjustmentsinfo import AdjustmentsInfo
    from .albuminfo import AlbumInfo, ImportInfo, ProjectInfo
    from .commentinfo import CommentInfo, LikeInfo
    from .exifinfo import ExifInfo
    from .exiftool import ExifToolCaching
    from .momentinfo import MomentInfo
    from .personinfo import FaceInfo, PersonInfo
    from .photoinfo import PhotoInfo
    from .phototables import PhotoTables
    from .phototemplate import RenderOptions
    from .placeinfo import PlaceInfo, PlaceInfo4, PlaceInfo5
    from .scoreinfo import ScoreInfo
    from .searchinfo import SearchInfo

__all__ = ["PhotoInfoProtocol", "PhotoInfoMixin"]


@runtime_checkable
class PhotoInfoProtocol(Protocol):
    @property
    def filename(self) -> str: ...

    @property
    def original_filename(self) -> str: ...

    @property
    def date(self) -> datetime.datetime: ...

    @property
    def date_modified(self) -> datetime.datetime | None: ...

    @property
    def tzoffset(self) -> int: ...

    @property
    def path(self) -> str | None: ...

    @property
    def path_edited(self) -> str | None: ...

    @property
    def description(self) -> str: ...

    @property
    def persons(self) -> list[str]: ...

    @property
    def person_info(self) -> list["PersonInfo"]: ...

    @property
    def face_info(self) -> list["FaceInfo"]: ...

    @property
    def moment_info(self) -> "MomentInfo" | None: ...

    @property
    def albums(self) -> list[str]: ...

    @property
    def burst_albums(self) -> list[str]: ...

    @property
    def album_info(self) -> list["AlbumInfo"]: ...

    @property
    def burst_album_info(self) -> list["AlbumInfo"]: ...

    @property
    def import_info(self) -> "ImportInfo" | None: ...

    @property
    def project_info(self) -> list["ProjectInfo"]: ...

    @property
    def keywords(self) -> list[str]: ...

    @property
    def title(self) -> str | None: ...

    @property
    def uuid(self) -> str: ...

    @property
    def ismissing(self) -> bool: ...

    @property
    def hasadjustments(self) -> bool: ...

    @property
    def adjustments_path(self) -> "pathlib.Path" | None: ...

    @property
    def adjustments(self) -> "AdjustmentsInfo" | None: ...

    @property
    def external_edit(self) -> bool: ...

    @property
    def favorite(self) -> bool: ...

    @property
    def rating(self) -> int: ...

    @property
    def hidden(self) -> bool: ...

    @property
    def visible(self) -> bool: ...

    @property
    def intrash(self) -> bool: ...

    @property
    def date_trashed(self) -> datetime.datetime | None: ...

    @property
    def date_added(self) -> datetime.datetime | None: ...

    @property
    def location(self) -> tuple[float | None, float | None]: ...

    @property
    def shared(self) -> bool | None: ...

    @property
    def uti(self) -> str: ...

    @property
    def uti_original(self) -> str: ...

    @property
    def uti_edited(self) -> str | None: ...

    @property
    def uti_raw(self) -> str | None: ...

    @property
    def ismovie(self) -> bool: ...

    @property
    def isphoto(self) -> bool: ...

    @property
    def incloud(self) -> bool | None: ...

    @property
    def iscloudasset(self) -> bool: ...

    @property
    def isreference(self) -> bool: ...

    @property
    def burst(self) -> bool: ...

    @property
    def burst_selected(self) -> bool: ...

    @property
    def burst_key(self) -> bool: ...

    @property
    def burst_default_pick(self) -> bool: ...

    @property
    def burst_photos(self) -> list[PhotoInfoProtocol]: ...

    @property
    def live_photo(self) -> bool: ...

    @property
    def path_live_photo(self) -> str | None: ...

    @property
    def path_edited_live_photo(self) -> str | None: ...

    @property
    def path_raw(self) -> str | None: ...

    @property
    def panorama(self) -> bool: ...

    @property
    def slow_mo(self) -> bool: ...

    @property
    def time_lapse(self) -> bool: ...

    @property
    def hdr(self) -> bool: ...

    @property
    def screenshot(self) -> bool: ...

    @property
    def screen_recording(self) -> bool: ...

    @property
    def portrait(self) -> bool: ...

    @property
    def selfie(self) -> bool: ...

    @property
    def path_derivatives(self) -> list[str]: ...

    @property
    def place(self) -> Union["PlaceInfo4", "PlaceInfo5"] | None: ...

    @property
    def has_raw(self) -> bool: ...

    @property
    def israw(self) -> bool: ...

    @property
    def raw_original(self) -> bool: ...

    @property
    def height(self) -> int: ...

    @property
    def width(self) -> int: ...

    @property
    def orientation(self) -> int: ...

    @property
    def original_height(self) -> int: ...

    @property
    def original_width(self) -> int: ...

    @property
    def original_orientation(self) -> int: ...

    @property
    def original_filesize(self) -> int: ...

    @property
    def owner(self) -> str | None: ...

    @property
    def score(self) -> "ScoreInfo" | None: ...

    @property
    def labels(self) -> list[str]: ...

    @property
    def labels_normalized(self) -> list[str]: ...

    @property
    def comments(self) -> list["CommentInfo"]: ...

    @property
    def likes(self) -> list["LikeInfo"]: ...

    @property
    def exif_info(self) -> "ExifInfo" | None: ...

    @property
    def exiftool(self) -> "ExifToolCaching" | None: ...

    @property
    def search_info(self) -> "SearchInfo" | None: ...

    @property
    def search_info_normalized(self) -> "SearchInfo" | None: ...

    @property
    def cloud_guid(self) -> str: ...

    @property
    def cloud_owner_hashed_id(self) -> str: ...

    @property
    def fingerprint(self) -> str | None: ...

    def render_template(
        self, template_str: str, options: "RenderOptions" | None = None
    ) -> tuple[list[str], list[str]]: ...

    def export(self, dest: str, **kwargs) -> list[str]: ...

    def asdict(self, shallow: bool = True) -> dict[str, Any]: ...

    def json(self, indent: int | None = None, shallow: bool = True) -> str: ...

    def detected_text(
        self, confidence_threshold: float = 0.5
    ) -> list[tuple[str, float]]: ...

    def tables(self) -> "PhotoTables" | None: ...

    @property
    def syndicated(self) -> bool: ...


import datetime


class PhotoInfoMixin:
    def __getattr__(self, name):
        if name in [
            "render_template",
            "export",
            "asdict",
            "json",
            "detected_text",
            "tables",
        ]:
            raise NotImplementedError(f"Method '{name}' is not implemented")
        elif name in [
            "date_modified",
            "path",
            "path_edited",
            "moment_info",
            "import_info",
            "title",
            "adjustments_path",
            "adjustments",
            "uti_edited",
            "uti_raw",
            "date_trashed",
            "date_added",
            "shared",
            "incloud",
            "path_live_photo",
            "path_edited_live_photo",
            "path_raw",
            "place",
            "owner",
            "score",
            "exif_info",
            "exiftool",
            "search_info",
            "search_info_normalized",
            "fingerprint",
            "syndicated",
            "shared_moment_info",
        ]:
            return None
        elif name in [
            "filename",
            "original_filename",
            "description",
            "uuid",
            "uti",
            "uti_original",
            "cloud_guid",
            "cloud_owner_hashed_id",
        ]:
            return ""
        elif name in [
            "ismissing",
            "hasadjustments",
            "external_edit",
            "favorite",
            "hidden",
            "intrash",
            "ismovie",
            "isphoto",
            "iscloudasset",
            "isreference",
            "burst",
            "burst_selected",
            "burst_key",
            "burst_default_pick",
            "live_photo",
            "panorama",
            "slow_mo",
            "time_lapse",
            "hdr",
            "screenshot",
            "screen_recording",
            "portrait",
            "selfie",
            "has_raw",
            "israw",
            "raw_original",
            "saved_to_library",
            "shared_moment",
            "shared_library",
        ]:
            return False
        elif name == "tzoffset":
            return 0
        elif name == "persons":
            return []
        elif name == "person_info":
            return []
        elif name == "face_info":
            return []
        elif name == "albums":
            return []
        elif name == "burst_albums":
            return []
        elif name == "album_info":
            return []
        elif name == "burst_album_info":
            return []
        elif name == "project_info":
            return []
        elif name == "keywords":
            return []
        elif name == "rating":
            return 0
        elif name == "visible":
            return True
        elif name == "location":
            return (None, None)
        elif name == "burst_photos":
            return []
        elif name == "path_derivatives":
            return []
        elif name == "height":
            return 0
        elif name == "width":
            return 0
        elif name == "orientation":
            return 0
        elif name == "original_height":
            return 0
        elif name == "original_width":
            return 0
        elif name == "original_orientation":
            return 0
        elif name == "original_filesize":
            return 0
        elif name == "labels":
            return []
        elif name == "labels_normalized":
            return []
        elif name == "comments":
            return []
        elif name == "likes":
            return []
        elif name == "share_participant_info":
            return []
        elif name == "share_participants":
            return []
        else:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )
