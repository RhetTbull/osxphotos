"""
PhotosDB class
Processes a Photos.app library database to extract information about photos
"""

from __future__ import annotations

import logging
import os
import os.path
import pathlib
import platform
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from unicodedata import normalize

from rich import print

from .._constants import (
    _DB_TABLE_NAMES,
    _MOVIE_TYPE,
    _PHOTO_TYPE,
    _PHOTOS_3_VERSION,
    _PHOTOS_4_ALBUM_KIND,
    _PHOTOS_4_ALBUM_TYPE_ALBUM,
    _PHOTOS_4_ALBUM_TYPE_PROJECT,
    _PHOTOS_4_ALBUM_TYPE_SLIDESHOW,
    _PHOTOS_4_ROOT_FOLDER,
    _PHOTOS_4_TOP_LEVEL_ALBUMS,
    _PHOTOS_4_VERSION,
    _PHOTOS_5_ALBUM_KIND,
    _PHOTOS_5_FOLDER_KIND,
    _PHOTOS_5_IMPORT_SESSION_ALBUM_KIND,
    _PHOTOS_5_PROJECT_ALBUM_KIND,
    _PHOTOS_5_ROOT_FOLDER_KIND,
    _PHOTOS_5_SHARED_ALBUM_KIND,
    _TESTED_OS_VERSIONS,
    _UNKNOWN_PERSON,
    BURST_KEY,
    BURST_PICK_TYPE_NONE,
    BURST_SELECTED,
    TIME_DELTA,
)
from .._version import __version__
from ..albuminfo import AlbumInfo, FolderInfo, ImportInfo, ProjectInfo
from ..datetime_utils import datetime_has_tz, datetime_naive_to_local
from ..fileutil import FileUtil
from ..iphoto import is_iphoto_library
from ..personinfo import PersonInfo
from ..photoinfo import PhotoInfo
from ..photoquery import QueryOptions, photo_query
from ..platform import get_macos_version, is_macos
from ..rich_utils import add_rich_markup_tag
from ..sqlite_utils import sqlite_db_is_locked, sqlite_open_ro
from ..unicode import normalize_unicode
from ..utils import _check_file_exists, get_last_library_path, noop
from .photosdb_utils import (
    get_db_version,
    get_model_version,
    get_photos_version_from_model,
)

if is_macos:
    import photoscript

logger = logging.getLogger("osxphotos")

__all__ = ["PhotosDB", "PhotosDBReadError"]

# TODO: Add test for imageTimeZoneOffsetSeconds = None
# TODO: Add test for __str__
# TODO: Add special albums and magic albums


class PhotosDBReadError(Exception):
    """Generic error when reading the Photos database"""

    pass


class PhotosDB:
    """Processes a Photos.app library database to extract information about photos"""

    # import additional methods
    from ._photosdb_process_comments import _process_comments
    from ._photosdb_process_exif import _process_exifinfo
    from ._photosdb_process_faceinfo import _process_faceinfo
    from ._photosdb_process_scoreinfo import _process_scoreinfo
    from ._photosdb_process_searchinfo import (
        _process_searchinfo,
        labels,
        labels_as_dict,
        labels_normalized,
        labels_normalized_as_dict,
    )
    from ._photosdb_process_shared_library import _process_shared_library_info
    from ._photosdb_process_syndicationinfo import _process_syndicationinfo

    def __init__(
        self,
        dbfile=None,
        verbose=None,
        exiftool=None,
        rich=None,
        _skip_searchinfo=False,
    ):
        """Create a new PhotosDB object.

        Args:
            dbfile: specify full path to photos library or photos.db; if None, will attempt to locate last library opened by Photos.
            verbose: optional callable function to use for printing verbose text during processing; if None (default), does not print output.
            exiftool: optional path to exiftool for methods that require this (e.g. PhotoInfo.exiftool); if not provided, will search PATH
            rich: use rich with verbose output
            _skip_searchinfo: if True, will not process search data from psi.sqlite; useful for processing standalone Photos.sqlite file

        Raises:
            PhotosDBReadError if dbfile is not a valid Photos library.
            TypeError if verbose is not None and not callable.
        """

        # Check that we're not trying to open an iPhoto library
        if dbfile and is_iphoto_library(dbfile):
            raise PhotosDBReadError(f"{dbfile} is an iPhoto library, not Photos")

        # Check OS version
        system = platform.system()
        (ver, major, _) = get_macos_version() if is_macos else (None, None, None)
        if system == "Darwin" and ((ver, major) not in _TESTED_OS_VERSIONS):
            logging.warning(
                f"WARNING: This module has only been tested with macOS versions "
                f"[{', '.join(f'{v}.{m}' for (v, m) in _TESTED_OS_VERSIONS)}]: "
                f"you have {system}, OS version: {ver}.{major}"
            )

        if verbose is None:
            verbose = noop
        elif not callable(verbose):
            raise TypeError("verbose must be callable")
        self._verbose = verbose
        self._skip_searchinfo = _skip_searchinfo

        # define functions for adding markup
        self._filepath = add_rich_markup_tag("filepath", rich=rich)
        self._filename = add_rich_markup_tag("filename", rich=rich)
        self._uuid = add_rich_markup_tag("uuid", rich=rich)
        self._num = add_rich_markup_tag("num", rich=rich)

        # enable beta features
        self._beta = False

        self._exiftool_path = exiftool

        # create a temporary directory
        # tempfile.TemporaryDirectory gets cleaned up when the object does
        self._tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
        self._tempdir_name = self._tempdir.name

        # set up the data structures used to store all the Photo database info

        # TODO: I don't think these keywords flags are actually used
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

        # Dict with information about all persons by person PK
        # key is person PK, value is dict with info about each person
        # e.g. {3: {"pk": 3, "fullname": "Maria Smith"...}}
        self._dbpersons_pk = {}

        # Dict with information about all persons by person fullname
        # key is person PK, value is list of person PKs with fullname
        # there may be more than one person PK with the same fullname
        # e.g. {"Maria Smith": [1, 2]}
        self._dbpersons_fullname = {}

        # Dict with information about all persons/photos by uuid
        # key is photo UUID, value is list of person primary keys of persons in the photo
        # Note: Photos 5 identifies faces even if not given a name
        # and those are labeled by process_database as _UNKNOWN_
        # e.g. {'1EB2B765-0765-43BA-A90C-0D0580E6172C': [1, 3, 5]}
        self._dbfaces_uuid = {}

        # Dict with information about detected faces by person primary key
        # key is person pk, value is list of photo UUIDs
        # e.g. {3: ['E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51']}
        self._dbfaces_pk = {}

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
        # key is album UUID, value is list of tuples of (photo UUID, sort order) contained in that album
        # e.g. {'0C514A98-7B77-4E4F-801B-364B7B65EAFA': [('1EB2B765-0765-43BA-A90C-0D0580E6172C', 1024)]}
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

        # Dict to hold signatures for finding possible duplicates
        # key is tuple of (original_filesize, date) and value is list of uuids that match that signature
        self._db_signatures = {}

        # Dict to hold information on volume names (Photos 5+)
        self._db_filesystem_volumes = {}

        # Dict to hold information on moments (Photos 5+)
        # key is Z_PK of ZMOMENT table and values are the moment info
        self._db_moment_pk = {}

        # Dict to hold data on imports for Photos <= 4
        self._db_import_group = {}

        # Dict to hold syndication info for Photos >= 7
        # key is UUID and value is dict of syndication info
        self._db_syndication_uuid = {}

        logger.debug(f"dbfile = {dbfile}")

        if dbfile is None:
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

        logger.debug(f"dbfile = {dbfile}")

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

        verbose(f"Processing database {self._filepath(self._dbfile)}")

        # if database is exclusively locked, make a copy of it and use the copy
        # Photos maintains an exclusive lock on the database file while Photos is open
        # photoanalysisd sometimes maintains this lock even after Photos is closed
        # In those cases, make a temp copy of the file for sqlite3 to read
        if sqlite_db_is_locked(self._dbfile):
            verbose("Database locked, creating temporary copy.")
            self._tmp_db = self._copy_db_file(self._dbfile)

        # _db_version is set from photos.db
        self._db_version = get_db_version(self._tmp_db)
        # _photos_version is set from Photos.sqlite which only exists for Photos 5+
        db_ver_int = int(self._db_version)
        if db_ver_int < 3000:
            self._photos_ver = 2
        elif db_ver_int < 4000:
            self._photos_ver = 3
        elif db_ver_int < 5000:
            self._photos_ver = 4
        else:
            self._photos_ver = 5
        self._model_ver = 0  # only set for Photos 5+

        # If Photos >= 5, actual data isn't in photos.db but in Photos.sqlite
        if int(self._db_version) > int(_PHOTOS_4_VERSION):
            dbpath = pathlib.Path(self._dbfile).parent
            dbfile = dbpath / "Photos.sqlite"
            if not _check_file_exists(dbfile):
                raise FileNotFoundError(f"dbfile {dbfile} does not exist", dbfile)
            self._dbfile_actual = self._tmp_db = dbfile
            verbose(f"Processing database {self._filepath(self._dbfile_actual)}")
            # if database is exclusively locked, make a copy of it and use the copy
            if sqlite_db_is_locked(self._dbfile_actual):
                verbose("Database locked, creating temporary copy.")
                self._tmp_db = self._copy_db_file(self._dbfile_actual)
            # set the photos version to actual value based on Photos.sqlite
            self._photos_ver = get_photos_version_from_model(self._tmp_db)
            self._model_ver = get_model_version(self._tmp_db)

            logger.debug(
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

        logger.debug(f"library = {library_path}, masters = {masters_path}")

        if int(self._db_version) <= int(_PHOTOS_4_VERSION):
            self._process_database4()
        else:
            self._process_database5()

        self._db_connection, _ = self.get_db_connection()

        self._source = "Photos"

    @property
    def keywords_as_dict(self):
        """Teturn keywords as dict of keyword: count in reverse sorted order (descending)"""
        keywords = {
            k: len(self._dbkeywords_keyword[k]) for k in self._dbkeywords_keyword.keys()
        }
        keywords |= {k: 0 for k in self.keywords_without_photo}
        keywords = dict(sorted(keywords.items(), key=lambda kv: kv[1], reverse=True))
        return keywords

    @property
    def keywords_without_photo(self):
        """Return keywords that exist in the database but are not assined to any photo (Photos 5+ only)"""
        if self._db_version <= _PHOTOS_4_VERSION:
            # not implemented for Photos <= 4
            return {}

        results = self.execute("SELECT ZTITLE FROM ZKEYWORD").fetchall()
        keywords = [normalize_unicode(r[0]) for r in results]
        no_photo_keywords = []
        for kw in keywords:
            if kw not in self._dbkeywords_keyword:
                no_photo_keywords.append(kw)
        return no_photo_keywords

    @property
    def persons_as_dict(self):
        """Return persons as dict of person, count in reverse sorted order (descending)"""
        persons = {}
        for pk in self._dbfaces_pk:
            fullname = self._dbpersons_pk[pk]["fullname"]
            try:
                persons[fullname] += len(self._dbfaces_pk[pk])
            except KeyError:
                persons[fullname] = len(self._dbfaces_pk[pk])
        persons = dict(sorted(persons.items(), key=lambda kv: kv[1], reverse=True))
        return persons

    @property
    def albums_as_dict(self):
        """Return albums as dict of albums, count in reverse sorted order (descending)"""
        albums = {}
        album_keys = self._get_album_uuids(shared=False)
        for album in album_keys:
            title = self._dbalbum_details[album]["title"]
            if album in self._dbalbums_album:
                try:
                    albums[title] += len(self._dbalbums_album[album])
                except KeyError:
                    albums[title] = len(self._dbalbums_album[album])
            else:
                albums[title] = 0  # empty album
        albums = dict(sorted(albums.items(), key=lambda kv: kv[1], reverse=True))
        return albums

    @property
    def albums_shared_as_dict(self):
        """Returns shared albums as dict of albums, count in reverse sorted order (descending)
        valid only on Photos 5; on Photos <= 4, prints warning and returns empty dict"""

        albums = {}
        album_keys = self._get_album_uuids(shared=True)
        for album in album_keys:
            title = self._dbalbum_details[album]["title"]
            if album in self._dbalbums_album:
                try:
                    albums[title] += len(self._dbalbums_album[album])
                except KeyError:
                    albums[title] = len(self._dbalbums_album[album])
            else:
                albums[title] = 0  # empty album
        albums = dict(sorted(albums.items(), key=lambda kv: kv[1], reverse=True))
        return albums

    @property
    def keywords(self):
        """Return list of keywords found in photos database and associated with at least one photo"""
        keywords = self._dbkeywords_keyword.keys()
        return list(keywords)

    @property
    def persons(self):
        """Return list of persons found in photos database and associated with at least one photo"""
        persons = {self._dbpersons_pk[k]["fullname"] for k in self._dbfaces_pk}
        return list(persons)

    @property
    def person_info(self):
        """Return list of PersonInfo objects for each person in the photos database"""
        try:
            return self._person_info
        except AttributeError:
            self._person_info = [
                PersonInfo(db=self, pk=pk) for pk in self._dbpersons_pk
            ]
            return self._person_info

    @property
    def folder_info(self):
        """Return list FolderInfo objects representing top-level folders in the photos database"""
        if self._db_version <= _PHOTOS_4_VERSION:
            folders = [
                FolderInfo(db=self, uuid=folder)
                for folder, detail in self._dbfolder_details.items()
                if not detail["intrash"]
                and not detail["isMagic"]
                and detail["parentFolderUuid"] in _PHOTOS_4_TOP_LEVEL_ALBUMS
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
        """Return list of top-level folder names in the photos database"""
        if self._db_version <= _PHOTOS_4_VERSION:
            folder_names = [
                folder["name"]
                for folder in self._dbfolder_details.values()
                if not folder["intrash"]
                and not folder["isMagic"]
                and folder["parentFolderUuid"] in _PHOTOS_4_TOP_LEVEL_ALBUMS
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
        """Return list of AlbumInfo objects for each album in the photos database"""
        try:
            return self._album_info
        except AttributeError:
            self._album_info = [
                AlbumInfo(db=self, uuid=album)
                for album in self._get_album_uuids(shared=False)
            ]
            return self._album_info

    @property
    def album_info_shared(self):
        """Return list of AlbumInfo objects for each shared album in the photos database
        only valid for Photos 5; on Photos <= 4, prints warning and returns empty list
        """
        # if _dbalbum_details[key]["cloudownerhashedpersonid"] is not None, then it's a shared album
        try:
            return self._album_info_shared
        except AttributeError:
            self._album_info_shared = [
                AlbumInfo(db=self, uuid=album)
                for album in self._get_album_uuids(shared=True)
            ]
            return self._album_info_shared

    @property
    def albums(self):
        """Return list of albums found in photos database"""

        # Could be more than one album with same name
        # Right now, they are treated as same album and photos are combined from albums with same name

        try:
            return self._albums
        except AttributeError:
            self._albums = self._get_albums(shared=False)
            return self._albums

    @property
    def albums_shared(self):
        """Return list of shared albums found in photos database
        only valid for Photos 5; on Photos <= 4, prints warning and returns empty list
        """

        # Could be more than one album with same name
        # Right now, they are treated as same album and photos are combined from albums with same name

        # if _dbalbum_details[key]["cloudownerhashedpersonid"] is not None, then it's a shared album

        try:
            return self._albums_shared
        except AttributeError:
            self._albums_shared = self._get_albums(shared=True)
            return self._albums_shared

    @property
    def import_info(self):
        """Return list of ImportInfo objects for each import session in the database"""
        try:
            return self._import_info
        except AttributeError:
            self._import_info = [
                ImportInfo(db=self, uuid=album)
                for album in self._get_album_uuids(import_session=True)
            ]
            return self._import_info

    @property
    def project_info(self):
        """Return list of AlbumInfo projects for each project in the database"""
        try:
            return self._project_info
        except AttributeError:
            self._project_info = [
                ProjectInfo(db=self, uuid=album)
                for album in self._get_album_uuids(project=True)
            ]
            return self._project_info

    @property
    def db_version(self):
        """Return the database version as stored in LiGlobals table"""
        return self._db_version

    @property
    def db_path(self):
        """Returns path to the Photos library database PhotosDB was initialized with"""
        return os.path.abspath(self._dbfile)

    @property
    def library_path(self):
        """Returns path to the Photos library PhotosDB was initialized with"""
        return self._library_path

    @property
    def photos_version(self):
        """Returns version of Photos app that created the library"""
        return self._photos_ver

    def get_db_connection(self):
        """Get connection to the working copy of the Photos database

        Returns:
            tuple of (connection, cursor) to sqlite3 database
        """
        return sqlite_open_ro(self._tmp_db)

    def _copy_db_file(self, fname: str) -> str:
        """copies the sqlite database file to a temp file"""
        """ returns the name of the temp file """
        """ If sqlite shared memory and write-ahead log files exist, those are copied too """
        # required because python's sqlite3 implementation can't read a locked file
        # _, suffix = os.path.splitext(fname)
        dest_name = dest_path = ""
        try:
            dest_name = pathlib.Path(fname).name
            dest_path = os.path.join(self._tempdir_name, dest_name)
            FileUtil.copy(fname, dest_path)
            # copy write-ahead log and shared memory files (-wal and -shm) files if they exist
            if os.path.exists(f"{fname}-wal"):
                FileUtil.copy(f"{fname}-wal", f"{dest_path}-wal")
            if os.path.exists(f"{fname}-shm"):
                FileUtil.copy(f"{fname}-shm", f"{dest_path}-shm")
        except:
            print(f"Error copying{fname} to {dest_path}", file=sys.stderr)
            raise Exception

        logger.debug(dest_path)

        return dest_path

    def _process_database4(self):
        """process the Photos database to extract info
        works on Photos version <= 4.0"""

        verbose = self._verbose
        verbose("Processing database.")
        verbose(f"Database version: {self._num(self._db_version)}.")

        (conn, c) = sqlite_open_ro(self._tmp_db)

        # get info to associate persons with photos
        # then get detected faces in each photo and link to persons
        verbose("Processing persons in photos.")
        c.execute(
            """ SELECT
                RKPerson.modelID,
                RKPerson.uuid,
                RKPerson.name,
                RKPerson.faceCount,
                RKPerson.displayName,
                RKPerson.representativeFaceId
                FROM RKPerson
            """
        )

        # 0     RKPerson.modelID,
        # 1     RKPerson.uuid,
        # 2     RKPerson.name,
        # 3     RKPerson.faceCount,
        # 4     RKPerson.displayName
        # 5     RKPerson.representativeFaceId

        for person in c:
            pk = person[0]
            fullname = (
                normalize_unicode(person[2])
                if person[2] is not None
                else _UNKNOWN_PERSON
            )
            self._dbpersons_pk[pk] = {
                "pk": pk,
                "uuid": person[1],
                "fullname": fullname,
                "facecount": person[3],
                "keyface": person[5],
                "displayname": normalize_unicode(person[4]),
                "photo_uuid": None,
                "keyface_uuid": None,
                "type": None,  # Photos 5+
                "manualorder": 0,  # Photos 5+
            }
            try:
                self._dbpersons_fullname[fullname].append(pk)
            except KeyError:
                self._dbpersons_fullname[fullname] = [pk]

        # get info on key face
        c.execute(
            """ SELECT
                RKPerson.modelID,
                RKPerson.representativeFaceId,
                RKVersion.uuid,
                RKFace.uuid
                FROM RKPerson, RKFace, RKVersion
                WHERE 
                RKFace.modelId = RKPerson.representativeFaceId AND
                RKVersion.modelId = RKFace.ImageModelId
            """
        )

        # 0     RKPerson.modelID,
        # 1     RKPerson.representativeFaceId
        # 2     RKVersion.uuid,
        # 3     RKFace.uuid

        for person in c:
            pk = person[0]
            try:
                self._dbpersons_pk[pk]["photo_uuid"] = person[2]
                self._dbpersons_pk[pk]["keyface_uuid"] = person[3]
            except KeyError:
                logger.debug(f"Unexpected KeyError _dbpersons_pk[{pk}]")

        # get information on detected faces
        verbose("Processing detected faces in photos.")
        c.execute(
            """ SELECT 
                RKPerson.modelID,
                RKVersion.uuid 
                FROM 
                RKFace, RKPerson, RKVersion, RKMaster 
                WHERE 
                RKFace.personID = RKperson.modelID AND 
                RKVersion.modelId = RKFace.ImageModelId AND
                RKVersion.masterUuid = RKMaster.uuid  
            """
        )

        # 0     RKPerson.modelID
        # 1     RKVersion.uuid

        for face in c:
            pk = face[0]
            uuid = face[1]
            try:
                self._dbfaces_uuid[uuid].append(pk)
            except KeyError:
                self._dbfaces_uuid[uuid] = [pk]

            try:
                self._dbfaces_pk[pk].append(uuid)
            except KeyError:
                self._dbfaces_pk[pk] = [uuid]

        # Get info on albums
        verbose("Processing albums.")
        c.execute(
            """ SELECT 
                RKAlbum.uuid, 
                RKVersion.uuid,
                RKCustomSortOrder.orderNumber
                FROM RKVersion
                JOIN RKCustomSortOrder on RKCustomSortOrder.objectUuid = RKVersion.uuid
                JOIN RKAlbum on RKAlbum.uuid = RKCustomSortOrder.containerUuid
            """
        )

        # 0     RKAlbum.uuid,
        # 1     RKVersion.uuid,
        # 2     RKCustomSortOrder.orderNumber

        for album in c:
            # store by uuid in _dbalbums_uuid and by album in _dbalbums_album
            album_uuid = album[0]
            photo_uuid = album[1]
            sort_order = album[2]
            try:
                self._dbalbums_uuid[photo_uuid].append(album_uuid)
            except KeyError:
                self._dbalbums_uuid[photo_uuid] = [album_uuid]

            try:
                self._dbalbums_album[album_uuid].append((photo_uuid, sort_order))
            except KeyError:
                self._dbalbums_album[album_uuid] = [(photo_uuid, sort_order)]

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
                albumSubclass,
                createDate 
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
        # 8:    createDate

        for album in c:
            self._dbalbum_details[album[0]] = {
                "_uuid": album[0],
                "title": normalize_unicode(album[1]),
                "cloudlibrarystate": album[2],
                "cloudidentifier": album[3],
                "intrash": False if album[4] == 0 else True,
                "cloudlocalstate": None,  # Photos 5+
                "cloudownerfirstname": None,  # Photos 5+
                "cloudownderlastname": None,  # Photos 5+
                "cloudownerhashedpersonid": None,  # Photos 5+
                "folderUuid": album[5],
                "albumType": album[6],
                "albumSubclass": album[7],
                # for compatability with Photos 5 where album kind is ZKIND
                "kind": album[7],
                "creation_date": album[8],
                "start_date": None,  # Photos 5+ only
                "end_date": None,  # Photos 5+ only
                "customsortascending": None,  # Photos 5+ only
                "customsortkey": None,  # Photos 5+ only
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
                "name": normalize_unicode(row[2]),
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
            if (
                details["albumSubclass"] == _PHOTOS_4_ALBUM_KIND
                and parent_folder not in _PHOTOS_4_TOP_LEVEL_ALBUMS
            ):
                folder_hierarchy = self._build_album_folder_hierarchy_4(parent_folder)
                self._dbalbum_folders[album] = folder_hierarchy
            else:
                self._dbalbum_folders[album] = {}

        # Get info on keywords
        verbose("Processing keywords.")
        c.execute(
            """ SELECT
                RKKeyword.name, 
                RKVersion.uuid, 
                RKMaster.uuid 
                FROM 
                RKKeyword, RKKeywordForVersion, RKVersion, RKMaster 
                WHERE 
                RKKeyword.modelId = RKKeyWordForVersion.keywordID AND 
                RKVersion.modelID = RKKeywordForVersion.versionID AND 
                RKMaster.uuid = RKVersion.masterUuid
            """
        )
        for keyword_title, keyword_uuid, _ in c:
            keyword_title = normalize_unicode(keyword_title)
            try:
                self._dbkeywords_uuid[keyword_uuid].append(keyword_title)
            except KeyError:
                self._dbkeywords_uuid[keyword_uuid] = [keyword_title]
            try:
                self._dbkeywords_keyword[keyword_title].append(keyword_uuid)
            except KeyError:
                self._dbkeywords_keyword[keyword_title] = [keyword_uuid]

        # Get info on disk volumes
        c.execute("select RKVolume.modelId, RKVolume.name from RKVolume")
        for vol in c:
            self._dbvolumes[vol[0]] = vol[1]

        # Get photo details
        verbose("Processing photo details.")
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
                    RKMaster.alternateMasterUuid,
                    RKVersion.isInTrash,
                    RKVersion.processedHeight, 
                    RKVersion.processedWidth, 
                    RKVersion.orientation,
                    RKMaster.height,
                    RKMaster.width, 
                    RKMaster.orientation,
                    RKMaster.fileSize,
                    RKVersion.subType,
                    RKVersion.inTrashDate,
                    RKVersion.showInLibrary,
                    RKMaster.fileIsReference,
                    RKMaster.importGroupUuid,
                    RKMaster.fingerprint
                    FROM RKVersion, RKMaster
                    WHERE RKVersion.masterUuid = RKMaster.uuid"""
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
                    RKMaster.alternateMasterUuid,
                    RKVersion.isInTrash,
                    RKVersion.processedHeight, 
                    RKVersion.processedWidth, 
                    RKVersion.orientation,
                    RKMaster.height,
                    RKMaster.width, 
                    RKMaster.orientation,
                    RKMaster.originalFileSize,
                    RKVersion.subType,
                    RKVersion.inTrashDate,
                    RKVersion.showInLibrary,
                    RKMaster.fileIsReference,
                    RKMaster.importGroupUuid,
                    RKMaster.fingerprint
                    FROM RKVersion, RKMaster
                    WHERE RKVersion.masterUuid = RKMaster.uuid"""
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
        # 32    RKVersion.isInTrash
        # 33    RKVersion.processedHeight,
        # 34    RKVersion.processedWidth,
        # 35    RKVersion.orientation,
        # 36    RKMaster.height,
        # 37    RKMaster.width,
        # 38    RKMaster.orientation,
        # 39    RKMaster.originalFileSize
        # 40    RKVersion.subType
        # 41    RKVersion.inTrashDate
        # 42    RKVersion.showInLibrary -- is item visible in library (e.g. non-selected burst images are not visible)
        # 43    RKMaster.fileIsReference -- file is reference (imported without copying to Photos library)
        # 44    RKMaster.importGroupUuid -- to get date added from RKImportGroup
        # 45    RKMaster.fingerprint -- fingerprint / hash of the file

        for row in c:
            uuid = row[0]
            self._dbphotos[uuid] = {}
            self._dbphotos[uuid]["_uuid"] = uuid  # stored here for easier debugging
            self._dbphotos[uuid]["modelID"] = row[1]
            self._dbphotos[uuid]["masterUuid"] = row[2]
            self._dbphotos[uuid]["filename"] = normalize_unicode(row[3])

            # There are sometimes negative values for lastmodifieddate in the database
            # I don't know what these mean but they will raise exception in datetime if
            # not accounted for
            self._dbphotos[uuid]["lastmodifieddate_timestamp"] = row[4]
            try:
                self._dbphotos[uuid]["lastmodifieddate"] = datetime.fromtimestamp(
                    row[4] + TIME_DELTA
                )
            except (ValueError, TypeError):
                # sometimes the date is invalid or null
                self._dbphotos[uuid]["lastmodifieddate"] = None

            self._dbphotos[uuid]["imageTimeZoneOffsetSeconds"] = row[9]
            self._dbphotos[uuid]["imageDate_timestamp"] = row[5]

            try:
                imagedate = datetime.fromtimestamp(row[5] + TIME_DELTA)
                seconds = self._dbphotos[uuid]["imageTimeZoneOffsetSeconds"] or 0
                delta = timedelta(seconds=seconds)
                tz = timezone(delta)
                self._dbphotos[uuid]["imageDate"] = imagedate.astimezone(tz=tz)
            except (ValueError, TypeError):
                # sometimes imageDate is invalid so use 1 Jan 1970 as image date
                imagedate = datetime(1970, 1, 1)
                tz = timezone(timedelta(0))
                self._dbphotos[uuid]["imageDate"] = imagedate.astimezone(tz=tz)

            self._dbphotos[uuid]["mainRating"] = row[6]
            self._dbphotos[uuid]["hasAdjustments"] = row[7]
            self._dbphotos[uuid]["hasKeywords"] = row[8]
            self._dbphotos[uuid]["volumeId"] = row[10]
            self._dbphotos[uuid]["imagePath"] = row[11]
            self._dbphotos[uuid]["extendedDescription"] = row[12]
            self._dbphotos[uuid]["name"] = normalize_unicode(row[13])
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
                logger.debug(f"WARNING: {uuid} found unknown type {row[21]}")
                self._dbphotos[uuid]["type"] = None

            self._dbphotos[uuid]["UTI"] = row[22]

            # The UTI in RKMaster will always be UTI of the original
            # Unlike Photos 5 which changes the UTI to match latest edit
            self._dbphotos[uuid]["UTI_original"] = row[22]

            # UTI edited will be read from RKModelResource
            self._dbphotos[uuid]["UTI_edited"] = None

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
            else:
                # not a burst photo
                self._dbphotos[uuid]["burst"] = False

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
            self._dbphotos[uuid]["pk"] = row[
                26
            ]  # same as masterModelID, to match Photos 5
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
            self._dbphotos[uuid]["cloudAssetGUID"] = None  # Photos 5+
            self._dbphotos[uuid]["cloudLocalState"] = None  # Photos 5+
            self._dbphotos[uuid]["cloudLibraryState"] = None
            self._dbphotos[uuid]["cloudStatus"] = None
            self._dbphotos[uuid]["cloudAvailable"] = None
            self._dbphotos[uuid]["incloud"] = None
            self._dbphotos[uuid]["cloudMasterGUID"] = None  # Photos 5+

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

            # original resource choice (e.g. RAW or jpeg)
            # In Photos 5+, original_resource_choice set from:
            # ZADDITIONALASSETATTRIBUTES.ZORIGINALRESOURCECHOICE
            # = 0 if jpeg is selected as "original" in Photos (the default)
            # = 1 if RAW is selected as "original" in Photos
            # RKVersion.subType, RAW always appears to be 16
            #   4 = mov
            #   16 = RAW
            #   32 = JPEG
            #   64 = TIFF
            #   2048 = PNG
            #   32768 = HIEC
            self._dbphotos[uuid]["original_resource_choice"] = (
                1 if row[40] == 16 and self._dbphotos[uuid]["has_raw"] else 0
            )
            self._dbphotos[uuid]["raw_is_original"] = bool(
                self._dbphotos[uuid]["original_resource_choice"]
            )

            # recently deleted items
            self._dbphotos[uuid]["intrash"] = row[32] == 1
            self._dbphotos[uuid]["trasheddate_timestamp"] = row[41]
            try:
                self._dbphotos[uuid]["trasheddate"] = datetime.fromtimestamp(
                    row[41] + TIME_DELTA
                )
            except (ValueError, TypeError):
                self._dbphotos[uuid]["trasheddate"] = None

            # height/width/orientation
            self._dbphotos[uuid]["height"] = row[33]
            self._dbphotos[uuid]["width"] = row[34]
            self._dbphotos[uuid]["orientation"] = row[35]
            self._dbphotos[uuid]["original_height"] = row[36]
            self._dbphotos[uuid]["original_width"] = row[37]
            self._dbphotos[uuid]["original_orientation"] = row[38]
            self._dbphotos[uuid]["original_filesize"] = row[39]

            # visibility state
            self._dbphotos[uuid]["visibility_state"] = row[42]
            self._dbphotos[uuid]["visible"] = row[42] == 1

            # file is reference (not copied into Photos library)
            self._dbphotos[uuid]["isreference"] = row[43] == 1
            self._dbphotos[uuid]["saved_asset_type"] = None  # Photos 5+

            # import session not yet handled for Photos 4
            self._dbphotos[uuid]["import_session"] = None
            self._dbphotos[uuid]["import_uuid"] = row[44]
            self._dbphotos[uuid]["fok_import_session"] = None

            # fingerprint
            self._dbphotos[uuid]["masterFingerprint"] = row[45]

            # photos 5+ only, for shared photos
            self._dbphotos[uuid]["cloudownerhashedpersonid"] = None

            # photos 7+ only, shared moments
            self._dbphotos[uuid]["moment_share"] = None

            # compute signatures for finding possible duplicates
            signature = self._duplicate_signature(uuid)
            try:
                self._db_signatures[signature].append(uuid)
            except KeyError:
                self._db_signatures[signature] = [uuid]

        # get additional details from RKMaster, needed for RAW processing
        verbose("Processing additional photo details.")
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
                RKMaster.alternateMasterUuid,
                RKMaster.filename
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
        # 10    RKMaster.filename

        for row in c:
            uuid = row[0]
            info = {}
            info["_uuid"] = uuid
            info["volumeId"] = row[1]
            info["imagePath"] = row[2]
            info["isMissing"] = row[3]
            info["originalFilename"] = normalize_unicode(row[4])
            info["UTI"] = row[5]
            info["modelID"] = row[6]
            info["fileSize"] = row[7]
            info["isTrulyRAW"] = row[8]
            info["alternateMasterUuid"] = row[9]
            info["filename"] = normalize_unicode(row[10])
            self._dbphotos_master[uuid] = info

        # get details needed to find path of the edited photos
        c.execute(
            """ SELECT RKVersion.uuid, RKVersion.adjustmentUuid, RKModelResource.modelId,
                RKModelResource.resourceTag, RKModelResource.UTI, RKVersion.specialType,
                RKModelResource.attachedModelType, RKModelResource.resourceType
                FROM RKVersion
                JOIN RKModelResource on RKModelResource.attachedModelId = RKVersion.modelId
                ORDER BY RKModelResource.modelId
            """
        )

        # Order of results:
        # 0     RKVersion.uuid
        # 1     RKVersion.adjustmentUuid
        # 2     RKModelResource.modelId
        # 3     RKModelResource.resourceTag
        # 4     RKModelResource.UTI
        # 5     RKVersion.specialType
        # 6     RKModelResource.attachedModelType (2 = edit)
        # 7     RKModelResource.resourceType (4 = photo, 8 = video)

        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                # get info on adjustments (edits)
                if self._dbphotos[uuid]["adjustmentUuid"] == row[3]:
                    if (
                        row[1] != "UNADJUSTEDNONRAW"
                        and row[1] != "UNADJUSTED"
                        and row[6] == 2
                    ):
                        resource_type = row[7]
                        # UTI_edited will be set to the appropriate UTI for the edited resource below
                        # a live photo that's edited will have both a photo and video resource but the photo
                        # UTI will be used for the edited live photo, see #859
                        if resource_type == 4:
                            # photo
                            if "edit_resource_id_photo" in self._dbphotos[uuid]:
                                logger.debug(
                                    f"WARNING: found more than one edit_resource_id_photo for "
                                    f"UUID {row[0]},adjustmentUUID {row[1]}, modelID {row[2]}"
                                )
                            self._dbphotos[uuid]["edit_resource_id_photo"] = row[2]
                            self._dbphotos[uuid]["UTI_edited_photo"] = row[4]
                        elif resource_type == 8:
                            # video
                            if "edit_resource_id_video" in self._dbphotos[uuid]:
                                logger.debug(
                                    f"WARNING: found more than one edit_resource_id_video for "
                                    f"UUID {row[0]},adjustmentUUID {row[1]}, modelID {row[2]}"
                                )
                            self._dbphotos[uuid]["edit_resource_id_video"] = row[2]
                            self._dbphotos[uuid]["UTI_edited_video"] = row[4]

        # get details on external edits
        c.execute(
            """ SELECT RKVersion.uuid, 
                RKVersion.adjustmentUuid, 
                RKAdjustmentData.originator, 
                RKAdjustmentData.format 
                FROM RKVersion, RKAdjustmentData 
                WHERE RKVersion.adjustmentUuid = RKAdjustmentData.uuid """
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
        # also initialized UTI_edited and edit_resource_id
        for uuid in self._dbphotos:
            if "edit_resource_id_photo" not in self._dbphotos[uuid]:
                self._dbphotos[uuid]["edit_resource_id_photo"] = None
            if "edit_resource_id_video" not in self._dbphotos[uuid]:
                self._dbphotos[uuid]["edit_resource_id_video"] = None
            if "UTI_edited_photo" not in self._dbphotos[uuid]:
                self._dbphotos[uuid]["UTI_edited_photo"] = None
            if "UTI_edited_video" not in self._dbphotos[uuid]:
                self._dbphotos[uuid]["UTI_edited_video"] = None
            # UTI_edited will be set to the appropriate UTI for the edited resource below
            # a live photo that's edited will have both a photo and video resource but the photo
            # UTI will be used for the edited live photo
            self._dbphotos[uuid]["UTI_edited"] = (
                self._dbphotos[uuid]["UTI_edited_photo"]
                or self._dbphotos[uuid]["UTI_edited_video"]
            )
            self._dbphotos[uuid]["edit_resource_id"] = (
                self._dbphotos[uuid]["edit_resource_id_photo"]
                or self._dbphotos[uuid]["edit_resource_id_video"]
            )
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
        # 0  RKVersion.uuid,
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
        verbose("Processing location data.")
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
            "SELECT modelID, defaultName, type, area FROM RKPlace"
        ).fetchall()
        places = {p[0]: p for p in place_data}
        self._db_places = places

        # get import data
        import_data = c.execute(
            "SELECT modelID, uuid, name, importDate from RKImportGroup"
        ).fetchall()
        self._db_import_group = {i[1]: i for i in import_data}

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
            # area could be None so assume 0 if it is (issue #230)
            place_names = [
                pname
                for pname in sorted(
                    [places[p] for p in places if p in place_ids],
                    key=lambda place: place[3] if place[3] is not None else 0,
                )
            ]

            self._dbphotos[uuid]["placeNames"] = place_names
            self._dbphotos[uuid]["reverse_geolocation"] = None  # Photos 5

            # add date added
            try:
                import_session = self._db_import_group[
                    self._dbphotos[uuid]["import_uuid"]
                ]
                self._dbphotos[uuid]["added_date"] = datetime.fromtimestamp(
                    import_session[3] + TIME_DELTA
                )
            except (ValueError, TypeError, KeyError):
                self._dbphotos[uuid]["added_date"] = datetime(1970, 1, 1)

        # build album_titles dictionary
        for album_id in self._dbalbum_details:
            title = self._dbalbum_details[album_id]["title"]
            if title in self._dbalbum_titles:
                self._dbalbum_titles[title].append(album_id)
            else:
                self._dbalbum_titles[title] = [album_id]

        # add volume name to _dbphotos_master
        for info in self._dbphotos_master.values():
            # issue 230: have seen bad volumeID values
            try:
                info["volume"] = (
                    self._dbvolumes[info["volumeId"]]
                    if info["volumeId"] is not None
                    else None
                )
            except KeyError:
                info["volume"] = None

        # add data on RAW images
        for info in self._dbphotos.values():
            if info["has_raw"]:
                raw_uuid = info["raw_master_uuid"]
                info["raw_info"] = self._dbphotos_master[raw_uuid]
                info["UTI_raw"] = self._dbphotos_master[raw_uuid]["UTI"]
                non_raw_uuid = info["non_raw_master_uuid"]
                info["raw_pair_info"] = self._dbphotos_master[non_raw_uuid]
            else:
                info["raw_info"] = None
                info["UTI_raw"] = None
                info["raw_pair_info"] = None

        # placeholders for shared library info on Photos 8+
        for uuid in self._dbphotos:
            self._dbphotos[uuid]["active_library_participation_state"] = None
            self._dbphotos[uuid]["library_scope_share_state"] = None
            self._dbphotos[uuid]["library_scope"] = None

        # done with the database connection
        conn.close()

        # process faces
        verbose("Processing face details.")
        self._process_faceinfo()

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
                # issue 230: have seen bad volumeID values
                try:
                    self._dbphotos[uuid]["volume"] = self._dbvolumes[
                        self._dbphotos[uuid]["volumeId"]
                    ]
                except KeyError:
                    self._dbphotos[uuid]["volume"] = None
            else:
                self._dbphotos[uuid]["volume"] = None

        # done processing, dump debug data if requested
        verbose("Done processing details from Photos library.")

    def _build_album_folder_hierarchy_4(self, uuid, folders=None):
        """Recursively build folder/album hierarchy
        uuid: parent uuid of the album being processed
             (parent uuid is a folder in RKFolders)
        folders: dict holding the folder hierarchy
        NOTE: This implementation is different than _build_album_folder_hierarchy_5
        which takes the uuid of the album being processed.  Here uuid is the parent uuid
        of the parent folder album because in Photos <=4, folders are in RKFolders and
        albums in RKAlbums.  In Photos 5, folders are just special albums
        with kind = _PHOTOS_5_FOLDER_KIND"""

        parent_uuid = self._dbfolder_details[uuid]["parentFolderUuid"]

        if parent_uuid is None:
            return folders

        if parent_uuid in _PHOTOS_4_TOP_LEVEL_ALBUMS:
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
        """process the Photos database to extract info
        works on Photos version 5 and version 6

        This is a big hairy 700 line function that should probably be refactored
        but it works so don't touch it.
        """

        logger.debug(f"_process_database5")
        verbose = self._verbose
        verbose(f"Processing database.")
        (conn, c) = sqlite_open_ro(self._tmp_db)

        # some of the tables/columns have different names in different versions of Photos
        # set local var for readability
        photos_ver = self._photos_ver
        verbose(
            f"Database version: {self._num(self._db_version)}, {self._num(photos_ver)}."
        )
        asset_table = _DB_TABLE_NAMES[photos_ver]["ASSET"]
        keyword_join = _DB_TABLE_NAMES[photos_ver]["KEYWORD_JOIN"]
        asset_album_table = _DB_TABLE_NAMES[photos_ver]["ASSET_ALBUM_TABLE"]
        album_join = _DB_TABLE_NAMES[photos_ver]["ALBUM_JOIN"]
        album_sort = _DB_TABLE_NAMES[photos_ver]["ALBUM_SORT_ORDER"]
        asset_album_join = _DB_TABLE_NAMES[photos_ver]["ASSET_ALBUM_JOIN"]
        import_fok = _DB_TABLE_NAMES[photos_ver]["IMPORT_FOK"]
        depth_state = _DB_TABLE_NAMES[photos_ver]["DEPTH_STATE"]
        uti_original_column = _DB_TABLE_NAMES[photos_ver]["UTI_ORIGINAL"]
        hdr_type_column = _DB_TABLE_NAMES[photos_ver]["HDR_TYPE"]

        # Look for all combinations of persons and pictures
        logger.debug(f"Getting information about persons")

        # get info to associate persons with photos
        # then get detected faces in each photo and link to persons
        verbose("Processing persons in photos.")
        c.execute(
            """ SELECT
                ZPERSON.Z_PK,
                ZPERSON.ZPERSONUUID,
                ZPERSON.ZFULLNAME,
                ZPERSON.ZFACECOUNT,
                ZPERSON.ZKEYFACE,
                ZPERSON.ZDISPLAYNAME,
                ZPERSON.ZTYPE,
                ZPERSON.ZMANUALORDER
                FROM ZPERSON
            """
        )

        # 0     ZPERSON.Z_PK,
        # 1     ZPERSON.ZPERSONUUID,
        # 2     ZPERSON.ZFULLNAME,
        # 3     ZPERSON.ZFACECOUNT,
        # 4     ZPERSON.ZKEYFACE,
        # 5     ZPERSON.ZDISPLAYNAME
        # 6     ZPERSON.ZTYPE,  # ZTYPE = 1 == favorite, 0 == not favorite
        # 7     ZPERSON.ZMANUALORDER # favorites are sorted by ZMANUALORDER

        for person in c:
            pk = person[0]
            fullname = (
                normalize_unicode(person[2])
                if (person[2] != "" and person[2] is not None)
                else _UNKNOWN_PERSON
            )
            self._dbpersons_pk[pk] = {
                "pk": pk,
                "uuid": person[1],
                "fullname": fullname,
                "facecount": person[3],
                "keyface": person[4],
                "displayname": normalize_unicode(person[5]),
                "photo_uuid": None,
                "keyface_uuid": None,
                "type": person[6],
                "manualorder": person[7],
            }
            try:
                self._dbpersons_fullname[fullname].append(pk)
            except KeyError:
                self._dbpersons_fullname[fullname] = [pk]

        # get info on keyface -- some photos have null keyface so can't do a single query
        # (at least not with my SQL skills)
        asset_fk = _DB_TABLE_NAMES[photos_ver]["DETECTED_FACE_ASSET_FK"]
        c.execute(
            f""" SELECT
                ZPERSON.Z_PK,
                ZPERSON.ZKEYFACE,
                {asset_table}.ZUUID,
                ZDETECTEDFACE.ZUUID
                FROM ZPERSON, ZDETECTEDFACE, {asset_table}
                WHERE ZDETECTEDFACE.Z_PK = ZPERSON.ZKEYFACE AND
                {asset_fk} = {asset_table}.Z_PK
            """
        )

        # 0 ZPERSON.Z_PK,
        # 1 ZPERSON.ZKEYFACE,
        # 2 ZGENERICASSET.ZUUID,
        # 3 ZDETECTEDFACE.ZUUID

        for person in c:
            pk = person[0]
            try:
                self._dbpersons_pk[pk]["photo_uuid"] = person[2]
                self._dbpersons_pk[pk]["keyface_uuid"] = person[3]
            except KeyError:
                logger.debug(f"Unexpected KeyError _dbpersons_pk[{pk}]")

        # get information on detected faces
        verbose("Processing detected faces in photos.")
        person_fk = _DB_TABLE_NAMES[photos_ver]["DETECTED_FACE_PERSON_FK"]
        c.execute(
            f""" SELECT
                ZPERSON.Z_PK,
                {asset_table}.ZUUID
                FROM ZPERSON, ZDETECTEDFACE, {asset_table}
                WHERE {person_fk} = ZPERSON.Z_PK AND
                {asset_fk} = {asset_table}.Z_PK
            """
        )

        # 0     ZPERSON.Z_PK,
        # 1     ZGENERICASSET.ZUUID,

        for face in c:
            pk = face[0]
            uuid = face[1]
            try:
                self._dbfaces_uuid[uuid].append(pk)
            except KeyError:
                self._dbfaces_uuid[uuid] = [pk]

            try:
                self._dbfaces_pk[pk].append(uuid)
            except KeyError:
                self._dbfaces_pk[pk] = [uuid]

        # get details about albums
        verbose("Processing albums.")
        c.execute(
            f""" SELECT 
                ZGENERICALBUM.ZUUID, 
                {asset_table}.ZUUID,
                {album_sort}
                FROM {asset_table} 
                JOIN {asset_album_table} ON {album_join} = {asset_table}.Z_PK 
                JOIN ZGENERICALBUM ON ZGENERICALBUM.Z_PK = {asset_album_join}
            """
        )

        # 0     ZGENERICALBUM.ZUUID,
        # 1     ZGENERICASSET.ZUUID,
        # 2     Z_26ASSETS.Z_FOK_34ASSETS

        for album in c:
            # store by uuid in _dbalbums_uuid and by album in _dbalbums_album
            album_uuid = album[0]
            photo_uuid = album[1]
            sort_order = album[2]
            try:
                self._dbalbums_uuid[photo_uuid].append(album_uuid)
            except KeyError:
                self._dbalbums_uuid[photo_uuid] = [album_uuid]

            try:
                self._dbalbums_album[album_uuid].append((photo_uuid, sort_order))
            except KeyError:
                self._dbalbums_album[album_uuid] = [(photo_uuid, sort_order)]

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
            "ZTRASHEDSTATE, "  # 9
            "ZCREATIONDATE, "  # 10
            "ZSTARTDATE, "  # 11
            "ZENDDATE, "  # 12
            "ZCUSTOMSORTASCENDING, "  # 13
            "ZCUSTOMSORTKEY "  # 14
            "FROM ZGENERICALBUM "
        )
        for album in c:
            self._dbalbum_details[album[0]] = {
                "_uuid": album[0],
                "title": normalize_unicode(album[1]),
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
                "creation_date": album[10]
                or 0,  # iPhone Photos.sqlite can have null value
                "start_date": album[11] or 0,
                "end_date": album[12] or 0,
                "customsortascending": album[13],
                "customsortkey": album[14],
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

        # get details on keywords
        verbose("Processing keywords.")
        c.execute(
            f"""SELECT ZKEYWORD.ZTITLE, {asset_table}.ZUUID
                FROM {asset_table} 
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK 
                JOIN Z_1KEYWORDS ON Z_1KEYWORDS.Z_1ASSETATTRIBUTES = ZADDITIONALASSETATTRIBUTES.Z_PK 
                JOIN ZKEYWORD ON ZKEYWORD.Z_PK = {keyword_join} """
        )
        for keyword_title, keyword_uuid in c:
            keyword_title = normalize_unicode(keyword_title)
            try:
                self._dbkeywords_uuid[keyword_uuid].append(keyword_title)
            except KeyError:
                self._dbkeywords_uuid[keyword_uuid] = [keyword_title]
            try:
                self._dbkeywords_keyword[keyword_title].append(keyword_uuid)
            except KeyError:
                self._dbkeywords_keyword[keyword_title] = [keyword_uuid]

        # get details on disk volumes
        c.execute("SELECT ZUUID, ZNAME from ZFILESYSTEMVOLUME")
        for vol in c:
            self._dbvolumes[vol[0]] = vol[1]

        # get details about photos
        verbose("Processing photo details.")
        c.execute(
            f"""SELECT {asset_table}.ZUUID, 
                ZADDITIONALASSETATTRIBUTES.ZMASTERFINGERPRINT, 
                ZADDITIONALASSETATTRIBUTES.ZTITLE, 
                ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME, 
                {asset_table}.ZMODIFICATIONDATE, 
                {asset_table}.ZDATECREATED, 
                ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET, 
                ZADDITIONALASSETATTRIBUTES.ZINFERREDTIMEZONEOFFSET, 
                ZADDITIONALASSETATTRIBUTES.ZTIMEZONENAME, 
                {asset_table}.ZHIDDEN, 
                {asset_table}.ZFAVORITE, 
                {asset_table}.ZDIRECTORY, 
                {asset_table}.ZFILENAME, 
                {asset_table}.ZLATITUDE, 
                {asset_table}.ZLONGITUDE, 
                {asset_table}.ZHASADJUSTMENTS, 
                {asset_table}.ZCLOUDBATCHPUBLISHDATE, 
                {asset_table}.ZKIND, 
                {asset_table}.ZUNIFORMTYPEIDENTIFIER,
                {asset_table}.ZAVALANCHEUUID,
                {asset_table}.ZAVALANCHEPICKTYPE,
                {asset_table}.ZKINDSUBTYPE,
                {asset_table}.{hdr_type_column},
                ZADDITIONALASSETATTRIBUTES.ZCAMERACAPTUREDEVICE,
                {asset_table}.ZCLOUDASSETGUID,
                ZADDITIONALASSETATTRIBUTES.ZREVERSELOCATIONDATA,
                {asset_table}.ZMOMENT,
                ZADDITIONALASSETATTRIBUTES.ZORIGINALRESOURCECHOICE,
                {asset_table}.ZTRASHEDSTATE,
                {asset_table}.ZHEIGHT, 
                {asset_table}.ZWIDTH, 
                {asset_table}.ZORIENTATION, 
                ZADDITIONALASSETATTRIBUTES.ZORIGINALHEIGHT, 
                ZADDITIONALASSETATTRIBUTES.ZORIGINALWIDTH, 
                ZADDITIONALASSETATTRIBUTES.ZORIGINALORIENTATION,
                ZADDITIONALASSETATTRIBUTES.ZORIGINALFILESIZE,
                {depth_state},
                {asset_table}.ZADJUSTMENTTIMESTAMP,
                {asset_table}.ZVISIBILITYSTATE,
                {asset_table}.ZTRASHEDDATE,
                {asset_table}.ZSAVEDASSETTYPE,
                {asset_table}.ZADDEDDATE,
                {asset_table}.Z_PK,
                {asset_table}.ZCLOUDOWNERHASHEDPERSONID,
                {asset_table}.ZMOMENTSHARE
                FROM {asset_table} 
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK 
                ORDER BY {asset_table}.ZUUID  """
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
        # 28   ZGENERICASSET.ZTRASHEDSTATE -- 0 if not in trash, 1 if in trash
        # 29   ZGENERICASSET.ZHEIGHT,
        # 30   ZGENERICASSET.ZWIDTH,
        # 31   ZGENERICASSET.ZORIENTATION,
        # 32   ZADDITIONALASSETATTRIBUTES.ZORIGINALHEIGHT,
        # 33   ZADDITIONALASSETATTRIBUTES.ZORIGINALWIDTH,
        # 34   ZADDITIONALASSETATTRIBUTES.ZORIGINALORIENTATION,
        # 35   ZADDITIONALASSETATTRIBUTES.ZORIGINALFILESIZE
        # 36   ZGENERICASSET.ZDEPTHSTATES / ZASSET.ZDEPTHTYPE
        # 37   ZGENERICASSET.ZADJUSTMENTTIMESTAMP -- when was photo edited?
        # 38   ZGENERICASSET.ZVISIBILITYSTATE -- 0 if visible, 2 if not (e.g. a burst image)
        # 39   ZGENERICASSET.ZTRASHEDDATE -- date item placed in the trash or null if not in trash
        # 40   ZGENERICASSET.ZSAVEDASSETTYPE -- how item imported
        # 41   ZGENERICASSET.ZADDEDDATE -- date item added to the library
        # 42   ZGENERICASSET.Z_PK -- primary key
        # 43   ZGENERICASSET.ZCLOUDOWNERHASHEDPERSONID -- used to look up owner name (for shared photos)
        # 44   ZASSET.ZMOMENTSHARE -- FK for ZSHARE (shared moments, Photos 5+; in Photos 7+ these are in the scopes/momentshared folder)

        for row in c:
            uuid = row[0]
            info = {}
            info["_uuid"] = uuid  # stored here for easier debugging
            info["modelID"] = None
            info["masterUuid"] = None
            info["masterFingerprint"] = row[1]
            info["name"] = normalize_unicode(row[2])

            # There are sometimes negative values for lastmodifieddate in the database
            # I don't know what these mean but they will raise exception in datetime if
            # not accounted for
            info["lastmodifieddate_timestamp"] = row[37]
            try:
                info["lastmodifieddate"] = datetime.fromtimestamp(row[37] + TIME_DELTA)
            except (ValueError, TypeError):
                info["lastmodifieddate"] = None

            info["imageTimeZoneOffsetSeconds"] = row[6]
            info["imageDate_timestamp"] = row[5]

            try:
                imagedate = datetime.fromtimestamp(row[5] + TIME_DELTA)
                seconds = info["imageTimeZoneOffsetSeconds"] or 0
                delta = timedelta(seconds=seconds)
                tz = timezone(delta)
                info["imageDate"] = imagedate.astimezone(tz=tz)
            except (ValueError, TypeError):
                # sometimes imageDate is invalid or null so use 1 Jan 1970 in UTC as image date (#1014)
                imagedate = datetime(1970, 1, 1)
                tz = timezone(timedelta(0))
                info["imageDate"] = imagedate.astimezone(tz=tz)

            info["hidden"] = row[9]
            info["favorite"] = row[10]
            info["originalFilename"] = normalize_unicode(row[3])
            info["filename"] = normalize_unicode(row[12])
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
                logger.debug(f"WARNING: {uuid} found unknown type {row[17]}")
                info["type"] = None

            info["UTI"] = row[18]
            info["UTI_original"] = None  # filled in later

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
            else:
                # not a burst photo
                info["burst"] = False

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
            # > 6 = portrait (sometimes, see ZDEPTHSTATE/ZDEPTHTYPE)
            info["customRenderedValue"] = row[22]
            info["hdr"] = True if row[22] == 3 else False
            info["depth_state"] = row[36]
            info["portrait"] = True if row[36] != 0 else False

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
            info["cloudMasterGUID"] = None

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

            # recently deleted items
            info["intrash"] = True if row[28] == 1 else False
            info["trasheddate_timestamp"] = row[39]
            try:
                info["trasheddate"] = datetime.fromtimestamp(row[39] + TIME_DELTA)
            except (ValueError, TypeError):
                info["trasheddate"] = None

            # height/width/orientation
            info["height"] = row[29]
            info["width"] = row[30]
            info["orientation"] = row[31]
            info["original_height"] = row[32]
            info["original_width"] = row[33]
            info["original_orientation"] = row[34]
            info["original_filesize"] = row[35]

            # visibility state, visible (True) if 0, otherwise not visible (False)
            # only values I've seen are 0 for visible, 2 for not-visible
            info["visibility_state"] = row[38]
            info["visible"] = row[38] == 0

            # ZSAVEDASSETTYPE Values:
            # 3: imported by copying to Photos library
            # 4: shared iCloud photo
            # 6: imported by iCloud (e.g. from iPhone)
            # 10: referenced file (not copied to Photos library)
            info["saved_asset_type"] = row[40]
            info["isreference"] = row[40] == 10

            try:
                info["added_date"] = datetime.fromtimestamp(row[41] + TIME_DELTA)
            except (ValueError, TypeError):
                info["added_date"] = datetime(1970, 1, 1)

            info["pk"] = row[42]
            info["cloudownerhashedpersonid"] = row[43]

            info["moment_share"] = row[44]

            # initialize import session info which will be filled in later
            # not every photo has an import session so initialize all records now
            info["import_session"] = None
            info["fok_import_session"] = None
            info["import_uuid"] = None

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

            # Photos 4 only
            info["edit_resource_id_photo"] = None
            info["edit_resource_id_video"] = None
            info["UTI_edited_photo"] = None
            info["UTI_edited_video"] = None

            # placeholder for shared library info (Photos 8+)
            info["active_library_participation_state"] = None
            info["library_scope_share_state"] = None
            info["library_scope"] = None

            self._dbphotos[uuid] = info

            # compute signatures for finding possible duplicates
            signature = self._duplicate_signature(uuid)
            try:
                self._db_signatures[signature].append(uuid)
            except KeyError:
                self._db_signatures[signature] = [uuid]

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

        # get info on import sessions
        # 0    ZGENERICASSET.ZUUID
        # 1    ZGENERICASSET.ZIMPORTSESSION
        # 2    ZGENERICASSET.Z_FOK_IMPORTSESSION
        # 3    ZGENERICALBUM.ZUUID,
        verbose("Processing import sessions.")
        c.execute(
            f"""SELECT
                {asset_table}.ZUUID,
                {asset_table}.ZIMPORTSESSION,
                {import_fok},
                ZGENERICALBUM.ZUUID
                FROM
                {asset_table}
                JOIN ZGENERICALBUM ON ZGENERICALBUM.Z_PK = {asset_table}.ZIMPORTSESSION
            """
        )

        for row in c:
            uuid = row[0]
            try:
                self._dbphotos[uuid]["import_session"] = row[1]
                self._dbphotos[uuid]["fok_import_session"] = row[2]
                self._dbphotos[uuid]["import_uuid"] = row[3]
            except KeyError:
                logger.debug(f"No info record for uuid {uuid} for import session")

        # Get extended description
        verbose("Processing additional photo details.")
        c.execute(
            f"""SELECT {asset_table}.ZUUID, 
                ZASSETDESCRIPTION.ZLONGDESCRIPTION 
                FROM {asset_table} 
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK 
                JOIN ZASSETDESCRIPTION ON ZASSETDESCRIPTION.Z_PK = ZADDITIONALASSETATTRIBUTES.ZASSETDESCRIPTION 
                ORDER BY {asset_table}.ZUUID """
        )
        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["extendedDescription"] = normalize_unicode(row[1])
            else:
                logger.debug(
                    f"WARNING: found description {row[1]} but no photo for {uuid}"
                )

        # get information about adjusted/edited photos
        c.execute(
            f"""SELECT {asset_table}.ZUUID, 
                {asset_table}.ZHASADJUSTMENTS, 
                ZUNMANAGEDADJUSTMENT.ZADJUSTMENTFORMATIDENTIFIER 
                FROM {asset_table}, ZUNMANAGEDADJUSTMENT 
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK 
                WHERE ZADDITIONALASSETATTRIBUTES.ZUNMANAGEDADJUSTMENT = ZUNMANAGEDADJUSTMENT.Z_PK """
        )
        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["adjustmentFormatID"] = row[2]
            else:
                logger.debug(
                    f"WARNING: found adjustmentformatidentifier {row[2]} but no photo for uuid {row[0]}"
                )

        # Find missing photos
        # TODO: this code is very kludgy and I had to make lots of assumptions
        # it's probably wrong and needs to be re-worked once I figure out how to reliably
        # determine if a photo is missing in Photos 5

        # Get info on remote/local availability for photos in shared albums
        # Also get UTI of original image (zdatastoresubtype = 1)
        if self._photos_ver >= 7:
            sql_missing = f""" SELECT 
                {asset_table}.ZUUID, 
                ZINTERNALRESOURCE.ZLOCALAVAILABILITY, 
                ZINTERNALRESOURCE.ZREMOTEAVAILABILITY,
                ZINTERNALRESOURCE.ZDATASTORESUBTYPE,
                {uti_original_column},
                null 
                FROM {asset_table}
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK 
                JOIN ZINTERNALRESOURCE ON ZINTERNALRESOURCE.ZASSET = ZADDITIONALASSETATTRIBUTES.ZASSET 
                WHERE  ZDATASTORESUBTYPE = 1 OR ZDATASTORESUBTYPE = 3 """
        else:
            sql_missing = f""" SELECT 
                {asset_table}.ZUUID, 
                ZINTERNALRESOURCE.ZLOCALAVAILABILITY, 
                ZINTERNALRESOURCE.ZREMOTEAVAILABILITY,
                ZINTERNALRESOURCE.ZDATASTORESUBTYPE,
                {uti_original_column},
                ZUNIFORMTYPEIDENTIFIER.ZIDENTIFIER
                FROM {asset_table}
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK 
                JOIN ZINTERNALRESOURCE ON ZINTERNALRESOURCE.ZASSET = ZADDITIONALASSETATTRIBUTES.ZASSET 
                JOIN ZUNIFORMTYPEIDENTIFIER ON ZUNIFORMTYPEIDENTIFIER.Z_PK = ZINTERNALRESOURCE.ZUNIFORMTYPEIDENTIFIER 
                WHERE  ZDATASTORESUBTYPE = 1 OR ZDATASTORESUBTYPE = 3 """

        c.execute(sql_missing)

        # Order of results:
        # 0 {asset_table}.ZUUID,
        # 1 ZINTERNALRESOURCE.ZLOCALAVAILABILITY,
        # 2 ZINTERNALRESOURCE.ZREMOTEAVAILABILITY,
        # 3 ZINTERNALRESOURCE.ZDATASTORESUBTYPE,
        # 4 ZINTERNALRESOURCE.ZUNIFORMTYPEIDENTIFIER,
        # 5 ZUNIFORMTYPEIDENTIFIER.ZIDENTIFIER

        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["localAvailability"] = row[1]
                self._dbphotos[uuid]["remoteAvailability"] = row[2]
                if row[3] == 1:
                    self._dbphotos[uuid]["UTI_original"] = row[5]

                if row[1] != 1:
                    self._dbphotos[uuid]["isMissing"] = 1
                else:
                    self._dbphotos[uuid]["isMissing"] = 0

        # get information on local/remote availability
        c.execute(
            f""" SELECT {asset_table}.ZUUID,
                ZINTERNALRESOURCE.ZLOCALAVAILABILITY,
                ZINTERNALRESOURCE.ZREMOTEAVAILABILITY
                FROM {asset_table}
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK
                JOIN ZINTERNALRESOURCE ON ZINTERNALRESOURCE.ZFINGERPRINT = ZADDITIONALASSETATTRIBUTES.ZMASTERFINGERPRINT """
        )

        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["localAvailability"] = row[1]
                self._dbphotos[uuid]["remoteAvailability"] = row[2]

                if row[1] != 1:
                    self._dbphotos[uuid]["isMissing"] = 1
                else:
                    self._dbphotos[uuid]["isMissing"] = 0

        # get information about cloud sync state
        c.execute(
            f""" SELECT
                {asset_table}.ZUUID,
                ZCLOUDMASTER.ZCLOUDLOCALSTATE,
                ZCLOUDMASTER.ZCLOUDMASTERGUID
                FROM ZCLOUDMASTER, {asset_table}
                WHERE {asset_table}.ZMASTER = ZCLOUDMASTER.Z_PK """
        )
        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["cloudLocalState"] = row[1]
                self._dbphotos[uuid]["incloud"] = True if row[1] == 3 else False
                self._dbphotos[uuid]["cloudMasterGUID"] = row[2]

        # get information about associted RAW images
        # RAW images have ZDATASTORESUBTYPE = 17
        if self._photos_ver >= 7:
            sql_raw = f""" SELECT
                {asset_table}.ZUUID,
                ZINTERNALRESOURCE.ZDATALENGTH, 
                null,
                ZINTERNALRESOURCE.ZDATASTORESUBTYPE,
                ZINTERNALRESOURCE.ZRESOURCETYPE,
                ZINTERNALRESOURCE.ZFILESYSTEMBOOKMARK
                FROM {asset_table}
                JOIN ZINTERNALRESOURCE ON ZINTERNALRESOURCE.ZASSET = ZADDITIONALASSETATTRIBUTES.ZASSET
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK 
                WHERE ZINTERNALRESOURCE.ZDATASTORESUBTYPE = 17
            """
        else:
            sql_raw = f""" SELECT
                {asset_table}.ZUUID,
                ZINTERNALRESOURCE.ZDATALENGTH, 
                ZUNIFORMTYPEIDENTIFIER.ZIDENTIFIER,
                ZINTERNALRESOURCE.ZDATASTORESUBTYPE,
                ZINTERNALRESOURCE.ZRESOURCETYPE,
                ZINTERNALRESOURCE.ZFILESYSTEMBOOKMARK
                FROM {asset_table}
                JOIN ZINTERNALRESOURCE ON ZINTERNALRESOURCE.ZASSET = ZADDITIONALASSETATTRIBUTES.ZASSET
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK 
                JOIN ZUNIFORMTYPEIDENTIFIER ON ZUNIFORMTYPEIDENTIFIER.Z_PK =  ZINTERNALRESOURCE.ZUNIFORMTYPEIDENTIFIER
                WHERE ZINTERNALRESOURCE.ZDATASTORESUBTYPE = 17
            """

        c.execute(sql_raw)

        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["has_raw"] = True
                self._dbphotos[uuid]["raw_data_length"] = row[1]
                self._dbphotos[uuid]["UTI_raw"] = row[2]
                self._dbphotos[uuid]["datastore_subtype"] = row[3]
                self._dbphotos[uuid]["resource_type"] = row[4]
                self._dbphotos[uuid]["raw_bookmark"] = row[5]

        # get paths for the relative imports for RAW+JPEG images
        c.execute(
            f""" SELECT
            {asset_table}.ZUUID,
            ZFILESYSTEMVOLUME.ZNAME,
            ZFILESYSTEMBOOKMARK.ZPATHRELATIVETOVOLUME
            FROM {asset_table} 
            JOIN ZINTERNALRESOURCE ON ZINTERNALRESOURCE.ZASSET = ZADDITIONALASSETATTRIBUTES.ZASSET
            JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK 
            JOIN ZFILESYSTEMBOOKMARK ON ZFILESYSTEMBOOKMARK.ZRESOURCE = ZINTERNALRESOURCE.Z_PK
            JOIN ZFILESYSTEMVOLUME ON ZFILESYSTEMVOLUME.Z_PK = ZINTERNALRESOURCE.ZFILESYSTEMVOLUME
            WHERE ZINTERNALRESOURCE.ZDATASTORESUBTYPE = 17
            """
        )

        # path to the raw image will be /Volumes/ZFILESYSTEMVOLUME.ZNAME/ZFILESYSTEMBOOKMARK.ZPATHRELATIVETOVOLUME
        # 0: {asset_table}.ZUUID, -- UUID
        # 1: ZFILESYSTEMVOLUME.ZNAME, -- name of the volume
        # 2: ZFILESYSTEMBOOKMARK.ZPATHRELATIVETOVOLUME -- path to the raw image

        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["raw_volume"] = row[1]
                self._dbphotos[uuid]["raw_relative_path"] = row[2]

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

        # process face info
        verbose("Processing face details.")
        self._process_faceinfo()

        # process search info
        verbose("Processing photo labels.")
        self._process_searchinfo()

        # process exif info
        verbose("Processing EXIF details.")
        self._process_exifinfo()

        # process computed scores
        verbose("Processing computed aesthetic scores.")
        self._process_scoreinfo()

        # process shared comments/likes
        verbose("Processing comments and likes for shared photos.")
        self._process_comments()

        # process moments
        verbose("Processing moments.")
        self._process_moments()

        if self.photos_version >= 7:
            verbose("Processing syndication info.")
            self._process_syndicationinfo()

        if self.photos_version >= 8:
            verbose("Processing shared iCloud library info")
            self._process_shared_library_info()

        verbose("Done processing details from Photos library.")

    def _process_moments(self):
        """Process data from ZMOMENT table"""
        # _db_moment_pk is dict in form {pk: {moment info}} by ZMOMENT.Z_PK

        if self._db_version <= _PHOTOS_4_VERSION:
            raise NotImplementedError(
                f"Moment info implemented for this database version"
            )
        else:
            self._process_moment_5()

    def _process_moment_5(self):
        """Process moment info for Photos 5 databases"""

        self._db_moment_pk = {}

        results = self.execute(
            f"""
            SELECT 
            Z_PK,
            ZTIMEZONEOFFSET,
            ZTRASHEDSTATE,
            ZAPPROXIMATELATITUDE,
            ZAPPROXIMATELONGITUDE,
            ZENDDATE,
            ZMODIFICATIONDATE,
            ZREPRESENTATIVEDATE,
            ZSTARTDATE,
            ZSUBTITLE,
            ZTITLE,
            ZUUID
            FROM ZMOMENT"""
        )

        # results
        # 0  Z_PK,
        # 1  ZTIMEZONEOFFSET,
        # 2  ZTRASHEDSTATE,
        # 3  ZAPPROXIMATELATITUDE,
        # 4  ZAPPROXIMATELONGITUDE,
        # 5  ZENDDATE,
        # 6  ZMODIFICATIONDATE,
        # 7  ZREPRESENTATIVEDATE,
        # 8  ZSTARTDATE,
        # 9  ZSUBTITLE,
        # 10 ZTITLE,
        # 11 ZUUID

        for row in results:
            moment_info = {}
            moment_info["pk"] = row[0]
            moment_info["timezoneOffset"] = row[1]
            moment_info["trashedState"] = row[2]
            moment_info["approximateLatitude"] = row[3]
            moment_info["approximateLongitude"] = row[4]
            moment_info["endDate"] = row[5]
            moment_info["modificationDate"] = row[6]
            moment_info["representativeDate"] = row[7]
            moment_info["startDate"] = row[8]
            moment_info["subtitle"] = normalize_unicode(row[9])
            moment_info["title"] = normalize_unicode(row[10])
            moment_info["uuid"] = row[11]

            # if both lat/lon == -180, then it means location undefined
            if (
                moment_info["approximateLatitude"] == -180.0
                and moment_info["approximateLongitude"] == -180.0
            ):
                moment_info["latitude"] = None
                moment_info["longitude"] = None
            else:
                moment_info["latitude"] = moment_info["approximateLatitude"]
                moment_info["longitude"] = moment_info["approximateLongitude"]

            # process date stamps
            offset_seconds = moment_info["timezoneOffset"] or 0
            delta = timedelta(seconds=offset_seconds)
            tz = timezone(delta)
            for date_name in [
                "startDate",
                "endDate",
                "modificationDate",
                "representativeDate",
            ]:
                date_stamp = moment_info[date_name]
                try:
                    moment_date = datetime.fromtimestamp(date_stamp + TIME_DELTA)
                    # save raw time stamp valu
                    moment_info[date_name + "_timestamp"] = moment_info[date_name]
                    moment_info[date_name] = moment_date.astimezone(tz=tz)
                except (ValueError, TypeError):
                    # sometimes imageDate is invalid or null so use 1 Jan 1970 in UTC as image date
                    moment_date = datetime(1970, 1, 1)
                    tz = timezone(timedelta(0))
                    moment_info[date_name + "_timestamp"] = date_stamp
                    moment_info[date_name] = moment_date.astimezone(tz=tz)

            # process title/subtitle
            # use unicodedata.normalize with KFKC instead of normalize_unicode as is done elsewhere
            # to replace non-breaking whitespace chars with spaces as Photos uses \xa0 as space in Moment titles, subtitles
            moment_info["title"] = (
                normalize("NFKC", moment_info["title"]) if moment_info["title"] else ""
            )
            moment_info["subtitle"] = (
                normalize("NFKC", moment_info["subtitle"])
                if moment_info["subtitle"]
                else ""
            )

            self._db_moment_pk[moment_info["pk"]] = moment_info

    def _build_album_folder_hierarchy_5(self, uuid, folders=None):
        """Recursively build folder/album hierarchy
        uuid: uuid of the album/folder being processed
        folders: dict holding the folder hierarchy"""

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
        """Return appropriate album_folder_hierarchy_list for the _db_version"""
        if self._db_version <= _PHOTOS_4_VERSION:
            return self._album_folder_hierarchy_list_4(album_uuid)
        else:
            return self._album_folder_hierarchy_list_5(album_uuid)

    def _album_folder_hierarchy_list_4(self, album_uuid):
        """Return hierarchical list of folder names album_uuid is contained in
        the folder list is in form:
        ["Top level folder", "sub folder 1", "sub folder 2"]
        returns empty list of album is not in any folders"""
        try:
            folders = self._dbalbum_folders[album_uuid]
        except KeyError:
            logger.debug(f"Caught _dbalbum_folders KeyError for album: {album_uuid}")
            return []

        def _recurse_folder_hierarchy(folders, hierarchy=[]):
            """Recursively walk the folders dict to build list of folder hierarchy"""
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
        """Return hierarchical list of folder names album_uuid is contained in
        the folder list is in form:
        ["Top level folder", "sub folder 1", "sub folder 2"]
        returns empty list of album is not in any folders"""
        try:
            folders = self._dbalbum_folders[album_uuid]
        except KeyError:
            logger.debug(f"Caught _dbalbum_folders KeyError for album: {album_uuid}")
            return []

        def _recurse_folder_hierarchy(folders, hierarchy=[]):
            """Recursively walk the folders dict to build list of folder hierarchy"""

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
        """Return hierarchical list of FolderInfo objects album_uuid is contained in
        ["Top level folder", "sub folder 1", "sub folder 2"]
        returns empty list of album is not in any folders"""
        # title = photosdb._dbalbum_details[album_uuid]["title"]
        folders = self._dbalbum_folders[album_uuid]
        # logging.warning(f"uuid = {album_uuid}, folder = {folders}")

        def _recurse_folder_hierarchy(folders, hierarchy=[]):
            """Recursively walk the folders dict to build list of folder hierarchy"""
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
        """Return hierarchical list of FolderInfo objects album_uuid is contained in
        ["Top level folder", "sub folder 1", "sub folder 2"]
        returns empty list of album is not in any folders"""
        # title = photosdb._dbalbum_details[album_uuid]["title"]
        folders = self._dbalbum_folders[album_uuid]

        def _recurse_folder_hierarchy(folders, hierarchy=[]):
            """Recursively walk the folders dict to build list of folder hierarchy"""

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

    def _get_album_uuids(self, shared=False, import_session=False, project=False):
        """Return list of album UUIDs found in photos database

            Filters out albums in the trash and any special album types

        Args:
            shared: boolean; if True, returns shared albums, else normal albums
            import_session: boolean, if True, returns import session albums, else normal or shared albums
            project: boolean, if True, returns albums that are part of My Projects
            Note: flags (shared, import_session) are mutually exclusive


        Raises:
            ValueError: raised if mutually exclusive flags passed

        Returns: list of album UUIDs
        """
        if sum(bool(x) for x in [shared, import_session, project]) > 1:
            raise ValueError(
                "flags are mutually exclusive: pass zero or one of shared, import_session, projects"
            )

        if self._db_version <= _PHOTOS_4_VERSION:
            if shared:
                logging.warning(
                    f"Shared albums not implemented for Photos library version {self._db_version}"
                )
                return []  # not implemented for _PHOTOS_4_VERSION
            elif import_session:
                logging.warning(
                    f"Import sessions not implemented for Photos library version {self._db_version}"
                )
                return []  # not implemented for _PHOTOS_4_VERSION
            elif project:
                album_type = [
                    _PHOTOS_4_ALBUM_TYPE_PROJECT,
                    _PHOTOS_4_ALBUM_TYPE_SLIDESHOW,
                ]
                album_kind = _PHOTOS_4_ALBUM_KIND
            else:
                album_type = [_PHOTOS_4_ALBUM_TYPE_ALBUM]
                album_kind = _PHOTOS_4_ALBUM_KIND

            album_list = []
            # look through _dbalbum_details because _dbalbums_album won't have empty albums it
            for album, detail in self._dbalbum_details.items():
                if (
                    detail["kind"] == album_kind
                    and detail["albumType"] in album_type
                    and not detail["intrash"]
                    and (
                        (shared and detail["cloudownerhashedpersonid"] is not None)
                        or (not shared and detail["cloudownerhashedpersonid"] is None)
                    )
                    and detail["folderUuid"] != _PHOTOS_4_ROOT_FOLDER
                    # in Photos <= 4, special albums like "printAlbum" have kind _PHOTOS_4_ALBUM_KIND
                    # but should not be listed here; they can be distinguished by looking
                    # for folderUuid of _PHOTOS_4_ROOT_FOLDER as opposed to _PHOTOS_4_TOP_LEVEL_ALBUM
                ):
                    album_list.append(album)
            return album_list

        # Photos version 5+
        if shared:
            album_kind = _PHOTOS_5_SHARED_ALBUM_KIND
        elif import_session:
            album_kind = _PHOTOS_5_IMPORT_SESSION_ALBUM_KIND
        elif project:
            album_kind = _PHOTOS_5_PROJECT_ALBUM_KIND
        else:
            album_kind = _PHOTOS_5_ALBUM_KIND

        album_list = []
        # look through _dbalbum_details because _dbalbums_album won't have empty albums it
        for album, detail in self._dbalbum_details.items():
            if (
                detail["kind"] == album_kind
                and not detail["intrash"]
                and (
                    (shared and detail["cloudownerhashedpersonid"] is not None)
                    or (not shared and detail["cloudownerhashedpersonid"] is None)
                )
            ):
                album_list.append(album)
        return album_list

    def _get_albums(self, shared=False):
        """Return list of album titles found in photos database
            Albums may have duplicate titles -- these will be treated as a single album.

            Filters out albums in the trash and any special album types

        Args:
            shared: boolean; if True, returns shared albums, else normal albums

        Returns: list of album names
        """

        album_uuids = self._get_album_uuids(shared=shared)
        return list({self._dbalbum_details[album]["title"] for album in album_uuids})

    def photos(
        self,
        keywords: Optional[List[str]] = None,
        uuid: Optional[List[str]] = None,
        persons: Optional[List[str]] = None,
        albums: Optional[List[str]] = None,
        images: bool = True,
        movies: bool = True,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        intrash: bool = False,
    ) -> List[PhotoInfo]:
        """Return a list of PhotoInfo objects
        If called with no args, returns the entire database of photos
        If called with args, returns photos matching the args (e.g. keywords, persons, etc.)
        If more than one arg, returns photos matching all the criteria (e.g. keywords AND persons)
        If more than one keyword, uuid, persons, albums is passed, they are treated as "OR" criteria
        e.g. keywords=["wedding","vacation"] returns photos matching either keyword
        from_date and to_date may be either naive or timezone-aware datetime.datetime objects.
        If naive, timezone will be assumed to be local timezone.

        Args:
            keywords: list of keywords to search for
            uuid: list of UUIDs to search for
            persons: list of persons to search for
            albums: list of album names to search for
            images: if True, returns image files, if False, does not return images; default is True
            movies: if True, returns movie files, if False, does not return movies; default is True
            from_date: return photos with creation date >= from_date (datetime.datetime object, default None)
            to_date: return photos with creation date < to_date (datetime.datetime object, default None)
            intrash: if True, returns only images in "Recently deleted items" folder,
                     if False returns only photos that aren't deleted; default is False

        Returns:
            list of PhotoInfo objects
        """

        # implementation is a bit kludgy but it works
        # build a set of each search argument then compute the intersection of the sets
        # use results to build a list of PhotoInfo objects

        photos_sets = []  # list of photo sets to perform intersection of
        if intrash:
            photos_sets.append(
                {p for p in self._dbphotos if self._dbphotos[p]["intrash"]}
            )
        else:
            photos_sets.append(
                {p for p in self._dbphotos if not self._dbphotos[p]["intrash"]}
            )

        if not any([keywords, uuid, persons, albums, from_date, to_date]):
            # return all the photos, filtering for images and movies
            # append keys of all photos as a single set to photos_sets
            photos_sets.append(set(self._dbphotos.keys()))
        else:
            if albums:
                album_set = set()
                for album in albums:
                    # glob together albums with same name
                    if album in self._dbalbum_titles:
                        title_set = set()
                        for album_id in self._dbalbum_titles[album]:
                            try:
                                # _dbalbums_album value is list of tuples: [(uuid, sort order)]
                                uuid_in_album, _ = zip(*self._dbalbums_album[album_id])
                                title_set.update(uuid_in_album)
                            except KeyError:
                                # an empty album will be in _dbalbum_titles but not _dbalbums_album
                                pass
                        album_set.update(title_set)
                photos_sets.append(album_set)

            if uuid:
                uuid_set = set()
                for u in uuid:
                    if u in self._dbphotos:
                        uuid_set.update([u])
                photos_sets.append(uuid_set)

            if keywords:
                keyword_set = set()
                for keyword in keywords:
                    keyword = normalize_unicode(keyword)
                    if keyword in self._dbkeywords_keyword:
                        keyword_set.update(self._dbkeywords_keyword[keyword])
                photos_sets.append(keyword_set)

            if persons:
                person_set = set()
                for person in persons:
                    person = normalize_unicode(person)
                    if person in self._dbpersons_fullname:
                        for pk in self._dbpersons_fullname[person]:
                            try:
                                person_set.update(self._dbfaces_pk[pk])
                            except KeyError:
                                # some persons have zero photos so they won't be in _dbfaces_pk
                                pass
                photos_sets.append(person_set)

            if from_date or to_date:  # sourcery off
                dsel = self._dbphotos
                if from_date:
                    if not datetime_has_tz(from_date):
                        from_date = datetime_naive_to_local(from_date)
                    dsel = {
                        k: v for k, v in dsel.items() if v["imageDate"] >= from_date
                    }
                if to_date:
                    if not datetime_has_tz(to_date):
                        to_date = datetime_naive_to_local(to_date)
                    dsel = {k: v for k, v in dsel.items() if v["imageDate"] < to_date}
                photos_sets.append(set(dsel.keys()))

        photoinfo = []
        if photos_sets:  # found some photos
            # get the intersection of each argument/search criteria
            for p in set.intersection(*photos_sets):
                # filter for non-selected burst photos
                if self._dbphotos[p]["burst"] and not (
                    self._dbphotos[p]["burstPickType"] & BURST_SELECTED
                    or self._dbphotos[p]["burstPickType"] & BURST_KEY
                    or self._dbphotos[p]["burstPickType"] == BURST_PICK_TYPE_NONE
                ):
                    # not a key/selected burst photo, don't include in returned results
                    continue

                # filter for images and/or movies
                if (images and self._dbphotos[p]["type"] == _PHOTO_TYPE) or (
                    movies and self._dbphotos[p]["type"] == _MOVIE_TYPE
                ):
                    info = PhotoInfo(db=self, uuid=p, info=self._dbphotos[p])
                    photoinfo.append(info)

        return photoinfo

    def get_photo(self, uuid):
        """Returns a single photo matching uuid

        Arguments:
            uuid: the UUID of photo to get

        Returns:
            PhotoInfo instance for photo with UUID matching uuid or None if no match
        """
        try:
            return PhotoInfo(db=self, uuid=uuid, info=self._dbphotos[uuid])
        except KeyError:
            return None

    def photos_by_uuid(self, uuids):
        """Returns a list of photos with UUID in uuids.
            Does not generate error if invalid or missing UUID passed.
            This is faster than using PhotosDB.photos if you have list of UUIDs.
            Returns photos regardless of intrash state.

        Arguments:
            uuid: list of UUIDs of photos to get

        Returns:
            list of PhotoInfo instance for photo with UUID matching uuid or [] if no match
        """
        return [
            PhotoInfo(db=self, uuid=uuid, info=self._dbphotos[uuid])
            for uuid in uuids
            if uuid in self._dbphotos
        ]

    def query(self, options: QueryOptions) -> list[PhotoInfo]:
        """Run a query against PhotosDB to extract the photos based on user supplied options

        Args:
            options: a QueryOptions instance
        """
        return photo_query(self, options)

    def execute(self, sql: str, params: Any | None = None) -> sqlite3.Cursor:
        """Execute sql statement and return cursor"""
        self._db_connection, _ = self.get_db_connection()
        params = params or ()
        return self._db_connection.cursor().execute(sql, params)

    def _duplicate_signature(self, uuid):
        """Compute a signature for finding possible duplicates"""
        return (
            self._dbphotos[uuid]["original_filesize"],
            self._dbphotos[uuid]["imageDate"],
            self._dbphotos[uuid]["height"],
            self._dbphotos[uuid]["width"],
            self._dbphotos[uuid]["UTI"],
            self._dbphotos[uuid]["hasAdjustments"],
        )

    def __repr__(self):
        return f"osxphotos.{self.__class__.__name__}(dbfile='{self.db_path}')"

    # compare two PhotosDB objects for equality
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__

        return False

    def __len__(self):
        """Returns number of photos in the database
        Includes recently deleted photos and non-selected burst images
        """
        return len(self._dbphotos)

    def __del__(self):
        if getattr(self, "_db_connection", None):
            self._db_connection.close()
