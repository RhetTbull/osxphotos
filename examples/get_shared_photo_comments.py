""" get shared comments associated with a photo """

import datetime
import sys
from dataclasses import dataclass

import osxphotos
from osxphotos._constants import TIME_DELTA


@dataclass
class Comment:
    """ Class for shared photo comments """

    uuid: str
    sort_fok: int
    datetime: datetime.datetime
    user: str
    ismine: bool
    text: str


@dataclass
class Like:
    """ Class for shared photo likes """

    uuid: str
    sort_fok: int
    datetime: datetime.datetime
    user: str
    ismine: bool


def get_shared_person_info(photosdb, hashed_person_id):
    """ returns tuple of (first name, last name, full name) 
        for person invited to shared album with 
        ZINVITEEHASHEDPERSONID = hashed_person_id
        
    Args:
        photosdb: a osxphotos.PhotosDB object
    """

    conn, _ = photosdb.get_db_connection()
    results = conn.execute(
        """
        SELECT
        ZINVITEEHASHEDPERSONID,
        ZINVITEEFIRSTNAME,
        ZINVITEELASTNAME,
        ZINVITEEFULLNAME
        FROM
        ZCLOUDSHAREDALBUMINVITATIONRECORD
        WHERE
        ZINVITEEHASHEDPERSONID = ?
        LIMIT 1
        """,
        ([hashed_person_id]),
    ).fetchall()

    if results:
        row = results[0]
        return (row[1], row[2], row[3])
    else:
        return (None, None, None)


def get_comments(photosdb, uuid):
    """ return comments and likes, if any, for photo with uuid

    Args:
        photosdb: a osxphotos.PhotosDB object
        uuid: uuid of the photo
    
    Returns:
        tuple of (list of comments or [] if no comments, int number of likes)
    """
    conn, _ = photosdb.get_db_connection()

    results = conn.execute(
        """
        SELECT 
        ZGENERICASSET.ZUUID, --0: UUID of the photo
        ZCLOUDSHAREDCOMMENT.ZISLIKE, --1: comment is actually a "like"
        ZCLOUDSHAREDCOMMENT.Z_FOK_COMMENTEDASSET, --2: sort order for comments on a photo
        ZCLOUDSHAREDCOMMENT.ZCOMMENTDATE, --3: date of comment
        ZCLOUDSHAREDCOMMENT.ZCOMMENTTEXT, --4: text of comment
        ZCLOUDSHAREDCOMMENT.ZCOMMENTERHASHEDPERSONID, --5: hashed ID of person who made comment/like
        ZCLOUDSHAREDCOMMENT.ZISMYCOMMENT --6: is my (this user's) comment
        FROM ZCLOUDSHAREDCOMMENT
        JOIN ZGENERICASSET ON
        ZGENERICASSET.Z_PK = ZCLOUDSHAREDCOMMENT.ZCOMMENTEDASSET
        OR
        ZGENERICASSET.Z_PK = ZCLOUDSHAREDCOMMENT.ZLIKEDASSET
        WHERE ZGENERICASSET.ZUUID = ?
    """,
        ([uuid]),
    ).fetchall()

    comments = []
    likes = []
    for row in results:
        photo_uuid = row[0]
        sort_fok = row[2] or 0  # sort_fok is Null/None for likes
        is_like = bool(row[1])
        text = row[4]
        user_info = get_shared_person_info(photosdb, row[5])
        try:
            dt = datetime.datetime.fromtimestamp(row[3] + TIME_DELTA)
        except:
            dt = datetime.datetime(1970, 1, 1)
        ismine = bool(row[6])
        if is_like:
            # it's a like
            likes.append(Like(photo_uuid, sort_fok, dt, user_info[2], ismine))
        elif text:
            # comment
            comments.append(
                Comment(photo_uuid, sort_fok, dt, user_info[2], ismine, text)
            )
    if likes:
        likes.sort(key=lambda x: x.datetime)
    if comments:
        comments.sort(key=lambda x: x.sort_fok)
    return (comments, likes)


def main():
    if len(sys.argv) > 1:
        # library as first argument
        photosdb = osxphotos.PhotosDB(dbfile=sys.argv[1])
    else:
        # open default library
        photosdb = osxphotos.PhotosDB()

    # shared albums
    shared_albums = photosdb.album_info_shared
    for album in shared_albums:
        print(f"Processing album {album.title}")
        # only shared albums can have comments
        for photo in album.photos:
            comments, likes = get_comments(photosdb, photo.uuid)
            if comments or likes:
                print(f"{photo.uuid}, {photo.original_filename}: ")
            if likes:
                print("Likes:")
                for like in likes:
                    print(like)
            if comments:
                print("Comments:")
                for comment in comments:
                    print(comment)


if __name__ == "__main__":
    main()
