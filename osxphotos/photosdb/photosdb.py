"""
PhotosDB class
Processes a Photos.app library database to extract information about photos
"""

import logging
import os
import os.path
import pathlib
import platform
import sqlite3
import sys
import tempfile
from datetime import datetime
from pprint import pformat
from shutil import copyfile

from .._constants import (
    _MOVIE_TYPE,
    _PHOTO_TYPE,
    _PHOTOS_3_VERSION,
    _PHOTOS_4_ALBUM_KIND,
    _PHOTOS_4_ROOT_FOLDER,
    _PHOTOS_4_TOP_LEVEL_ALBUM,
    _PHOTOS_4_VERSION,
    _PHOTOS_5_ALBUM_KIND,
    _PHOTOS_5_FOLDER_KIND,
    _PHOTOS_5_ROOT_FOLDER_KIND,
    _PHOTOS_5_SHARED_ALBUM_KIND,
    _PHOTOS_5_VERSION,
    _TESTED_DB_VERSIONS,
    _TESTED_OS_VERSIONS,
    _UNKNOWN_PERSON,
)
from .._version import __version__
from ..albuminfo import AlbumInfo, FolderInfo
from ..photoinfo import PhotoInfo
from ..utils import (
    _check_file_exists,
    _db_is_locked,
    _debug,
    _get_os_version,
    _open_sql_file,
    get_last_library_path,
)


# TODO: Add test for imageTimeZoneOffsetSeconds = None
# TODO: Fix command line so multiple --keyword, etc. are AND (instead of OR as they are in .photos())
#       Or fix the help text to match behavior
# TODO: Add test for __str__
# TODO: Add special albums and magic albums


class PhotosDB:
    """ Processes a Photos.app library database to extract information about photos """

    # import additional methods
    from ._photosdb_process_exif import _process_exifinfo
    from ._photosdb_process_searchinfo import (
        _process_searchinfo,
        labels,
        labels_normalized,
        labels_as_dict,
        labels_normalized_as_dict,
    )

    def __init__(self, *dbfile_, dbfile=None):
        """ create a new PhotosDB object 
            path to photos library or database may be specified EITHER as first argument or as named argument dbfile=path 
            specify full path to photos library or photos.db as first argument 
            specify path to photos library or photos.db using named argument dbfile=path """

        # Check OS version
        system = platform.system()
        (_, major, _) = _get_os_version()
        if system != "Darwin" or (major not in _TESTED_OS_VERSIONS):
            logging.warning(
                f"WARNING: This module has only been tested with MacOS 10."
                f"[{', '.join(_TESTED_OS_VERSIONS)}]: "
                f"you have {system}, OS version: {major}"
            )

        # create a temporary directory
        # tempfile.TemporaryDirectory gets cleaned up when the object does
        self._tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
        self._tempdir_name = self._tempdir.name

        # set up the data structures used to store all the Photo database info

        # if True, will treat persons as keywords when exporting metadata
        self.use_persons_as_keywords = False

        # if True, will treat albums as keywords when exporting metadata
        self.use_albums_as_keywords = False

        # Path to the Photos library database file
        # photos.db in the photos library database/ directory
        self._dbfile = None

        # the actual file with library data
        # in Photos 5 this is Photos.sqlite instead of photos.db
        self._dbfile_actual = None

        # Dict with information about all photos by uuid
        # This is the "master" data structure, built by process_database
        # key is a photo UUID, value is a dictionary with all the information
        # known about a photo
        # this is built by joining data from multiple queries against the photos database
        # several of the keys in the info dictionary point to other data structures described below
        # e.g. self._dbphotos[uuid]["keywords"] = self._dbkeywords_uuid[uuid]
        #      self._dbphotos[uuid]["persons"] = self._dbfaces_uuid[uuid]
        #      self._dbphotos[uuid]["albums"] = self._dbalbums_uuid[uuid]
        self._dbphotos = {}

        # Dict with information about all burst photos by burst uuid
        # key is UUID of the burst set, value is a set of photo UUIDs in the burst set
        # e.g. {'BD94B7C0-2EB8-43DB-98B4-3B8E9653C255': {'8B386814-CA8A-42AA-BCA8-97C1AA746D8A', '52B95550-DE4A-44DD-9E67-89E979F2E97F'}}
        self._dbphotos_burst = {}

        # Dict with additional information from RKMaster
        # key is UUID from RKMaster, value is dict with info related to each master
        # currently used to get information on RAW images
        self._dbphotos_master = {}

        # Dict with information about all persons/photos by uuid
        # key is photo UUID, value is list of face names in that photo
        # Note: Photos 5 identifies faces even if not given a name
        # and those are labeled by process_database as _UNKNOWN_
        # e.g. {'1EB2B765-0765-43BA-A90C-0D0580E6172C': ['Katie', '_UNKNOWN_', 'Suzy']}
        self._dbfaces_uuid = {}

        # Dict with information about all persons/photos by person
        # key is person name, value is list of photo UUIDs
        # e.g. {'Maria': ['E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51']}
        self._dbfaces_person = {}

        # Dict with information about all keywords/photos by uuid
        # key is photo uuid and value is list of keywords
        # e.g.  {'1EB2B765-0765-43BA-A90C-0D0580E6172C': ['Kids']}
        self._dbkeywords_uuid = {}

        # Dict with information about all keywords/photos by keyword
        # key is keyword and value is list of photo UUIDs that have that keyword
        # e.g. {'England': ['DC99FBDD-7A52-4100-A5BB-344131646C30']}
        self._dbkeywords_keyword = {}

        # Dict with information about all albums/photos by uuid
        # key is photo UUID, value is list of album UUIDs the photo is contained in
        # e.g.  {'1EB2B765-0765-43BA-A90C-0D0580E6172C': ['0C514A98-7B77-4E4F-801B-364B7B65EAFA']}
        self._dbalbums_uuid = {}

        # Dict with information about all albums/photos by primary key in the album database
        # key is album pk, value is album uuid
        # e.g.  {'43': '0C514A98-7B77-4E4F-801B-364B7B65EAFA'}
        # specific to Photos versions >= 5
        self._dbalbums_pk = {}

        # Dict with information about all albums/photos by album
        # key is album UUID, value is list of photo UUIDs contained in that album
        # e.g. {'0C514A98-7B77-4E4F-801B-364B7B65EAFA': ['1EB2B765-0765-43BA-A90C-0D0580E6172C']}
        self._dbalbums_album = {}

        # Dict with information about album details
        # key is album UUID, value is a dict with some additional details
        # (mostly about cloud status) of the album
        # e.g.  {'0C514A98-7B77-4E4F-801B-364B7B65EAFA': {'cloudidentifier': None,
        #       'cloudlibrarystate': None, 'cloudlocalstate': 0, 'cloudownderlastname': None,
        #       'cloudownerfirstname': None, 'cloudownerhashedpersonid': None, 'title': 'Pumpkin Farm'}}
        self._dbalbum_details = {}

        # Dict with information about album titles
        # key is title of album, value is list of album UUIDs with that title
        # (It's possible to have more than one album with the same title)
        # e.g. {'Pumpkin Farm': ['0C514A98-7B77-4E4F-801B-364B7B65EAFA']}
        self._dbalbum_titles = {}

        # Dict with information about all the file system volumes/photos by uuid
        # key is volume UUID, value is name of file system volume
        # e.g. {'8A0B2944-7B09-4D06-9AC3-4B0BF3F363F1': 'MacBook Mojave'}
        # Used to find path of photos imported but not copied to the Photos library
        self._dbvolumes = {}

        # Dict with information about parent folders for folders and albums
        # key is album or folder UUID and value is list of UUIDs of parent folder
        # e.g. {'0C514A98-7B77-4E4F-801B-364B7B65EAFA': ['92D68107-B6C7-453B-96D2-97B0F26D5B8B'],}
        self._dbalbum_parent_folders = {}

        # Dict with information about folder hierarchy for each album / folder
        # key is uuid of album / folder, value is dict with uuid of descendant folder / album
        # structure is recursive as a descendant may itself have descendants
        # e.g. {'AA4145F5-098C-496E-9197-B7584958FF9B': {'99D24D3E-59E7-465F-B386-A48A94B00BC1': {'F2246D82-1A12-4994-9654-3DC6FE38A7A8': None}}, }
        self._dbalbum_folders = {}

        # Dict with information about folders
        self._dbfolder_details = {}

        # Will hold the primary key of root folder
        self._folder_root_pk = None

        if _debug():
            logging.debug(f"dbfile = {dbfile}")

        # get the path to photos library database
        if dbfile_:
            # got a library path as argument
            if dbfile:
                # shouldn't pass via both *args and dbfile=
                raise TypeError(
                    f"photos database path must be specified as argument or "
                    f"named parameter dbfile but not both: args: {dbfile_}, dbfile: {dbfile}",
                    dbfile_,
                    dbfile,
                )
            elif len(dbfile_) == 1:
                dbfile = dbfile_[0]
            else:
                raise TypeError(
                    f"__init__ takes only a single argument (photos database path): {dbfile_}",
                    dbfile_,
                )
        elif dbfile is None:
            dbfile = get_last_library_path()
            if dbfile is None:
                # get_last_library_path must have failed to find library
                raise FileNotFoundError("Could not get path to photo library database")

        if os.path.isdir(dbfile):
            # passed a directory, assume it's a photoslibrary
            dbfile = os.path.join(dbfile, "database/photos.db")

        # if get here, should have a dbfile path; make sure it exists
        if not _check_file_exists(dbfile):
            raise FileNotFoundError(f"dbfile {dbfile} does not exist", dbfile)

        if _debug():
            logging.debug(f"dbfile = {dbfile}")

        # init database names
        # _tmp_db is the file that will processed by _process_database4/5
        # assume _tmp_db will be _dbfile or _dbfile_actual based on Photos version
        # unless DB is locked, in which case _tmp_db will point to a temporary copy
        # if Photos <=4, _dbfile = _dbfile_actual = photos.db
        # if Photos >= 5, _dbfile = photos.db, from which we get DB version but the actual
        # photos data is in Photos.sqlite
        # In either case, a temporary copy will be made if the DB is locked by Photos
        # or photosanalysisd
        self._dbfile = self._dbfile_actual = self._tmp_db = os.path.abspath(dbfile)

        # if database is exclusively locked, make a copy of it and use the copy
        # Photos maintains an exclusive lock on the database file while Photos is open
        # photoanalysisd sometimes maintains this lock even after Photos is closed
        # In those cases, make a temp copy of the file for sqlite3 to read
        if _db_is_locked(self._dbfile):
            self._tmp_db = self._copy_db_file(self._dbfile)

        self._db_version = self._get_db_version()

        # If Photos >= 5, actual data isn't in photos.db but in Photos.sqlite
        if int(self._db_version) > int(_PHOTOS_4_VERSION):
            dbpath = pathlib.Path(self._dbfile).parent
            dbfile = dbpath / "Photos.sqlite"
            if not _check_file_exists(dbfile):
                raise FileNotFoundError(f"dbfile {dbfile} does not exist", dbfile)
            else:
                self._dbfile_actual = self._tmp_db = dbfile
                # if database is exclusively locked, make a copy of it and use the copy
                if _db_is_locked(self._dbfile_actual):
                    self._tmp_db = self._copy_db_file(self._dbfile_actual)

            if _debug():
                logging.debug(
                    f"_dbfile = {self._dbfile}, _dbfile_actual = {self._dbfile_actual}"
                )

        library_path = os.path.dirname(os.path.abspath(dbfile))
        (library_path, _) = os.path.split(library_path)  # drop /database from path
        self._library_path = library_path
        if int(self._db_version) <= int(_PHOTOS_4_VERSION):
            masters_path = os.path.join(library_path, "Masters")
            self._masters_path = masters_path
        else:
            masters_path = os.path.join(library_path, "originals")
            self._masters_path = masters_path

        if _debug():
            logging.debug(f"library = {library_path}, masters = {masters_path}")

        if int(self._db_version) <= int(_PHOTOS_4_VERSION):
            self._process_database4()
        else:
            self._process_database5()

    @property
    def keywords_as_dict(self):
        """ return keywords as dict of keyword, count in reverse sorted order (descending) """
        keywords = {}
        for k in self._dbkeywords_keyword.keys():
            keywords[k] = len(self._dbkeywords_keyword[k])
        keywords = dict(sorted(keywords.items(), key=lambda kv: kv[1], reverse=True))
        return keywords

    @property
    def persons_as_dict(self):
        """ return persons as dict of person, count in reverse sorted order (descending) """
        persons = {}
        for k in self._dbfaces_person.keys():
            persons[k] = len(self._dbfaces_person[k])
        persons = dict(sorted(persons.items(), key=lambda kv: kv[1], reverse=True))
        return persons

    @property
    def albums_as_dict(self):
        """ return albums as dict of albums, count in reverse sorted order (descending) """
        albums = {}
        album_keys = [
            k
            for k in self._dbalbums_album.keys()
            if self._dbalbum_details[k]["cloudownerhashedpersonid"] is None
            and not self._dbalbum_details[k]["intrash"]
        ]
        for k in album_keys:
            title = self._dbalbum_details[k]["title"]
            if title in albums:
                albums[title] += len(self._dbalbums_album[k])
            else:
                albums[title] = len(self._dbalbums_album[k])
        albums = dict(sorted(albums.items(), key=lambda kv: kv[1], reverse=True))
        return albums

    @property
    def albums_shared_as_dict(self):
        """ returns shared albums as dict of albums, count in reverse sorted order (descending)
            valid only on Photos 5; on Photos <= 4, prints warning and returns empty dict """

        # if _dbalbum_details[key]["cloudownerhashedpersonid"] is not None, then it's a shared album
        if self._db_version <= _PHOTOS_4_VERSION:
            logging.warning(
                f"albums_shared not implemented for Photos versions < {_PHOTOS_5_VERSION}"
            )
            return {}

        albums = {}
        album_keys = [
            k
            for k in self._dbalbums_album.keys()
            if self._dbalbum_details[k]["cloudownerhashedpersonid"] is not None
        ]
        for k in album_keys:
            title = self._dbalbum_details[k]["title"]
            if title in albums:
                albums[title] += len(self._dbalbums_album[k])
            else:
                albums[title] = len(self._dbalbums_album[k])
        albums = dict(sorted(albums.items(), key=lambda kv: kv[1], reverse=True))
        return albums

    @property
    def keywords(self):
        """ return list of keywords found in photos database """
        keywords = self._dbkeywords_keyword.keys()
        return list(keywords)

    @property
    def persons(self):
        """ return list of persons found in photos database """
        persons = self._dbfaces_person.keys()
        return list(persons)

    @property
    def folder_info(self):
        """ return list FolderInfo objects representing top-level folders in the photos database """
        if self._db_version <= _PHOTOS_4_VERSION:
            folders = [
                FolderInfo(db=self, uuid=folder)
                for folder, detail in self._dbfolder_details.items()
                if not detail["intrash"]
                and not detail["isMagic"]
                and detail["parentFolderUuid"] == _PHOTOS_4_TOP_LEVEL_ALBUM
            ]
        else:
            folders = [
                FolderInfo(db=self, uuid=album)
                for album, detail in self._dbalbum_details.items()
                if not detail["intrash"]
                and detail["kind"] == _PHOTOS_5_FOLDER_KIND
                and detail["parentfolder"] == self._folder_root_pk
            ]
        return folders

    @property
    def folders(self):
        """ return list of top-level folder names in the photos database """
        if self._db_version <= _PHOTOS_4_VERSION:
            folder_names = [
                folder["name"]
                for folder in self._dbfolder_details.values()
                if not folder["intrash"]
                and not folder["isMagic"]
                and folder["parentFolderUuid"] == _PHOTOS_4_TOP_LEVEL_ALBUM
            ]
        else:
            folder_names = [
                detail["title"]
                for detail in self._dbalbum_details.values()
                if not detail["intrash"]
                and detail["kind"] == _PHOTOS_5_FOLDER_KIND
                and detail["parentfolder"] == self._folder_root_pk
            ]
        return folder_names

    @property
    def album_info(self):
        """ return list of AlbumInfo objects for each album in the photos database """

        albums = [
            AlbumInfo(db=self, uuid=album)
            for album in self._dbalbums_album.keys()
            if self._dbalbum_details[album]["cloudownerhashedpersonid"] is None
            and not self._dbalbum_details[album]["intrash"]
        ]
        return albums

    @property
    def album_info_shared(self):
        """ return list of AlbumInfo objects for each shared album in the photos database
            only valid for Photos 5; on Photos <= 4, prints warning and returns empty list """
        # if _dbalbum_details[key]["cloudownerhashedpersonid"] is not None, then it's a shared album

        if self._db_version <= _PHOTOS_4_VERSION:
            logging.warning(
                f"albums_shared not implemented for Photos versions < {_PHOTOS_5_VERSION}"
            )
            return []

        albums_shared = [
            AlbumInfo(db=self, uuid=album)
            for album in self._dbalbums_album.keys()
            if self._dbalbum_details[album]["cloudownerhashedpersonid"] is not None
            and not self._dbalbum_details[album]["intrash"]
        ]
        return albums_shared

    @property
    def albums(self):
        """ return list of albums found in photos database """

        # Could be more than one album with same name
        # Right now, they are treated as same album and photos are combined from albums with same name

        albums = {
            self._dbalbum_details[album]["title"]
            for album in self._dbalbums_album.keys()
            if self._dbalbum_details[album]["cloudownerhashedpersonid"] is None
            and not self._dbalbum_details[album]["intrash"]
        }
        return list(albums)

    @property
    def albums_shared(self):
        """ return list of shared albums found in photos database
            only valid for Photos 5; on Photos <= 4, prints warning and returns empty list """

        # Could be more than one album with same name
        # Right now, they are treated as same album and photos are combined from albums with same name

        # if _dbalbum_details[key]["cloudownerhashedpersonid"] is not None, then it's a shared album

        if self._db_version <= _PHOTOS_4_VERSION:
            logging.warning(
                f"album_names_shared not implemented for Photos versions < {_PHOTOS_5_VERSION}"
            )
            return []

        albums = {
            self._dbalbum_details[album]["title"]
            for album in self._dbalbums_album.keys()
            if self._dbalbum_details[album]["cloudownerhashedpersonid"] is not None
            and not self._dbalbum_details[album]["intrash"]
        }
        return list(albums)

    @property
    def db_version(self):
        """ return the database version as stored in LiGlobals table """
        return self._db_version

    @property
    def db_path(self):
        """ returns path to the Photos library database PhotosDB was initialized with """
        return os.path.abspath(self._dbfile)

    @property
    def library_path(self):
        """ returns path to the Photos library PhotosDB was initialized with """
        return self._library_path

    def _copy_db_file(self, fname):
        """ copies the sqlite database file to a temp file """
        """ returns the name of the temp file """
        """ If sqlite shared memory and write-ahead log files exist, those are copied too """
        # required because python's sqlite3 implementation can't read a locked file
        # _, suffix = os.path.splitext(fname)
        try:
            dest_name = pathlib.Path(fname).name
            dest_path = os.path.join(self._tempdir_name, dest_name)
            copyfile(fname, dest_path)
            # copy write-ahead log and shared memory files (-wal and -shm) files if they exist
            if os.path.exists(f"{fname}-wal"):
                copyfile(f"{fname}-wal", f"{dest_path}-wal")
            if os.path.exists(f"{fname}-shm"):
                copyfile(f"{fname}-shm", f"{dest_path}-shm")
        except:
            print("Error copying " + fname + " to " + dest_path, file=sys.stderr)
            raise Exception

        if _debug():
            logging.debug(dest_path)

        return dest_path

    def _get_db_version(self):
        """ gets the Photos DB version from LiGlobals table """
        """ returns the version as str"""
        version = None

        (conn, c) = _open_sql_file(self._tmp_db)

        # get database version
        c.execute(
            "SELECT value from LiGlobals where LiGlobals.keyPath is 'libraryVersion'"
        )
        version = c.fetchone()[0]
        conn.close()

        if version not in _TESTED_DB_VERSIONS:
            print(
                f"WARNING: Only tested on database versions [{', '.join(_TESTED_DB_VERSIONS)}]"
                + f" You have database version={version} which has not been tested"
            )

        return version

    def _process_database4(self):
        """ process the Photos database to extract info
            works on Photos version <= 4.0 """

        # Epoch is Jan 1, 2001
        td = (datetime(2001, 1, 1, 0, 0) - datetime(1970, 1, 1, 0, 0)).total_seconds()

        (conn, c) = _open_sql_file(self._tmp_db)

        # Look for all combinations of persons and pictures
        c.execute(
            """ select RKPerson.name, RKVersion.uuid from RKFace, RKPerson, RKVersion, RKMaster 
                where RKFace.personID = RKperson.modelID and RKVersion.modelId = RKFace.ImageModelId 
                and RKVersion.masterUuid = RKMaster.uuid  
                and RKVersion.isInTrash = 0 """
        )
        for person in c:
            if person[0] is None:
                continue
            if not person[1] in self._dbfaces_uuid:
                self._dbfaces_uuid[person[1]] = []
            if not person[0] in self._dbfaces_person:
                self._dbfaces_person[person[0]] = []
            self._dbfaces_uuid[person[1]].append(person[0])
            self._dbfaces_person[person[0]].append(person[1])

        # Get info on albums
        c.execute(
            """ select 
                RKAlbum.uuid, 
                RKVersion.uuid 
                from RKAlbum, RKVersion, RKAlbumVersion 
                where RKAlbum.modelID = RKAlbumVersion.albumId and 
                RKAlbumVersion.versionID = RKVersion.modelId  
                and RKVersion.isInTrash = 0 """
        )
        for album in c:
            # store by uuid in _dbalbums_uuid and by album in _dbalbums_album
            if not album[1] in self._dbalbums_uuid:
                self._dbalbums_uuid[album[1]] = []
            if not album[0] in self._dbalbums_album:
                self._dbalbums_album[album[0]] = []
            self._dbalbums_uuid[album[1]].append(album[0])
            self._dbalbums_album[album[0]].append(album[1])

        # now get additional details about albums
        c.execute(
            """ SELECT 
                uuid, 
                name, 
                cloudLibraryState, 
                cloudIdentifier, 
                isInTrash, 
                folderUuid,
                albumType, 
                albumSubclass 
                FROM RKAlbum """
        )

        # Order of results
        # 0:    uuid
        # 1:    name
        # 2:    cloudLibraryState
        # 3:    cloudIdentifier
        # 4:    isInTrash
        # 5:    folderUuid
        # 6:    albumType
        # 7:    albumSubclass -- if 3, normal user album

        for album in c:
            self._dbalbum_details[album[0]] = {
                "_uuid": album[0],
                "title": album[1],
                "cloudlibrarystate": album[2],
                "cloudidentifier": album[3],
                "intrash": False if album[4] == 0 else True,
                "cloudlocalstate": None,  # Photos 5
                "cloudownerfirstname": None,  # Photos 5
                "cloudownderlastname": None,  # Photos 5
                "cloudownerhashedpersonid": None,  # Photos 5
                "folderUuid": album[5],
                "albumType": album[6],
                "albumSubclass": album[7],
            }

        # get details about folders
        c.execute(
            """ SELECT 
                uuid, 
                modelId, 
                name, 
                isMagic, 
                isInTrash, 
                folderType, 
                parentFolderUuid, 
                folderPath
                FROM RKFolder """
        )

        # Order of results
        # 0     uuid,
        # 1     modelId,
        # 2     name,
        # 3     isMagic,
        # 4     isInTrash,
        # 5     folderType,
        # 6     parentFolderUuid,
        # 7     folderPath

        for row in c:
            uuid = row[0]
            self._dbfolder_details[uuid] = {
                "_uuid": row[0],
                "modelId": row[1],
                "name": row[2],
                "isMagic": row[3],
                "intrash": row[4],
                "folderType": row[5],
                "parentFolderUuid": row[6],
                "folderPath": row[7],
            }

        # build _dbalbum_folders in form uuid: [parent uuid] to be consistent with _process_database5
        for album, details in self._dbalbum_details.items():
            # album can be in a single folder
            parent = details["folderUuid"]
            self._dbalbum_parent_folders[album] = [parent]

        # build folder hierarchy
        for album, details in self._dbalbum_details.items():
            parent_folder = details["folderUuid"]
            if details[
                "albumSubclass"
            ] == _PHOTOS_4_ALBUM_KIND and parent_folder not in [
                _PHOTOS_4_TOP_LEVEL_ALBUM
            ]:
                folder_hierarchy = self._build_album_folder_hierarchy_4(parent_folder)
                self._dbalbum_folders[album] = folder_hierarchy
            else:
                self._dbalbum_folders[album] = {}

        if _debug():
            logging.debug(f"Finished walking through albums")
            logging.debug(pformat(self._dbalbums_album))
            logging.debug(pformat(self._dbalbums_uuid))
            logging.debug(pformat(self._dbalbum_details))
            logging.debug(pformat(self._dbalbum_folders))
            logging.debug(pformat(self._dbfolder_details))

        # Get info on keywords
        c.execute(
            """ select RKKeyword.name, RKVersion.uuid, RKMaster.uuid from 
                RKKeyword, RKKeywordForVersion, RKVersion, RKMaster 
                where RKKeyword.modelId = RKKeyWordForVersion.keywordID and 
                RKVersion.modelID = RKKeywordForVersion.versionID and 
                RKMaster.uuid = RKVersion.masterUuid and 
                RKVersion.isInTrash = 0 """
        )
        for keyword in c:
            if not keyword[1] in self._dbkeywords_uuid:
                self._dbkeywords_uuid[keyword[1]] = []
            if not keyword[0] in self._dbkeywords_keyword:
                self._dbkeywords_keyword[keyword[0]] = []
            self._dbkeywords_uuid[keyword[1]].append(keyword[0])
            self._dbkeywords_keyword[keyword[0]].append(keyword[1])

        # Get info on disk volumes
        c.execute("select RKVolume.modelId, RKVolume.name from RKVolume")
        for vol in c:
            self._dbvolumes[vol[0]] = vol[1]

        # Get photo details
        if self._db_version < _PHOTOS_3_VERSION:
            # Photos < 3.0 doesn't have RKVersion.selfPortrait (selfie)
            c.execute(
                """ SELECT RKVersion.uuid, RKVersion.modelId, RKVersion.masterUuid, RKVersion.filename, 
                    RKVersion.lastmodifieddate, RKVersion.imageDate, RKVersion.mainRating, 
                    RKVersion.hasAdjustments, RKVersion.hasKeywords, RKVersion.imageTimeZoneOffsetSeconds, 
                    RKMaster.volumeId, RKMaster.imagePath, RKVersion.extendedDescription, RKVersion.name, 
                    RKMaster.isMissing, RKMaster.originalFileName, RKVersion.isFavorite, RKVersion.isHidden, 
                    RKVersion.latitude, RKVersion.longitude, 
                    RKVersion.adjustmentUuid, RKVersion.type, RKMaster.UTI,
                    RKVersion.burstUuid, RKVersion.burstPickType,
                    RKVersion.specialType, RKMaster.modelID, null, RKVersion.momentUuid,
                    RKVersion.rawMasterUuid,
                    RKVersion.nonRawMasterUuid,
                    RKMaster.alternateMasterUuid
                    FROM RKVersion, RKMaster WHERE RKVersion.isInTrash = 0 AND 
                    RKVersion.masterUuid = RKMaster.uuid AND RKVersion.filename NOT LIKE '%.pdf' """
            )
        else:
            c.execute(
                """ SELECT RKVersion.uuid, RKVersion.modelId, RKVersion.masterUuid, RKVersion.filename, 
                    RKVersion.lastmodifieddate, RKVersion.imageDate, RKVersion.mainRating, 
                    RKVersion.hasAdjustments, RKVersion.hasKeywords, RKVersion.imageTimeZoneOffsetSeconds, 
                    RKMaster.volumeId, RKMaster.imagePath, RKVersion.extendedDescription, RKVersion.name, 
                    RKMaster.isMissing, RKMaster.originalFileName, RKVersion.isFavorite, RKVersion.isHidden, 
                    RKVersion.latitude, RKVersion.longitude, 
                    RKVersion.adjustmentUuid, RKVersion.type, RKMaster.UTI,
                    RKVersion.burstUuid, RKVersion.burstPickType,
                    RKVersion.specialType, RKMaster.modelID,
                    RKVersion.selfPortrait,
                    RKVersion.momentUuid,
                    RKVersion.rawMasterUuid,
                    RKVersion.nonRawMasterUuid,
                    RKMaster.alternateMasterUuid
                    FROM RKVersion, RKMaster WHERE RKVersion.isInTrash = 0 AND 
                    RKVersion.masterUuid = RKMaster.uuid AND RKVersion.filename NOT LIKE '%.pdf' """
            )

        # order of results
        # 0     RKVersion.uuid
        # 1     RKVersion.modelId
        # 2     RKVersion.masterUuid
        # 3     RKVersion.filename
        # 4     RKVersion.lastmodifieddate
        # 5     RKVersion.imageDate
        # 6     RKVersion.mainRating
        # 7     RKVersion.hasAdjustments
        # 8     RKVersion.hasKeywords
        # 9     RKVersion.imageTimeZoneOffsetSeconds
        # 10    RKMaster.volumeId
        # 11    RKMaster.imagePath
        # 12    RKVersion.extendedDescription
        # 13    RKVersion.name
        # 14    RKMaster.isMissing
        # 15    RKMaster.originalFileName
        # 16    RKVersion.isFavorite
        # 17    RKVersion.isHidden
        # 18    RKVersion.latitude
        # 19    RKVersion.longitude
        # 20    RKVersion.adjustmentUuid
        # 21    RKVersion.type
        # 22    RKMaster.UTI
        # 23    RKVersion.burstUuid
        # 24    RKVersion.burstPickType
        # 25    RKVersion.specialType
        # 26    RKMaster.modelID
        # 27    RKVersion.selfPortrait -- 1 if selfie, Photos >= 3, not present for Photos < 3
        # 28    RKVersion.momentID (# 27 for Photos < 3)
        # 29    RKVersion.rawMasterUuid, -- UUID of RAW master
        # 30    RKVersion.nonRawMasterUuid, -- UUID of non-RAW master
        # 31    RKMaster.alternateMasterUuid -- UUID of alternate master (will be RAW master for JPEG and JPEG master for RAW)

        for row in c:
            uuid = row[0]
            if _debug():
                logging.debug(f"uuid = '{uuid}, master = '{row[2]}")
            self._dbphotos[uuid] = {}
            self._dbphotos[uuid]["_uuid"] = uuid  # stored here for easier debugging
            self._dbphotos[uuid]["modelID"] = row[1]
            self._dbphotos[uuid]["masterUuid"] = row[2]
            self._dbphotos[uuid]["filename"] = row[3]

            # There are sometimes negative values for lastmodifieddate in the database
            # I don't know what these mean but they will raise exception in datetime if
            # not accounted for
            if row[4] is not None and row[4] >= 0:
                self._dbphotos[uuid]["lastmodifieddate"] = datetime.fromtimestamp(
                    row[4] + td
                )
            else:
                self._dbphotos[uuid]["lastmodifieddate"] = None

            self._dbphotos[uuid]["imageDate"] = datetime.fromtimestamp(row[5] + td)
            self._dbphotos[uuid]["mainRating"] = row[6]
            self._dbphotos[uuid]["hasAdjustments"] = row[7]
            self._dbphotos[uuid]["hasKeywords"] = row[8]
            self._dbphotos[uuid]["imageTimeZoneOffsetSeconds"] = row[9]
            self._dbphotos[uuid]["volumeId"] = row[10]
            self._dbphotos[uuid]["imagePath"] = row[11]
            self._dbphotos[uuid]["extendedDescription"] = row[12]
            self._dbphotos[uuid]["name"] = row[13]
            self._dbphotos[uuid]["isMissing"] = row[14]
            self._dbphotos[uuid]["originalFilename"] = row[15]
            self._dbphotos[uuid]["favorite"] = row[16]
            self._dbphotos[uuid]["hidden"] = row[17]
            self._dbphotos[uuid]["latitude"] = row[18]
            self._dbphotos[uuid]["longitude"] = row[19]
            self._dbphotos[uuid]["adjustmentUuid"] = row[20]
            self._dbphotos[uuid]["adjustmentFormatID"] = None

            # find type and UTI
            if row[21] == 2:
                # photo
                self._dbphotos[uuid]["type"] = _PHOTO_TYPE
            elif row[21] == 8:
                # movie
                self._dbphotos[uuid]["type"] = _MOVIE_TYPE
            else:
                # unknown
                if _debug():
                    logging.debug(f"WARNING: {uuid} found unknown type {row[21]}")
                self._dbphotos[uuid]["type"] = None

            self._dbphotos[uuid]["UTI"] = row[22]

            # handle burst photos
            # if burst photo, determine whether or not it's a selected burst photo
            self._dbphotos[uuid]["burstUUID"] = row[23]
            self._dbphotos[uuid]["burstPickType"] = row[24]
            if row[23] is not None:
                # it's a burst photo
                self._dbphotos[uuid]["burst"] = True
                burst_uuid = row[23]
                if burst_uuid not in self._dbphotos_burst:
                    self._dbphotos_burst[burst_uuid] = set()
                self._dbphotos_burst[burst_uuid].add(uuid)
                if row[24] != 2 and row[24] != 4:
                    self._dbphotos[uuid][
                        "burst_key"
                    ] = True  # it's a key photo (selected from the burst)
                else:
                    self._dbphotos[uuid][
                        "burst_key"
                    ] = False  # it's a burst photo but not one that's selected
            else:
                # not a burst photo
                self._dbphotos[uuid]["burst"] = False
                self._dbphotos[uuid]["burst_key"] = None

            # RKVersion.specialType
            # 1 == panorama
            # 2 == slow-mo movie
            # 3 == time-lapse movie
            # 4 == HDR
            # 5 == live photo
            # 6 == screenshot
            # 7 == JPEG/RAW pair
            # 8 == HDR live photo
            # 9 = portrait

            # get info on special types
            self._dbphotos[uuid]["specialType"] = row[25]
            self._dbphotos[uuid]["masterModelID"] = row[26]
            self._dbphotos[uuid]["panorama"] = True if row[25] == 1 else False
            self._dbphotos[uuid]["slow_mo"] = True if row[25] == 2 else False
            self._dbphotos[uuid]["time_lapse"] = True if row[25] == 3 else False
            self._dbphotos[uuid]["hdr"] = (
                True if (row[25] == 4 or row[25] == 8) else False
            )
            self._dbphotos[uuid]["live_photo"] = (
                True if (row[25] == 5 or row[25] == 8) else False
            )
            self._dbphotos[uuid]["screenshot"] = True if row[25] == 6 else False
            self._dbphotos[uuid]["portrait"] = True if row[25] == 9 else False

            # selfies (front facing camera, RKVersion.selfPortrait == 1)
            if row[27] is not None:
                self._dbphotos[uuid]["selfie"] = True if row[27] == 1 else False
            else:
                self._dbphotos[uuid]["selfie"] = None

            self._dbphotos[uuid]["momentID"] = row[28]

            # Init cloud details that will be filled in later if cloud asset
            self._dbphotos[uuid]["cloudAssetGUID"] = None  # Photos 5
            self._dbphotos[uuid]["cloudLocalState"] = None  # Photos 5
            self._dbphotos[uuid]["cloudLibraryState"] = None
            self._dbphotos[uuid]["cloudStatus"] = None
            self._dbphotos[uuid]["cloudAvailable"] = None
            self._dbphotos[uuid]["incloud"] = None

            # TODO: NOT YET USED -- PLACEHOLDER for RAW processing (currently only in _process_database5)
            # original resource choice (e.g. RAW or jpeg)
            self._dbphotos[uuid]["original_resource_choice"] = None
            self._dbphotos[uuid]["raw_is_original"] = None

            # associated RAW image info
            self._dbphotos[uuid]["has_raw"] = True if row[25] == 7 else False
            self._dbphotos[uuid]["UTI_raw"] = None
            self._dbphotos[uuid]["raw_data_length"] = None
            self._dbphotos[uuid]["raw_info"] = None
            self._dbphotos[uuid]["resource_type"] = None  # Photos 5
            self._dbphotos[uuid]["datastore_subtype"] = None  # Photos 5
            self._dbphotos[uuid]["raw_master_uuid"] = row[29]
            self._dbphotos[uuid]["non_raw_master_uuid"] = row[30]
            self._dbphotos[uuid]["alt_master_uuid"] = row[31]

        # get additional details from RKMaster, needed for RAW processing
        c.execute(
            """ SELECT 
                RKMaster.uuid,
                RKMaster.volumeId, 
                RKMaster.imagePath, 
                RKMaster.isMissing, 
                RKMaster.originalFileName, 
                RKMaster.UTI,
                RKMaster.modelID, 
                RKMaster.fileSize, 
                RKMaster.isTrulyRaw,
                RKMaster.alternateMasterUuid
                FROM RKMaster
            """
        )

        # Order of results:
        # 0     RKMaster.uuid,
        # 1     RKMaster.volumeId,
        # 2     RKMaster.imagePath,
        # 3     RKMaster.isMissing,
        # 4     RKMaster.originalFileName,
        # 5     RKMaster.UTI,
        # 6     RKMaster.modelID,
        # 7     RKMaster.fileSize,
        # 8     RKMaster.isTrulyRaw,
        # 9     RKMaster.alternateMasterUuid

        for row in c:
            uuid = row[0]
            info = {}
            info["_uuid"] = uuid
            info["volumeId"] = row[1]
            info["imagePath"] = row[2]
            info["isMissing"] = row[3]
            info["originalFilename"] = row[4]
            info["UTI"] = row[5]
            info["modelID"] = row[6]
            info["fileSize"] = row[7]
            info["isTrulyRAW"] = row[8]
            info["alternateMasterUuid"] = row[9]
            self._dbphotos_master[uuid] = info

        # get details needed to find path of the edited photos
        c.execute(
            """ SELECT RKVersion.uuid, RKVersion.adjustmentUuid, RKModelResource.modelId,
                RKModelResource.resourceTag, RKModelResource.UTI, RKVersion.specialType,
                RKModelResource.attachedModelType, RKModelResource.resourceType
                FROM RKVersion
                JOIN RKModelResource on RKModelResource.attachedModelId = RKVersion.modelId
                WHERE RKVersion.isInTrash = 0 """
        )

        # Order of results:
        # 0     RKVersion.uuid
        # 1     RKVersion.adjustmentUuid
        # 2     RKModelResource.modelId
        # 3     RKModelResource.resourceTag
        # 4     RKModelResource.UTI
        # 5     RKVersion.specialType
        # 6     RKModelResource.attachedModelType
        # 7     RKModelResource.resourceType

        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                # get info on adjustments (edits)
                if self._dbphotos[uuid]["adjustmentUuid"] == row[3]:
                    if (
                        row[1] != "UNADJUSTEDNONRAW"
                        and row[1] != "UNADJUSTED"
                        # and row[4] == "public.jpeg"
                        and row[6] == 2
                    ):
                        if "edit_resource_id" in self._dbphotos[uuid]:
                            if _debug():
                                logging.debug(
                                    f"WARNING: found more than one edit_resource_id for "
                                    f"UUID {row[0]},adjustmentUUID {row[1]}, modelID {row[2]}"
                                )
                        # TODO: I think there should never be more than one edit but
                        # I've seen this once in my library
                        # should we return all edits or just most recent one?
                        # For now, return most recent edit
                        self._dbphotos[uuid]["edit_resource_id"] = row[2]

        # get details on external edits
        c.execute(
            """ SELECT RKVersion.uuid, 
                RKVersion.adjustmentUuid, 
                RKAdjustmentData.originator, 
                RKAdjustmentData.format 
                FROM RKVersion, RKAdjustmentData 
                WHERE RKVersion.adjustmentUuid = RKAdjustmentData.uuid 
                AND RKVersion.isInTrash = 0 """
        )

        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["adjustmentFormatID"] = row[3]

        # get details to find path of live photos
        c.execute(
            """ SELECT 
                RKVersion.uuid, 
                RKModelResource.modelId,
                RKModelResource.UTI,
                RKVersion.specialType, 
                RKModelResource.attachedModelType,
                RKModelResource.resourceType,
                RKModelResource.isOnDisk
                FROM RKVersion 
                INNER JOIN RKMaster on RKVersion.masterUuid = RKMaster.uuid 
                INNER JOIN RKModelResource on RKMaster.modelId = RKModelResource.attachedModelId  
                WHERE RKModelResource.UTI = 'com.apple.quicktime-movie'
				AND RKMaster.isInTrash = 0
                AND RKVersion.isInTrash = 0 
              """
        )

        # Order of results
        # 0     RKVersion.uuid,
        # 1     RKModelResource.modelId,
        # 2     RKModelResource.UTI,
        # 3     RKVersion.specialType,
        # 4     RKModelResource.attachedModelType,
        # 5     RKModelResource.resourceType
        # 6     RKModelResource.isOnDisk

        # TODO: don't think we need most of these fields, remove from SQL query?
        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["live_model_id"] = row[1]
                self._dbphotos[uuid]["modeResourceIsOnDisk"] = (
                    True if row[6] == 1 else False
                )

        # init any uuids that had no edits or live photos
        for uuid in self._dbphotos:
            if "edit_resource_id" not in self._dbphotos[uuid]:
                self._dbphotos[uuid]["edit_resource_id"] = None
            if "live_model_id" not in self._dbphotos[uuid]:
                self._dbphotos[uuid]["live_model_id"] = None
                self._dbphotos[uuid]["modeResourceIsOnDisk"] = None

        # get cloud details
        c.execute(
            """ SELECT 
                RKVersion.uuid, 
                RKMaster.cloudLibraryState,
                RKCloudResource.available, 
                RKCloudResource.status
                FROM RKCloudResource
                INNER JOIN RKMaster ON RKMaster.fingerprint = RKCloudResource.fingerprint
                INNER JOIN RKVersion ON RKVersion.masterUuid = RKMaster.uuid """
        )

        # Order of results
        # 0  RKMaster.uuid,
        # 1  RKMaster.cloudLibraryState,
        # 2  RKCloudResource.available,
        # 3  RKCloudResource.status

        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["cloudLibraryState"] = row[1]
                self._dbphotos[uuid]["cloudAvailable"] = row[2]
                self._dbphotos[uuid]["cloudStatus"] = row[3]
                self._dbphotos[uuid]["incloud"] = True if row[2] == 1 else False

        # get location data
        # get the country codes
        country_codes = c.execute(
            "SELECT modelID, countryCode "
            "FROM RKPlace "
            "WHERE countryCode IS NOT NULL "
        ).fetchall()
        countries = {code[0]: code[1] for code in country_codes}
        self._db_countries = countries

        # get the place data
        place_data = c.execute(
            "SELECT modelID, defaultName, type, area " "FROM RKPlace "
        ).fetchall()
        places = {p[0]: p for p in place_data}
        self._db_places = places

        for uuid in self._dbphotos:
            # get placeId which is then used to lookup defaultName
            place_ids_query = c.execute(
                "SELECT placeId "
                "FROM RKPlaceForVersion "
                f"WHERE versionId = '{self._dbphotos[uuid]['modelID']}'"
            )

            place_ids = [id[0] for id in place_ids_query.fetchall()]
            self._dbphotos[uuid]["placeIDs"] = place_ids
            country_code = [countries[x] for x in place_ids if x in countries]
            if len(country_code) > 1:
                logging.warning(f"Found more than one country code for uuid: {uuid}")

            if country_code:
                self._dbphotos[uuid]["countryCode"] = country_code[0]
            else:
                self._dbphotos[uuid]["countryCode"] = None

            # get the place info that matches the RKPlace modelIDs for this photo
            # (place_ids), sort by area (element 3 of the place_data tuple in places)
            place_names = [
                pname
                for pname in sorted(
                    [places[p] for p in places if p in place_ids],
                    key=lambda place: place[3],
                )
            ]

            self._dbphotos[uuid]["placeNames"] = place_names
            self._dbphotos[uuid]["reverse_geolocation"] = None  # Photos 5

        # build album_titles dictionary
        for album_id in self._dbalbum_details:
            title = self._dbalbum_details[album_id]["title"]
            if title in self._dbalbum_titles:
                self._dbalbum_titles[title].append(album_id)
            else:
                self._dbalbum_titles[title] = [album_id]

        # add volume name to _dbphotos_master
        for info in self._dbphotos_master.values():
            info["volume"] = (
                self._dbvolumes[info["volumeId"]]
                if info["volumeId"] is not None
                else None
            )

        # add data on RAW images
        for info in self._dbphotos.values():
            if info["has_raw"]:
                raw_uuid = info["raw_master_uuid"]
                info["raw_info"] = self._dbphotos_master[raw_uuid]

        # done with the database connection
        conn.close()

        # add faces and keywords to photo data
        for uuid in self._dbphotos:
            # keywords
            if self._dbphotos[uuid]["hasKeywords"] == 1:
                self._dbphotos[uuid]["keywords"] = self._dbkeywords_uuid[uuid]
            else:
                self._dbphotos[uuid]["keywords"] = []

            if uuid in self._dbfaces_uuid:
                self._dbphotos[uuid]["hasPersons"] = 1
                self._dbphotos[uuid]["persons"] = self._dbfaces_uuid[uuid]
            else:
                self._dbphotos[uuid]["hasPersons"] = 0
                self._dbphotos[uuid]["persons"] = []

            if uuid in self._dbalbums_uuid:
                self._dbphotos[uuid]["albums"] = self._dbalbums_uuid[uuid]
                self._dbphotos[uuid]["hasAlbums"] = 1
            else:
                self._dbphotos[uuid]["albums"] = []
                self._dbphotos[uuid]["hasAlbums"] = 0

            if self._dbphotos[uuid]["volumeId"] is not None:
                self._dbphotos[uuid]["volume"] = self._dbvolumes[
                    self._dbphotos[uuid]["volumeId"]
                ]
            else:
                self._dbphotos[uuid]["volume"] = None

        # done processing, dump debug data if requested
        if _debug():
            logging.debug("Faces (_dbfaces_uuid):")
            logging.debug(pformat(self._dbfaces_uuid))

            logging.debug("Faces by person (_dbfaces_person):")
            logging.debug(pformat(self._dbfaces_person))

            logging.debug("Keywords by uuid (_dbkeywords_uuid):")
            logging.debug(pformat(self._dbkeywords_uuid))

            logging.debug("Keywords by keyword (_dbkeywords_keywords):")
            logging.debug(pformat(self._dbkeywords_keyword))

            logging.debug("Albums by uuid (_dbalbums_uuid):")
            logging.debug(pformat(self._dbalbums_uuid))

            logging.debug("Albums by album (_dbalbums_albums):")
            logging.debug(pformat(self._dbalbums_album))

            logging.debug("Album details (_dbalbum_details):")
            logging.debug(pformat(self._dbalbum_details))

            logging.debug("Album titles (_dbalbum_titles):")
            logging.debug(pformat(self._dbalbum_titles))

            logging.debug("Volumes (_dbvolumes):")
            logging.debug(pformat(self._dbvolumes))

            logging.debug("Photos (_dbphotos):")
            logging.debug(pformat(self._dbphotos))

            logging.debug("Burst Photos (dbphotos_burst:")
            logging.debug(pformat(self._dbphotos_burst))

    def _build_album_folder_hierarchy_4(self, uuid, folders=None):
        """ recursively build folder/album hierarchy
            uuid: parent uuid of the album being processed 
                 (parent uuid is a folder in RKFolders)
            folders: dict holding the folder hierarchy 
            NOTE: This implementation is different than _build_album_folder_hierarchy_5 
            which takes the uuid of the album being processed.  Here uuid is the parent uuid
            of the parent folder album because in Photos <=4, folders are in RKFolders and 
            albums in RKAlbums.  In Photos 5, folders are just special albums 
            with kind = _PHOTOS_5_FOLDER_KIND """

        parent_uuid = self._dbfolder_details[uuid]["parentFolderUuid"]

        if parent_uuid is None:
            return folders

        if parent_uuid == _PHOTOS_4_TOP_LEVEL_ALBUM:
            if not folders:
                # this is a top-level folder with no sub-folders
                folders = {uuid: None}
            # at top of hierarchy, we're done
            return folders

        # recurse to keep building
        if not folders:
            # first time building
            folders = {uuid: None}
        folders = {parent_uuid: folders}
        folders = self._build_album_folder_hierarchy_4(parent_uuid, folders=folders)
        return folders

    def _process_database5(self):
        """ process the Photos database to extract info """
        """ works on Photos version >= 5.0 """

        if _debug():
            logging.debug(f"_process_database5")

        # Epoch is Jan 1, 2001
        td = (datetime(2001, 1, 1, 0, 0) - datetime(1970, 1, 1, 0, 0)).total_seconds()

        (conn, c) = _open_sql_file(self._tmp_db)

        # Look for all combinations of persons and pictures
        if _debug():
            logging.debug(f"Getting information about persons")

        c.execute(
            "SELECT ZPERSON.ZFULLNAME, ZGENERICASSET.ZUUID "
            "FROM ZPERSON, ZDETECTEDFACE, ZGENERICASSET "
            "WHERE ZDETECTEDFACE.ZPERSON = ZPERSON.Z_PK AND ZDETECTEDFACE.ZASSET = ZGENERICASSET.Z_PK "
            "AND ZGENERICASSET.ZTRASHEDSTATE = 0"
        )
        for person in c:
            if person[0] is None:
                continue
            person_name = person[0] if person[0] != "" else _UNKNOWN_PERSON
            if not person[1] in self._dbfaces_uuid:
                self._dbfaces_uuid[person[1]] = []
            if not person_name in self._dbfaces_person:
                self._dbfaces_person[person_name] = []
            self._dbfaces_uuid[person[1]].append(person_name)
            self._dbfaces_person[person_name].append(person[1])

        if _debug():
            logging.debug(f"Finished walking through persons")
            logging.debug(pformat(self._dbfaces_person))
            logging.debug(self._dbfaces_uuid)

        # get details about albums
        c.execute(
            "SELECT ZGENERICALBUM.ZUUID, ZGENERICASSET.ZUUID "
            "FROM ZGENERICASSET "
            "JOIN Z_26ASSETS ON Z_26ASSETS.Z_34ASSETS = ZGENERICASSET.Z_PK "
            "JOIN ZGENERICALBUM ON ZGENERICALBUM.Z_PK = Z_26ASSETS.Z_26ALBUMS "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 "
        )
        for album in c:
            # store by uuid in _dbalbums_uuid and by album in _dbalbums_album
            try:
                self._dbalbums_uuid[album[1]].append(album[0])
            except KeyError:
                self._dbalbums_uuid[album[1]] = [album[0]]

            try:
                self._dbalbums_album[album[0]].append(album[1])
            except KeyError:
                self._dbalbums_album[album[0]] = [album[1]]

        # now get additional details about albums
        c.execute(
            "SELECT "
            "ZUUID, "  # 0
            "ZTITLE, "  # 1
            "ZCLOUDLOCALSTATE, "  # 2
            "ZCLOUDOWNERFIRSTNAME, "  # 3
            "ZCLOUDOWNERLASTNAME, "  # 4
            "ZCLOUDOWNERHASHEDPERSONID, "  # 5
            "ZKIND, "  # 6
            "ZPARENTFOLDER, "  # 7
            "Z_PK, "  # 8
            "ZTRASHEDSTATE "  # 9
            "FROM ZGENERICALBUM "
        )
        for album in c:
            self._dbalbum_details[album[0]] = {
                "_uuid": album[0],
                "title": album[1],
                "cloudlocalstate": album[2],
                "cloudownerfirstname": album[3],
                "cloudownderlastname": album[4],
                "cloudownerhashedpersonid": album[5],
                "cloudlibrarystate": None,  # Photos 4
                "cloudidentifier": None,  # Photos 4
                "kind": album[6],
                "parentfolder": album[7],
                "pk": album[8],
                "intrash": False if album[9] == 0 else True,
            }

            # add cross-reference by pk to uuid
            # needed to extract folder hierarchy
            # in Photos >= 5, folders are special albums
            self._dbalbums_pk[album[8]] = album[0]

        # get pk of root folder
        root_uuid = [
            album
            for album, details in self._dbalbum_details.items()
            if details["kind"] == _PHOTOS_5_ROOT_FOLDER_KIND
        ]
        if len(root_uuid) != 1:
            raise ValueError(f"Error finding root folder: {root_uuid}")
        else:
            self._folder_root_pk = self._dbalbum_details[root_uuid[0]]["pk"]

        # build _dbalbum_folders which is in form uuid: [list of parent uuids]
        # TODO: look at this code...it works but I think I album can only be in a single folder
        # which means there's a code path that will never get executed
        for album, details in self._dbalbum_details.items():
            pk_parent = details["parentfolder"]
            if pk_parent is None:
                continue

            try:
                parent = self._dbalbums_pk[pk_parent]
            except KeyError:
                raise ValueError(f"Did not find uuid for album {album} pk {pk_parent}")

            try:
                self._dbalbum_parent_folders[album].append(parent)
            except KeyError:
                self._dbalbum_parent_folders[album] = [parent]

        for album, details in self._dbalbum_details.items():
            # if details["kind"] in [_PHOTOS_5_ALBUM_KIND, _PHOTOS_5_FOLDER_KIND]:
            if details["kind"] == _PHOTOS_5_ALBUM_KIND:
                folder_hierarchy = self._build_album_folder_hierarchy_5(album)
                self._dbalbum_folders[album] = folder_hierarchy
            elif details["kind"] == _PHOTOS_5_SHARED_ALBUM_KIND:
                # shared albums can't be in folders
                self._dbalbum_folders[album] = []

        if _debug():
            logging.debug(f"Finished walking through albums")
            logging.debug(pformat(self._dbalbums_album))
            logging.debug(pformat(self._dbalbums_uuid))
            logging.debug(pformat(self._dbalbum_details))
            logging.debug(pformat(self._dbalbum_folders))

        # get details on keywords
        c.execute(
            "SELECT ZKEYWORD.ZTITLE, ZGENERICASSET.ZUUID "
            "FROM ZGENERICASSET "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "JOIN Z_1KEYWORDS ON Z_1KEYWORDS.Z_1ASSETATTRIBUTES = ZADDITIONALASSETATTRIBUTES.Z_PK "
            "JOIN ZKEYWORD ON ZKEYWORD.Z_PK = Z_1KEYWORDS.Z_37KEYWORDS "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 "
        )
        for keyword in c:
            if not keyword[1] in self._dbkeywords_uuid:
                self._dbkeywords_uuid[keyword[1]] = []
            if not keyword[0] in self._dbkeywords_keyword:
                self._dbkeywords_keyword[keyword[0]] = []
            self._dbkeywords_uuid[keyword[1]].append(keyword[0])
            self._dbkeywords_keyword[keyword[0]].append(keyword[1])

        if _debug():
            logging.debug(f"Finished walking through keywords")
            logging.debug(pformat(self._dbkeywords_keyword))
            logging.debug(pformat(self._dbkeywords_uuid))

        # get details on disk volumes
        c.execute("SELECT ZUUID, ZNAME from ZFILESYSTEMVOLUME")
        for vol in c:
            self._dbvolumes[vol[0]] = vol[1]

        if _debug():
            logging.debug(f"Finished walking through volumes")
            logging.debug(self._dbvolumes)

        # get details about photos
        logging.debug(f"Getting information about photos")
        c.execute(
            """SELECT ZGENERICASSET.ZUUID, 
                ZADDITIONALASSETATTRIBUTES.ZMASTERFINGERPRINT, 
                ZADDITIONALASSETATTRIBUTES.ZTITLE, 
                ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME, 
                ZGENERICASSET.ZMODIFICATIONDATE, 
                ZGENERICASSET.ZDATECREATED, 
                ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET, 
                ZADDITIONALASSETATTRIBUTES.ZINFERREDTIMEZONEOFFSET, 
                ZADDITIONALASSETATTRIBUTES.ZTIMEZONENAME, 
                ZGENERICASSET.ZHIDDEN, 
                ZGENERICASSET.ZFAVORITE, 
                ZGENERICASSET.ZDIRECTORY, 
                ZGENERICASSET.ZFILENAME, 
                ZGENERICASSET.ZLATITUDE, 
                ZGENERICASSET.ZLONGITUDE, 
                ZGENERICASSET.ZHASADJUSTMENTS, 
                ZGENERICASSET.ZCLOUDBATCHPUBLISHDATE, 
                ZGENERICASSET.ZKIND, 
                ZGENERICASSET.ZUNIFORMTYPEIDENTIFIER,
				ZGENERICASSET.ZAVALANCHEUUID,
				ZGENERICASSET.ZAVALANCHEPICKTYPE,
                ZGENERICASSET.ZKINDSUBTYPE,
                ZGENERICASSET.ZCUSTOMRENDEREDVALUE,
                ZADDITIONALASSETATTRIBUTES.ZCAMERACAPTUREDEVICE,
                ZGENERICASSET.ZCLOUDASSETGUID,
                ZADDITIONALASSETATTRIBUTES.ZREVERSELOCATIONDATA,
                ZGENERICASSET.ZMOMENT,
	            ZADDITIONALASSETATTRIBUTES.ZORIGINALRESOURCECHOICE
                FROM ZGENERICASSET 
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK 
                WHERE ZGENERICASSET.ZTRASHEDSTATE = 0  
                ORDER BY ZGENERICASSET.ZUUID  """
        )
        # Order of results
        # 0    SELECT ZGENERICASSET.ZUUID,
        # 1    ZADDITIONALASSETATTRIBUTES.ZMASTERFINGERPRINT,
        # 2    ZADDITIONALASSETATTRIBUTES.ZTITLE,
        # 3    ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME,
        # 4    ZGENERICASSET.ZMODIFICATIONDATE,
        # 5    ZGENERICASSET.ZDATECREATED,
        # 6    ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET,
        # 7    ZADDITIONALASSETATTRIBUTES.ZINFERREDTIMEZONEOFFSET,
        # 8    ZADDITIONALASSETATTRIBUTES.ZTIMEZONENAME,
        # 9    ZGENERICASSET.ZHIDDEN,
        # 10   ZGENERICASSET.ZFAVORITE,
        # 11   ZGENERICASSET.ZDIRECTORY,
        # 12   ZGENERICASSET.ZFILENAME,
        # 13   ZGENERICASSET.ZLATITUDE,
        # 14   ZGENERICASSET.ZLONGITUDE,
        # 15   ZGENERICASSET.ZHASADJUSTMENTS
        # 16   ZCLOUDBATCHPUBLISHDATE   -- If not null, indicates a shared photo
        # 17   ZKIND, -- 0 = photo, 1 = movie
        # 18   ZUNIFORMTYPEIDENTIFIER  -- UTI
        # 19   ZGENERICASSET.ZAVALANCHEUUID, -- if not NULL, is burst photo
        # 20   ZGENERICASSET.ZAVALANCHEPICKTYPE -- if not 2, is a selected burst photo
        # 21   ZGENERICASSET.ZKINDSUBTYPE -- determine if live photos, etc
        # 22   ZGENERICASSET.ZCUSTOMRENDEREDVALUE -- determine if HDR photo
        # 23   ZADDITIONALASSETATTRIBUTES.ZCAMERACAPTUREDEVICE -- 1 if selfie (front facing camera)
        # 24   ZGENERICASSET.ZCLOUDASSETGUID  -- not null if asset is cloud asset
        #       (e.g. user has "iCloud Photos" checked in Photos preferences)
        # 25   ZADDITIONALASSETATTRIBUTES.ZREVERSELOCATIONDATA -- reverse geolocation data
        # 26   ZGENERICASSET.ZMOMENT -- FK for ZMOMENT.Z_PK
        # 27   ZADDITIONALASSETATTRIBUTES.ZORIGINALRESOURCECHOICE -- 1 if associated RAW image is original else 0

        for row in c:
            uuid = row[0]
            info = {}
            info["_uuid"] = uuid  # stored here for easier debugging
            info["modelID"] = None
            info["masterUuid"] = None
            info["masterFingerprint"] = row[1]
            info["name"] = row[2]

            # There are sometimes negative values for lastmodifieddate in the database
            # I don't know what these mean but they will raise exception in datetime if
            # not accounted for
            if row[4] is not None and row[4] >= 0:
                info["lastmodifieddate"] = datetime.fromtimestamp(row[4] + td)
            else:
                info["lastmodifieddate"] = None

            # Sometimes the year is waaay out of range (82665413681585!) so
            # like lastmodifieddate, skip setting this if it is out of whack
            #
            if row[5] is not None and row[5] <= 9999999999:
                info["imageDate"] = datetime.fromtimestamp(row[5] + td)
            else:
                info["imageDate"] = None
            info["imageTimeZoneOffsetSeconds"] = row[6]
            info["hidden"] = row[9]
            info["favorite"] = row[10]
            info["originalFilename"] = row[3]
            info["filename"] = row[12]
            info["directory"] = row[11]

            # set latitude and longitude
            # if both latitude and longitude = -180.0, then they are NULL
            if row[13] == -180.0 and row[14] == -180.0:
                info["latitude"] = None
                info["longitude"] = None
            else:
                info["latitude"] = row[13]
                info["longitude"] = row[14]

            info["hasAdjustments"] = row[15]

            info["cloudbatchpublishdate"] = row[16]
            info["shared"] = True if row[16] is not None else False

            # these will get filled in later
            # init to avoid key errors
            info["extendedDescription"] = None  # fill this in later
            info["localAvailability"] = None
            info["remoteAvailability"] = None
            info["isMissing"] = None
            info["adjustmentUuid"] = None
            info["adjustmentFormatID"] = None

            # find type
            if row[17] == 0:
                info["type"] = _PHOTO_TYPE
            elif row[17] == 1:
                info["type"] = _MOVIE_TYPE
            else:
                if _debug():
                    logging.debug(f"WARNING: {uuid} found unknown type {row[17]}")
                info["type"] = None

            info["UTI"] = row[18]

            # handle burst photos
            # if burst photo, determine whether or not it's a selected burst photo
            # in Photos 5, burstUUID is called avalancheUUID
            info["burstUUID"] = row[19]  # avalancheUUID
            info["burstPickType"] = row[20]  # avalanchePickType
            if row[19] is not None:
                # it's a burst photo
                info["burst"] = True
                burst_uuid = row[19]
                if burst_uuid not in self._dbphotos_burst:
                    self._dbphotos_burst[burst_uuid] = set()
                self._dbphotos_burst[burst_uuid].add(uuid)
                if row[20] != 2 and row[20] != 4:
                    info[
                        "burst_key"
                    ] = True  # it's a key photo (selected from the burst)
                else:
                    info[
                        "burst_key"
                    ] = False  # it's a burst photo but not one that's selected
            else:
                # not a burst photo
                info["burst"] = False
                info["burst_key"] = None

            # Info on sub-type (live photo, panorama, etc)
            # ZGENERICASSET.ZKINDSUBTYPE
            # 1 == panorama
            # 2 == live photo
            # 10 = screenshot
            # 100 = shared movie (MP4) ??
            # 101 = slow-motion video
            # 102 = Time lapse video
            info["subtype"] = row[21]
            info["live_photo"] = True if row[21] == 2 else False
            info["screenshot"] = True if row[21] == 10 else False
            info["slow_mo"] = True if row[21] == 101 else False
            info["time_lapse"] = True if row[21] == 102 else False

            # Handle HDR photos and portraits
            # ZGENERICASSET.ZCUSTOMRENDEREDVALUE
            # 3 = HDR photo
            # 4 = non-HDR version of the photo
            # 6 = panorama
            # 8 = portrait
            info["customRenderedValue"] = row[22]
            info["hdr"] = True if row[22] == 3 else False
            info["portrait"] = True if row[22] == 8 else False

            # Set panorama from either KindSubType or RenderedValue
            info["panorama"] = True if row[21] == 1 or row[22] == 6 else False

            # Handle selfies (front facing camera, ZCAMERACAPTUREDEVICE=1)
            info["selfie"] = True if row[23] == 1 else False

            # Determine if photo is part of cloud library (ZGENERICASSET.ZCLOUDASSETGUID not NULL)
            # Initialize cloud fields that will filled in later
            info["cloudAssetGUID"] = row[24]
            info["cloudLocalState"] = None
            info["incloud"] = None
            info["cloudLibraryState"] = None  # Photos 4
            info["cloudStatus"] = None  # Photos 4
            info["cloudAvailable"] = None  # Photos 4

            # reverse geolocation info
            info["reverse_geolocation"] = row[25]
            info["placeIDs"] = None  # Photos 4
            info["placeNames"] = None  # Photos 4
            info["countryCode"] = None  # Photos 4

            # moment info
            info["momentID"] = row[26]

            # original resource choice (e.g. RAW or jpeg)
            # for images part of a RAW/jpeg pair,
            # ZADDITIONALASSETATTRIBUTES.ZORIGINALRESOURCECHOICE
            # = 0 if jpeg is selected as "original" in Photos (the default)
            # = 1 if RAW is selected as "original" in Photos
            info["original_resource_choice"] = row[27]
            info["raw_is_original"] = True if row[27] == 1 else False

            # associated RAW image info
            # will be filled in later
            info["has_raw"] = False
            info["raw_data_length"] = None
            info["UTI_raw"] = None
            info["datastore_subtype"] = None
            info["resource_type"] = None
            info["raw_master_uuid"] = None  # Photos 4
            info["non_raw_master_uuid"] = None  # Photos 4
            info["alt_master_uuid"] = None  # Photos 4
            info["raw_info"] = None  # Photos 4

            self._dbphotos[uuid] = info

            # # if row[19] is not None and ((row[20] == 2) or (row[20] == 4)):
            # # burst photo
            # if row[19] is not None:
            #     # burst photo, add to _dbphotos_burst
            #     info["burst"] = True
            #     burst_uuid = row[19]
            #     if burst_uuid not in self._dbphotos_burst:
            #         self._dbphotos_burst[burst_uuid] = {}
            #     self._dbphotos_burst[burst_uuid][uuid] = info
            # else:
            #     info["burst"] = False

        # Get extended description
        c.execute(
            "SELECT ZGENERICASSET.ZUUID, "
            "ZASSETDESCRIPTION.ZLONGDESCRIPTION "
            "FROM ZGENERICASSET "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "JOIN ZASSETDESCRIPTION ON ZASSETDESCRIPTION.Z_PK = ZADDITIONALASSETATTRIBUTES.ZASSETDESCRIPTION "
            "ORDER BY ZGENERICASSET.ZUUID "
        )
        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["extendedDescription"] = row[1]
            else:
                if _debug():
                    logging.debug(
                        f"WARNING: found description {row[1]} but no photo for {uuid}"
                    )

        # get information about adjusted/edited photos
        c.execute(
            "SELECT ZGENERICASSET.ZUUID, "
            "ZGENERICASSET.ZHASADJUSTMENTS, "
            "ZUNMANAGEDADJUSTMENT.ZADJUSTMENTFORMATIDENTIFIER "
            "FROM ZGENERICASSET, ZUNMANAGEDADJUSTMENT "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "WHERE ZADDITIONALASSETATTRIBUTES.ZUNMANAGEDADJUSTMENT = ZUNMANAGEDADJUSTMENT.Z_PK "
            "AND ZGENERICASSET.ZTRASHEDSTATE = 0 "
        )
        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["adjustmentFormatID"] = row[2]
            else:
                if _debug():
                    logging.debug(
                        f"WARNING: found adjustmentformatidentifier {row[2]} but no photo for uuid {row[0]}"
                    )

        # Find missing photos
        # TODO: this code is very kludgy and I had to make lots of assumptions
        # it's probably wrong and needs to be re-worked once I figure out how to reliably
        # determine if a photo is missing in Photos 5

        # Get info on remote/local availability for photos in shared albums
        # Shared photos have a null fingerprint (and some other photos do too)
        # TODO: There may be a bug here, perhaps ZDATASTORESUBTYPE should be 1 --> it's the longest ZDATALENGTH (is this the original)
        c.execute(
            """ SELECT 
                ZGENERICASSET.ZUUID, 
                ZINTERNALRESOURCE.ZLOCALAVAILABILITY, 
                ZINTERNALRESOURCE.ZREMOTEAVAILABILITY
                FROM ZGENERICASSET
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK 
                JOIN ZINTERNALRESOURCE ON ZINTERNALRESOURCE.ZASSET = ZADDITIONALASSETATTRIBUTES.ZASSET 
                WHERE  ZDATASTORESUBTYPE = 0 OR ZDATASTORESUBTYPE = 3 """
            # WHERE  ZDATASTORESUBTYPE = 1 OR ZDATASTORESUBTYPE = 3 """
            # WHERE  ZDATASTORESUBTYPE = 0 OR ZDATASTORESUBTYPE = 3 """
            # WHERE ZINTERNALRESOURCE.ZFINGERPRINT IS NULL AND ZINTERNALRESOURCE.ZDATASTORESUBTYPE = 3 """
        )

        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                #  and self._dbphotos[uuid]["isMissing"] is None:
                self._dbphotos[uuid]["localAvailability"] = row[1]
                self._dbphotos[uuid]["remoteAvailability"] = row[2]

                # old = self._dbphotos[uuid]["isMissing"]

                if row[1] != 1:
                    self._dbphotos[uuid]["isMissing"] = 1
                else:
                    self._dbphotos[uuid]["isMissing"] = 0

                # if old is not None and old != self._dbphotos[uuid]["isMissing"]:
                #     logging.warning(
                #         f"{uuid} isMissing changed: {old} {self._dbphotos[uuid]['isMissing']}"
                #     )

        # get information on local/remote availability
        c.execute(
            """ SELECT ZGENERICASSET.ZUUID,
                ZINTERNALRESOURCE.ZLOCALAVAILABILITY,
                ZINTERNALRESOURCE.ZREMOTEAVAILABILITY
                FROM ZGENERICASSET
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK
                JOIN ZINTERNALRESOURCE ON ZINTERNALRESOURCE.ZFINGERPRINT = ZADDITIONALASSETATTRIBUTES.ZMASTERFINGERPRINT """
        )

        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["localAvailability"] = row[1]
                self._dbphotos[uuid]["remoteAvailability"] = row[2]

                # old = self._dbphotos[uuid]["isMissing"]

                if row[1] != 1:
                    self._dbphotos[uuid]["isMissing"] = 1
                else:
                    self._dbphotos[uuid]["isMissing"] = 0

                # if old is not None and old != self._dbphotos[uuid]["isMissing"]:
                #     logging.warning(
                #         f"{uuid} isMissing changed: {old} {self._dbphotos[uuid]['isMissing']}"
                #     )

        # get information about cloud sync state
        c.execute(
            """ SELECT
                ZGENERICASSET.ZUUID,
                ZCLOUDMASTER.ZCLOUDLOCALSTATE
                FROM ZCLOUDMASTER, ZGENERICASSET
                WHERE ZGENERICASSET.ZMASTER = ZCLOUDMASTER.Z_PK """
        )
        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["cloudLocalState"] = row[1]
                self._dbphotos[uuid]["incloud"] = True if row[1] == 3 else False

        # get information about associted RAW images
        # RAW images have ZDATASTORESUBTYPE = 17
        c.execute(
            """ SELECT
                ZGENERICASSET.ZUUID,
                ZINTERNALRESOURCE.ZDATALENGTH, 
                ZUNIFORMTYPEIDENTIFIER.ZIDENTIFIER,
                ZINTERNALRESOURCE.ZDATASTORESUBTYPE,
                ZINTERNALRESOURCE.ZRESOURCETYPE
                FROM ZGENERICASSET
                JOIN ZINTERNALRESOURCE ON ZINTERNALRESOURCE.ZASSET = ZADDITIONALASSETATTRIBUTES.ZASSET
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK 
                JOIN ZUNIFORMTYPEIDENTIFIER ON ZUNIFORMTYPEIDENTIFIER.Z_PK =  ZINTERNALRESOURCE.ZUNIFORMTYPEIDENTIFIER
                WHERE ZINTERNALRESOURCE.ZDATASTORESUBTYPE = 17
        """
        )
        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["has_raw"] = True
                self._dbphotos[uuid]["raw_data_length"] = row[1]
                self._dbphotos[uuid]["UTI_raw"] = row[2]
                self._dbphotos[uuid]["datastore_subtype"] = row[3]
                self._dbphotos[uuid]["resource_type"] = row[4]

        # add faces and keywords to photo data
        for uuid in self._dbphotos:
            # keywords
            if uuid in self._dbkeywords_uuid:
                self._dbphotos[uuid]["hasKeywords"] = 1
                self._dbphotos[uuid]["keywords"] = self._dbkeywords_uuid[uuid]
            else:
                self._dbphotos[uuid]["hasKeywords"] = 0
                self._dbphotos[uuid]["keywords"] = []

            if uuid in self._dbfaces_uuid:
                self._dbphotos[uuid]["hasPersons"] = 1
                self._dbphotos[uuid]["persons"] = self._dbfaces_uuid[uuid]
            else:
                self._dbphotos[uuid]["hasPersons"] = 0
                self._dbphotos[uuid]["persons"] = []

            if uuid in self._dbalbums_uuid:
                self._dbphotos[uuid]["albums"] = self._dbalbums_uuid[uuid]
                self._dbphotos[uuid]["hasAlbums"] = 1
            else:
                self._dbphotos[uuid]["albums"] = []
                self._dbphotos[uuid]["hasAlbums"] = 0

        # build album_titles dictionary
        for album_id in self._dbalbum_details:
            title = self._dbalbum_details[album_id]["title"]
            if title in self._dbalbum_titles:
                self._dbalbum_titles[title].append(album_id)
            else:
                self._dbalbum_titles[title] = [album_id]

        # country codes (only used in Photos <=4)
        self._db_countries = None

        # close connection and remove temporary files
        conn.close()

        # process search info
        self._process_searchinfo()

        # process exif info
        self._process_exifinfo()

        # done processing, dump debug data if requested
        if _debug():
            logging.debug("Faces (_dbfaces_uuid):")
            logging.debug(pformat(self._dbfaces_uuid))

            logging.debug("Faces by person (_dbfaces_person):")
            logging.debug(pformat(self._dbfaces_person))

            logging.debug("Keywords by uuid (_dbkeywords_uuid):")
            logging.debug(pformat(self._dbkeywords_uuid))

            logging.debug("Keywords by keyword (_dbkeywords_keywords):")
            logging.debug(pformat(self._dbkeywords_keyword))

            logging.debug("Albums by uuid (_dbalbums_uuid):")
            logging.debug(pformat(self._dbalbums_uuid))

            logging.debug("Albums by album (_dbalbums_albums):")
            logging.debug(pformat(self._dbalbums_album))

            logging.debug("Album details (_dbalbum_details):")
            logging.debug(pformat(self._dbalbum_details))

            logging.debug("Album titles (_dbalbum_titles):")
            logging.debug(pformat(self._dbalbum_titles))

            logging.debug("Album folders (_dbalbum_folders):")
            logging.debug(pformat(self._dbalbum_folders))

            logging.debug("Album parent folders (_dbalbum_parent_folders):")
            logging.debug(pformat(self._dbalbum_parent_folders))

            logging.debug("Albums pk (_dbalbums_pk):")
            logging.debug(pformat(self._dbalbums_pk))

            logging.debug("Volumes (_dbvolumes):")
            logging.debug(pformat(self._dbvolumes))

            logging.debug("Photos (_dbphotos):")
            logging.debug(pformat(self._dbphotos))

            logging.debug("Burst Photos (dbphotos_burst:")
            logging.debug(pformat(self._dbphotos_burst))

    def _build_album_folder_hierarchy_5(self, uuid, folders=None):
        """ recursively build folder/album hierarchy
            uuid: uuid of the album/folder being processed
            folders: dict holding the folder hierarchy """

        # get parent uuid
        parent = self._dbalbum_details[uuid]["parentfolder"]

        if parent is not None:
            parent_uuid = self._dbalbums_pk[parent]
        else:
            # folder with no parent (e.g. shared iCloud folders)
            return folders

        if self._db_version > _PHOTOS_4_VERSION and parent == self._folder_root_pk:
            # at the top of the folder hierarchy, we're done
            return folders

        # recurse to keep building
        folders = {parent_uuid: folders}
        folders = self._build_album_folder_hierarchy_5(parent_uuid, folders=folders)
        return folders

    def _album_folder_hierarchy_list(self, album_uuid):
        if self._db_version <= _PHOTOS_4_VERSION:
            return self._album_folder_hierarchy_list_4(album_uuid)
        else:
            return self._album_folder_hierarchy_list_5(album_uuid)

    def _album_folder_hierarchy_list_4(self, album_uuid):
        """ return hierarchical list of folder names album_uuid is contained in
            the folder list is in form:
            ["Top level folder", "sub folder 1", "sub folder 2"]
            returns empty list of album is not in any folders """
        # title = photosdb._dbalbum_details[album_uuid]["title"]
        folders = self._dbalbum_folders[album_uuid]

        def _recurse_folder_hierarchy(folders, hierarchy=[]):
            """ recursively walk the folders dict to build list of folder hierarchy """
            if not folders:
                # empty folder dict (album has no folder hierarchy)
                return []

            if len(folders) != 1:
                raise ValueError("Expected only a single key in folders dict")

            folder_uuid = list(folders)[0]  # first and only key of dict

            parent_title = self._dbfolder_details[folder_uuid]["name"]
            hierarchy.append(parent_title)

            folders = folders[folder_uuid]
            if folders:
                # still have elements left to recurse
                hierarchy = _recurse_folder_hierarchy(folders, hierarchy=hierarchy)
                return hierarchy

            # no elements left to recurse
            return hierarchy

        hierarchy = _recurse_folder_hierarchy(folders)
        return hierarchy

    def _album_folder_hierarchy_list_5(self, album_uuid):
        """ return hierarchical list of folder names album_uuid is contained in
            the folder list is in form:
            ["Top level folder", "sub folder 1", "sub folder 2"]
            returns empty list of album is not in any folders """
        # title = photosdb._dbalbum_details[album_uuid]["title"]
        folders = self._dbalbum_folders[album_uuid]

        def _recurse_folder_hierarchy(folders, hierarchy=[]):
            """ recursively walk the folders dict to build list of folder hierarchy """

            if not folders:
                # empty folder dict (album has no folder hierarchy)
                return []

            if len(folders) != 1:
                raise ValueError("Expected only a single key in folders dict")

            folder_uuid = list(folders)[0]  # first and only key of dict
            parent_title = self._dbalbum_details[folder_uuid]["title"]
            hierarchy.append(parent_title)

            folders = folders[folder_uuid]
            if folders:
                # still have elements left to recurse
                hierarchy = _recurse_folder_hierarchy(folders, hierarchy=hierarchy)
                return hierarchy

            # no elements left to recurse
            return hierarchy

        hierarchy = _recurse_folder_hierarchy(folders)
        return hierarchy

    def _album_folder_hierarchy_folderinfo(self, album_uuid):
        if self._db_version <= _PHOTOS_4_VERSION:
            return self._album_folder_hierarchy_folderinfo_4(album_uuid)
        else:
            return self._album_folder_hierarchy_folderinfo_5(album_uuid)

    def _album_folder_hierarchy_folderinfo_4(self, album_uuid):
        """ return hierarchical list of FolderInfo objects album_uuid is contained in
            ["Top level folder", "sub folder 1", "sub folder 2"]
            returns empty list of album is not in any folders """
        # title = photosdb._dbalbum_details[album_uuid]["title"]
        folders = self._dbalbum_folders[album_uuid]
        # logging.warning(f"uuid = {album_uuid}, folder = {folders}")

        def _recurse_folder_hierarchy(folders, hierarchy=[]):
            """ recursively walk the folders dict to build list of folder hierarchy """
            # logging.warning(f"folders={folders},hierarchy = {hierarchy}")
            if not folders:
                # empty folder dict (album has no folder hierarchy)
                return []

            if len(folders) != 1:
                raise ValueError("Expected only a single key in folders dict")

            folder_uuid = list(folders)[0]  # first and only key of dict
            hierarchy.append(FolderInfo(db=self, uuid=folder_uuid))

            folders = folders[folder_uuid]
            if folders:
                # still have elements left to recurse
                hierarchy = _recurse_folder_hierarchy(folders, hierarchy=hierarchy)
                return hierarchy

            # no elements left to recurse
            return hierarchy

        hierarchy = _recurse_folder_hierarchy(folders)
        # logging.warning(f"hierarchy = {hierarchy}")
        return hierarchy

    def _album_folder_hierarchy_folderinfo_5(self, album_uuid):
        """ return hierarchical list of FolderInfo objects album_uuid is contained in
            ["Top level folder", "sub folder 1", "sub folder 2"]
            returns empty list of album is not in any folders """
        # title = photosdb._dbalbum_details[album_uuid]["title"]
        folders = self._dbalbum_folders[album_uuid]

        def _recurse_folder_hierarchy(folders, hierarchy=[]):
            """ recursively walk the folders dict to build list of folder hierarchy """

            if not folders:
                # empty folder dict (album has no folder hierarchy)
                return []

            if len(folders) != 1:
                raise ValueError("Expected only a single key in folders dict")

            folder_uuid = list(folders)[0]  # first and only key of dict
            hierarchy.append(FolderInfo(db=self, uuid=folder_uuid))

            folders = folders[folder_uuid]
            if folders:
                # still have elements left to recurse
                hierarchy = _recurse_folder_hierarchy(folders, hierarchy=hierarchy)
                return hierarchy

            # no elements left to recurse
            return hierarchy

        hierarchy = _recurse_folder_hierarchy(folders)
        return hierarchy

    def photos(
        self,
        keywords=None,
        uuid=None,
        persons=None,
        albums=None,
        images=True,
        movies=False,
        from_date=None,
        to_date=None,
    ):
        """ 
        Return a list of PhotoInfo objects
        If called with no args, returns the entire database of photos
        If called with args, returns photos matching the args (e.g. keywords, persons, etc.)
        If more than one arg, returns photos matching all the criteria (e.g. keywords AND persons)
        If more than one keyword, uuid, persons, albums is passed, they are treated as "OR" criteria
        e.g. keywords=["wedding","vacation"] returns photos matching either keyword
        keywords: list of keywords to search for
        uuid: list of UUIDs to search for
        persons: list of persons to search for
        albums: list of album names to search for
        images: if True, returns image files, if False, does not return images; default is True
        movies: if True, returns movie files, if False, does not return movies; default is False
        from_date: return photos with creation date >= from_date (datetime.datetime object, default None)
        to_date: return photos with creation date <= to_date (datetime.datetime object, default None)
        """

        # implementation is a bit kludgy but it works
        # build a set of each search argument then compute the intersection of the sets
        # use results to build a list of PhotoInfo objects

        photos_sets = []  # list of photo sets to perform intersection of
        if not any([keywords, uuid, persons, albums, from_date, to_date]):
            # return all the photos, filtering for images and movies
            # append keys of all photos as a single set to photos_sets
            photos_sets.append(set(self._dbphotos.keys()))
        else:
            if albums:
                album_set = set()
                for album in albums:
                    # TODO: can have >1 album with same name. This globs them together.
                    # Need a way to select which album?
                    if album in self._dbalbum_titles:
                        title_set = set()
                        for album_id in self._dbalbum_titles[album]:
                            title_set.update(self._dbalbums_album[album_id])
                        album_set.update(title_set)
                    else:
                        logging.debug(f"Could not find album '{album}' in database")
                photos_sets.append(album_set)

            if uuid:
                uuid_set = set()
                for u in uuid:
                    if u in self._dbphotos:
                        uuid_set.update([u])
                    else:
                        logging.debug(f"Could not find uuid '{u}' in database")
                photos_sets.append(uuid_set)

            if keywords:
                keyword_set = set()
                for keyword in keywords:
                    if keyword in self._dbkeywords_keyword:
                        keyword_set.update(self._dbkeywords_keyword[keyword])
                    else:
                        logging.debug(f"Could not find keyword '{keyword}' in database")
                photos_sets.append(keyword_set)

            if persons:
                person_set = set()
                for person in persons:
                    if person in self._dbfaces_person:
                        person_set.update(self._dbfaces_person[person])
                    else:
                        logging.debug(f"Could not find person '{person}' in database")
                photos_sets.append(person_set)

            if from_date or to_date:
                dsel = self._dbphotos
                if from_date:
                    dsel = {
                        k: v for k, v in dsel.items() if v["imageDate"] >= from_date
                    }
                    logging.debug(
                        f"Found %i items with from_date {from_date}" % len(dsel)
                    )
                if to_date:
                    dsel = {k: v for k, v in dsel.items() if v["imageDate"] <= to_date}
                    logging.debug(f"Found %i items with to_date {to_date}" % len(dsel))
                photos_sets.append(set(dsel.keys()))

        photoinfo = []
        if photos_sets:  # found some photos
            # get the intersection of each argument/search criteria
            logging.debug(f"Got photo_sets: {photos_sets}")
            for p in set.intersection(*photos_sets):
                # filter for non-selected burst photos
                if self._dbphotos[p]["burst"] and not self._dbphotos[p]["burst_key"]:
                    # not a key/selected burst photo, don't include in returned results
                    continue

                # filter for images and/or movies
                if (images and self._dbphotos[p]["type"] == _PHOTO_TYPE) or (
                    movies and self._dbphotos[p]["type"] == _MOVIE_TYPE
                ):
                    info = PhotoInfo(db=self, uuid=p, info=self._dbphotos[p])
                    photoinfo.append(info)
        if _debug:
            logging.debug(f"photoinfo: {pformat(photoinfo)}")

        return photoinfo

    def __repr__(self):
        return f"osxphotos.{self.__class__.__name__}(dbfile='{self.db_path}')"

    # compare two PhotosDB objects for equality
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__

        return False

    def __len__(self):
        """ returns number of photos in the database """
        return len(self._dbphotos)
