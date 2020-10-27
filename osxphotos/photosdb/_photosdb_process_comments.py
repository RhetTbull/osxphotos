""" PhotosDB method for processing comments and likes on shared photos.
    Do not import this module directly """

import dataclasses
import datetime
from dataclasses import dataclass

from .._constants import _DB_TABLE_NAMES, _PHOTOS_4_VERSION, TIME_DELTA
from ..utils import _open_sql_file, normalize_unicode


def _process_comments(self):
    """ load the comments and likes data from the database 
        this is a PhotosDB method that should be imported in 
        the PhotosDB class definition in photosdb.py
    """
    self._db_hashed_person_id = {}
    self._db_comments_uuid = {}
    if self._db_version <= _PHOTOS_4_VERSION:
        _process_comments_4(self)
    else:
        _process_comments_5(self)


@dataclass
class CommentInfo:
    """ Class for shared photo comments """

    datetime: datetime.datetime
    user: str
    ismine: bool
    text: str

    def asdict(self):
        return dataclasses.asdict(self)


@dataclass
class LikeInfo:
    """ Class for shared photo likes """

    datetime: datetime.datetime
    user: str
    ismine: bool

    def asdict(self):
        return dataclasses.asdict(self)


# The following methods do not get imported into PhotosDB
# but will get called by _process_comments
def _process_comments_4(photosdb):
    """ process comments and likes info for Photos <= 4 
        photosdb: PhotosDB instance """
    raise NotImplementedError(
        f"Not implemented for database version {photosdb._db_version}."
    )


def _process_comments_5(photosdb):
    """ process comments and likes info for Photos >= 5 
        photosdb: PhotosDB instance """

    db = photosdb._tmp_db

    asset_table = _DB_TABLE_NAMES[photosdb._photos_ver]["ASSET"]

    (conn, cursor) = _open_sql_file(db)

    results = conn.execute(
        """
        SELECT DISTINCT
        ZINVITEEHASHEDPERSONID,
        ZINVITEEFIRSTNAME,
        ZINVITEELASTNAME,
        ZINVITEEFULLNAME
        FROM
        ZCLOUDSHAREDALBUMINVITATIONRECORD
        """
    )

    # order of results
    # 0: ZINVITEEHASHEDPERSONID,
    # 1: ZINVITEEFIRSTNAME,
    # 2: ZINVITEELASTNAME,
    # 3: ZINVITEEFULLNAME

    photosdb._db_hashed_person_id = {}
    for row in results.fetchall():
        person_id = row[0]
        photosdb._db_hashed_person_id[person_id] = {
            "first_name": normalize_unicode(row[1]),
            "last_name": normalize_unicode(row[2]),
            "full_name": normalize_unicode(row[3]),
        }

    results = conn.execute(
        f"""
        SELECT 
        {asset_table}.ZUUID, -- UUID of the photo
        ZCLOUDSHAREDCOMMENT.ZISLIKE, -- comment is actually a "like"
        ZCLOUDSHAREDCOMMENT.ZCOMMENTDATE, -- date of comment
        ZCLOUDSHAREDCOMMENT.ZCOMMENTTEXT, -- text of comment
        ZCLOUDSHAREDCOMMENT.ZCOMMENTERHASHEDPERSONID, -- hashed ID of person who made comment/like
        ZCLOUDSHAREDCOMMENT.ZISMYCOMMENT -- is my (this user's) comment
        FROM ZCLOUDSHAREDCOMMENT
        JOIN {asset_table} ON
        {asset_table}.Z_PK = ZCLOUDSHAREDCOMMENT.ZCOMMENTEDASSET
        OR
        {asset_table}.Z_PK = ZCLOUDSHAREDCOMMENT.ZLIKEDASSET
    """
    )

    # order of results
    # 0: ZGENERICASSET.ZUUID, -- UUID of the photo
    # 1: ZCLOUDSHAREDCOMMENT.ZISLIKE, -- comment is actually a "like"
    # 2: ZCLOUDSHAREDCOMMENT.ZCOMMENTDATE, -- date of comment
    # 3: ZCLOUDSHAREDCOMMENT.ZCOMMENTTEXT, -- text of comment
    # 4: ZCLOUDSHAREDCOMMENT.ZCOMMENTERHASHEDPERSONID, -- hashed ID of person who made comment/like
    # 5: ZCLOUDSHAREDCOMMENT.ZISMYCOMMENT -- is my (this user's) comment

    photosdb._db_comments_uuid = {}
    for row in results:
        uuid = row[0]
        is_like = bool(row[1])
        text = normalize_unicode(row[3])
        try:
            user_name = photosdb._db_hashed_person_id[row[4]]["full_name"]
        except KeyError:
            user_name = None

        try:
            dt = datetime.datetime.fromtimestamp(row[2] + TIME_DELTA)
        except:
            dt = datetime.datetime(1970, 1, 1)

        ismine = bool(row[5])

        try:
            db_comments = photosdb._db_comments_uuid[uuid]
        except KeyError:
            photosdb._db_comments_uuid[uuid] = {"likes": [], "comments": []}
            db_comments = photosdb._db_comments_uuid[uuid]

        if is_like:
            db_comments["likes"].append(LikeInfo(dt, user_name, ismine))
        elif text:
            db_comments["comments"].append(CommentInfo(dt, user_name, ismine, text))

    # sort results
    for uuid in photosdb._db_comments_uuid:
        if photosdb._db_comments_uuid[uuid]["likes"]:
            photosdb._db_comments_uuid[uuid]["likes"].sort(key=lambda x: x.datetime)
        if photosdb._db_comments_uuid[uuid]["comments"]:
            photosdb._db_comments_uuid[uuid]["comments"].sort(key=lambda x: x.datetime)

    conn.close()
