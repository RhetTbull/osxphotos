import json
import os.path
import platform
import pprint
import sqlite3
import sys
import tempfile
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from plistlib import load as plistload
from shutil import copyfile

import CoreFoundation
import objc
import yaml
from Foundation import *

from . import _applescript

# from loguru import logger

# TODO: Add favorites, hidden
# TODO: Add location
# TODO: Does not work with Photos 5.0 / Mac OS 10.15 Catalina
# TODO: standardize _ and __ as leading char for private variables
# TODO: fix docstrings

# which Photos library database versions have been tested
# Photos 2.0 (10.12.6) == 2622
# Photos 3.0 (10.13.6) == 3301
# Photos 4.0 (10.14.5) == 4016
# Photos 4.0 (10.14.6) == 4025
# Photos 5.0 (10.15.0) == 6000
# TODO: Should this also use compatibleBackToVersion from LiGlobals?
_TESTED_DB_VERSIONS = ["4025", "4016", "3301", "2622"]

# versions later than this have a different database structure
_PHOTOS_5_VERSION = "6000"

# which major version operating systems have been tested
_TESTED_OS_VERSIONS = ["12", "13", "14"]

_debug = True


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
        # logger.debug(system, major)
        if system != "Darwin" or (major not in _TESTED_OS_VERSIONS):
            print(
                "WARNING: This module has only been tested with MacOS 10."
                + f"[{', '.join(_TESTED_OS_VERSIONS)}]: "
                + f"you have {system}, OS version: {major}",
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

        print(f"DEBUG: dbfile = {dbfile}")
        if dbfile is None:
            library_path = self.get_photos_library_path()
            # logger.debug("library_path: " + library_path)
            # TODO: verify library path not None
            dbfile = os.path.join(library_path, "database/photos.db")
            # logger.debug(dbfile)

        if not _check_file_exists(dbfile):
            sys.exit(f"_dbfile {dbfile} does not exist")

        self._dbfile = dbfile

        # force Photos to quit (TODO: this might not be needed since we copy the file)
        self._scpt_quit.run()
        self._tmp_db = self._copy_db_file(self._dbfile)
        self._db_version = self._get_db_version()
        if int(self._db_version) >= int(_PHOTOS_5_VERSION):
            print(f"DEBUG: version is {self._db_version}")
            dbpath = Path(self._dbfile).parent
            dbfile = dbpath / "Photos.sqlite"
            print(f"DEBUG: dbfile = {dbfile}")
            if not _check_file_exists(dbfile):
                sys.exit(f"dbfile {dbfile} does not exist")
            else:
                self._dbfile = dbfile
                self._tmp_db = self._copy_db_file(self._dbfile)

        # zzz

        # TODO: replace os.path with pathlib
        # TODO: clean this up -- we'll already know library_path
        library_path = os.path.dirname(dbfile)
        (library_path, _) = os.path.split(library_path)
        if int(self._db_version) < int(_PHOTOS_5_VERSION):
            masters_path = os.path.join(library_path, "Masters")
            self._masters_path = masters_path
        else:
            masters_path = os.path.join(library_path, "originals")
            self._masters_path = masters_path

        print(f"DEBUG: library = {library_path}, masters = {masters_path}")

        # logger.info(f"database filename = {dbfile}")

        if int(self._db_version) < int(_PHOTOS_5_VERSION):
            self._process_database4()
        else:
            self._process_database5()

    def _cleanup_tmp_files(self):
        """ removes all temporary files whose names are stored in self.tmp_files """
        """ does not raise exception if file cannot be deleted (e.g. it was already cleaned up) """
        print(f"DEBUG: tmp files ={self._tmp_files}")
        for f in self._tmp_files:
            print(f"DEBUG: cleaning up {f}")
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

        if photosurlref != None:
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
        #  logger.debug("copying " + fname + " to " + tmp)
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
        #  logger.debug(f"Trying to open database {fname}")
        try:
            conn = sqlite3.connect(f"{fname}")
            c = conn.cursor()
        except sqlite3.Error as e:
            print(f"An error occurred: {e.args[0]} {fname}")
            sys.exit(3)
        #  logger.debug("SQLite database is open")
        return (conn, c)

    def _get_db_version(self):
        """ gets the Photos DB version from LiGlobals table """
        """ returns the version as str"""
        global _debug
        version = None

        (conn, c) = self._open_sql_file(self._tmp_db)
        # (conn, c) = self._open_sql_file(self._dbfile)
        #  logger.debug("Have connection with database")

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
        global _debug

        # Epoch is Jan 1, 2001
        td = (datetime(2001, 1, 1, 0, 0) - datetime(1970, 1, 1, 0, 0)).total_seconds()

        # Ensure Photos.App is not running
        # TODO: Don't think we need this here
        self._scpt_quit.run()

        (conn, c) = self._open_sql_file(self._tmp_db)
        #  logger.debug("Have connection with database")

        # if int(self._db_version) > int(_PHOTOS_5_VERSION):
        #     # need to close the photos.db database and re-open Photos.sqlite
        #     c.close()
        #     try:
        #         #  logger.info("Removing temporary database file: " + tmp_db)
        #         os.remove(tmp_db)
        #     except:
        #         print("Could not remove temporary database: " + tmp_db, file=sys.stderr)

        #     self._dbfile2 = Path(self._dbfile) "Photos.sqlite"
        #     tmp_db = self._copy_db_file(fname)
        #     (conn, c) = self._open_sql_file(tmp_db)

        # Look for all combinations of persons and pictures
        #  logger.debug("Getting information about persons")

        i = 0
        c.execute(
            "select count(*) from RKFace, RKPerson, RKVersion where RKFace.personID = RKperson.modelID "
            + "and RKFace.imageModelId = RKVersion.modelId and RKVersion.isInTrash = 0"
        )
        # init_pbar_status("Faces", c.fetchone()[0])
        # c.execute("select RKPerson.name, RKFace.imageID from RKFace, RKPerson where RKFace.personID = RKperson.modelID")
        c.execute(
            "select RKPerson.name, RKVersion.uuid from RKFace, RKPerson, RKVersion, RKMaster "
            + "where RKFace.personID = RKperson.modelID and RKVersion.modelId = RKFace.ImageModelId "
            + "and RKVersion.type = 2 and RKVersion.masterUuid = RKMaster.uuid and "
            + "RKVersion.filename not like '%.pdf' and RKVersion.isInTrash = 0"
        )
        for person in c:
            if person[0] == None:
                #  logger.debug(f"skipping person = None {person[1]}")
                continue
            if not person[1] in self._dbfaces_uuid:
                self._dbfaces_uuid[person[1]] = []
            if not person[0] in self._dbfaces_person:
                self._dbfaces_person[person[0]] = []
            self._dbfaces_uuid[person[1]].append(person[0])
            self._dbfaces_person[person[0]].append(person[1])
            #  set_pbar_status(i)
            i = i + 1
        #  logger.debug("Finished walking through persons")
        #  close_pbar_status()

        #  logger.debug("Getting information about albums")
        i = 0
        c.execute(
            "select count(*) from RKAlbum, RKVersion, RKAlbumVersion where "
            + "RKAlbum.modelID = RKAlbumVersion.albumId and "
            + "RKAlbumVersion.versionID = RKVersion.modelId and "
            + "RKVersion.filename not like '%.pdf' and RKVersion.isInTrash = 0"
        )
        #  init_pbar_status("Albums", c.fetchone()[0])
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
            #  logger.debug(f"{album[1]} {album[0]}")
            #  set_pbar_status(i)
            i = i + 1
        #  logger.debug("Finished walking through albums")
        #  close_pbar_status()

        #  logger.debug("Getting information about keywords")
        c.execute(
            "select count(*) from RKKeyword, RKKeywordForVersion,RKVersion, RKMaster "
            + "where RKKeyword.modelId = RKKeyWordForVersion.keywordID and "
            + "RKVersion.modelID = RKKeywordForVersion.versionID and RKMaster.uuid = "
            + "RKVersion.masterUuid and RKVersion.filename not like '%.pdf' and RKVersion.isInTrash = 0"
        )
        #  init_pbar_status("Keywords", c.fetchone()[0])
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
            #  logger.debug(f"{keyword[1]} {keyword[0]}")
            #  set_pbar_status(i)
            i = i + 1
        #  logger.debug("Finished walking through keywords")
        #  close_pbar_status()

        #  logger.debug("Getting information about volumes")
        c.execute("select count(*) from RKVolume")
        #  init_pbar_status("Volumes", c.fetchone()[0])
        c.execute("select RKVolume.modelId, RKVolume.name from RKVolume")
        i = 0
        for vol in c:
            self._dbvolumes[vol[0]] = vol[1]
            #  logger.debug(f"{vol[0]} {vol[1]}")
            #  set_pbar_status(i)
            i = i + 1
        #  logger.debug("Finished walking through volumes")
        #  close_pbar_status()

        #  logger.debug("Getting information about photos")
        c.execute(
            "select count(*) from RKVersion, RKMaster where RKVersion.isInTrash = 0 and "
            + "RKVersion.type = 2 and RKVersion.masterUuid = RKMaster.uuid and "
            + "RKVersion.filename not like '%.pdf'"
        )
        #  init_pbar_status("Photos", c.fetchone()[0])
        c.execute(
            "select RKVersion.uuid, RKVersion.modelId, RKVersion.masterUuid, RKVersion.filename, "
            + "RKVersion.lastmodifieddate, RKVersion.imageDate, RKVersion.mainRating, "
            + "RKVersion.hasAdjustments, RKVersion.hasKeywords, RKVersion.imageTimeZoneOffsetSeconds, "
            + "RKMaster.volumeId, RKMaster.imagePath, RKVersion.extendedDescription, RKVersion.name, "
            + "RKMaster.isMissing "
            + "from RKVersion, RKMaster where RKVersion.isInTrash = 0 and RKVersion.type = 2 and "
            + "RKVersion.masterUuid = RKMaster.uuid and RKVersion.filename not like '%.pdf'"
        )
        i = 0
        for row in c:
            #  set_pbar_status(i)
            i = i + 1
            uuid = row[0]
            if _debug:
                print(f"i = {i:d}, uuid = '{uuid}, master = '{row[2]}")
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
            #  logger.debug(
        #                  "Fetching data for photo %d %s %s %s %s %s: %s"
        #  % (
        #  i,
        #  uuid,
        #  self._dbphotos[uuid]["masterUuid"],
        #  self._dbphotos[uuid]["volumeId"],
        #  self._dbphotos[uuid]["filename"],
        #  self._dbphotos[uuid]["extendedDescription"],
        #  self._dbphotos[uuid]["imageDate"],
        #  )
        #  )

        #  close_pbar_status()
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
            pp = pprint.PrettyPrinter(indent=4)
            print("Faces:")
            pp.pprint(self._dbfaces_uuid)

            print("Keywords by uuid:")
            pp.pprint(self._dbkeywords_uuid)

            print("Keywords by keyword:")
            pp.pprint(self._dbkeywords_keyword)

            print("Albums by uuid:")
            pp.pprint(self._dbalbums_uuid)

            print("Albums by album:")
            pp.pprint(self._dbalbums_album)

            print("Volumes:")
            pp.pprint(self._dbvolumes)

            print("Photos:")
            pp.pprint(self._dbphotos)

        #  logger.debug(f"processed {len(self._dbphotos)} photos")

    def _process_database5(self):
        """ process the Photos database to extract info """
        """ works on Photos version >= 5.0 """

        global _debug

        if _debug:
            print(f"DEBUG: _process_database5")

        # Epoch is Jan 1, 2001
        td = (datetime(2001, 1, 1, 0, 0) - datetime(1970, 1, 1, 0, 0)).total_seconds()

        # Ensure Photos.App is not running
        # TODO: Don't think we need this here
        self._scpt_quit.run()

        (conn, c) = self._open_sql_file(self._tmp_db)
        #  logger.debug("Have connection with database")

        # if int(self._db_version) > int(_PHOTOS_5_VERSION):
        #     # need to close the photos.db database and re-open Photos.sqlite
        #     c.close()
        #     try:
        #         #  logger.info("Removing temporary database file: " + tmp_db)
        #         os.remove(tmp_db)
        #     except:
        #         print("Could not remove temporary database: " + tmp_db, file=sys.stderr)

        #     self._dbfile2 = Path(self._dbfile) "Photos.sqlite"
        #     tmp_db = self._copy_db_file(fname)
        #     (conn, c) = self._open_sql_file(tmp_db)

        # Look for all combinations of persons and pictures
        print(f"DEBUG: Getting information about persons")

        i = 0
        c.execute(
            "SELECT COUNT(*) "
            "FROM ZPERSON, ZDETECTEDFACE, ZGENERICASSET "
            "WHERE ZDETECTEDFACE.ZPERSON = ZPERSON.Z_PK AND ZDETECTEDFACE.ZASSET = ZGENERICASSET.Z_PK "
            "AND ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        # init_pbar_status("Faces", c.fetchone()[0])
        # c.execute("select RKPerson.name, RKFace.imageID from RKFace, RKPerson where RKFace.personID = RKperson.modelID")
        c.execute(
            "SELECT ZPERSON.ZFULLNAME, ZGENERICASSET.ZUUID "
            "FROM ZPERSON, ZDETECTEDFACE, ZGENERICASSET "
            "WHERE ZDETECTEDFACE.ZPERSON = ZPERSON.Z_PK AND ZDETECTEDFACE.ZASSET = ZGENERICASSET.Z_PK "
            "AND ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        for person in c:
            if person[0] == None:
                #  logger.debug(f"skipping person = None {person[1]}")
                continue
            if not person[1] in self._dbfaces_uuid:
                self._dbfaces_uuid[person[1]] = []
            if not person[0] in self._dbfaces_person:
                self._dbfaces_person[person[0]] = []
            self._dbfaces_uuid[person[1]].append(person[0])
            self._dbfaces_person[person[0]].append(person[1])
            #  set_pbar_status(i)
            i = i + 1
        print(f"DEBUG: Finished walking through persons")
        pp = pprint.PrettyPrinter(indent=4)
        print(f"DEBUG: {pp.pprint(self._dbfaces_person)}")
        print(f"DEBUG: {pp.pprint(self._dbfaces_uuid)}")

        #  close_pbar_status()

        #  logger.debug("Getting information about albums")
        i = 0
        c.execute(
            "SELECT COUNT(*)"
            "FROM ZGENERICASSET "
            "JOIN Z_26ASSETS ON Z_26ASSETS.Z_34ASSETS = ZGENERICASSET.Z_PK "
            "JOIN ZGENERICALBUM ON ZGENERICALBUM.Z_PK = Z_26ASSETS.Z_26ALBUMS "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        #  init_pbar_status("Albums", c.fetchone()[0])
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
            #  logger.debug(f"{album[1]} {album[0]}")
            #  set_pbar_status(i)
            i = i + 1
        print(f"DEBUG: Finished walking through albums")
        print(f"DEBUG: {pp.pprint(self._dbalbums_album)}")
        print(f"DEBUG: {pp.pprint(self._dbalbums_uuid)}")
        #  close_pbar_status()

        #  logger.debug("Getting information about keywords")
        c.execute(
            "SELECT COUNT(*) "
            "FROM ZGENERICASSET "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "JOIN Z_1KEYWORDS ON Z_1KEYWORDS.Z_1ASSETATTRIBUTES = ZADDITIONALASSETATTRIBUTES.Z_PK "
            "JOIN ZKEYWORD ON ZKEYWORD.Z_PK = Z_1KEYWORDS.Z_37KEYWORDS "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        #  init_pbar_status("Keywords", c.fetchone()[0])
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
            #  logger.debug(f"{keyword[1]} {keyword[0]}")
            #  set_pbar_status(i)
            i = i + 1
        print(f"DEBUG: Finished walking through keywords")
        #  close_pbar_status()
        pp.pprint(self._dbkeywords_keyword)
        pp.pprint(self._dbkeywords_uuid)

        #  logger.debug("Getting information about volumes")
        c.execute("SELECT COUNT(*) FROM ZFILESYSTEMVOLUME")
        #  init_pbar_status("Volumes", c.fetchone()[0])
        c.execute("SELECT ZUUID, ZNAME from ZFILESYSTEMVOLUME")
        i = 0
        for vol in c:
            self._dbvolumes[vol[0]] = vol[1]
            #  logger.debug(f"{vol[0]} {vol[1]}")
            #  set_pbar_status(i)
            i = i + 1
        print(f"DEBUG: Finished walking through volumes")
        pp.pprint(self._dbvolumes)
        #  close_pbar_status()

        print(f"DEBUG: Getting information about photos")
        # TODO: Since I don't use progress bars now, can probably remove the count
        c.execute(
            "SELECT COUNT(*) "
            "FROM ZGENERICASSET "
            "JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK "
            "WHERE ZGENERICASSET.ZTRASHEDSTATE = 0 AND ZGENERICASSET.ZKIND = 0 "
        )
        #  init_pbar_status("Photos", c.fetchone()[0])
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
            #  set_pbar_status(i)
            i = i + 1
            uuid = row[0]
            if _debug:
                print(f"i = {i:d}, uuid = '{uuid}")
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
            # self._dbphotos[uuid]["isMissing"] = row[14]
            #  logger.debug(
        #                  "Fetching data for photo %d %s %s %s %s %s: %s"
        #  % (
        #  i,
        #  uuid,
        #  self._dbphotos[uuid]["masterUuid"],
        #  self._dbphotos[uuid]["volumeId"],
        #  self._dbphotos[uuid]["filename"],
        #  self._dbphotos[uuid]["extendedDescription"],
        #  self._dbphotos[uuid]["imageDate"],
        #  )
        #  )

        #  close_pbar_status()

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
                print(
                    f"DEBUG WARNING: found description {row[1]} but no photo for {uuid}"
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
            i = i+1
            uuid = row[0]
            if uuid in self._dbphotos:
                self._dbphotos[uuid]["localAvailability"] = row[1]
                self._dbphotos[uuid]["remoteAvailability"] = row[2]
                if row[1] != 1:
                    self._dbphotos[uuid]["isMissing"] = 1
                else:
                    self._dbphotos[uuid]["isMissing"] = 0
        
        if _debug:
            pp.pprint(self._dbphotos)

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
            pp = pprint.PrettyPrinter(indent=4)
            print("Faces:")
            pp.pprint(self._dbfaces_uuid)

            print("Keywords by uuid:")
            pp.pprint(self._dbkeywords_uuid)

            print("Keywords by keyword:")
            pp.pprint(self._dbkeywords_keyword)

            print("Albums by uuid:")
            pp.pprint(self._dbalbums_uuid)

            print("Albums by album:")
            pp.pprint(self._dbalbums_album)

            print("Volumes:")
            pp.pprint(self._dbvolumes)

            print("Photos:")
            pp.pprint(self._dbphotos)

        #  logger.debug(f"processed {len(self._dbphotos)} photos")

    """ 
    Return a list of PhotoInfo objects
    If called with no args, returns the entire database of photos
    If called with args, returns photos matching the args (e.g. keywords, persons, etc.)
    If more than one arg, returns photos matching all the criteria (e.g. keywords AND persons)
    """

    def photos(self, keywords=[], uuid=[], persons=[], albums=[]):
        # TODO: remove the logger code then dangling else: pass statements
        photos_sets = []  # list of photo sets to perform intersection of
        if not keywords and not uuid and not persons and not albums:
            # return all the photos
            # append keys of all photos as a single set to photos_sets
            #  logger.debug("return all photos")
            photos_sets.append(set(self._dbphotos.keys()))
        else:
            if albums:
                for album in albums:
                    #  logger.info(f"album={album}")
                    if album in self._dbalbums_album:
                        #  logger.info(f"processing album {album}:")
                        photos_sets.append(set(self._dbalbums_album[album]))
                    else:
                        #  logger.debug(f"Could not find album '{album}' in database")
                        pass

            if uuid:
                for u in uuid:
                    #  logger.info(f"uuid={u}")
                    if u in self._dbphotos:
                        #  logger.info(f"processing uuid {u}:")
                        photos_sets.append(set([u]))
                    else:
                        #  logger.debug(f"Could not find uuid '{u}' in database")
                        pass

            if keywords:
                for keyword in keywords:
                    #  logger.info(f"keyword={keyword}")
                    if keyword in self._dbkeywords_keyword:
                        #  logger.info(f"processing keyword {keyword}:")
                        photos_sets.append(set(self._dbkeywords_keyword[keyword]))
                        #  logger.debug(f"photos_sets {photos_sets}")
                    else:
                        #  logger.debug(f"Could not find keyword '{keyword}' in database")
                        pass

            if persons:
                for person in persons:
                    #  logger.info(f"person={person}")
                    if person in self._dbfaces_person:
                        #  logger.info(f"processing person {person}:")
                        photos_sets.append(set(self._dbfaces_person[person]))
                    else:
                        #  logger.debug(f"Could not find person '{person}' in database")
                        pass

        photoinfo = []
        if photos_sets:  # found some photos
            # get the intersection of each argument/search criteria
            for p in set.intersection(*photos_sets):
                #  logger.debug(f"p={p}")
                info = PhotoInfo(db=self, uuid=p, info=self._dbphotos[p])
                #  logger.debug(f"info={info}")
                photoinfo.append(info)
        return photoinfo

    def __repr__(self):
        return f"osxphotos.PhotosDB(dbfile='{self.get_db_path()}')"


"""
Info about a specific photo, contains all the details we know about the photo
including keywords, persons, albums, uuid, path, etc.
"""


class PhotoInfo:
    def __init__(self, db=None, uuid=None, info=None):
        self.__uuid = uuid
        self.__info = info
        self.__db = db

    def filename(self):
        return self.__info["filename"]

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
        photopath = ""

        vol = self.__info["volume"]
        if vol is not None:
            photopath = os.path.join("/Volumes", vol, self.__info["imagePath"])
        else:
            photopath = os.path.join(self.__db._masters_path, self.__info["imagePath"])

        if self.__info["isMissing"] == 1:
            #  logger.warning(
            #  f"Skipping photo, not yet downloaded from iCloud: {photopath}"
            #  )
            #  logger.debug(self.__info)
            photopath = None  # path would be meaningless until downloaded
            # TODO: Is there a way to use applescript to force the download in this

        return photopath

    def description(self):
        return self.__info["extendedDescription"]

    def persons(self):
        return self.__info["persons"]

    def albums(self):
        return self.__info["albums"]

    def keywords(self):
        return self.__info["keywords"]

    def name(self):
        return self.__info["name"]

    def uuid(self):
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
        return True if self.__info["hasAdjustments"] == 1 else False

    def __repr__(self):
        return f"osxphotos.PhotoInfo(db={self.__db}, uuid='{self.__uuid}', info={self.__info})"

    def __str__(self):
        info = {
            "uuid": self.uuid(),
            "filename": self.filename(),
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
        pic = {
            "uuid": self.uuid(),
            "filename": self.filename(),
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
