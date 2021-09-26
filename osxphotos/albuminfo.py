"""
AlbumInfo and FolderInfo classes for dealing with albums and folders

AlbumInfo class
Represents a single Album in the Photos library and provides access to the album's attributes
PhotosDB.albums() returns a list of AlbumInfo objects

FolderInfo class
Represents a single Folder in the Photos library and provides access to the folders attributes
PhotosDB.folders() returns a list of FolderInfo objects
"""

from datetime import datetime, timedelta, timezone

from ._constants import (
    _PHOTOS_4_ALBUM_KIND,
    _PHOTOS_4_TOP_LEVEL_ALBUM,
    _PHOTOS_4_VERSION,
    _PHOTOS_5_ALBUM_KIND,
    _PHOTOS_5_FOLDER_KIND,
    TIME_DELTA,
    AlbumSortOrder,
)
from .datetime_utils import get_local_tz
from .query_builder import get_query


def sort_list_by_keys(values, sort_keys):
    """Sorts list values by a second list sort_keys
        e.g. given ["a","c","b"], [1, 3, 2], returns ["a", "b", "c"]

    Args:
        values: a list of values to be sorted
        sort_keys: a list of keys to sort values by

    Returns:
        list of values, sorted by sort_keys

    Raises:
        ValueError: raised if len(values) != len(sort_keys)
    """
    if len(values) != len(sort_keys):
        return ValueError("values and sort_keys must have same length")

    return list(zip(*sorted(zip(sort_keys, values))))[1]


class AlbumInfoBaseClass:
    """
    Base class for AlbumInfo, ImportInfo
    Info about a specific Album, contains all the details about the album
    including folders, photos, etc.
    """

    def __init__(self, db=None, uuid=None):
        self._uuid = uuid
        self._db = db
        self._title = self._db._dbalbum_details[uuid]["title"]
        self._creation_date_timestamp = self._db._dbalbum_details[uuid]["creation_date"]
        self._start_date_timestamp = self._db._dbalbum_details[uuid]["start_date"]
        self._end_date_timestamp = self._db._dbalbum_details[uuid]["end_date"]
        self._local_tz = get_local_tz(
            datetime.fromtimestamp(self._creation_date_timestamp + TIME_DELTA)
        )

    @property
    def uuid(self):
        """return uuid of album"""
        return self._uuid

    @property
    def creation_date(self):
        """return creation date of album"""
        try:
            return self._creation_date
        except AttributeError:
            try:
                self._creation_date = (
                    datetime.fromtimestamp(
                        self._creation_date_timestamp + TIME_DELTA
                    ).astimezone(tz=self._local_tz)
                    if self._creation_date_timestamp
                    else datetime(1970, 1, 1, 0, 0, 0).astimezone(
                        tz=timezone(timedelta(0))
                    )
                )
            except ValueError:
                self._creation_date = datetime(1970, 1, 1, 0, 0, 0).astimezone(
                    tz=timezone(timedelta(0))
                )
            return self._creation_date

    @property
    def start_date(self):
        """For Albums, return start date (earliest image) of album or None for albums with no images
        For Import Sessions, return start date of import session (when import began)"""
        try:
            return self._start_date
        except AttributeError:
            try:
                self._start_date = (
                    datetime.fromtimestamp(
                        self._start_date_timestamp + TIME_DELTA
                    ).astimezone(tz=self._local_tz)
                    if self._start_date_timestamp
                    else None
                )
            except ValueError:
                self._start_date = None
            return self._start_date

    @property
    def end_date(self):
        """For Albums, return end date (most recent image) of album or None for albums with no images
        For Import Sessions, return end date of import sessions (when import was completed)"""
        try:
            return self._end_date
        except AttributeError:
            try:
                self._end_date = (
                    datetime.fromtimestamp(
                        self._end_date_timestamp + TIME_DELTA
                    ).astimezone(tz=self._local_tz)
                    if self._end_date_timestamp
                    else None
                )
            except ValueError:
                self._end_date = None
            return self._end_date

    @property
    def photos(self):
        return []

    @property
    def owner(self):
        """Return name of photo owner for shared album (Photos 5+ only), or None if not shared"""
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return None

        try:
            return self._owner
        except AttributeError:
            try:
                personid = self._db._dbalbum_details[self.uuid][
                    "cloudownerhashedpersonid"
                ]
                self._owner = (
                    self._db._db_hashed_person_id[personid]["full_name"]
                    if personid
                    else None
                )
            except KeyError:
                self._owner = None
            return self._owner

    def __len__(self):
        """return number of photos contained in album"""
        return len(self.photos)


class AlbumInfo(AlbumInfoBaseClass):
    """
    Base class for AlbumInfo, ImportInfo
    Info about a specific Album, contains all the details about the album
    including folders, photos, etc.
    """

    @property
    def title(self):
        """return title / name of album"""
        return self._title

    @property
    def photos(self):
        """return list of photos contained in album sorted in same sort order as Photos"""
        try:
            return self._photos
        except AttributeError:
            if self.uuid in self._db._dbalbums_album:
                uuid, sort_order = zip(*self._db._dbalbums_album[self.uuid])
                sorted_uuid = sort_list_by_keys(uuid, sort_order)
                photos = self._db.photos_by_uuid(sorted_uuid)
                sort_order = self.sort_order
                if sort_order == AlbumSortOrder.NEWEST_FIRST:
                    self._photos = sorted(photos, key=lambda p: p.date, reverse=True)
                elif sort_order == AlbumSortOrder.OLDEST_FIRST:
                    self._photos = sorted(photos, key=lambda p: p.date)
                elif sort_order == AlbumSortOrder.TITLE:
                    self._photos = sorted(photos, key=lambda p: p.title or "")
                else:
                    # assume AlbumSortOrder.MANUAL
                    self._photos = photos
            else:
                self._photos = []
            return self._photos

    @property
    def folder_names(self):
        """return hierarchical list of folders the album is contained in
        the folder list is in form:
        ["Top level folder", "sub folder 1", "sub folder 2", ...]
        returns empty list if album is not in any folders"""

        try:
            return self._folder_names
        except AttributeError:
            self._folder_names = self._db._album_folder_hierarchy_list(self._uuid)
            return self._folder_names

    @property
    def folder_list(self):
        """return hierarchical list of folders the album is contained in
        as list of FolderInfo objects in form
        ["Top level folder", "sub folder 1", "sub folder 2", ...]
        returns empty list if album is not in any folders"""

        try:
            return self._folders
        except AttributeError:
            self._folders = self._db._album_folder_hierarchy_folderinfo(self._uuid)
            return self._folders

    @property
    def parent(self):
        """returns FolderInfo object for parent folder or None if no parent (e.g. top-level album)"""
        try:
            return self._parent
        except AttributeError:
            if self._db._db_version <= _PHOTOS_4_VERSION:
                parent_uuid = self._db._dbalbum_details[self._uuid]["folderUuid"]
                self._parent = (
                    FolderInfo(db=self._db, uuid=parent_uuid)
                    if parent_uuid != _PHOTOS_4_TOP_LEVEL_ALBUM
                    else None
                )
            else:
                parent_pk = self._db._dbalbum_details[self._uuid]["parentfolder"]
                self._parent = (
                    FolderInfo(db=self._db, uuid=self._db._dbalbums_pk[parent_pk])
                    if parent_pk != self._db._folder_root_pk
                    else None
                )
            return self._parent

    @property
    def sort_order(self):
        """return sort order of album"""
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return AlbumSortOrder.MANUAL

        details = self._db._dbalbum_details[self._uuid]
        if details["customsortkey"] == 1:
            if details["customsortascending"] == 0:
                return AlbumSortOrder.NEWEST_FIRST
            elif details["customsortascending"] == 1:
                return AlbumSortOrder.OLDEST_FIRST
            else:
                return AlbumSortOrder.UNKNOWN
        elif details["customsortkey"] == 5:
            return AlbumSortOrder.TITLE
        elif details["customsortkey"] == 0:
            return AlbumSortOrder.MANUAL
        else:
            return AlbumSortOrder.UNKNOWN

    def photo_index(self, photo):
        """return index of photo in album (based on album sort order)"""
        index = 0
        for p in self.photos:
            if p.uuid == photo.uuid:
                return index
            index += 1
        else:
            raise ValueError(
                f"Photo with uuid {photo.uuid} does not appear to be in this album"
            )


class ImportInfo(AlbumInfoBaseClass):
    @property
    def photos(self):
        """return list of photos contained in import session"""
        try:
            return self._photos
        except AttributeError:
            uuid_list, sort_order = zip(
                *[
                    (uuid, self._db._dbphotos[uuid]["fok_import_session"])
                    for uuid in self._db._dbphotos
                    if self._db._dbphotos[uuid]["import_uuid"] == self.uuid
                ]
            )
            sorted_uuid = sort_list_by_keys(uuid_list, sort_order)
            self._photos = self._db.photos_by_uuid(sorted_uuid)
            return self._photos


class FolderInfo:
    """
    Info about a specific folder, contains all the details about the folder
    including folders, albums, etc
    """

    def __init__(self, db=None, uuid=None):
        self._uuid = uuid
        self._db = db
        if self._db._db_version <= _PHOTOS_4_VERSION:
            self._pk = None
            self._title = self._db._dbfolder_details[uuid]["name"]
        else:
            self._pk = self._db._dbalbum_details[uuid]["pk"]
            self._title = self._db._dbalbum_details[uuid]["title"]

    @property
    def title(self):
        """return title / name of folder"""
        return self._title

    @property
    def uuid(self):
        """return uuid of folder"""
        return self._uuid

    @property
    def album_info(self):
        """return list of albums (as AlbumInfo objects) contained in the folder"""
        try:
            return self._albums
        except AttributeError:
            if self._db._db_version <= _PHOTOS_4_VERSION:
                albums = [
                    AlbumInfo(db=self._db, uuid=album)
                    for album, detail in self._db._dbalbum_details.items()
                    if not detail["intrash"]
                    and detail["albumSubclass"] == _PHOTOS_4_ALBUM_KIND
                    and detail["folderUuid"] == self._uuid
                ]
            else:
                albums = [
                    AlbumInfo(db=self._db, uuid=album)
                    for album, detail in self._db._dbalbum_details.items()
                    if not detail["intrash"]
                    and detail["kind"] == _PHOTOS_5_ALBUM_KIND
                    and detail["parentfolder"] == self._pk
                ]
            self._albums = albums
            return self._albums

    @property
    def parent(self):
        """returns FolderInfo object for parent or None if no parent (e.g. top-level folder)"""
        try:
            return self._parent
        except AttributeError:
            if self._db._db_version <= _PHOTOS_4_VERSION:
                parent_uuid = self._db._dbfolder_details[self._uuid]["parentFolderUuid"]
                self._parent = (
                    FolderInfo(db=self._db, uuid=parent_uuid)
                    if parent_uuid != _PHOTOS_4_TOP_LEVEL_ALBUM
                    else None
                )
            else:
                parent_pk = self._db._dbalbum_details[self._uuid]["parentfolder"]
                self._parent = (
                    FolderInfo(db=self._db, uuid=self._db._dbalbums_pk[parent_pk])
                    if parent_pk != self._db._folder_root_pk
                    else None
                )
            return self._parent

    @property
    def subfolders(self):
        """return list of folders (as FolderInfo objects) contained in the folder"""
        try:
            return self._folders
        except AttributeError:
            if self._db._db_version <= _PHOTOS_4_VERSION:
                folders = [
                    FolderInfo(db=self._db, uuid=folder)
                    for folder, detail in self._db._dbfolder_details.items()
                    if not detail["intrash"]
                    and not detail["isMagic"]
                    and detail["parentFolderUuid"] == self._uuid
                ]
            else:
                folders = [
                    FolderInfo(db=self._db, uuid=album)
                    for album, detail in self._db._dbalbum_details.items()
                    if not detail["intrash"]
                    and detail["kind"] == _PHOTOS_5_FOLDER_KIND
                    and detail["parentfolder"] == self._pk
                ]
            self._folders = folders
            return self._folders

    def __len__(self):
        """returns count of folders + albums contained in the folder"""
        return len(self.subfolders) + len(self.album_info)
