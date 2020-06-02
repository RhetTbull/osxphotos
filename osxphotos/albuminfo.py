"""
AlbumInfo and FolderInfo classes for dealing with albums and folders

AlbumInfo class
Represents a single Album in the Photos library and provides access to the album's attributes
PhotosDB.albums() returns a list of AlbumInfo objects

FolderInfo class
Represents a single Folder in the Photos library and provides access to the folders attributes
PhotosDB.folders() returns a list of FolderInfo objects
"""

import logging

from ._constants import (
    _PHOTOS_4_ALBUM_KIND,
    _PHOTOS_4_TOP_LEVEL_ALBUM,
    _PHOTOS_4_VERSION,
    _PHOTOS_5_ALBUM_KIND,
    _PHOTOS_5_FOLDER_KIND,
)


class AlbumInfo:
    """
    Info about a specific Album, contains all the details about the album
    including folders, photos, etc.
    """

    def __init__(self, db=None, uuid=None):
        self._uuid = uuid
        self._db = db
        self._title = self._db._dbalbum_details[uuid]["title"]

    @property
    def title(self):
        """ return title / name of album """
        return self._title

    @property
    def uuid(self):
        """ return uuid of album """
        return self._uuid

    @property
    def photos(self):
        """ return list of photos contained in album """
        try:
            return self._photos
        except AttributeError:
            uuid = self._db._dbalbums_album[self._uuid]
            self._photos = self._db.photos(uuid=uuid)
            return self._photos

    @property
    def folder_names(self):
        """ return hierarchical list of folders the album is contained in
            the folder list is in form:
            ["Top level folder", "sub folder 1", "sub folder 2", ...]
            returns empty list if album is not in any folders """

        try:
            return self._folder_names
        except AttributeError:
            self._folder_names = self._db._album_folder_hierarchy_list(self._uuid)
            return self._folder_names

    @property
    def folder_list(self):
        """ return hierarchical list of folders the album is contained in
            as list of FolderInfo objects in form 
            ["Top level folder", "sub folder 1", "sub folder 2", ...]
            returns empty list if album is not in any folders """

        try:
            return self._folders
        except AttributeError:
            self._folders = self._db._album_folder_hierarchy_folderinfo(self._uuid)
            return self._folders

    @property
    def parent(self):
        """ returns FolderInfo object for parent folder or None if no parent (e.g. top-level album) """
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

    def __len__(self):
        """ return number of photos contained in album """
        return len(self.photos)


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
        """ return title / name of folder"""
        return self._title

    @property
    def uuid(self):
        """ return uuid of folder """
        return self._uuid

    @property
    def album_info(self):
        """ return list of albums (as AlbumInfo objects) contained in the folder """
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
        """ returns FolderInfo object for parent or None if no parent (e.g. top-level folder) """
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
        """ return list of folders (as FolderInfo objects) contained in the folder """
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
        """ returns count of folders + albums contained in the folder """
        return len(self.subfolders) + len(self.album_info)
