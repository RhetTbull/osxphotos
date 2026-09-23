"""Info about shared photos"""

from __future__ import annotations

import dataclasses
import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .photos_datetime import photos_datetime_local

if TYPE_CHECKING:
    from .photosdb import PhotosDB


@dataclass
class ShareInfo:
    """Info about a share"""

    _pk: int | None
    cloud_delete_state: int | None
    local_publish_state: int | None
    public_permission: int | None
    scope_type: int | None
    status: int | None
    trashed_state: int | None
    auto_share_policy: int | None
    cloud_item_count: int | None
    cloud_local_state: int | None
    cloud_photo_count: int | None
    cloud_video_count: int | None
    exit_state: int | None
    participant_cloud_update_state: int | None
    preview_state: int | None
    scope_syncing_state: int | None
    asset_count: int | None
    force_sync_attempted: int | None
    photos_count: int | None
    should_ignore_budgets: int | None
    should_notify_on_upload_completion: int | None
    uploaded_photos_count: int | None
    uploaded_videos_count: int | None
    videos_count: int | None
    creation_date: datetime.datetime | None
    expiry_date: datetime.datetime | None
    trashed_date: datetime.datetime | None
    last_participant_asset_trash_notification_date: datetime.datetime | None
    last_participant_asset_trash_notification_viewed_date: datetime.datetime | None
    end_date: datetime.datetime | None
    start_date: datetime.datetime | None
    scope_identifier: str | None
    title: str | None
    uuid: str | None
    originating_scope_identifier: str | None
    share_url: str | None
    rules_data: bytes | None
    preview_data: bytes | None
    thumbnail_image_data: bytes | None
    exit_source: int | None
    count_of_assets_added_by_camera_smart_sharing: int | None
    exit_type: int | None

    def __post_init__(self):
        """Convert dates from str to datetime"""
        for field in [
            "creation_date",
            "expiry_date",
            "trashed_date",
            "last_participant_asset_trash_notification_date",
            "last_participant_asset_trash_notification_viewed_date",
            "end_date",
            "start_date",
        ]:
            if val := getattr(self, field):
                setattr(self, field, photos_datetime_local(val))

    def asdict(self):
        """Return info as dict"""
        return dataclasses.asdict(self)


# ZSHARE columns in the order of ShareInfo fields
_SHARE_INFO_COLUMNS = [
    "Z_PK",
    "ZCLOUDDELETESTATE",
    "ZLOCALPUBLISHSTATE",
    "ZPUBLICPERMISSION",
    "ZSCOPETYPE",
    "ZSTATUS",
    "ZTRASHEDSTATE",
    "ZAUTOSHAREPOLICY",
    "ZCLOUDITEMCOUNT",
    "ZCLOUDLOCALSTATE",
    "ZCLOUDPHOTOCOUNT",
    "ZCLOUDVIDEOCOUNT",
    "ZEXITSTATE",
    "ZPARTICIPANTCLOUDUPDATESTATE",
    "ZPREVIEWSTATE",
    "ZSCOPESYNCINGSTATE",
    "ZASSETCOUNT",
    "ZFORCESYNCATTEMPTED",
    "ZPHOTOSCOUNT",
    "ZSHOULDIGNOREBUDGETS",
    "ZSHOULDNOTIFYONUPLOADCOMPLETION",
    "ZUPLOADEDPHOTOSCOUNT",
    "ZUPLOADEDVIDEOSCOUNT",
    "ZVIDEOSCOUNT",
    "ZCREATIONDATE",
    "ZEXPIRYDATE",
    "ZTRASHEDDATE",
    "ZLASTPARTICIPANTASSETTRASHNOTIFICATIONDATE",
    "ZLASTPARTICIPANTASSETTRASHNOTIFICATIONVIEWEDDATE",
    "ZENDDATE",
    "ZSTARTDATE",
    "ZSCOPEIDENTIFIER",
    "ZTITLE",
    "ZUUID",
    "ZORIGINATINGSCOPEIDENTIFIER",
    "ZSHAREURL",
    "ZRULESDATA",
    "ZPREVIEWDATA",
    "ZTHUMBNAILIMAGEDATA",
    "ZEXITSOURCE",
    "ZCOUNTOFASSETSADDEDBYCAMERASMARTSHARING",
    "ZEXITTYPE",
]


def _get_share_info(db: PhotosDB, uuid: str | None, asset_fk: str) -> ShareInfo:
    """Get info about the share joined to the asset with uuid via ZASSET.{asset_fk}

    Columns not present in this version of the database are returned as None
    (e.g. ZUPLOADEDPHOTOSCOUNT, ZUPLOADEDVIDEOSCOUNT were removed in macOS 26.1)
    """
    share_columns = {row[1] for row in db.execute("PRAGMA table_info(ZSHARE)")}
    columns = ", ".join(
        f"ZSHARE.{column}" if column in share_columns else "NULL"
        for column in _SHARE_INFO_COLUMNS
    )
    sql = f"""  SELECT {columns}
                FROM ZSHARE
                JOIN ZASSET ON ZASSET.{asset_fk} = ZSHARE.Z_PK
                WHERE ZASSET.ZUUID = ?
                ;"""

    if row := db.execute(sql, (uuid,)).fetchone():
        return ShareInfo(*row)
    raise ValueError(f"Could not find share for uuid {uuid}")


def get_moment_share_info(db: PhotosDB, uuid: str | None) -> ShareInfo:
    """Get info about a moment share"""
    return _get_share_info(db, uuid, "ZMOMENTSHARE")


def get_share_info(db: PhotosDB, uuid: str | None) -> ShareInfo:
    """Get info about a shared iCloud library share"""

    # TODO: this is a total guess right now. I think that ZSHARE holds information
    # about both shared moments and shared iCloud Library
    # The foreign key for shared moments appears to be ZASSET.ZMOMENTSHARE
    # but I don't know the key for shared iCloud Libraries
    # I'm guessing it's ZASSET.ZSHARESCOPE but I don't know for sure and will need
    # to test on a library that has shared iCloud Library and shared moments
    return _get_share_info(db, uuid, "ZLIBRARYSCOPE")
