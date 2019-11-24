import json
import logging
import os.path
import platform
import sqlite3
import sys
import tempfile
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from plistlib import load as plistload
from pprint import pformat
from shutil import copyfile

import yaml

import CoreFoundation
import objc
from Foundation import *

from . import _applescript


# TODO: Add RKMaster.originalFileName to Photos 4 code for original_file
# TODO: Add favorites, hidden
# TODO: Add location
# TODO: standardize _ and __ as leading char for private variables
# TODO: fix docstrings
# TODO: handle Null person for Photos 5

# which Photos library database versions have been tested
# Photos 2.0 (10.12.6) == 2622
# Photos 3.0 (10.13.6) == 3301
# Photos 4.0 (10.14.5) == 4016
# Photos 4.0 (10.14.6) == 4025
# Photos 5.0 (10.15.0) == 6000
# TODO: Should this also use compatibleBackToVersion from LiGlobals?
_TESTED_DB_VERSIONS = ["6000", "4025", "4016", "3301", "2622"]

# versions later than this have a different database structure
_PHOTOS_5_VERSION = "6000"

# which major version operating systems have been tested
_TESTED_OS_VERSIONS = ["12", "13", "14", "15"]

# set _debug = True to enable debug output
_debug = False

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s",
)

if not _debug:
    logging.disable(logging.DEBUG)


def _get_os_version():
    # returns tuple containing OS version
    # e.g. 10.13.6 = (10, 13, 6)
    version = platform.mac_ver()[0].split(".")
    if len(version) == 2:
        (ver, major) = version
        minor = "0"
    elif len(version) == 3:
        (ver, major, minor) = version
    else:
        raise (
            ValueError(
                f"Could not parse version string: {platform.mac_ver()} {version}"
            )
        )
    return (ver, major, minor)


def _check_file_exists(filename):
    # returns true if file exists and is not a directory
    # otherwise returns false
    filename = os.path.abspath(filename)
    return os.path.exists(filename) and not os.path.isdir(filename)


class PhotosDB:
    def __init__(self, dbfile=None):
        """ create a new PhotosDB object """
        """ optional: dbfile=path to photos.db from the Photos library """

        # Check OS version
        system = platform.system()
        (_, major, _) = _get_os_version()
        if system != "Darwin" or (major not in _TESTED_OS_VERSIONS):
            print(
                f"WARNING: This module has only been tested with MacOS 10."
                f"[{', '.join(_TESTED_OS_VERSIONS)}]: "
                f"you have {system}, OS version: {major}",
                file=sys.stderr,
            )

        # configure AppleScripts used to manipulate Photos
        self._setup_applescript()

        # set up the data structures used to store all the Photo database info

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
        # Dict with information about all the volumes/photos by uuid
        self._dbvolumes = {}

        # list of temporary files created so we can clean them up later
        self._tmp_files = []

        logging.debug(f"dbfile = {dbfile}")
        if dbfile is None:
            library_path = self.get_photos_library_path()
            # TODO: verify library path not None
            dbfile = os.path.join(library_path, "database/photos.db")

        if not _check_file_exists(dbfile):
            sys.exit(f"_dbfile {dbfile} does not exist")

        self._dbfile = dbfile

        # force Photos to quit (TODO: this might not be needed since we copy the file)
        self._scpt_quit.run()
        self._tmp_db = self._copy_db_file(self._dbfile)
        self._db_version = self._get_db_version()
        if int(self._db_version) >= int(_PHOTOS_5_VERSION):
            logging.debug(f"version is {self._db_version}")
            dbpath = Path(self._dbfile).parent
            dbfile = dbpath / "Photos.sqlite"
            logging.debug(f"dbfile = {dbfile}")
            if not _check_file_exists(dbfile):
                sys.exit(f"dbfile {dbfile} does not exist")
            else:
                self._dbfile = dbfile
                self._tmp_db = self._copy_db_file(self._dbfile)

        # zzz

        # TODO: replace os.path with pathlib
        # TODO: clean this up -- we'll already know library_path
        library_path = os.path.dirname(os.path.abspath(dbfile))
        (library_path, _) = os.path.split(library_path)
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
        """ removes all temporary files whose names are stored in self.tmp_files """
        """ does not raise exception if file cannot be deleted (e.g. it was already cleaned up) """
        logging.debug(f"tmp files ={self._tmp_files}")
        for f in self._tmp_files:
            logging.debug(f"cleaning up {f}")
            try:
                os.remove(f)
            except Exception as e:
                pass
                # print(f"WARNING: Unable to remove tmp file {e}")
                # raise e

    def __del__(self):
        self._cleanup_tmp_files()

    def keywords_as_dict(self):
        """ return keywords as dict of keyword, count in reverse sorted order (descending) """
        keywords = {}
        for k in self._dbkeywords_keyword.keys():
            keywords[k] = len(self._dbkeywords_keyword[k])
        keywords = dict(sorted(keywords.items(), key=lambda kv: kv[1], reverse=True))
        return keywords

    def persons_as_dict(self):
        """ return persons as dict of person, count in reverse sorted order (descending) """
        persons = {}
        for k in self._dbfaces_person.keys():
            persons[k] = len(self._dbfaces_person[k])
        persons = dict(sorted(persons.items(), key=lambda kv: kv[1], reverse=True))
        return persons

    def albums_as_dict(self):
        """ return albums as dict of albums, count in reverse sorted order (descending) """
        albums = {}
        for k in self._dbalbums_album.keys():
            albums[k] = len(self._dbalbums_album[k])
        albums = dict(sorted(albums.items(), key=lambda kv: kv[1], reverse=True))
        return albums

    def keywords(self):
        """ return list of keywords found in photos database """
        keywords = self._dbkeywords_keyword.keys()
        return list(keywords)

    def persons(self):
        """ return persons as dict of person, count in reverse sorted order (descending) """
        persons = self._dbfaces_person.keys()
        return list(persons)

    def albums(self):
        """ return albums as dict of albums, count in reverse sorted order (descending) """
        albums = self._dbalbums_album.keys()
        return list(albums)

    def _setup_applescript(self):
        """ setup various applescripts used internally (e.g. to close Photos) """
        self._scpt_export = ""
        self._scpt_launch = ""
        self._scpt_quit = ""

        # Compile apple script that exports one image
        #          self._scpt_export = _applescript.AppleScript('''
        #  on run {arg}
        #  set thepath to "%s"
        #  tell application "Photos"
        #  set theitem to media item id arg
        #  set thelist to {theitem}
        #  export thelist to POSIX file thepath
        #  end tell
        #  end run
        #  ''' % (tmppath))
        #
        # Compile apple script that launches Photos.App
        self._scpt_launch = _applescript.AppleScript(
            """
            on run
              tell application "Photos"
                activate
              end tell
            end run
            """
        )

        # Compile apple script that quits Photos.App
        self._scpt_quit = _applescript.AppleScript(
            """
            on run
              tell application "Photos"
                quit
              end tell
            end run
            """
        )

    def get_db_version(self):
        """ return the database version as stored in LiGlobals table """
        return self._db_version

    def get_db_path(self):
        """ return path to the Photos library database PhotosDB was initialized with """
        return os.path.abspath(self._dbfile)

    def get_photos_library_path(self):
        """ return the path to the Photos library """
        # TODO: move this to a module-level function
        plist_file = Path(
            str(Path.home())
            + "/Library/Containers/com.apple.Photos/Data/Library/Preferences/com.apple.Photos.plist"
        )
        if plist_file.is_file():
            with open(plist_file, "rb") as fp:
                pl = plistload(fp)
        else:
            print("could not find plist file: " + str(plist_file), file=sys.stderr)
            return None

        # get the IPXDefaultLibraryURLBookmark from com.apple.Photos.plist
        # this is a serialized CFData object
        photosurlref = pl["IPXDefaultLibraryURLBookmark"]

        if photosurlref is not None:
            # use CFURLCreateByResolvingBookmarkData to de-serialize bookmark data into a CFURLRef
            photosurl = CoreFoundation.CFURLCreateByResolvingBookmarkData(
                kCFAllocatorDefault, photosurlref, 0, None, None, None, None
            )

            # the CFURLRef we got is a sruct that python treats as an array
            # I'd like to pass this to CFURLGetFileSystemRepresentation to get the path but
            # CFURLGetFileSystemRepresentation barfs when it gets an array from python instead of expected struct
            # first element is the path string in form:
            # file:///Users/username/Pictures/Photos%20Library.photoslibrary/
            photosurlstr = photosurl[0].absoluteString() if photosurl[0] else None

            # now coerce the file URI back into an OS path
            # surely there must be a better way
            if photosurlstr is not None:
                photospath = os.path.normpath(
                    urllib.parse.unquote(urllib.parse.urlparse(photosurlstr).path)
                )
            else:
                print(
                    "Could not extract photos URL String from IPXDefaultLibraryURLBookmark",
                    file=sys.stderr,
                )
                return None

            return photospath
        else:
            print("Could not get path to Photos database", file=sys.stderr)
            return None

    # TODO: do we need to copy the db-wal write-ahead log file?
    def _copy_db_file(self, fname):
        """ copies the sqlite database file to a temp file """
        """ returns the name of the temp file and appends name to self->_tmp_files """
        # required because python's sqlite3 implementation can't read a locked file
        _, tmp = tempfile.mkstemp(suffix=".db", prefix="photos")
        try:
            copyfile(fname, tmp)
        except:
            print("Error copying " + fname + " to " + tmp, file=sys.stderr)
            raise Exception

        self._tmp_files.append(tmp)
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
        for ver in c:
            version = ver[0]
            break  # TODO: is there a more pythonic way to do get the first element from cursor?

        conn.close()

        if version not in _TESTED_DB_VERSIONS:
            print(
                f"WARNING: Only tested on database versions [{', '.join(_TESTED_DB_VERSIONS)}]"
                + f" You have database version={version} which has not been tested"
            )

        return version

    def _process_database4(self):
        """ process the Photos database to extract info """
        """ works on Photos version <= 4.0 """

        # Epoch is Jan 1, 2001
        td = (datetime(2001, 1, 1, 0, 0) - datetime(1970, 1, 1, 0, 0)).total_seconds()

        # Ensure Photos.App is not running
        # TODO: Don't think we need this here
        self._scpt_quit.run()

        (conn, c) = self._open_sql_file(self._tmp_db)

        # if int(self._db_version) > int(_PHOTOS_5_VERSION):
        #     # need to close the photos.db database and re-open Photos.sqlite
        #     c.close()
        #     try:
        #         os.remove(tmp_db)
        #     except:
        #         print("Could not remove temporary database: " + tmp_db, file=sys.stderr)

        #     self._dbfile2 = Path(self._dbfile) "Photos.sqlite"
        #     tmp_db = self._copy_db_file(fname)
        #     (conn, c) = self._open_sql_file(tmp_db)

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
            "select RKAlbum.name, RKVersion.uuid from RKAlbum, RKVersion, RKAlbumVersion "
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
            + "RKMaster.isMissing, RKMaster.originalFileName "
            + "from RKVersion, RKMaster where RKVersion.isInTrash = 0 and RKVersion.type = 2 and "
            + "RKVersion.masterUuid = RKMaster.uuid and RKVersion.filename not like '%.pdf'"
        )
        i = 0
        for row in c:
            i = i + 1
            uuid = row[0]
            logging.debug(f"i = {i:d}, uuid = '{uuid}, master = '{row[2]}")
            self._dbphotos[uuid] = {}
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

        if _debug:
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
        self._scpt_quit.run()

        (conn, c) = self._open_sql_file(self._tmp_db)

        # if int(self._db_version) > int(_PHOTOS_5_VERSION):
        #     # need to close the photos.db database and re-open Photos.sqlite
        #     c.close()
        #     try:
        #         os.remove(tmp_db)
        #     except:
        #         print("Could not remove temporary database: " + tmp_db, file=sys.stderr)

        #     self._dbfile2 = Path(self._dbfile) "Photos.sqlite"
        #     tmp_db = self._copy_db_file(fname)
        #     (conn, c) = self._open_sql_file(tmp_db)

        # Look for all combinations of persons and pictures
        logging.debug(f"Getting information about persons")

        i = 0
        c.execute(
            "SELECT COUNT(*) "
            "FROM ZPERSON, ZDETECTEDFACE, ZGENERICASSET "
            "WHERE ZDETECTEDFACE.ZPERSON = ZPERSON.Z_PK AND ZDETECTEDFACE.ZASSET = ZGENERICASSET.Z_PK "
            "AND ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        # c.execute("select RKPerson.name, RKFace.imageID from RKFace, RKPerson where RKFace.personID = RKperson.modelID")
        c.execute(
            "SELECT ZPERSON.ZFULLNAME, ZGENERICASSET.ZUUID "
            "FROM ZPERSON, ZDETECTEDFACE, ZGENERICASSET "
            "WHERE ZDETECTEDFACE.ZPERSON = ZPERSON.Z_PK AND ZDETECTEDFACE.ZASSET = ZGENERICASSET.Z_PK "
            "AND ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
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
        # c.execute("select RKPerson.name, RKFace.imageID from RKFace, RKPerson where RKFace.personID = RKperson.modelID")
        c.execute(
            "SELECT ZGENERICALBUM.ZTITLE, ZGENERICASSET.ZUUID "
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
        logging.debug(f"Finished walking through albums")
        logging.debug(pformat(self._dbalbums_album))
        logging.debug(pformat(self._dbalbums_uuid))

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
            "ZGENERICASSET.ZFILENAME "
            "FROM ZGENERICASSET "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
            "ORDER BY ZGENERICASSET.ZUUID "
            # "select RKVersion.uuid, RKVersion.modelId, RKVersion.masterUuid, RKVersion.filename, "
            # + "RKVersion.lastmodifieddate, RKVersion.imageDate, RKVersion.mainRating, "
            # + "RKVersion.hasAdjustments, RKVersion.hasKeywords, RKVersion.imageTimeZoneOffsetSeconds, "
            # + "RKMaster.volumeId, RKMaster.imagePath, RKVersion.extendedDescription, RKVersion.name, "
            # + "RKMaster.isMissing "
            # + "from RKVersion, RKMaster where RKVersion.isInTrash = 0 and RKVersion.type = 2 and "
            # + "RKVersion.masterUuid = RKMaster.uuid and RKVersion.filename not like '%.pdf'"
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
        # 12   "ZGENERICASSET.ZFILENAME "

        i = 0
        for row in c:
            i = i + 1
            uuid = row[0]
            if _debug:
                logging.debug(f"i = {i:d}, uuid = '{uuid}")
            self._dbphotos[uuid] = {}
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

            self._dbphotos[uuid]["imageDate"] = datetime.fromtimestamp(
                row[5] + td
            )  # - row[9],  timezone.utc)
            # self._dbphotos[uuid]["mainRating"] = row[6]
            # self._dbphotos[uuid]["hasAdjustments"] = row[7]
            # self._dbphotos[uuid]["hasKeywords"] = row[8]
            self._dbphotos[uuid]["imageTimeZoneOffsetSeconds"] = row[6]
            # self._dbphotos[uuid]["volumeId"] = row[10]
            # self._dbphotos[uuid]["imagePath"] = row[11]
            # self._dbphotos[uuid]["extendedDescription"] = row[12]
            self._dbphotos[uuid]["hidden"] = row[9]
            self._dbphotos[uuid]["favorite"] = row[10]
            self._dbphotos[uuid]["originalFilename"] = row[3]
            self._dbphotos[uuid]["filename"] = row[12]
            self._dbphotos[uuid]["directory"] = row[11]

            # these will get filled in later
            # init to avoid key errors
            self._dbphotos[uuid]["extendedDescription"] = None  # fill this in later
            self._dbphotos[uuid]["localAvailability"] = None
            self._dbphotos[uuid]["remoteAvailability"] = None
            self._dbphotos[uuid]["isMissing"] = None
            self._dbphotos[uuid]["hasAdjustments"] = None

            # self._dbphotos[uuid]["isMissing"] = row[14]

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

        if _debug:
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

            # if self._dbphotos[uuid]["volumeId"] is not None:
            #     self._dbphotos[uuid]["volume"] = self._dbvolumes[
            #         self._dbphotos[uuid]["volumeId"]
            #     ]
            # else:
            #     self._dbphotos[uuid]["volume"] = None

        # close connection and remove temporary files
        conn.close()
        self._cleanup_tmp_files()

        if _debug:
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


    """ 
    Return a list of PhotoInfo objects
    If called with no args, returns the entire database of photos
    If called with args, returns photos matching the args (e.g. keywords, persons, etc.)
    If more than one arg, returns photos matching all the criteria (e.g. keywords AND persons)
    """

    def photos(self, keywords=[], uuid=[], persons=[], albums=[]):
        photos_sets = []  # list of photo sets to perform intersection of
        if not keywords and not uuid and not persons and not albums:
            # return all the photos
            # append keys of all photos as a single set to photos_sets
            photos_sets.append(set(self._dbphotos.keys()))
        else:
            if albums:
                for album in albums:
                    if album in self._dbalbums_album:
                        photos_sets.append(set(self._dbalbums_album[album]))
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
            for p in set.intersection(*photos_sets):
                info = PhotoInfo(db=self, uuid=p, info=self._dbphotos[p])
                photoinfo.append(info)
        return photoinfo

    def __repr__(self):
        return f"osxphotos.PhotosDB(dbfile='{self.get_db_path()}')"


class PhotoInfo:
    """
    Info about a specific photo, contains all the details about the photo
    including keywords, persons, albums, uuid, path, etc.
    """
    def __init__(self, db=None, uuid=None, info=None):
        self.__uuid = uuid
        self.__info = info
        self.__db = db

    def filename(self):
        """ filename of the picture """
        return self.__info["filename"]

    def original_filename(self):
        """ original filename of the picture """
        """ Photos 5 mangles filenames upon import """
        return self.__info["originalFilename"]

    def date(self):
        """ image creation date as timezone aware datetime object """
        imagedate = self.__info["imageDate"]
        delta = timedelta(seconds=self.__info["imageTimeZoneOffsetSeconds"])
        tz = timezone(delta)
        imagedate_utc = imagedate.astimezone(tz=tz)
        return imagedate_utc

    def tzoffset(self):
        """ timezone offset from UTC in seconds """
        return self.__info["imageTimeZoneOffsetSeconds"]

    def path(self):
        """ absolute path on disk of the picture """
        photopath = ""

        if self.__db._db_version < _PHOTOS_5_VERSION:
            vol = self.__info["volume"]
            if vol is not None:
                photopath = os.path.join("/Volumes", vol, self.__info["imagePath"])
            else:
                photopath = os.path.join(
                    self.__db._masters_path, self.__info["imagePath"]
                )

            if self.__info["isMissing"] == 1:
                photopath = None  # path would be meaningless until downloaded
                # TODO: Is there a way to use applescript or PhotoKit to force the download in this
        else:
            if self.__info["masterFingerprint"]:
                # if masterFingerprint is not null, path appears to be valid
                if self.__info["directory"].startswith("/"):
                    photopath = os.path.join(
                        self.__info["directory"], self.__info["filename"]
                    )
                else:
                    photopath = os.path.join(
                        self.__db._masters_path,
                        self.__info["directory"],
                        self.__info["filename"],
                    )
            else:
                photopath = None
                logging.debug(f"WARNING: masterFingerprint null {pformat(self.__info)}")

            # TODO: fix the logic for isMissing
            if self.__info["isMissing"] == 1:
                photopath = None  # path would be meaningless until downloaded

            logging.debug(photopath)

        return photopath

    def description(self):
        """ long / extended description of picture """
        return self.__info["extendedDescription"]

    def persons(self):
        """ list of persons in picture """
        return self.__info["persons"]

    def albums(self):
        """ list of albums picture is contained in """
        return self.__info["albums"]

    def keywords(self):
        """ list of keywords for picture """
        return self.__info["keywords"]

    def name(self):
        """ name / title of picture """
        return self.__info["name"]

    def uuid(self):
        """ UUID of picture """
        return self.__uuid

    def ismissing(self):
        """ returns true if photo is missing from disk (which means it's not been downloaded from iCloud) 
        NOTE:   the photos.db database uses an asynchrounous write-ahead log so changes in Photos
                do not immediately get written to disk. In particular, I've noticed that downloading 
                an image from the cloud does not force the database to be updated until something else
                e.g. an edit, keyword, etc. occurs forcing a database synch
                The exact process / timing is a mystery to be but be aware that if some photos were recently
                downloaded from cloud to local storate their status in the database might still show
                isMissing = 1
        """
        return True if self.__info["isMissing"] == 1 else False

    def hasadjustments(self):
        """ True if picture has adjustments """
        """ TODO: not accurate for Photos version >= 5 """
        return True if self.__info["hasAdjustments"] == 1 else False

    def __repr__(self):
        return f"osxphotos.PhotoInfo(db={self.__db}, uuid='{self.__uuid}', info={self.__info})"

    def __str__(self):
        info = {
            "uuid": self.uuid(),
            "filename": self.filename(),
            "original_filename": self.original_filename(),
            "date": str(self.date()),
            "description": self.description(),
            "name": self.name(),
            "keywords": self.keywords(),
            "albums": self.albums(),
            "persons": self.persons(),
            "path": self.path(),
            "ismissing": self.ismissing(),
            "hasadjustments": self.hasadjustments(),
        }
        return yaml.dump(info, sort_keys=False)

    def to_json(self):
        """ return JSON representation """
        # TODO: Add additional details here
        pic = {
            "uuid": self.uuid(),
            "filename": self.filename(),
            "original_filename": self.original_filename(),
            "date": str(self.date()),
            "description": self.description(),
            "name": self.name(),
            "keywords": self.keywords(),
            "albums": self.albums(),
            "persons": self.persons(),
            "path": self.path(),
            "ismissing": self.ismissing(),
            "hasadjustments": self.hasadjustments(),
        }
        return json.dumps(pic)

    # compare two PhotoInfo objects for equality
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)
