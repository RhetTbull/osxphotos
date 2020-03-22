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

from ._constants import (
    _MOVIE_TYPE,
    _PHOTO_TYPE,
    _PHOTOS_3_VERSION,
    _PHOTOS_5_VERSION,
    _TESTED_DB_VERSIONS,
    _TESTED_OS_VERSIONS,
    _UNKNOWN_PERSON,
)
from ._version import __version__
from .photoinfo import PhotoInfo
from .utils import (
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
# TODO: fix "if X not in y" dictionary checks to use try/except EAFP style


class PhotosDB:
    """ Processes a Photos.app library database to extract information about photos """

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
        if int(self._db_version) >= int(_PHOTOS_5_VERSION):
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
        if int(self._db_version) < int(_PHOTOS_5_VERSION):
            masters_path = os.path.join(library_path, "Masters")
            self._masters_path = masters_path
        else:
            masters_path = os.path.join(library_path, "originals")
            self._masters_path = masters_path

        if _debug():
            logging.debug(f"library = {library_path}, masters = {masters_path}")

        if int(self._db_version) < int(_PHOTOS_5_VERSION):
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
        if self._db_version < _PHOTOS_5_VERSION:
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
    def albums(self):
        """ return list of albums found in photos database """

        # Could be more than one album with same name
        # Right now, they are treated as same album and photos are combined from albums with same name

        albums = set()
        album_keys = [
            k
            for k in self._dbalbums_album.keys()
            if self._dbalbum_details[k]["cloudownerhashedpersonid"] is None
        ]
        for album in album_keys:
            albums.add(self._dbalbum_details[album]["title"])
        return list(albums)

    @property
    def albums_shared(self):
        """ return list of shared albums found in photos database
            only valid for Photos 5; on Photos <= 4, prints warning and returns empty list """

        # Could be more than one album with same name
        # Right now, they are treated as same album and photos are combined from albums with same name

        # if _dbalbum_details[key]["cloudownerhashedpersonid"] is not None, then it's a shared album

        if self._db_version < _PHOTOS_5_VERSION:
            logging.warning(
                f"albums_shared not implemented for Photos versions < {_PHOTOS_5_VERSION}"
            )
            return []

        albums = set()
        album_keys = [
            k
            for k in self._dbalbums_album.keys()
            if self._dbalbum_details[k]["cloudownerhashedpersonid"] is not None
        ]
        for album in album_keys:
            albums.add(self._dbalbum_details[album]["title"])
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

    # def _open_sql_file(self, fname):
    #     """ opens sqlite file fname in read-only mode
    #         returns tuple of (connection, cursor) """
    #     try:
    #         conn = sqlite3.connect(
    #             f"{pathlib.Path(fname).as_uri()}?mode=ro", timeout=1, uri=True
    #         )
    #         c = conn.cursor()
    #     except sqlite3.Error as e:
    #         sys.exit(f"An error occurred opening sqlite file: {e.args[0]} {fname}")
    #     return (conn, c)

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

        # TODO: Update strings to remove + (not needed)
        # Epoch is Jan 1, 2001
        td = (datetime(2001, 1, 1, 0, 0) - datetime(1970, 1, 1, 0, 0)).total_seconds()

        (conn, c) = _open_sql_file(self._tmp_db)

        # Look for all combinations of persons and pictures
        c.execute(
            "select RKPerson.name, RKVersion.uuid from RKFace, RKPerson, RKVersion, RKMaster "
            + "where RKFace.personID = RKperson.modelID and RKVersion.modelId = RKFace.ImageModelId "
            + "and RKVersion.masterUuid = RKMaster.uuid and "
            + "RKVersion.filename not like '%.pdf' and RKVersion.isInTrash = 0"
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
            "select RKAlbum.uuid, RKVersion.uuid from RKAlbum, RKVersion, RKAlbumVersion "
            + "where RKAlbum.modelID = RKAlbumVersion.albumId and "
            + "RKAlbumVersion.versionID = RKVersion.modelId and "
            + "RKVersion.filename not like '%.pdf' and RKVersion.isInTrash = 0"
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
            "SELECT "
            "uuid, "  # 0
            "name, "  # 1
            "cloudLibraryState, "  # 2
            "cloudIdentifier "  # 3
            "FROM RKAlbum "
            "WHERE isInTrash = 0"
        )

        for album in c:
            self._dbalbum_details[album[0]] = {
                "title": album[1],
                "cloudlibrarystate": album[2],
                "cloudidentifier": album[3],
                "cloudlocalstate": None,  # Photos 5
                "cloudownerfirstname": None,  # Photos 5
                "cloudownderlastname": None,  # Photos 5
                "cloudownerhashedpersonid": None,  # Photos 5
            }

        if _debug():
            logging.debug(f"Finished walking through albums")
            logging.debug(pformat(self._dbalbums_album))
            logging.debug(pformat(self._dbalbums_uuid))
            logging.debug(pformat(self._dbalbum_details))

        # Get info on keywords
        c.execute(
            "select RKKeyword.name, RKVersion.uuid, RKMaster.uuid from "
            + "RKKeyword, RKKeywordForVersion, RKVersion, RKMaster "
            + "where RKKeyword.modelId = RKKeyWordForVersion.keywordID and "
            + "RKVersion.modelID = RKKeywordForVersion.versionID "
            + "and RKMaster.uuid = RKVersion.masterUuid "
            + "and RKVersion.filename not like '%.pdf' and RKVersion.isInTrash = 0"
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
                    RKVersion.specialType, RKMaster.modelID, RKVersion.momentUuid
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
                    RKVersion.momentUuid
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
            if self._db_version >= _PHOTOS_3_VERSION:
                self._dbphotos[uuid]["selfie"] = True if row[27] == 1 else False
                self._dbphotos[uuid]["momentID"] = row[28]
            else:
                self._dbphotos[uuid]["selfie"] = None
                self._dbphotos[uuid]["momentID"] = row[27]

            # Init cloud details that will be filled in later if cloud asset
            self._dbphotos[uuid]["cloudAssetGUID"] = None  # Photos 5
            self._dbphotos[uuid]["cloudLocalState"] = None  # Photos 5
            self._dbphotos[uuid]["cloudLibraryState"] = None
            self._dbphotos[uuid]["cloudStatus"] = None
            self._dbphotos[uuid]["cloudAvailable"] = None
            self._dbphotos[uuid]["incloud"] = None

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
            "SELECT RKVersion.uuid, "
            "RKVersion.adjustmentUuid, "
            "RKAdjustmentData.originator, "
            "RKAdjustmentData.format "
            "FROM RKVersion, RKAdjustmentData "
            "WHERE RKVersion.adjustmentUuid = RKAdjustmentData.uuid "
            "AND RKVersion.isInTrash = 0"
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

        # save existing row_factory
        old_row_factory = c.row_factory

        # want only the list of values, not a list of tuples
        c.row_factory = lambda cursor, row: row[0]

        for uuid in self._dbphotos:
            # get placeId which is then used to lookup defaultName
            place_ids = c.execute(
                "SELECT placeId "
                "FROM RKPlaceForVersion "
                f"WHERE versionId = '{self._dbphotos[uuid]['modelID']}'"
            ).fetchall()
            self._dbphotos[uuid]["placeIDs"] = place_ids
            country_code = [countries[x] for x in place_ids if x in countries]
            if len(country_code) > 1:
                logging.warning(f"Found more than one country code for uuid: {uuid}")

            if country_code:
                self._dbphotos[uuid]["countryCode"] = country_code[0]
            else:
                self._dbphotos[uuid]["countryCode"] = None

            place_names = c.execute(
                "SELECT DISTINCT defaultName AS name "
                "FROM RKPlace "
                f"WHERE modelId IN({','.join(map(str,place_ids))}) "
                "ORDER BY area ASC "
            ).fetchall()

            self._dbphotos[uuid]["placeNames"] = place_names
            self._dbphotos[uuid]["reverse_geolocation"] = None  # Photos 5

        # restore row_factory
        c.row_factory = old_row_factory

        # build album_titles dictionary
        for album_id in self._dbalbum_details:
            title = self._dbalbum_details[album_id]["title"]
            if title in self._dbalbum_titles:
                self._dbalbum_titles[title].append(album_id)
            else:
                self._dbalbum_titles[title] = [album_id]

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

        c.execute(
            "SELECT ZGENERICALBUM.ZUUID, ZGENERICASSET.ZUUID "
            "FROM ZGENERICASSET "
            "JOIN Z_26ASSETS ON Z_26ASSETS.Z_34ASSETS = ZGENERICASSET.Z_PK "
            "JOIN ZGENERICALBUM ON ZGENERICALBUM.Z_PK = Z_26ASSETS.Z_26ALBUMS "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 "
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
            "SELECT "
            "ZUUID, "  # 0
            "ZTITLE, "  # 1
            "ZCLOUDLOCALSTATE, "  # 2
            "ZCLOUDOWNERFIRSTNAME, "  # 3
            "ZCLOUDOWNERLASTNAME, "  # 4
            "ZCLOUDOWNERHASHEDPERSONID "  # 5
            "FROM ZGENERICALBUM"
        )
        for album in c:
            self._dbalbum_details[album[0]] = {
                "title": album[1],
                "cloudlocalstate": album[2],
                "cloudownerfirstname": album[3],
                "cloudownderlastname": album[4],
                "cloudownerhashedpersonid": album[5],
                "cloudlibrarystate": None,  # Photos 4
                "cloudidentifier": None,  # Photos4
            }

        if _debug():
            logging.debug(f"Finished walking through albums")
            logging.debug(pformat(self._dbalbums_album))
            logging.debug(pformat(self._dbalbums_uuid))
            logging.debug(pformat(self._dbalbum_details))

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
                ZGENERICASSET.ZMOMENT
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

            info["imageDate"] = datetime.fromtimestamp(row[5] + td)
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

    def _process_database5X(self):
        """ ALPHA: TESTING using SimpleNamespace to clean up code for info, DO NOT CALL THIS METHOD """
        """ Needs to be updated for changes in process_database5 due to adding PlaceInfo """
        """ process the Photos database to extract info """
        """ works on Photos version >= 5.0 """

        if _debug():
            logging.debug(f"_process_database5X")

        from types import SimpleNamespace

        _DB_FIELD_NAMES = [
            "adjustment_format_id",
            "adjustment_uuid",
            "albums",
            "burst_key",
            "burst_pick_type",
            "burst_uuid",
            "burst",
            "cloud_asset_guid",
            "cloud_available",
            "cloud_batch_publish_date",
            "cloud_library_state",
            "cloud_local_state",
            "cloud_status",
            "custom_rendered_value",
            "directory",
            "extended_description",
            "favorite",
            "filename",
            "has_adjustments",
            "has_albums",
            "has_keywords",
            "has_persons",
            "hdr",
            "hidden",
            "image_date",
            "image_tz_offset_seconds",
            "in_cloud",
            "is_missing",
            "keywords",
            "last_modified_date",
            "latitude",
            "live_photo",
            "local_availability",
            "longitude",
            "master_fingerprint",
            "master_uuid",
            "model_id",
            "name",
            "original_filename",
            "panorama",
            "portrait",
            "remote_availability",
            "screenshot",
            "selfie",
            "shared",
            "slow_mo",
            "subtype",
            "time_lapse",
            "title",
            "type",
            "uti",
            "uuid",
        ]
        _DB_FIELDS = {field: None for field in _DB_FIELD_NAMES}

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

        c.execute(
            "SELECT ZGENERICALBUM.ZUUID, ZGENERICASSET.ZUUID "
            "FROM ZGENERICASSET "
            "JOIN Z_26ASSETS ON Z_26ASSETS.Z_34ASSETS = ZGENERICASSET.Z_PK "
            "JOIN ZGENERICALBUM ON ZGENERICALBUM.Z_PK = Z_26ASSETS.Z_26ALBUMS "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 "
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
            "SELECT "
            "ZUUID, "  # 0
            "ZTITLE, "  # 1
            "ZCLOUDLOCALSTATE, "  # 2
            "ZCLOUDOWNERFIRSTNAME, "  # 3
            "ZCLOUDOWNERLASTNAME, "  # 4
            "ZCLOUDOWNERHASHEDPERSONID "  # 5
            "FROM ZGENERICALBUM"
        )
        for album in c:
            self._dbalbum_details[album[0]] = {
                "title": album[1],
                "cloudlocalstate": album[2],
                "cloudownerfirstname": album[3],
                "cloudownderlastname": album[4],
                "cloudownerhashedpersonid": album[5],
                "cloudlibrarystate": None,  # Photos 4
                "cloudidentifier": None,  # Photos4
            }

        if _debug():
            logging.debug(f"Finished walking through albums")
            logging.debug(pformat(self._dbalbums_album))
            logging.debug(pformat(self._dbalbums_uuid))
            logging.debug(pformat(self._dbalbum_details))

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
                ZGENERICASSET.ZCLOUDASSETGUID
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
        # 25   ZGENERICASSET.ZCLOUDASSETGUID  -- not null if asset is cloud asset
        #       (e.g. user has "iCloud Photos" checked in Photos preferences)

        for row in c:
            info = SimpleNamespace(**_DB_FIELDS)
            info.uuid = uuid = row[0]  # stored here for easier debugging
            info.master_fingerprint = row[1]
            info.title = info.name = row[2]  # TODO: replace all uses of name with title

            # There are sometimes negative values for lastmodifieddate in the database
            # I don't know what these mean but they will raise exception in datetime if
            # not accounted for
            if row[4] is not None and row[4] >= 0:
                info.last_modified_date = datetime.fromtimestamp(row[4] + td)
            else:
                info.last_modified_dat = None

            info.image_date = datetime.fromtimestamp(row[5] + td)
            info.image_tz_offset_seconds = row[6]
            info.hidden = row[9]
            info.favorite = row[10]
            info.original_filename = row[3]
            info.filename = row[12]
            info.directory = row[11]

            # set latitude and longitude
            # if both latitude and longitude = -180.0, then they are NULL
            if row[13] == -180.0 and row[14] == -180.0:
                info.latitude = None
                info.longitude = None
            else:
                info.latitude = row[13]
                info.longitude = row[14]

            info.has_adjustments = row[15]

            info.cloud_batch_publish_date = row[16]
            info.shared = True if row[16] is not None else False

            # these will get filled in later
            # init to avoid key errors
            # info.extended_description = None  # fill this in later
            # info.local_availability = None
            # info.remote_availability = None
            # info.is_missing = None
            # info.has_adjustments = None
            # info.adjustment_format_id = None

            # find type
            if row[17] == 0:
                info.type = _PHOTO_TYPE
            elif row[17] == 1:
                info.type = _MOVIE_TYPE
            else:
                if _debug():
                    logging.debug(f"WARNING: {uuid} found unknown type {row[17]}")
                info.type = None

            info.uti = row[18]

            # handle burst photos
            # if burst photo, determine whether or not it's a selected burst photo
            # in Photos 5, burstUUID is called avalancheUUID
            info.burst_uuid = row[19]  # avalancheUUID
            info.burst_pick_type = row[20]  # avalanchePickType
            if row[19] is not None:
                # it's a burst photo
                info.burst = True
                burst_uuid = row[19]
                if burst_uuid not in self._dbphotos_burst:
                    self._dbphotos_burst[burst_uuid] = set()
                self._dbphotos_burst[burst_uuid].add(uuid)
                if row[20] != 2 and row[20] != 4:
                    info.burst_key = True  # it's a key photo (selected from the burst)
                else:
                    info.burst_key = (
                        False  # it's a burst photo but not one that's selected
                    )
            else:
                # not a burst photo
                info.burst = False
                info.burst_key = None

            # Info on sub-type (live photo, panorama, etc)
            # ZGENERICASSET.ZKINDSUBTYPE
            # 1 == panorama
            # 2 == live photo
            # 10 = screenshot
            # 100 = shared movie (MP4) ??
            # 101 = slow-motion video
            # 102 = Time lapse video
            info.subtype = row[21]
            info.live_photo = True if row[21] == 2 else False
            info.screenshot = True if row[21] == 10 else False
            info.slow_mo = True if row[21] == 101 else False
            info.time_lapse = True if row[21] == 102 else False

            # Handle HDR photos and portraits
            # ZGENERICASSET.ZCUSTOMRENDEREDVALUE
            # 3 = HDR photo
            # 4 = non-HDR version of the photo
            # 6 = panorama
            # 8 = portrait
            info.custom_rendered_value = row[22]
            info.hdr = True if row[22] == 3 else False
            info.portrait = True if row[22] == 8 else False

            # Set panorama from either KindSubType or RenderedValue
            info.panorama = True if row[21] == 1 or row[22] == 6 else False

            # Handle selfies (front facing camera, ZCAMERACAPTUREDEVICE=1)
            info.selfie = True if row[23] == 1 else False

            # Determine if photo is part of cloud library (ZGENERICASSET.ZCLOUDASSETGUID not NULL)
            # Initialize cloud fields that will filled in later
            info.cloud_asset_guid = row[24]
            info.cloud_local_state = None
            info.in_cloud = None
            info.cloud_library_state = None  # Photos 4
            info.cloud_status = None  # Photos 4
            info.cloud_available = None  # Photos 4

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
                self._dbphotos[uuid].extended_description = row[1]
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
                self._dbphotos[uuid].adjustment_format_id = row[2]
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
                self._dbphotos[uuid].local_availability = row[1]
                self._dbphotos[uuid].remote_availability = row[2]

                # old = self._dbphotos[uuid]["isMissing"]

                if row[1] != 1:
                    self._dbphotos[uuid].is_missing = 1
                else:
                    self._dbphotos[uuid].is_missing = 0

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
                self._dbphotos[uuid].local_availability = row[1]
                self._dbphotos[uuid].remote_availability = row[2]

                # old = self._dbphotos[uuid]["isMissing"]

                if row[1] != 1:
                    self._dbphotos[uuid].is_missing = 1
                else:
                    self._dbphotos[uuid].is_missing = 0

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
                self._dbphotos[uuid].cloud_local_state = row[1]
                self._dbphotos[uuid].in_cloud = True if row[1] == 3 else False

        # add faces and keywords to photo data
        for uuid in self._dbphotos:
            # keywords
            if uuid in self._dbkeywords_uuid:
                self._dbphotos[uuid].has_keywords = 1
                self._dbphotos[uuid].keywords = self._dbkeywords_uuid[uuid]
            else:
                self._dbphotos[uuid].has_keywords = 0
                self._dbphotos[uuid].keywords = []

            if uuid in self._dbfaces_uuid:
                self._dbphotos[uuid].has_persons = 1
                self._dbphotos[uuid].persons = self._dbfaces_uuid[uuid]
            else:
                self._dbphotos[uuid].has_persons = 0
                self._dbphotos[uuid].persons = []

            if uuid in self._dbalbums_uuid:
                self._dbphotos[uuid].has_albums = 1
                self._dbphotos[uuid].albums = self._dbalbums_uuid[uuid]
            else:
                self._dbphotos[uuid].has_albums = 0
                self._dbphotos[uuid].albums = []

        # build album_titles dictionary
        for album_id in self._dbalbum_details:
            title = self._dbalbum_details[album_id]["title"]
            if title in self._dbalbum_titles:
                self._dbalbum_titles[title].append(album_id)
            else:
                self._dbalbum_titles[title] = [album_id]

        # close connection and remove temporary files
        conn.close()

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
                for album in albums:
                    # TODO: can have >1 album with same name. This globs them together.
                    # Need a way to select which album?
                    if album in self._dbalbum_titles:
                        album_set = set()
                        for album_id in self._dbalbum_titles[album]:
                            album_set.update(self._dbalbums_album[album_id])
                        photos_sets.append(album_set)
                    else:
                        logging.debug(f"Could not find album '{album}' in database")

            if uuid:
                for u in uuid:
                    if u in self._dbphotos:
                        photos_sets.append(set([u]))
                    else:
                        logging.debug(f"Could not find uuid '{u}' in database")

            if keywords:
                for keyword in keywords:
                    if keyword in self._dbkeywords_keyword:
                        photos_sets.append(set(self._dbkeywords_keyword[keyword]))
                    else:
                        logging.debug(f"Could not find keyword '{keyword}' in database")

            if persons:
                for person in persons:
                    if person in self._dbfaces_person:
                        photos_sets.append(set(self._dbfaces_person[person]))
                    else:
                        logging.debug(f"Could not find person '{person}' in database")

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
