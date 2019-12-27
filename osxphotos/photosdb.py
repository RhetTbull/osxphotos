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
    _PHOTOS_5_VERSION,
    _TESTED_DB_VERSIONS,
    _TESTED_OS_VERSIONS,
    _UNKNOWN_PERSON,
)
from ._version import __version__
from .photoinfo import PhotoInfo
from .utils import _check_file_exists, _get_os_version, get_last_library_path

# TODO: find edited photos: see https://github.com/orangeturtle739/photos-export/blob/master/extract_photos.py
# TODO: Add test for imageTimeZoneOffsetSeconds = None
# TODO: Fix command line so multiple --keyword, etc. are AND (instead of OR as they are in .photos())
#       Or fix the help text to match behavior
# TODO: Add test for __str__ and to_json
# TODO: fix docstrings
# TODO: Add special albums and magic albums
# TODO: cleanup os.path and pathlib code (import pathlib and also from pathlib import Path)


class PhotosDB:
    """ Processes a Photos.app library database to extract information about photos """

    def __init__(self, *args, dbfile=None):
        """ create a new PhotosDB object """
        """ path to photos library or database may be specified EITHER as first argument or as named argument dbfile=path """
        """ optional: specify full path to photos library or photos.db as first argument """
        """ optional: specify path to photos library or photos.db using named argument dbfile=path """

        # Check OS version
        system = platform.system()
        (_, major, _) = _get_os_version()
        if system != "Darwin" or (major not in _TESTED_OS_VERSIONS):
            logging.warning(
                f"WARNING: This module has only been tested with MacOS 10."
                f"[{', '.join(_TESTED_OS_VERSIONS)}]: "
                f"you have {system}, OS version: {major}"
            )

        # configure AppleScripts used to manipulate Photos
        # self._setup_applescript()

        # set up the data structures used to store all the Photo database info

        # Path to the Photos library database file
        self._dbfile = None
        # Dict with information about all photos by uuid
        self._dbphotos = {}
        # Dict with information about all persons/photos by uuid
        self._dbfaces_uuid = {}
        # Dict with information about all persons/photos by person
        self._dbfaces_person = {}
        # Dict with information about all keywords/photos by uuid
        self._dbkeywords_uuid = {}
        # Dict with information about all keywords/photos by keyword
        self._dbkeywords_keyword = {}
        # Dict with information about all albums/photos by uuid
        self._dbalbums_uuid = {}
        # Dict with information about all albums/photos by album
        self._dbalbums_album = {}
        # Dict with information about album details
        self._dbalbum_details = {}
        # Dict with information about all the volumes/photos by uuid
        self._dbvolumes = {}

        # list of temporary files created so we can clean them up later
        self._tmp_files = []

        logging.debug(f"dbfile = {dbfile}")

        # get the path to photos library database
        if args:
            # got a library path as argument
            if dbfile:
                # shouldn't pass via both *args and dbfile=
                raise TypeError(
                    f"photos database path must be specified as argument or named parameter dbfile but not both: args: {args}, dbfile: {dbfile}",
                    args,
                    dbfile,
                )
            elif len(args) == 1:
                dbfile = args[0]
            else:
                raise TypeError(
                    f"__init__ takes only a single argument (photos database path): {args}",
                    args,
                )
        elif dbfile is None:
            # no args and dbfile not passed, try to get last opened library
            library_path = get_last_library_path()
            if not library_path:
                raise FileNotFoundError("could not get library path")
            dbfile = os.path.join(library_path, "database/photos.db")

        if os.path.isdir(dbfile):
            # passed a directory, assume it's a photoslibrary
            dbfile = os.path.join(dbfile, "database/photos.db")

        # if get here, should have a dbfile path; make sure it exists
        if not _check_file_exists(dbfile):
            raise FileNotFoundError(f"dbfile {dbfile} does not exist", dbfile)

        logging.debug(f"dbfile = {dbfile}")

        self._dbfile = dbfile

        # force Photos to quit (TODO: this might not be needed since we copy the file)
        # self._scpt_quit.run()
        self._tmp_db = self._copy_db_file(self._dbfile)
        self._db_version = self._get_db_version()
        if int(self._db_version) >= int(_PHOTOS_5_VERSION):
            logging.debug(f"version is {self._db_version}")
            dbpath = pathlib.Path(self._dbfile).parent
            dbfile = dbpath / "Photos.sqlite"
            logging.debug(f"dbfile = {dbfile}")
            if not _check_file_exists(dbfile):
                sys.exit(f"dbfile {dbfile} does not exist")
            else:
                self._dbfile = dbfile
                self._tmp_db = self._copy_db_file(self._dbfile)

        # TODO: replace os.path with pathlib?
        # TODO: clean this up -- library path computed twice
        library_path = os.path.dirname(os.path.abspath(dbfile))
        (library_path, _) = os.path.split(library_path)
        self._library_path = library_path
        if int(self._db_version) < int(_PHOTOS_5_VERSION):
            masters_path = os.path.join(library_path, "Masters")
            self._masters_path = masters_path
        else:
            masters_path = os.path.join(library_path, "originals")
            self._masters_path = masters_path

        logging.debug(f"library = {library_path}, masters = {masters_path}")

        if int(self._db_version) < int(_PHOTOS_5_VERSION):
            self._process_database4()
        else:
            self._process_database5()

    def _cleanup_tmp_files(self):
        """ removes all temporary files whose names are stored in self.tmp_files
        does not raise exception if file cannot be deleted (e.g. it was already cleaned up) """

        # logging.debug(f"tmp files = {self._tmp_files}")
        for f in self._tmp_files:
            if os.path.exists(f):
                logging.debug(f"cleaning up {f}")
                try:
                    os.remove(f)
                    self._tmp_files.remove(f)
                except Exception as e:
                    logging.debug("exception %e removing %s" % (e, f))
            else:
                self._tmp_files.remove(f)

    def __del__(self):
        pass
        # TODO: not sure this is needed as cleanup called in process_database
        # but commenting out for now as it was causing weird error during testing
        # AttributeError: 'NoneType' object has no attribute 'exists'
        # self._cleanup_tmp_files()

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

    # def _setup_applescript(self):
    #     """ setup various applescripts used internally (e.g. to close Photos) """
    #     self._scpt_export = ""
    #     self._scpt_launch = ""
    #     self._scpt_quit = ""

    #     # Compile apple script that exports one image
    #     #          self._scpt_export = _applescript.AppleScript('''
    #     #  on run {arg}
    #     #  set thepath to "%s"
    #     #  tell application "Photos"
    #     #  set theitem to media item id arg
    #     #  set thelist to {theitem}
    #     #  export thelist to POSIX file thepath
    #     #  end tell
    #     #  end run
    #     #  ''' % (tmppath))
    #     #
    #     # Compile apple script that launches Photos.App
    #     self._scpt_launch = _applescript.AppleScript(
    #         """
    #         on run
    #           tell application "Photos"
    #             activate
    #           end tell
    #         end run
    #         """
    #     )

    #     # Compile apple script that quits Photos.App
    #     self._scpt_quit = _applescript.AppleScript(
    #         """
    #         on run
    #           tell application "Photos"
    #             quit
    #           end tell
    #         end run
    #         """
    #     )

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
        """ returns the name of the temp file and appends name to self->_tmp_files """
        """ If sqlite shared memory and write-ahead log files exist, those are copied too """
        # required because python's sqlite3 implementation can't read a locked file
        _, suffix = os.path.splitext(fname)
        tmp_files = []
        try:
            _, tmp = tempfile.mkstemp(suffix=suffix, prefix="osxphotos-")
            copyfile(fname, tmp)
            tmp_files.append(tmp)
            # copy write-ahead log and shared memory files (-wal and -shm) files if they exist
            if os.path.exists(f"{fname}-wal"):
                copyfile(f"{fname}-wal", f"{tmp}-wal")
                tmp_files.append(f"{tmp}-wal")
            if os.path.exists(f"{fname}-shm"):
                copyfile(f"{fname}-shm", f"{tmp}-shm")
                tmp_files.append(f"{tmp}-shm")
        except:
            print("Error copying " + fname + " to " + tmp, file=sys.stderr)
            raise Exception

        self._tmp_files.extend(tmp_files)
        logging.debug(self._tmp_files)

        return tmp

    def _open_sql_file(self, file):
        """ opens sqlite file and returns connection to the database """
        fname = file
        try:
            conn = sqlite3.connect(f"{fname}")
            c = conn.cursor()
        except sqlite3.Error as e:
            print(f"An error occurred: {e.args[0]} {fname}", file=sys.stderr)
            sys.exit(3)
        return (conn, c)

    def _get_db_version(self):
        """ gets the Photos DB version from LiGlobals table """
        """ returns the version as str"""
        version = None

        (conn, c) = self._open_sql_file(self._tmp_db)
        # (conn, c) = self._open_sql_file(self._dbfile)

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

        # Ensure Photos.App is not running
        # TODO: Don't think we need this here
        # self._scpt_quit.run()

        (conn, c) = self._open_sql_file(self._tmp_db)

        # Look for all combinations of persons and pictures

        i = 0
        c.execute(
            "select count(*) from RKFace, RKPerson, RKVersion where RKFace.personID = RKperson.modelID "
            + "and RKFace.imageModelId = RKVersion.modelId and RKVersion.isInTrash = 0"
        )
        # c.execute("select RKPerson.name, RKFace.imageID from RKFace, RKPerson where RKFace.personID = RKperson.modelID")
        c.execute(
            "select RKPerson.name, RKVersion.uuid from RKFace, RKPerson, RKVersion, RKMaster "
            + "where RKFace.personID = RKperson.modelID and RKVersion.modelId = RKFace.ImageModelId "
            + "and RKVersion.type = 2 and RKVersion.masterUuid = RKMaster.uuid and "
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
            i = i + 1

        i = 0
        c.execute(
            "select count(*) from RKAlbum, RKVersion, RKAlbumVersion where "
            + "RKAlbum.modelID = RKAlbumVersion.albumId and "
            + "RKAlbumVersion.versionID = RKVersion.modelId and "
            + "RKVersion.filename not like '%.pdf' and RKVersion.isInTrash = 0"
        )
        # c.execute("select RKPerson.name, RKFace.imageID from RKFace, RKPerson where RKFace.personID = RKperson.modelID")
        c.execute(
            "select RKAlbum.uuid, RKVersion.uuid from RKAlbum, RKVersion, RKAlbumVersion "
            + "where RKAlbum.modelID = RKAlbumVersion.albumId and "
            + "RKAlbumVersion.versionID = RKVersion.modelId and RKVersion.type = 2 and "
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
            i = i + 1

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

        logging.debug(f"Finished walking through albums")
        logging.debug(pformat(self._dbalbums_album))
        logging.debug(pformat(self._dbalbums_uuid))
        logging.debug(pformat(self._dbalbum_details))

        c.execute(
            "select count(*) from RKKeyword, RKKeywordForVersion,RKVersion, RKMaster "
            + "where RKKeyword.modelId = RKKeyWordForVersion.keywordID and "
            + "RKVersion.modelID = RKKeywordForVersion.versionID and RKMaster.uuid = "
            + "RKVersion.masterUuid and RKVersion.filename not like '%.pdf' and RKVersion.isInTrash = 0"
        )
        c.execute(
            "select RKKeyword.name, RKVersion.uuid, RKMaster.uuid from "
            + "RKKeyword, RKKeywordForVersion, RKVersion, RKMaster "
            + "where RKKeyword.modelId = RKKeyWordForVersion.keywordID and "
            + "RKVersion.modelID = RKKeywordForVersion.versionID "
            + "and RKMaster.uuid = RKVersion.masterUuid and RKVersion.type = 2 "
            + "and RKVersion.filename not like '%.pdf' and RKVersion.isInTrash = 0"
        )
        i = 0
        for keyword in c:
            if not keyword[1] in self._dbkeywords_uuid:
                self._dbkeywords_uuid[keyword[1]] = []
            if not keyword[0] in self._dbkeywords_keyword:
                self._dbkeywords_keyword[keyword[0]] = []
            self._dbkeywords_uuid[keyword[1]].append(keyword[0])
            self._dbkeywords_keyword[keyword[0]].append(keyword[1])
            i = i + 1

        c.execute("select count(*) from RKVolume")
        c.execute("select RKVolume.modelId, RKVolume.name from RKVolume")
        i = 0
        for vol in c:
            self._dbvolumes[vol[0]] = vol[1]
            i = i + 1

        c.execute(
            "select count(*) from RKVersion, RKMaster where RKVersion.isInTrash = 0 and "
            + "RKVersion.type = 2 and RKVersion.masterUuid = RKMaster.uuid and "
            + "RKVersion.filename not like '%.pdf'"
        )
        c.execute(
            "select RKVersion.uuid, RKVersion.modelId, RKVersion.masterUuid, RKVersion.filename, "
            + "RKVersion.lastmodifieddate, RKVersion.imageDate, RKVersion.mainRating, "
            + "RKVersion.hasAdjustments, RKVersion.hasKeywords, RKVersion.imageTimeZoneOffsetSeconds, "
            + "RKMaster.volumeId, RKMaster.imagePath, RKVersion.extendedDescription, RKVersion.name, "
            + "RKMaster.isMissing, RKMaster.originalFileName, RKVersion.isFavorite, RKVersion.isHidden, "
            + "RKVersion.latitude, RKVersion.longitude, "
            + "RKVersion.adjustmentUuid "
            + "from RKVersion, RKMaster where RKVersion.isInTrash = 0 and RKVersion.type = 2 and "
            + "RKVersion.masterUuid = RKMaster.uuid and RKVersion.filename not like '%.pdf'"
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

        i = 0
        for row in c:
            i = i + 1
            uuid = row[0]
            logging.debug(f"i = {i:d}, uuid = '{uuid}, master = '{row[2]}")
            self._dbphotos[uuid] = {}
            self._dbphotos[uuid]["_uuid"] = uuid  # stored here for easier debugging
            self._dbphotos[uuid]["modelID"] = row[1]
            self._dbphotos[uuid]["masterUuid"] = row[2]
            self._dbphotos[uuid]["filename"] = row[3]

            try:
                self._dbphotos[uuid]["lastmodifieddate"] = datetime.fromtimestamp(
                    row[4] + td
                )
            except:
                self._dbphotos[uuid]["lastmodifieddate"] = datetime.fromtimestamp(
                    row[5] + td
                )

            self._dbphotos[uuid]["imageDate"] = datetime.fromtimestamp(
                row[5] + td
            )  # - row[9],  timezone.utc)
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

        # get details needed to find path of the edited photos and live photos
        c.execute(
            "SELECT RKVersion.uuid, RKVersion.adjustmentUuid, RKModelResource.modelId, "
            "RKModelResource.resourceTag, RKModelResource.UTI, RKVersion.specialType, "
            "RKModelResource.attachedModelType, RKModelResource.resourceType "
            "FROM RKVersion "
            "JOIN RKModelResource on RKModelResource.attachedModelId = RKVersion.modelId "
            "WHERE RKVersion.isInTrash = 0 "
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

        # TODO: add live photos
        # attachedmodeltype is 2, it's a photo, could be more than one
        # if 5, it's a facetile
        # specialtype = 0 == image, 5 or 8 == live photo movie

        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                if self._dbphotos[uuid]["adjustmentUuid"] == row[3]:
                    if (
                        row[1] != "UNADJUSTEDNONRAW"
                        and row[1] != "UNADJUSTED"
                        and row[4] == "public.jpeg"
                        and row[6] == 2
                    ):
                        if "edit_resource_id" in self._dbphotos[uuid]:
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

        # init any uuids that had no edits
        for uuid in self._dbphotos:
            if "edit_resource_id" not in self._dbphotos[uuid]:
                self._dbphotos[uuid]["edit_resource_id"] = None

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

        # remove temporary files
        self._cleanup_tmp_files()

        logging.debug("Faces:")
        logging.debug(pformat(self._dbfaces_uuid))

        logging.debug("Keywords by uuid:")
        logging.debug(pformat(self._dbkeywords_uuid))

        logging.debug("Keywords by keyword:")
        logging.debug(pformat(self._dbkeywords_keyword))

        logging.debug("Albums by uuid:")
        logging.debug(pformat(self._dbalbums_uuid))

        logging.debug("Albums by album:")
        logging.debug(pformat(self._dbalbums_album))

        logging.debug("Volumes:")
        logging.debug(pformat(self._dbvolumes))

        logging.debug("Photos:")
        logging.debug(pformat(self._dbphotos))

    def _process_database5(self):
        """ process the Photos database to extract info """
        """ works on Photos version >= 5.0 """

        logging.debug(f"_process_database5")

        # Epoch is Jan 1, 2001
        td = (datetime(2001, 1, 1, 0, 0) - datetime(1970, 1, 1, 0, 0)).total_seconds()

        # Ensure Photos.App is not running
        # TODO: Don't think we need this here
        # self._scpt_quit.run()

        (conn, c) = self._open_sql_file(self._tmp_db)

        # Look for all combinations of persons and pictures
        logging.debug(f"Getting information about persons")

        i = 0
        c.execute(
            "SELECT COUNT(*) "
            "FROM ZPERSON, ZDETECTEDFACE, ZGENERICASSET "
            "WHERE ZDETECTEDFACE.ZPERSON = ZPERSON.Z_PK AND ZDETECTEDFACE.ZASSET = ZGENERICASSET.Z_PK "
            "AND ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        c.execute(
            "SELECT ZPERSON.ZFULLNAME, ZGENERICASSET.ZUUID "
            "FROM ZPERSON, ZDETECTEDFACE, ZGENERICASSET "
            "WHERE ZDETECTEDFACE.ZPERSON = ZPERSON.Z_PK AND ZDETECTEDFACE.ZASSET = ZGENERICASSET.Z_PK "
            "AND ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
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
            i = i + 1
        logging.debug(f"Finished walking through persons")
        logging.debug(pformat(self._dbfaces_person))
        logging.debug(self._dbfaces_uuid)

        i = 0
        c.execute(
            "SELECT COUNT(*)"
            "FROM ZGENERICASSET "
            "JOIN Z_26ASSETS ON Z_26ASSETS.Z_34ASSETS = ZGENERICASSET.Z_PK "
            "JOIN ZGENERICALBUM ON ZGENERICALBUM.Z_PK = Z_26ASSETS.Z_26ALBUMS "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        c.execute(
            "SELECT ZGENERICALBUM.ZUUID, ZGENERICASSET.ZUUID "
            "FROM ZGENERICASSET "
            "JOIN Z_26ASSETS ON Z_26ASSETS.Z_34ASSETS = ZGENERICASSET.Z_PK "
            "JOIN ZGENERICALBUM ON ZGENERICALBUM.Z_PK = Z_26ASSETS.Z_26ALBUMS "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        for album in c:
            # store by uuid in _dbalbums_uuid and by album in _dbalbums_album
            if not album[1] in self._dbalbums_uuid:
                self._dbalbums_uuid[album[1]] = []
            if not album[0] in self._dbalbums_album:
                self._dbalbums_album[album[0]] = []
            self._dbalbums_uuid[album[1]].append(album[0])
            self._dbalbums_album[album[0]].append(album[1])
            i = i + 1

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

        logging.debug(f"Finished walking through albums")
        logging.debug(pformat(self._dbalbums_album))
        logging.debug(pformat(self._dbalbums_uuid))
        logging.debug(pformat(self._dbalbum_details))

        c.execute(
            "SELECT COUNT(*) "
            "FROM ZGENERICASSET "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "JOIN Z_1KEYWORDS ON Z_1KEYWORDS.Z_1ASSETATTRIBUTES = ZADDITIONALASSETATTRIBUTES.Z_PK "
            "JOIN ZKEYWORD ON ZKEYWORD.Z_PK = Z_1KEYWORDS.Z_37KEYWORDS "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        c.execute(
            "SELECT ZKEYWORD.ZTITLE, ZGENERICASSET.ZUUID "
            "FROM ZGENERICASSET "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "JOIN Z_1KEYWORDS ON Z_1KEYWORDS.Z_1ASSETATTRIBUTES = ZADDITIONALASSETATTRIBUTES.Z_PK "
            "JOIN ZKEYWORD ON ZKEYWORD.Z_PK = Z_1KEYWORDS.Z_37KEYWORDS "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        i = 0
        for keyword in c:
            if not keyword[1] in self._dbkeywords_uuid:
                self._dbkeywords_uuid[keyword[1]] = []
            if not keyword[0] in self._dbkeywords_keyword:
                self._dbkeywords_keyword[keyword[0]] = []
            self._dbkeywords_uuid[keyword[1]].append(keyword[0])
            self._dbkeywords_keyword[keyword[0]].append(keyword[1])
            i = i + 1
        logging.debug(f"Finished walking through keywords")
        logging.debug(pformat(self._dbkeywords_keyword))
        logging.debug(pformat(self._dbkeywords_uuid))

        c.execute("SELECT COUNT(*) FROM ZFILESYSTEMVOLUME")
        c.execute("SELECT ZUUID, ZNAME from ZFILESYSTEMVOLUME")
        i = 0
        for vol in c:
            self._dbvolumes[vol[0]] = vol[1]
            i = i + 1
        logging.debug(f"Finished walking through volumes")
        logging.debug(self._dbvolumes)

        logging.debug(f"Getting information about photos")
        # TODO: Since I don't use progress bars now, can probably remove the count
        c.execute(
            "SELECT COUNT(*) "
            "FROM ZGENERICASSET "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        c.execute(
            "SELECT ZGENERICASSET.ZUUID, "
            "ZADDITIONALASSETATTRIBUTES.ZMASTERFINGERPRINT, "
            "ZADDITIONALASSETATTRIBUTES.ZTITLE, "
            "ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME, "
            "ZGENERICASSET.ZMODIFICATIONDATE, "
            "ZGENERICASSET.ZDATECREATED, "
            "ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET, "
            "ZADDITIONALASSETATTRIBUTES.ZINFERREDTIMEZONEOFFSET, "
            "ZADDITIONALASSETATTRIBUTES.ZTIMEZONENAME, "
            "ZGENERICASSET.ZHIDDEN, "
            "ZGENERICASSET.ZFAVORITE, "
            "ZGENERICASSET.ZDIRECTORY, "
            "ZGENERICASSET.ZFILENAME, "
            "ZGENERICASSET.ZLATITUDE, "
            "ZGENERICASSET.ZLONGITUDE, "
            "ZGENERICASSET.ZHASADJUSTMENTS, "
            "ZGENERICASSET.ZCLOUDOWNERHASHEDPERSONID "
            "FROM ZGENERICASSET "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
            "ORDER BY ZGENERICASSET.ZUUID "
        )
        # Order of results
        # 0    "SELECT ZGENERICASSET.ZUUID, "
        # 1    "ZADDITIONALASSETATTRIBUTES.ZMASTERFINGERPRINT, "
        # 2    "ZADDITIONALASSETATTRIBUTES.ZTITLE, "
        # 3    "ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME, "
        # 4    "ZGENERICASSET.ZMODIFICATIONDATE, "
        # 5    "ZGENERICASSET.ZDATECREATED, "
        # 6    "ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET, "
        # 7    "ZADDITIONALASSETATTRIBUTES.ZINFERREDTIMEZONEOFFSET, "
        # 8    "ZADDITIONALASSETATTRIBUTES.ZTIMEZONENAME, "
        # 9    "ZGENERICASSET.ZHIDDEN, "
        # 10   "ZGENERICASSET.ZFAVORITE, "
        # 11   "ZGENERICASSET.ZDIRECTORY, "
        # 12   "ZGENERICASSET.ZFILENAME, "
        # 13   "ZGENERICASSET.ZLATITUDE, "
        # 14   "ZGENERICASSET.ZLONGITUDE, "
        # 15   "ZGENERICASSET.ZHASADJUSTMENTS "
        # 16   "ZCLOUDOWNERHASHEDPERSONID "   -- If not null, indicates a shared photo

        i = 0
        for row in c:
            i = i + 1
            uuid = row[0]
            logging.debug(f"i = {i:d}, uuid = '{uuid}")

            self._dbphotos[uuid] = {}
            self._dbphotos[uuid]["_uuid"] = uuid  # stored here for easier debugging
            self._dbphotos[uuid]["modelID"] = None
            self._dbphotos[uuid]["masterUuid"] = None
            self._dbphotos[uuid]["masterFingerprint"] = row[1]
            self._dbphotos[uuid]["name"] = row[2]
            try:
                self._dbphotos[uuid]["lastmodifieddate"] = datetime.fromtimestamp(
                    row[4] + td
                )
            except:
                self._dbphotos[uuid]["lastmodifieddate"] = datetime.fromtimestamp(
                    row[5] + td
                )

            self._dbphotos[uuid]["imageDate"] = datetime.fromtimestamp(row[5] + td)
            self._dbphotos[uuid]["imageTimeZoneOffsetSeconds"] = row[6]
            self._dbphotos[uuid]["hidden"] = row[9]
            self._dbphotos[uuid]["favorite"] = row[10]
            self._dbphotos[uuid]["originalFilename"] = row[3]
            self._dbphotos[uuid]["filename"] = row[12]
            self._dbphotos[uuid]["directory"] = row[11]

            # set latitude and longitude
            # if both latitude and longitude = -180.0, then they are NULL
            if row[13] == -180.0 and row[14] == -180.0:
                self._dbphotos[uuid]["latitude"] = None
                self._dbphotos[uuid]["longitude"] = None
            else:
                self._dbphotos[uuid]["latitude"] = row[13]
                self._dbphotos[uuid]["longitude"] = row[14]

            self._dbphotos[uuid]["hasAdjustments"] = row[15]

            self._dbphotos[uuid]["cloudOwnerHashedPersonID"] = row[16]
            self._dbphotos[uuid]["shared"] = True if row[16] is not None else False

            # these will get filled in later
            # init to avoid key errors
            self._dbphotos[uuid]["extendedDescription"] = None  # fill this in later
            self._dbphotos[uuid]["localAvailability"] = None
            self._dbphotos[uuid]["remoteAvailability"] = None
            self._dbphotos[uuid]["isMissing"] = None
            self._dbphotos[uuid]["adjustmentUuid"] = None
            self._dbphotos[uuid]["adjustmentFormatID"] = None

        # Get extended description
        c.execute(
            "SELECT ZGENERICASSET.ZUUID, "
            "ZASSETDESCRIPTION.ZLONGDESCRIPTION "
            "FROM ZGENERICASSET "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "JOIN ZASSETDESCRIPTION ON ZASSETDESCRIPTION.Z_PK = ZADDITIONALASSETATTRIBUTES.ZASSETDESCRIPTION "
            "ORDER BY ZGENERICASSET.ZUUID "
        )
        i = 0
        for row in c:
            i = i + 1
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["extendedDescription"] = row[1]
            else:
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
            "AND ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        for row in c:
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["adjustmentFormatID"] = row[2]
            else:
                logging.debug(
                    f"WARNING: found adjustmentformatidentifier {row[2]} but no photo for uuid {row[0]}"
                )

        # get information on local/remote availability
        c.execute(
            "SELECT ZGENERICASSET.ZUUID, "
            "ZINTERNALRESOURCE.ZLOCALAVAILABILITY, "
            "ZINTERNALRESOURCE.ZREMOTEAVAILABILITY "
            "FROM ZGENERICASSET "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "JOIN ZINTERNALRESOURCE ON ZINTERNALRESOURCE.ZFINGERPRINT = ZADDITIONALASSETATTRIBUTES.ZMASTERFINGERPRINT "
        )

        i = 0
        for row in c:
            i = i + 1
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["localAvailability"] = row[1]
                self._dbphotos[uuid]["remoteAvailability"] = row[2]
                if row[1] != 1:
                    self._dbphotos[uuid]["isMissing"] = 1
                else:
                    self._dbphotos[uuid]["isMissing"] = 0

        # temp fix for cloud shared files
        c.execute(
            """ SELECT 
                ZGENERICASSET.ZUUID, 
                ZINTERNALRESOURCE.ZLOCALAVAILABILITY, 
                ZINTERNALRESOURCE.ZREMOTEAVAILABILITY
                FROM ZGENERICASSET
                JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK 
                JOIN ZINTERNALRESOURCE ON ZINTERNALRESOURCE.ZASSET = ZADDITIONALASSETATTRIBUTES.ZASSET 
                WHERE ZINTERNALRESOURCE.ZFINGERPRINT IS NULL AND ZINTERNALRESOURCE.ZDATASTORESUBTYPE = 3 """
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

        logging.debug(pformat(self._dbphotos))

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

        # close connection and remove temporary files
        conn.close()
        self._cleanup_tmp_files()

        logging.debug("Faces:")
        logging.debug(pformat(self._dbfaces_uuid))

        logging.debug("Keywords by uuid:")
        logging.debug(pformat(self._dbkeywords_uuid))

        logging.debug("Keywords by keyword:")
        logging.debug(pformat(self._dbkeywords_keyword))

        logging.debug("Albums by uuid:")
        logging.debug(pformat(self._dbalbums_uuid))

        logging.debug("Albums by album:")
        logging.debug(pformat(self._dbalbums_album))

        logging.debug("Volumes:")
        logging.debug(pformat(self._dbvolumes))

        logging.debug("Photos:")
        logging.debug(pformat(self._dbphotos))

    # TODO: fix default values to None instead of []
    def photos(self, keywords=[], uuid=[], persons=[], albums=[]):
        """ 
        Return a list of PhotoInfo objects
        If called with no args, returns the entire database of photos
        If called with args, returns photos matching the args (e.g. keywords, persons, etc.)
        If more than one arg, returns photos matching all the criteria (e.g. keywords AND persons)
        """
        photos_sets = []  # list of photo sets to perform intersection of
        if not keywords and not uuid and not persons and not albums:
            # return all the photos
            # append keys of all photos as a single set to photos_sets
            photos_sets.append(set(self._dbphotos.keys()))
        else:
            if albums:
                album_titles = {}
                for album_id in self._dbalbum_details:
                    title = self._dbalbum_details[album_id]["title"]
                    if title in album_titles:
                        album_titles[title].append(album_id)
                    else:
                        album_titles[title] = [album_id]
                for album in albums:
                    # TODO: can have >1 album with same name. This globs them together.
                    # Need a way to select with album?
                    if album in album_titles:
                        album_set = set()
                        for album_id in album_titles[album]:
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

        photoinfo = []
        if photos_sets:  # found some photos
            # get the intersection of each argument/search criteria
            logging.debug(f"Got here: {photos_sets}")
            for p in set.intersection(*photos_sets):
                info = PhotoInfo(db=self, uuid=p, info=self._dbphotos[p])
                photoinfo.append(info)
        logging.debug(f"photoinfo: {pformat(photoinfo)}")
        return photoinfo

    def __repr__(self):
        # TODO: update to use __class__ and __name__
        return f"osxphotos.PhotosDB(dbfile='{self.db_path}')"
