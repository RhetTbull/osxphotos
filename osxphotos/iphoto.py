"""Support for iPhoto libraries

This code is based on https://github.com/jensb/iphoto2xmp by @jensb
who kindly gave permission to use the derived code under the MIT license.
The original iphoto2xmp is licensed under the GPL v3 license.

The following code largely follows the structure of the original iphoto2xmp code
with adaptations to convert it to python, break into functions for readability,
and add additional queries needed by osxphotos.

The code is not optimized. For example, redundant data is stored in multiple
data structures and the various database files used by iPhoto are opened & closed
multiple times as needed. This was a deliberate design choice to make the code
match the original as closely as possible and to make it easier to follow the
logic of the original code. I also optimized for implementation speed over execution
speed. iPhoto has not been supported by Apple since 2015 so the expected use case
for this code is to convert an iPhoto library to a Photos library or to export the
iPhoto library. Unlike the rest of the osxphotos code, it is not expected the user
will be using this code repeatedly.

The iPhotoDB, iPhotoPhotoInfo, iPhotoAlbumInfo, etc. classes are minimal implementations
of the corresponding classes in osxphotos and are designed to be drop-in replacements
for the osxphotos classes.  This was done to minimize changes to the rest of the
osxphotos codebase. These iPhoto implementations do not implement all the methods
of the corresponding osxphotos classes, only those needed to export or convert
an iPhoto library.

All the iPhoto code is contained in this single file. I didn't want to mess with creating
a separate package and dealing with the type-hint hell from circular dependencies as all
the classes are tightly coupled.
"""

from __future__ import annotations

import dataclasses
import datetime
import functools
import inspect
import json
import logging
import os
import pathlib
import sqlite3
from functools import cached_property
from typing import Any, Callable, get_type_hints
from zoneinfo import ZoneInfo

from ._constants import (
    _UNKNOWN_PERSON,
    SIDECAR_EXIFTOOL,
    SIDECAR_JSON,
    SIDECAR_XMP,
    TIME_DELTA,
)
from .datetime_utils import datetime_has_tz, datetime_naive_to_local
from .exiftool import ExifToolCaching, get_exiftool_path
from .exportoptions import ExportOptions
from .personinfo import MPRI_Reg_Rect, MWG_RS_Area
from .photoexporter import PhotoExporter
from .photoinfo import PhotoInfo
from .photoquery import QueryOptions, photo_query
from .phototemplate import PhotoTemplate, RenderOptions
from .platform import is_macos
from .scoreinfo import ScoreInfo
from .unicode import normalize_unicode
from .uti import get_preferred_uti_extension, get_uti_for_path
from .utils import hexdigest, noop, path_exists

if is_macos:
    from .fingerprint import fingerprint

logger = logging.getLogger("osxphotos")


class iPhotoDB:
    """Read an iPhoto library database; interface matches osxphotos.PhotosDB"""

    def __init__(
        self,
        dbfile: str,
        verbose: Callable[..., None] = None,
        exiftool: str | None = None,
        rich: bool = False,
        _skip_searchinfo: bool = True,
    ):
        """Create a new iPhotoDB object.

        Args:
            dbfile: specify full path to iPhoto library
            verbose: optional callable function to use for printing verbose text during processing; if None (default), does not print output.
            exiftool: optional path to exiftool for methods that require this (e.g. iPhotoPhotoInfo.exiftool); if not provided, will search PATH
            rich: use rich with verbose output
            _skip_searchinfo: if True, will not process search data from psi.sqlite; useful for processing standalone Photos.sqlite file

        Raises:
            PhotosDBReadError if dbfile is not a valid Photos library.
            TypeError if verbose is not None and not callable.

        Note:
            Unlike PhotosDB, you must specify only the path to the root library in dbfile, not the database file
            rich is not used with iPhoto
            _skip_searchinfo is not used with iPhoto
        """
        self.library_path: pathlib.Path = pathlib.Path(dbfile).absolute()
        if not self.library_path.is_dir():
            raise FileNotFoundError(f"Invalid iPhoto library path: {self.library_path}")
        if not self.library_path.joinpath("Database").is_dir():
            raise FileNotFoundError(f"Invalid iPhoto library path: {self.library_path}")
        self._library_path = str(self.library_path)  # compatibility with PhotosDB

        # for compatibility with PhotosDB but not a 1:1 mapping as iPhoto uses several databases
        self.db_path = str(self.library_path.joinpath("Database/apdb/Library.apdb"))

        if verbose is None:
            verbose = noop
        elif not callable(verbose):
            raise TypeError("verbose must be callable")
        self.verbose = verbose
        self._verbose = self.verbose  # compatibility with PhotosDB

        self._rich = rich  # currently unused, compatibility with PhotosDB
        self._exiftool_path = exiftool

        # initialize database dictionaries
        self._db_photos = {}  # mapping of uuid to photo data
        self._db_event_notes = {}  # mapping of modelId to event notes
        self._db_places = {}  # mapping of modelId to places
        self._db_properties = {}  # mapping of versionId to properties
        self._db_exif_info = {}  # mapping of versionId to EXIF info
        self._db_persons = {}  # mapping of modelId to persons
        self._db_faces = {}  # mapping of modelID to face info
        self._db_faces_edited = {}  # mapping of modelID to face info for edited photos
        self._db_folders = {}  # mapping of modelId to folders
        self._db_albums = {}  # mapping of modelId to albums
        self._db_volumes = {}  # mapping of volume uuid to volume name

        self._load_library()

        self._source = "iPhoto"

    def _load_library(self):
        """Load iPhoto library"""
        self.verbose(f"Loading iPhoto library: {self.library_path}")
        self._load_library_db()
        self._load_properties_db()
        self._load_persons()
        self._load_face_info()
        self._load_edited_face_info()
        self._load_folders()
        self._load_albums()
        self._load_keywords()
        self._load_volumes()
        self._build_photo_paths()

        # logger.debug(f"{self._db_photos=}")
        # logger.debug(f"{self._db_event_notes=}")
        # logger.debug(f"{self._db_places=}")
        # logger.debug(f"{self._db_properties=}")
        # logger.debug(f"{self._db_exif_info=}")
        # logger.debug(f"{self._db_persons=}")
        # logger.debug(f"{self._db_faces=}")
        # logger.debug(f"{self._db_faces_edited=}")
        # logger.debug(f"{self._db_folders=}")
        # logger.debug(f"{self._db_albums=}")
        # logger.debug(f"{self._db_volumes=}")

    def _load_library_db(self):
        """Load the Library.apdb database"""

        library_db = self.library_path.joinpath("Database/apdb/Library.apdb")
        query = """
        SELECT
        RKVersion.modelId AS id,
        RKVersion.masterId AS master_id,
        RKVersion.name AS title,
        RKFolder.name AS rollname,
        RKFolder.modelId AS roll,
        RKFolder.minImageDate AS roll_min_image_date,
        RKFolder.maxImageDate AS roll_max_image_date,
        RKFolder.minImageTimeZoneName AS roll_min_image_tz,
        RKFolder.maxImageTimeZoneName AS roll_max_image_tz,
        RKFolder.posterVersionUuid AS poster_version_uuid,
        -- event thumbnail image uuid
        RKFolder.createDate AS date_foldercreation,
        -- is this the 'imported as' date?
        RKVersion.uuid AS uuid,
        RKMaster.uuid AS master_uuid,
        -- master (unedited) image. Required for face rectangle conversion.
        -- RKVersion.versionNumber AS version_number,
        -- 1 if edited image, 0 if original image
        RKVersion.mainRating AS rating,
        -- TODO: Rating is always applied to the master image, not the edited one
        RKMaster.type AS mediatype, -- IMGT, VIDT
        RKMaster.imagePath AS imagepath,
        -- 2015/04/27/20150427-123456/FOO.RW2, yields Masters/$imagepath and
        -- Previews: either Previews/$imagepath/ or dirname($imagepath)/$uuid/basename($imagepath)
        -- ,RKVersion.createDate AS date_imported
        RKMaster.createDate AS date_imported,
        RKVersion.imageDate AS date_taken,
        -- ,RKMaster.imageDate AS datem
        RKVersion.exportImageChangeDate AS date_modified,
        -- ,RKMaster.fileCreationDate AS date_filecreation -- is this the 'date imported'? No
        -- ,RKMaster.fileModificationDate AS date_filemod
        -- ,replace(RKImportGroup.name, ' @ ', 'T') AS date_importgroup -- contains datestamp of import procedure for a group of files,
        -- but this is apparently incorrect for images before 2012 -> ignore
        RKVersion.imageTimeZoneName AS timezone,
        RKVersion.exifLatitude AS latitude,
        RKVersion.exifLongitude AS longitude,
        RKVersion.isHidden AS hidden,
        RKVersion.isFlagged AS flagged,
        RKVersion.isOriginal AS original,
        RKMaster.isInTrash AS in_trash,
        RKVersion.masterHeight AS master_height,
        -- Height of original image (master)
        RKVersion.masterWidth AS master_width,
        -- Width of original image (master)
        RKVersion.processedHeight AS processed_height,
        -- Height of processed (eg. cropped, rotated) image
        RKVersion.processedWidth AS processed_width,
        -- Width of processed (eg. cropped, rotated) image
        RKVersion.overridePlaceId AS place_id,
        -- modelId of Properties::RKPlace
        RKVersion.faceDetectionRotationFromMaster AS face_rotation,
        -- don't know, maybe a hint for face detection algorithm
        RKVersion.rotation AS rotation, -- was the original image rotated?
        RKVersion.hasAdjustments as hasadjustments,
        RKVersion.fileName as filename,
        RKMaster.fileVolumeUuid AS volume_uuid,
        RKMaster.isMissing AS ismissing,
        RKMaster.isTrulyRaw AS truly_raw,
        RKMaster.fileIsReference AS is_reference,
        RKMaster.originalFileSize as original_filesize,
        RKMaster.burstUuid as burst_uuid
        FROM RKVersion
        LEFT JOIN RKFolder ON RKVersion.projectUuid = RKFolder.uuid
        LEFT JOIN RKMaster ON RKMaster.uuid = RKVersion.masterUuid
        LEFT JOIN RKImportGroup ON RKMaster.importGroupUuid = RKImportGroup.uuid
        WHERE RKVersion.versionNumber = 1
        """
        logger.debug(f"Executing query: {query}")

        # open the database
        conn = sqlite3.connect(library_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        results = cursor.execute(query).fetchall()
        for row in results:
            self._db_photos[row["uuid"]] = dict(row)

        # normalize unicode
        for uuid in self._db_photos:
            self._db_photos[uuid]["title"] = normalize_unicode(
                self._db_photos[uuid]["title"]
            )
            self._db_photos[uuid]["rollname"] = normalize_unicode(
                self._db_photos[uuid]["rollname"]
            )
        self.verbose(f"Loaded {len(self._db_photos)} assets from iPhoto library")

        # Event notes (pre-iPhoto 9.1)
        query = """
            SELECT
            RKNote.modelId AS modelId,
            RKNote.note AS note,
            RKFolder.name AS name,
            RKFolder.uuid AS folder_uuid,
            RKFolder.modelId AS folder_model_id
            FROM RKNote
            LEFT JOIN RKFolder on RKNote.attachedToUuid = RKFolder.uuid
            WHERE RKFolder.name IS NOT NULL AND RKFolder.name != ''
            ORDER BY RKFolder.modelId
        """
        logger.debug(f"Executing query: {query}")

        self.verbose("Loading event notes from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            row = dict(row)
            row["note"] = normalize_unicode(row["note"])
            row["name"] = normalize_unicode(row["name"])
            self._db_event_notes[int(row["folder_model_id"])] = dict(row)
        conn.close()

    def _load_properties_db(self):
        """Load the Properties.apdb database"""
        properties_db = self.library_path.joinpath("Database/apdb/Properties.apdb")

        # Places
        query = """
            SELECT
            RKPlace.modelId,
            RKPlace.uuid,
            RKPlace.defaultName,
            RKPlace.minLatitude,
            RKPlace.minLongitude,
            RKPlace.maxLatitude,
            RKPlace.maxLongitude,
            RKPlace.centroid,
            RKPlace.userDefined
            FROM RKPlace
        """
        logger.debug(f"Executing query: {query}")

        conn = sqlite3.connect(properties_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        self.verbose("Loading places from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            self._db_places[int(row["modelId"])] = dict(row)

        # normalize unicode
        for model_id in self._db_places:
            self._db_places[model_id]["defaultName"] = normalize_unicode(
                self._db_places[model_id]["defaultName"]
            )

        # Properties
        query = """
            SELECT
            RKIptcProperty.modelId AS id,
            RKIptcProperty.versionId AS versionId,
            RKIptcProperty.modDate AS modDate,
            RKUniqueString.stringProperty AS string
            FROM RKIptcProperty
            LEFT JOIN RKUniqueString ON RKIptcProperty.stringId = RKUniqueString.modelId
            WHERE RKIptcProperty.propertyKey = 'Caption/Abstract' -- description
            ORDER BY versionId
        """
        logger.debug(f"Executing query: {query}")
        self.verbose("Loading properties from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            row = dict(row)
            row["string"] = normalize_unicode(row["string"])
            self._db_properties[row["versionId"]] = dict(row)

        # put description back into _db_photos
        # mapping of versionId -> RKVersion.modelID -> uuid
        version_id_to_uuid = {}
        for uuid, photo in self._db_photos.items():
            version_id = photo["id"]
            if version_id not in version_id_to_uuid:
                version_id_to_uuid[version_id] = uuid

        for version_id, data in self._db_properties.items():
            if uuid := version_id_to_uuid.get(version_id):
                self._db_photos[uuid]["description"] = data["string"]

        # orientation
        query = """
            SELECT
            RKOtherProperty.versionId AS version_id,
            RKUniqueString.stringProperty AS str
            FROM RKOtherProperty
            LEFT JOIN RKUniqueString ON RKUniqueString.modelId = RKOtherProperty.stringId
            WHERE RKOtherProperty.propertyKey = 'Orientation'
        """
        logger.debug(f"Executing query: {query}")

        self.verbose("Loading orientation from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            if uuid := version_id_to_uuid.get(row["version_id"]):
                self._db_photos[uuid]["orientation"] = row["str"].lower()

        # EXIF Properties
        query = """
            SELECT
            RKExifStringProperty.versionId as versionId,
            RKExifStringProperty.propertyKey AS property,
            RKUniqueString.stringProperty AS value
            FROM RKExifStringProperty
            INNER JOIN RKUniqueString ON RKUniqueString.modelId = RKExifStringProperty.stringId
        """
        logger.debug(f"Executing query: {query}")
        self.verbose("Loading EXIF properties from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            row = dict(row)
            row["value"] = normalize_unicode(row["value"])
            if row["versionId"] not in self._db_exif_info:
                self._db_exif_info[row["versionId"]] = {}
            self._db_exif_info[row["versionId"]][row["property"]] = row["value"]

        # EXIF data is stored separately whether string or numerical
        query = """
            SELECT
            RKExifNumberProperty.versionId AS versionId,
            RKExifNumberProperty.propertyKey AS property,
            RKExifNumberProperty.numberProperty AS value
            FROM RKExifNumberProperty
        """
        logger.debug(f"Executing query: {query}")
        results = cursor.execute(query).fetchall()
        for row in results:
            row = dict(row)
            if row["versionId"] not in self._db_exif_info:
                self._db_exif_info[row["versionId"]] = {}
            self._db_exif_info[row["versionId"]][row["property"]] = row["value"]

        conn.close()

    def _load_persons(self):
        """Load persons from Faces.db database"""

        faces_db = self.library_path.joinpath("Database/apdb/Faces.db")

        # Faces
        query = """
            SELECT
            modelId,
            uuid,
            faceKey as face_key,
            name,
            email
            FROM RKFaceName
        """
        logger.debug(f"Executing query: {query}")

        conn = sqlite3.connect(faces_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        self.verbose("Loading faces from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            self._db_persons[int(row["modelId"])] = dict(row)
        conn.close()

    def _load_face_info(self) -> dict[str, dict[Any, Any]]:
        """Load face info for each photo from database"""

        face_db = self.library_path.joinpath("Database/apdb/Faces.db")

        query = """
            SELECT
            RKDetectedFace.modelId, -- primary key
            RKDetectedFace.uuid AS detect_uuid, -- primary key
            RKDetectedFace.masterUuid, -- --> Library::RKMaster::uuid
            RKDetectedFace.faceKey AS face_key, -- --> RKFaceName::faceKey
            -- *relative* coordinates within *original, non-rotated* image (0..1)
            -- Y values are counted from the bottom in iPhoto, but X values are counted from the left like usual!
            RKDetectedFace.topLeftX,
            1 - RKDetectedFace.topLeftY AS topLeftY,
            RKDetectedFace.topRightX,
            1 - RKDetectedFace.topRightY AS topRightY,
            RKDetectedFace.bottomLeftX,
            1 - RKDetectedFace.bottomLeftY AS bottomLeftY,
            RKDetectedFace.bottomRightX,
            1 - RKDetectedFace.bottomRightY AS bottomRightY,
            abs(
                RKDetectedFace.topLeftX - RKDetectedFace.bottomRightX
            ) AS width,
            abs(
                RKDetectedFace.topLeftY - RKDetectedFace.bottomRightY
            ) AS height,
            RKDetectedFace.width AS image_width, -- TODO: check whether face was meant to be rotated?
            RKDetectedFace.height AS image_height,
            RKDetectedFace.faceDirectionAngle AS face_dir_angle,
            RKDetectedFace.faceAngle AS face_angle, -- always 0?
            RKDetectedFace.confidence AS confidence,
            RKDetectedFace.rejected AS rejected,
            RKDetectedFace.ignore AS ignore,
            RKFaceName.uuid AS name_uuid,
            RKFaceName.name AS name, -- more reliable, also seems to contain manually added names
            RKFaceName.fullName AS full_name, -- might be empty if person is not listed in user's address book
            RKFaceName.email AS email
            FROM RKDetectedFace
            LEFT JOIN RKFaceName ON RKFaceName.faceKey = RKDetectedFace.faceKey
            WHERE RKDetectedFace.masterUuid = ? -- master_uuid
            AND RKDetectedFace.ignore = 0
            AND RKDetectedFace.rejected = 0
            -- ORDER BY RKDetectedFace.modelId
    """
        logger.debug(f"Executing query: {query}")

        conn = sqlite3.connect(face_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        self.verbose("Loading face info from iPhoto library")
        for uuid, photo in self._db_photos.items():
            master_uuid = photo["master_uuid"]
            results = cursor.execute(query, (master_uuid,)).fetchall()
            self._db_photos[uuid]["faces"] = []
            for row in results:
                row = dict(row)
                # normalize unicode
                row["name"] = normalize_unicode(row["name"])
                row["full_name"] = normalize_unicode(row["full_name"])
                row["email"] = normalize_unicode(row["email"])
                # assign to library data for matching uuid
                self._db_photos[uuid]["faces"].append(row)
                self._db_faces[row["modelId"]] = row
        conn.close()

    def _load_edited_face_info(self):
        """Load edited face info for each photo from database"""

        library_db = self.library_path.joinpath("Database/apdb/Library.apdb")

        # get edited face info
        query = """
            SELECT
            RKVersionFaceContent.modelId AS id,
            RKVersionFaceContent.versionId AS version_id,
            RKVersionFaceContent.masterId AS master_id,
            RKVersionFaceContent.faceKey AS face_key,
            RKVersionFaceContent.faceRectLeft AS topLeftX, -- use same naming scheme as in 'faces'
            1 - RKVersionFaceContent.faceRectTop AS bottomRightY, -- Y values are counted from the bottom in this table!
            RKVersionFaceContent.faceRectWidth AS width,
            RKVersionFaceContent.faceRectHeight AS height,
            RKVersionFaceContent.faceRectWidth + RKVersionFaceContent.faceRectLeft AS bottomRightX,
            1 - RKVersionFaceContent.faceRectTop - RKVersionFaceContent.faceRectHeight AS topLeftY
            FROM RKVersionFaceContent
            WHERE RKVersionFaceContent.versionId = ? -- id of the photo
            ORDER BY RKVersionFaceContent.versionId
        """
        logger.debug(f"Executing query: {query}")

        conn = sqlite3.connect(library_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        self.verbose("Loading edited face info from iPhoto library")
        for photo in self._db_photos.values():
            version_id = photo["id"]
            results = cursor.execute(query, (version_id,)).fetchall()
            photo["edited_faces"] = []
            for row in results:
                row = dict(row)
                row[
                    "confidence"
                ] = 0.0  # TODO: figure out original face and use those values
                face_key = row["face_key"]
                for person in self._db_persons.values():
                    if face_key == person["face_key"]:
                        row["name"] = person["name"]
                        row["email"] = person["email"]
                        row["full_name"] = ""
                        break
                else:
                    row["name"] = ""
                    row["full_name"] = ""
                    row["email"] = ""
                # assign to library data for matching uuid
                photo["edited_faces"].append(row)
                self._db_faces_edited[row["id"]] = row
        conn.close()

    def _load_folders(self):
        """Load folders from iPhoto library"""
        # Get Folders and Albums. Convert to (hierarchical) keywords since "Albums" are nothing but tag collections.
        # Also get search criteria for "smart albums". Save into text file (for lack of better solution).
        # 1. Get folder structure, create tag pathnames as strings.
        #    Folders are just a pseudo hierarchy and can contain Albums and Smart Albums.

        library_db = self.library_path.joinpath("Database/apdb/Library.apdb")

        query = """
            SELECT
            modelId,
            uuid,
            folderType,
            name,
            parentFolderUuid,
            folderPath,
            isMagic,
            createDate as date,
            minImageDate AS min_image_date,
            maxImageDate AS max_image_date,
            minImageTimeZoneName AS min_image_tz,
            maxImageTimeZoneName AS max_image_tz
            FROM RKFolder
        """
        logger.debug(f"Executing query: {query}")

        conn = sqlite3.connect(library_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        self.verbose("Loading folders from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            self._db_folders[row["modelID"]] = dict(row)

        # normalize unicode
        for model_id in self._db_folders:
            self._db_folders[model_id]["name"] = normalize_unicode(
                self._db_folders[model_id]["name"]
            )
            self._db_folders[model_id]["folderPath"] = normalize_unicode(
                self._db_folders[model_id]["folderPath"]
            )

        # folderPath is a string like "modelId1/modelId2/...".
        # convert these using the real folder names to get the path strings.
        # the top level libray folder is always modelId 1 and has name ''
        for model_id, folder_data in self._db_folders.items():
            folder_list = []
            for folder_id in folder_data["folderPath"].split("/"):
                if folder_id == "":
                    continue
                folder_id = int(folder_id)
                folder_name = self._db_folders[folder_id]["name"]
                ismagic = bool(self._db_folders[folder_id]["isMagic"])
                if folder_name == "" or ismagic:
                    # skip magic folders like "TopLevelAlbums"
                    # if someone has a folder with no name, it will be skipped
                    continue
                folder_list.append(folder_name)
            self._db_folders[model_id]["folderlist"] = folder_list

        conn.close()

    def _load_albums(self):
        """Load albums from iPhoto library"""
        library_db = self.library_path.joinpath("Database/apdb/Library.apdb")

        query = """
            SELECT
            RKAlbumVersion.modelId,
            RKAlbumVersion.versionId, -- -->Library::RKVersion::modelId
            RKAlbumVersion.albumId,
            RKAlbum.name,
            RKAlbum.uuid as album_uuid,
            RKFolder.modelId AS folder_id,
            RKFolder.uuid AS folder_uuid
            FROM RKAlbumVersion
            LEFT JOIN RKAlbum ON RKAlbumVersion.albumId = RKAlbum.modelId
            LEFT JOIN RKFolder ON RKFolder.uuid = RKAlbum.folderUuid
        """
        logger.debug(f"Executing query: {query}")

        conn = sqlite3.connect(library_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        self.verbose("Loading albums from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            row = dict(row)
            row["name"] = normalize_unicode(row["name"])
            version_id = row["versionId"]
            if version_id not in self._db_albums:
                self._db_albums[version_id] = []
            self._db_albums[version_id].append(row)

        # get album hierarchy
        for albums in self._db_albums.values():
            for album in albums:
                album["path"] = [
                    *self._db_folders[album["folder_id"]]["folderlist"],
                    album["name"],
                ]

        # add album data to library data
        for uuid, library in self._db_photos.items():
            self._db_photos[uuid]["albums"] = self._db_albums.get(library["id"], [])

        conn.close()

    def _load_keywords(self):
        """Load keywords from the database"""

        db = self.library_path.joinpath("Database/apdb/Library.apdb")
        query = """
            SELECT
            RKVersion.uuid AS uuid,
            RKKeyword.modelId AS modelId,
            RKKeyword.name AS name
            FROM RKKeywordForVersion
            INNER JOIN RKversion ON RKKeywordForVersion.versionId=RKVersion.modelId
            INNER JOIN RKKeyword ON RKKeywordForVersion.keywordId=RKKeyword.modelId
        """
        logger.debug(f"Executing query: {query}")

        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        self.verbose("Loading keywords from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            uuid = row["uuid"]
            if uuid not in self._db_photos:
                # logger.warning(f"Missing uuid {uuid} in _db_library")
                continue
            if "keywords" not in self._db_photos[uuid]:
                self._db_photos[uuid]["keywords"] = []
            self._db_photos[uuid]["keywords"].append(normalize_unicode(row["name"]))
        conn.close()

    def _load_volumes(self):
        """Load volume data for referenced files"""
        library_db = self.library_path.joinpath("Database/apdb/Library.apdb")

        query = """
            SELECT
            RKVolume.uuid as uuid,
            RKVolume.name as name
            FROM RKVolume
        """
        logger.debug(f"Executing query: {query}")

        conn = sqlite3.connect(library_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        self.verbose("Loading volumes from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            # TODO: does unicode normalization make sense here?
            self._db_volumes[row["uuid"]] = row["name"]
        conn.close()

    def _build_photo_paths(self):
        """Build photo paths for each photo in the library"""

        # original path
        for uuid, photo in self._db_photos.items():
            if photo["is_reference"]:
                volume_uuid = photo["volume_uuid"]
                volume_name = self._db_volumes[volume_uuid]
                photo["photo_path"] = pathlib.Path("/Volumes").joinpath(
                    volume_name, photo["imagepath"]
                )
            else:
                photo["photo_path"] = self.library_path.joinpath(
                    "Masters", photo["imagepath"]
                )

            # derivative paths
            image_path = pathlib.Path(photo["imagepath"])
            path_previews = self.library_path.joinpath(
                "Thumbnails", image_path.parent, photo["uuid"]
            )
            derivatives = list(path_previews.glob("*"))
            # sort by size, largest first
            derivatives.sort(key=lambda x: x.stat().st_size, reverse=True)
            photo["path_derivatives"] = [str(x) for x in derivatives]

            # edited path
            if photo["hasadjustments"]:
                image_path = pathlib.Path(photo["imagepath"])
                path_edited = self.library_path.joinpath(
                    "Previews", image_path.parent, uuid
                )
                edited_files = list(path_edited.glob("*"))
                # edited image named with Photo's title not imagepath.stem
                if edited_files := [
                    x
                    for x in edited_files
                    if normalize_unicode(x.stem) == photo["title"]
                ]:
                    photo["path_edited"] = edited_files[0]
                else:
                    photo["path_edited"] = ""
            else:
                photo["path_edited"] = ""

    @cached_property
    def db_version(self) -> str:
        """Return the database version as stored in Library.apdb RKAdminData table"""
        library_db = self.library_path.joinpath("Database/apdb/Library.apdb")
        query = """
            SELECT
            propertyValue
            FROM RKAdminData
            WHERE propertyName IN ('versionMajor', 'versionMinor');
        """
        logger.debug(f"Executing query: {query}")

        conn = sqlite3.connect(library_db)
        cursor = conn.cursor()
        results = cursor.execute(query).fetchall()
        return ".".join(row[0] for row in results)

    @cached_property
    def photos_version(self) -> str:
        """Returns version of the library as a string"""
        library_db = self.library_path.joinpath("Database/apdb/Library.apdb")
        query = """
            SELECT
            propertyValue
            FROM RKAdminData
            WHERE propertyName IN ('applicationIdentifier');
        """
        logger.debug(f"Executing query: {query}")

        conn = sqlite3.connect(library_db)
        cursor = conn.cursor()
        results = cursor.execute(query).fetchall()
        return f"{results[0][0]} - {self.db_version}"

    def get_db_connection(self) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
        """Get connection to the working copy of the Photos database

        Returns:
            tuple of (connection, cursor) to sqlite3 database

        Raises:
            NotImplementedError on iPhoto
        """
        raise NotImplementedError("get_db_connection not implemented for iPhoto")

    @property
    def keywords_as_dict(self) -> dict[str, int]:
        """Return keywords as dict of list of keywords keyed by count of photos"""
        keywords = {}
        for photo in self._db_photos.values():
            if "keywords" in photo:
                for keyword in photo["keywords"]:
                    if keyword not in keywords:
                        keywords[keyword] = 0
                    keywords[keyword] += 1
        return keywords

    @property
    def persons_as_dict(self) -> dict[str, list[str]]:
        """Return persons as dict of list of persons keyed count of photos"""
        persons = {}
        for photo in self._db_photos.values():
            if photo["hasadjustments"]:
                face_list = photo.get("edited_faces", [])
            else:
                face_list = photo.get("faces", [])
            for face in face_list:
                face_name = face["name"]
                if face_name not in persons:
                    persons[face_name] = 0
                persons[face_name] += 1
        return persons

    @property
    def albums_as_dict(self) -> dict[str, int]:
        """Return albums as dict of list of albums keyed by count of photos"""
        albums = {}
        for photo in self._db_photos.values():
            for album in photo["albums"]:
                album_name = album["name"]
                if album_name not in albums:
                    albums[album_name] = 0
                albums[album_name] += 1
        return albums

    @property
    def album_info(self) -> list[iPhotoAlbumInfo]:
        """Return list of iPhotoAlbumInfo objects for each album in the library"""
        album_info = {}
        for albums in self._db_albums.values():
            for album in albums:
                if album["album_uuid"] not in album_info:
                    album_info[album["album_uuid"]] = iPhotoAlbumInfo(album, self)
        return list(album_info.values())

    @property
    def albums(self) -> list[str]:
        """Return list of album names"""
        return list(self.albums_as_dict.keys())

    def photos(
        self,
        keywords: list[str] | None = None,
        uuid: list[str] | None = None,
        persons: list[str] | None = None,
        albums: list[str] | None = None,
        images: bool = True,
        movies: bool = True,
        from_date: datetime.datetime | None = None,
        to_date: datetime.datetime | None = None,
        intrash: bool = False,
    ) -> list[iPhotoPhotoInfo]:
        """Return a list of iPhotoPhotoInfo objects
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
            list of iPhotoPhotoInfo objects
        """

        photos = [iPhotoPhotoInfo(uuid, self) for uuid in self._db_photos]
        if uuid:
            photos = [photo for photo in photos if photo.uuid in uuid]
        if not images:
            photos = [photo for photo in photos if not photo.isphoto]
        if not movies:
            photos = [photo for photo in photos if not photo.ismovie]
        if keywords:
            for keyword in keywords:
                photos = [
                    photo
                    for photo in photos
                    if photo.keywords and keyword in photo.keywords
                ]
        if persons:
            for person in persons:
                photos = [
                    photo
                    for photo in photos
                    if photo.persons and person in photo.persons
                ]
        if albums:
            for album in albums:
                photos = [
                    photo for photo in photos if photo.albums and album in photo.albums
                ]
        if from_date:
            if not datetime_has_tz(from_date):
                from_date = datetime_naive_to_local(from_date)
            photos = [photo for photo in photos if photo.date >= from_date]
        if to_date:
            if not datetime_has_tz(to_date):
                to_date = datetime_naive_to_local(to_date)
            photos = [photo for photo in photos if photo.date < to_date]
        if intrash:
            photos = [photo for photo in photos if photo.intrash]
        else:
            photos = [photo for photo in photos if not photo.intrash]
        return photos

    def get_photo(self, uuid: str) -> iPhotoPhotoInfo:
        """Return photo by uuid"""
        if uuid not in self._db_photos:
            raise ValueError(f"Photo with uuid {uuid} not found")
        return iPhotoPhotoInfo(uuid, self)

    def query(self, options: QueryOptions) -> list[iPhotoPhotoInfo]:
        """Run a query against PhotosDB to extract the photos based on user supplied options

        Args:
            options: a QueryOptions instance
        """
        return photo_query(self, options)

    def __len__(self) -> int:
        """Return number of photos in the library"""
        return len(self.photos())


class iPhotoPhotoInfo:
    """PhotoInfo implementation for iPhoto"""

    def __init__(self, uuid: str, db: iPhotoDB):
        self._uuid = uuid
        self._db = db
        self._info = self._db._db_photos[self._uuid]
        self._id = self._info["id"]  # modelID / versionId
        self._attributes = get_user_attributes(PhotoInfo)
        self._verbose = db._verbose  # compatibility with PhotoInfo

    @property
    def uuid(self) -> str:
        """UUID of photo"""
        return self._uuid

    @property
    def filename(self) -> str:
        """Filename of photo"""
        return self._db._db_photos[self._uuid]["filename"]

    @property
    def original_filename(self) -> str:
        """Original filename of photo"""
        return self._db._db_photos[self._uuid]["filename"]

    @property
    def isphoto(self) -> bool:
        """Return True if asset is a photo"""
        return self._db._db_photos[self._uuid]["mediatype"] == "IMGT"

    @property
    def ismovie(self) -> bool:
        """Return True if asset is a movie"""
        return self._db._db_photos[self._uuid]["mediatype"] == "VIDT"

    @property
    def israw(self) -> bool:
        """Return True if asset is a raw image"""
        return bool(self._db._db_photos[self._uuid]["truly_raw"])

    @property
    def raw_original(self) -> bool:
        """Return True if asset original is a raw image"""
        return bool(self._db._db_photos[self._uuid]["truly_raw"])

    @property
    def uti(self) -> str | None:
        """UTI of current version of photo (edited if hasadjustments, otherwise original)"""
        # this isn't stored in the database so we have to determine from filename
        if self.hasadjustments and self.path_edited:
            return get_uti_for_path(self.path_edited)
        return get_uti_for_path(self.filename)

    @property
    def uti_original(self) -> str | None:
        """UTI of original version of photo"""
        return get_uti_for_path(self.filename)

    @property
    def uti_edited(self) -> str | None:
        """UTI of edited version of photo"""
        return (
            get_uti_for_path(self.path_edited)
            if self.hasadjustments and self.path_edited
            else None
        )

    @property
    def uti_raw(self) -> str | None:
        """UTI of raw version of photo"""
        return get_uti_for_path(self.path) if self.israw else None

    @property
    def ismissing(self) -> bool:
        """Return True if asset is missing"""
        return self._db._db_photos[self._uuid]["ismissing"]

    @property
    def isreference(self) -> bool:
        """Return True if asset is a referenced file"""
        return self._db._db_photos[self._uuid]["is_reference"]

    @property
    def date(self) -> datetime.datetime:
        """Date photo was taken"""
        return iphoto_date_to_datetime(
            self._db._db_photos[self._uuid]["date_taken"],
            self._db._db_photos[self._uuid]["timezone"],
        )

    @property
    def date_modified(self) -> datetime.datetime:
        """Date modified in library"""
        return iphoto_date_to_datetime(
            self._db._db_photos[self._uuid]["date_modified"],
            self._db._db_photos[self._uuid]["timezone"],
        )

    @property
    def date_added(self) -> datetime.datetime:
        """Date added to library"""
        return iphoto_date_to_datetime(
            self._db._db_photos[self._uuid]["date_imported"],
            self._db._db_photos[self._uuid]["timezone"],
        )

    @property
    def tzoffset(self) -> int:
        """TZ Offset from GMT in seconds"""
        tzname = self._db._db_photos[self._uuid]["timezone"]
        if not tzname:
            return 0
        tz = ZoneInfo(tzname)
        return int(tz.utcoffset(datetime.datetime.now()).total_seconds())

    @property
    def path(self) -> str | None:
        """Path to original photo asset in library"""
        path = self._db._db_photos[self._uuid]["photo_path"]
        if path_exists(path):
            return str(path)
        logger.debug(f"Photo path {path} does not exist")
        return None

    @property
    def path_edited(self) -> str | None:
        """Path to edited asset in library"""
        path = self._db._db_photos[self._uuid]["path_edited"]
        if path_exists(path):
            return str(path)
        logger.debug(f"Edited photo path {path} does not exist")
        return None

    @property
    def path_derivatives(self) -> list[str]:
        """Path to derivatives in library"""
        # don't need to check for existence since we just globbed the directory
        return self._db._db_photos[self._uuid]["path_derivatives"]

    @property
    def description(self) -> str:
        """Description of photo"""
        return self._db._db_photos[self._uuid].get("description", "")

    @property
    def title(self) -> str | None:
        """Title of photo"""
        return self._db._db_photos[self._uuid].get("title", None)

    @property
    def favorite(self) -> bool:
        """Returns True if photo is favorite; iPhoto doesn't have favorite so always returns False"""
        return False

    @property
    def flagged(self) -> bool:
        """Returns True if photo is flagged"""
        return bool(self._db._db_photos[self._uuid].get("flagged", False))

    @property
    def rating(self) -> int:
        """Rating of photo as int from 0 to 5"""
        return self._db._db_photos[self._uuid]["rating"]

    @property
    def hidden(self) -> bool:
        """True if photo is hidden"""
        return bool(self._db._db_photos[self._uuid]["hidden"])

    @property
    def visible(self) -> bool:
        """True if photo is visible in Photos; always returns False for iPhoto"""
        logger.debug("visible not implemented for iPhoto")
        return False

    @property
    def intrash(self) -> bool:
        """True if photo is in the Photos trash"""
        return self._db._db_photos[self._uuid]["in_trash"]

    @property
    def persons(self) -> list[str]:
        """List of persons in photo"""
        faces = self._get_faces()
        persons = []
        for face in faces:
            if person := face["name"]:
                persons.append(person)
            else:
                persons.append(_UNKNOWN_PERSON)
        return persons

    @property
    def person_info(self) -> list[iPhotoPersonInfo]:
        """List of iPhotoPersonInfo objects for photo"""
        faces = self._get_faces()
        return [iPhotoPersonInfo(face, self._db) for face in faces]

    @property
    def face_info(self) -> list[iPhotoFaceInfo]:
        """List of iPhotoFaceInfo objects for photo"""
        faces = self._get_faces()
        return [iPhotoFaceInfo(self, face, self._db) for face in faces]

    @property
    def keywords(self) -> list[str]:
        """Keywords for photo"""
        return self._db._db_photos[self._uuid].get("keywords", [])

    @property
    def hasadjustments(self) -> bool:
        """True if photo has adjustments"""
        return bool(self._db._db_photos[self._uuid]["hasadjustments"])

    @property
    def width(self) -> int:
        """Width of photo in pixels"""
        return self._db._db_photos[self._uuid]["processed_width"]

    @property
    def height(self) -> int:
        """Height of photo in pixels"""
        return self._db._db_photos[self._uuid]["processed_height"]

    @property
    def original_width(self) -> int:
        """Original width of photo in pixels"""
        return self._db._db_photos[self._uuid]["master_width"]

    @property
    def original_height(self) -> int:
        """Original height of photo in pixels"""
        return self._db._db_photos[self._uuid]["master_height"]

    @property
    def latitude(self) -> float | None:
        """Latitude of photo"""
        return self._db._db_photos[self._uuid]["latitude"]

    @property
    def longitude(self) -> float | None:
        """Longitude of photo"""
        return self._db._db_photos[self._uuid]["longitude"]

    @property
    def location(self) -> tuple[float, float] | tuple[None, None]:
        """Location of photo as (latitude, longitude)"""
        return (self.latitude, self.longitude)

    @property
    def original_filesize(self) -> int:
        """Size of original file in bytes"""
        return self._db._db_photos[self._uuid]["original_filesize"]

    @property
    def albums(self) -> list[str]:
        """List of albums photo is contained in"""
        return [
            album["name"] for album in self._db._db_photos[self._uuid].get("albums", [])
        ]

    @property
    def album_info(self) -> list[iPhotoAlbumInfo]:
        """ "Return list of iPhotoAlbumInfo objects for photo"""
        return [
            iPhotoAlbumInfo(album, self._db)
            for album in self._db._db_photos[self._uuid].get("albums", [])
        ]

    @property
    def event_info(self) -> iPhotoEventInfo | None:
        """Return iPhotoEventInfo object for photo or None if photo is not in an event"""
        if event := self._db._db_photos[self._uuid].get("roll"):
            if event_data := self._db._db_folders.get(event):
                return iPhotoEventInfo(event_data, self._db)
        return None

    @property
    def moment_info(self) -> iPhotoMomentInfo | None:
        """Return iPhotoMomentInfo object for photo or None if photo is not in a moment; for iPhoto returns event as moment"""
        # iPhoto doesn't actually have moment so use event
        if event := self._db._db_photos[self._uuid].get("roll"):
            if event_data := self._db._db_folders.get(event):
                return iPhotoMomentInfo(event_data, self._db)
        return None

    @cached_property
    def fingerprint(self) -> str | None:
        """Returns fingerprint of original photo as a string; returns None if not available"""
        if not is_macos:
            logger.warning("fingerprint only supported on macOS")
            return None

        if not self.path:
            logger.debug(f"Missing path, cannot compute fingerprint for {self.uuid}")
            return None

        return fingerprint(self.path)

    @cached_property
    def exif_info(self) -> iPhotoExifInfo:
        """Return iPhotoExifInfo object for photo"""

        exif_info = self._db._db_exif_info.get(self._id, {})
        return iPhotoExifInfo(
            flash_fired=bool(exif_info.get("Flash", False)),
            iso=exif_info.get("ISOSpeedRating", 0),
            metering_mode=exif_info.get("MeteringMode", 0),
            sample_rate=0,
            track_format=0,
            white_balance=exif_info.get("WhiteBalance", 0),
            aperture=exif_info.get("ApertureValue", 0.0),
            bit_rate=exif_info.get("DataRate", 0.0),
            duration=exif_info.get("MovieDuration", 0.0),
            exposure_bias=exif_info.get("ExposureBiasValue", 0.0),
            focal_length=exif_info.get("FocalLength", 0.0),
            fps=exif_info.get("FPS", 0.0),
            latitude=exif_info.get("Latitude", 0.0),
            longitude=exif_info.get("Longitude", 0.0),
            shutter_speed=exif_info.get("ShutterSpeed", 0.0),
            camera_make=exif_info.get("Make", ""),
            camera_model=exif_info.get("Model", ""),
            codec="",
            lens_model=exif_info.get("LensModel", ""),
            software=exif_info.get("Software", ""),
            dict=exif_info,
        )

    @property
    def burst_albums(self) -> list[str]:
        """For iPhoto, returns self.albums; this is different behavior than Photos"""
        return self.albums

    @property
    def burst_album_info(self) -> list[iPhotoAlbumInfo]:
        """For iPhoto, returns self.album_info; this is different behavior than Photos"""
        return self.album_info

    @property
    def burst(self) -> bool:
        """Returns True if photo is part of a Burst photo set, otherwise False"""
        return bool(self._info["burst_uuid"])

    @property
    def burst_photos(self) -> list[PhotoInfo]:
        """If photo is a burst photo, returns list of iPhotoPhotoInfo objects
        that are part of the same burst photo set; otherwise returns empty list.
        self is not included in the returned list"""
        if not self.burst:
            return []

        burst_uuid = self._info["burst_uuid"]
        return [
            iPhotoPhotoInfo(uuid, self._db)
            for uuid in self._db._db_photos
            if uuid != self.uuid
            and self._db._db_photos[uuid]["burst_uuid"] == burst_uuid
        ]

    @cached_property
    def hexdigest(self) -> str:
        """Returns a unique digest of the photo's properties and metadata;
        useful for detecting changes in any property/metadata of the photo"""
        return hexdigest(self._json_hexdigest())

    @property
    def score(self) -> ScoreInfo:
        return ScoreInfo(
            overall=0.0,
            curation=0.0,
            promotion=0.0,
            highlight_visibility=0.0,
            behavioral=0.0,
            failure=0.0,
            harmonious_color=0.0,
            immersiveness=0.0,
            interaction=0.0,
            interesting_subject=0.0,
            intrusive_object_presence=0.0,
            lively_color=0.0,
            low_light=0.0,
            noise=0.0,
            pleasant_camera_tilt=0.0,
            pleasant_composition=0.0,
            pleasant_lighting=0.0,
            pleasant_pattern=0.0,
            pleasant_perspective=0.0,
            pleasant_post_processing=0.0,
            pleasant_reflection=0.0,
            pleasant_symmetry=0.0,
            sharply_focused_subject=0.0,
            tastefully_blurred=0.0,
            well_chosen_subject=0.0,
            well_framed_subject=0.0,
            well_timed_shot=0.0,
        )

    def export(
        self,
        dest: str,
        filename: str | None = None,
        edited: bool = False,
        raw_photo: bool = False,
        export_as_hardlink: bool = False,
        overwrite: bool = False,
        increment: bool = True,
        sidecar_json: bool = False,
        sidecar_exiftool: bool = False,
        sidecar_xmp: bool = False,
        exiftool: bool = False,
        use_albums_as_keywords: bool = False,
        use_persons_as_keywords: bool = False,
        keyword_template: list[str] | None = None,
        description_template: str | None = None,
        render_options: RenderOptions | None = None,
        **kwargs,
    ) -> list[str]:
        """Export a photo

        Args:
            dest: must be valid destination path (or exception raised)
            filename: (optional): name of exported picture; if not provided, will use current filename
              **NOTE**: if provided, user must ensure file extension (suffix) is correct.
              For example, if photo is .CR2 file, edited image may be .jpeg.
              If you provide an extension different than what the actual file is,
              export will print a warning but will export the photo using the
              incorrect file extension (unless use_photos_export is true, in which case export will
              use the extension provided by Photos upon export; in this case, an incorrect extension is
              silently ignored).
              e.g. to get the extension of the edited photo,
              reference iPhotoPhotoInfo.path_edited
            edited: (boolean, default=False); if True will export the edited version of the photo, otherwise exports the original version
              (or raise exception if no edited version)
            raw_photo: (boolean, default=False); if True, will also export the associated RAW photo
            export_as_hardlink: (boolean, default=False); if True, will hardlink files instead of copying them
            overwrite: (boolean, default=False); if True will overwrite files if they already exist
            increment: (boolean, default=True); if True, will increment file name until a non-existant name is found
              if overwrite=False and increment=False, export will fail if destination file already exists
            sidecar_json: if set will write a json sidecar with data in format readable by exiftool
              sidecar filename will be dest/filename.json; includes exiftool tag group names (e.g. `exiftool -G -j`)
            sidecar_exiftool: if set will write a json sidecar with data in format readable by exiftool
              sidecar filename will be dest/filename.json; does not include exiftool tag group names (e.g. `exiftool -j`)
            sidecar_xmp: if set will write an XMP sidecar with IPTC data
              sidecar filename will be dest/filename.xmp
            exiftool: (boolean, default = False); if True, will use exiftool to write metadata to export file
            returns list of full paths to the exported files
            use_albums_as_keywords: (boolean, default = False); if True, will include album names in keywords
            when exporting metadata with exiftool or sidecar
            use_persons_as_keywords: (boolean, default = False); if True, will include person names in keywords
            when exporting metadata with exiftool or sidecar
            keyword_template: (list of strings); list of template strings that will be rendered as used as keywords
            description_template: string; optional template string that will be rendered for use as photo description
            render_options: an optional osxphotos.phototemplate.RenderOptions instance with options to pass to template renderer

        Returns: list of paths to photos exported
        """

        if kwargs:
            raise NotImplementedError(
                f"Unsupported export options: {', '.join(kwargs.keys())}"
            )

        exporter = PhotoExporter(self)
        sidecar = 0
        if sidecar_json:
            sidecar |= SIDECAR_JSON
        if sidecar_exiftool:
            sidecar |= SIDECAR_EXIFTOOL
        if sidecar_xmp:
            sidecar |= SIDECAR_XMP

        if not filename:
            if not edited:
                filename = self.original_filename
            else:
                original_name = pathlib.Path(self.original_filename)
                if self.path_edited:
                    ext = pathlib.Path(self.path_edited).suffix
                else:
                    uti = self.uti_edited if edited and self.uti_edited else self.uti
                    ext = get_preferred_uti_extension(uti)
                    ext = f".{ext}"
                filename = f"{original_name.stem}_edited{ext}"

        options = ExportOptions(
            description_template=description_template,
            edited=edited,
            exiftool=exiftool,
            export_as_hardlink=export_as_hardlink,
            increment=increment,
            keyword_template=keyword_template,
            overwrite=overwrite,
            raw_photo=raw_photo,
            render_options=render_options,
            sidecar=sidecar,
            use_albums_as_keywords=use_albums_as_keywords,
            use_persons_as_keywords=use_persons_as_keywords,
        )

        results = exporter.export(dest, filename=filename, options=options)
        return results.exported

    def render_template(
        self, template_str: str, options: RenderOptions | None = None
    ) -> tuple[list[str], list[str]]:
        """Renders a template string for iPhotoPhotoInfo instance using PhotoTemplate

        Args:
            template_str: a template string with fields to render
            options: a RenderOptions instance

        Returns:
            ([rendered_strings], [unmatched]): tuple of list of rendered strings and list of unmatched template values
        """
        options = options or RenderOptions()
        template = PhotoTemplate(self, exiftool_path=self._db._exiftool_path)
        return template.render(template_str, options)

    @cached_property
    def exiftool(self) -> ExifToolCaching | None:
        """Returns a ExifToolCaching (read-only instance of ExifTool) object for the photo.
        Requires that exiftool (https://exiftool.org/) be installed
        If exiftool not installed, logs warning and returns None
        If photo path is missing, returns None
        """
        try:
            exiftool_path = self._db._exiftool_path or get_exiftool_path()
            if self.path is not None and pathlib.Path(self.path).is_file():
                exiftool = ExifToolCaching(self.path, exiftool=exiftool_path)
            else:
                exiftool = None
        except FileNotFoundError:
            # get_exiftool_path raises FileNotFoundError if exiftool not found
            exiftool = None
            logging.warning(
                "exiftool not in path; download and install from https://exiftool.org/"
            )
        return exiftool

    def asdict(self, shallow: bool = True) -> dict[str, Any]:
        """Return dict representation of iPhotoPhotoInfo object.

        Args:
            shallow: if True, return shallow representation (does not contain folder_info, person_info, etc.)

        Returns:
            dict representation of iPhotoPhotoInfo object

        Note:
            The shallow representation is used internally by export as it contains only the subset of data needed for export.
        """

        comments = [comment.asdict() for comment in self.comments]
        exif_info = dataclasses.asdict(self.exif_info) if self.exif_info else {}
        face_info = [face.asdict() for face in self.face_info]
        folders = {album.title: album.folder_names for album in self.album_info}
        likes = [like.asdict() for like in self.likes]
        place = self.place.asdict() if self.place else {}
        score = dataclasses.asdict(self.score) if self.score else {}

        # do not add any new properties to data_dict as this is used by export to determine
        # if a photo needs to be re-exported and adding new properties may cause all photos
        # to be re-exported
        # see below `if not shallow:`
        dict_data = {
            "albums": self.albums,
            "burst": self.burst,
            "cloud_guid": self.cloud_guid,
            "cloud_owner_hashed_id": self.cloud_owner_hashed_id,
            "comments": comments,
            "date_added": self.date_added,
            "date_modified": self.date_modified,
            "date_trashed": self.date_trashed,
            "date": self.date,
            "description": self.description,
            "exif_info": exif_info,
            "external_edit": self.external_edit,
            "face_info": face_info,
            "favorite": self.favorite,
            "filename": self.filename,
            "fingerprint": self.fingerprint,
            "folders": folders,
            "has_raw": self.has_raw,
            "hasadjustments": self.hasadjustments,
            "hdr": self.hdr,
            "height": self.height,
            "hidden": self.hidden,
            "incloud": self.incloud,
            "intrash": self.intrash,
            "iscloudasset": self.iscloudasset,
            "ismissing": self.ismissing,
            "ismovie": self.ismovie,
            "isphoto": self.isphoto,
            "israw": self.israw,
            "isreference": self.isreference,
            "keywords": self.keywords,
            "labels": self.labels,
            "latitude": self._latitude,
            "library": self._db._library_path,
            "likes": likes,
            "live_photo": self.live_photo,
            "location": self.location,
            "longitude": self._longitude,
            "orientation": self.orientation,
            "original_filename": self.original_filename,
            "original_filesize": self.original_filesize,
            "original_height": self.original_height,
            "original_orientation": self.original_orientation,
            "original_width": self.original_width,
            "owner": self.owner,
            "panorama": self.panorama,
            "path_edited_live_photo": self.path_edited_live_photo,
            "path_edited": self.path_edited,
            "path_live_photo": self.path_live_photo,
            "path_raw": self.path_raw,
            "path": self.path,
            "persons": self.persons,
            "place": place,
            "portrait": self.portrait,
            "raw_original": self.raw_original,
            "score": score,
            "screenshot": self.screenshot,
            "selfie": self.selfie,
            "shared": self.shared,
            "slow_mo": self.slow_mo,
            "time_lapse": self.time_lapse,
            "title": self.title,
            "tzoffset": self.tzoffset,
            "uti_edited": self.uti_edited,
            "uti_original": self.uti_original,
            "uti_raw": self.uti_raw,
            "uti": self.uti,
            "uuid": self.uuid,
            "visible": self.visible,
            "width": self.width,
        }

        # non-shallow keys
        # add any new properties here
        if not shallow:
            dict_data["album_info"] = [album.asdict() for album in self.album_info]
            dict_data["path_derivatives"] = self.path_derivatives
            dict_data["adjustments"] = (
                self.adjustments.asdict() if self.adjustments else {}
            )
            dict_data["burst_album_info"] = [a.asdict() for a in self.burst_album_info]
            dict_data["burst_albums"] = self.burst_albums
            dict_data["burst_default_pick"] = self.burst_default_pick
            dict_data["burst_key"] = self.burst_key
            dict_data["burst_photos"] = [p.uuid for p in self.burst_photos]
            dict_data["burst_selected"] = self.burst_selected
            dict_data["cloud_metadata"] = self.cloud_metadata
            dict_data["import_info"] = (
                self.import_info.asdict() if self.import_info else {}
            )
            dict_data["labels_normalized"] = self.labels_normalized
            dict_data["person_info"] = [p.asdict() for p in self.person_info]
            dict_data["project_info"] = [p.asdict() for p in self.project_info]
            dict_data["search_info"] = (
                self.search_info.asdict() if self.search_info else {}
            )
            dict_data["search_info_normalized"] = (
                self.search_info_normalized.asdict()
                if self.search_info_normalized
                else {}
            )
            dict_data["syndicated"] = self.syndicated
            dict_data["saved_to_library"] = self.saved_to_library
            dict_data["shared_moment"] = self.shared_moment
            dict_data["shared_library"] = self.shared_library

        return dict_data

    def json(self, indent: int | None = None, shallow: bool = True) -> str:
        """Return JSON representation

        Args:
            indent: indent level for JSON, if None, no indent
            shallow: if True, return shallow JSON representation (does not contain folder_info, person_info, etc.)

        Returns:
            JSON string

        Note:
            The shallow representation is used internally by export as it contains only the subset of data needed for export.
        """

        def default(o):
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()

        dict_data = self.asdict(shallow=True) if shallow else self.asdict(shallow=False)

        for k, v in dict_data.items():
            # sort lists such as keywords so JSON is consistent
            # but do not sort certain items like location
            if k in ["location"]:
                continue
            if v and isinstance(v, (list, tuple)) and not isinstance(v[0], dict):
                dict_data[k] = sorted(v, key=lambda v: v if v is not None else "")
        return json.dumps(dict_data, sort_keys=True, default=default, indent=indent)

    def _json_hexdigest(self) -> str:
        """JSON for use by hexdigest()"""

        # This differs from json() because hexdigest must not change if metadata changed
        # With json(), sort order of lists of dicts is not consistent but these aren't needed
        # for computing hexdigest so we can ignore them
        # also don't use visible because it changes based on Photos UI state

        def default(o):
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()

        dict_data = self.asdict(shallow=True)

        for k in ["face_info", "visible"]:
            del dict_data[k]

        for k, v in dict_data.items():
            # sort lists such as keywords so JSON is consistent
            # but do not sort certain items like location
            if k in ["location"]:
                continue
            if v and isinstance(v, (list, tuple)) and not isinstance(v[0], dict):
                dict_data[k] = sorted(v, key=lambda v: v if v is not None else "")
        return json.dumps(dict_data, sort_keys=True, default=default)

    def _get_faces(self) -> list[dict[str, Any]]:
        """Get faces for photo"""
        return (
            self._db._db_photos[self._uuid].get("edited_faces", [])
            if self.hasadjustments
            else self._db._db_photos[self._uuid].get("faces", [])
        )

    def __getattr__(self, name: str) -> Any:
        """If attribute is not found in iPhotoPhotoInfo, look at PhotoInfo and return default type"""
        if name not in self._attributes:
            raise AttributeError(f"Invalid attribute: {name}")
        logger.debug(f"Returning default value for {name}; not implemented for iPhoto")
        try:
            return default_return_value(self._attributes[name])
        except Exception as e:
            # on <= Python 3.9, default_return_value can raise exception for Union types
            logger.warning("Error getting default value for {name}: {e}")
            return None


class iPhotoPersonInfo:
    """PersonInfo implementation for iPhoto"""

    def __init__(self, face: dict[str, Any], db: iPhotoDB):
        self._face = face
        self._db = db

        face_key = self._face["face_key"]
        for person in self._db._db_persons.values():
            if face_key == person["face_key"]:
                self._person = person
                break
        else:
            logger.debug(f"Didn't find person for face {face_key}")
            self._person = {}

    @property
    def uuid(self) -> str:
        """UUID of person"""
        return self._person.get("uuid", "")

    @property
    def name(self) -> str:
        """Name of person"""
        # self._person["name"] could be None
        return self._person.get("name") or _UNKNOWN_PERSON

    @property
    def keyphoto(self) -> iPhotoPhotoInfo | None:
        """Key photo for person"""
        logger.debug("Not implemented for iPhoto")
        return None

    @property
    def keyface(self) -> iPhotoFaceInfo | None:
        """Key face for person"""
        logger.debug("Not implemented for iPhoto")
        return None

    @property
    def photos(self) -> list[iPhotoPhotoInfo]:
        """List of photos face is contained in"""
        photos = []
        for uuid, photo in self._db._db_photos:
            photos.extend(
                iPhotoPhotoInfo(uuid, self._db)
                for face in photo["faces"]
                if face["face_key"] == self._face["face_key"]
            )
        return photos

    @property
    def facecount(self) -> int:
        """Count of faces for person"""
        faces = 0
        for photo in self._db._db_photos.values():
            for face in photo["faces"]:
                if face["face_key"] == self._face["face_key"]:
                    faces += 1
        return faces

    @property
    def favorite(self) -> bool:
        """Returns False for iPhoto"""
        logger.debug("Not implemented for iPhoto")
        return False

    @property
    def sort_order(self) -> int:
        """Always returns 0 for iPhoto"""
        logger.debug("Not implemented for iPhoto")
        return 0

    @property
    def feature_less(self) -> bool:
        """Always returns False for iPhoto"""
        logger.debug("Not implemented for iPhoto")
        return False

    def asdict(self) -> dict[str, Any]:
        """Return person as dict"""
        return {
            "uuid": self.uuid,
            "name": self.name,
            "displayname": self.name,
            "keyface": self.keyface,
            "facecount": self.facecount,
            "keyphoto": self.keyphoto,
            "favorite": self.favorite,
            "sort_order": self.sort_order,
            "feature_less": self.feature_less,
        }

    def json(self) -> str:
        """Return person as json"""
        return json.dumps(self.asdict())


class iPhotoFaceInfo:
    """FaceInfo implementation for iPhoto"""

    def __init__(self, photo: iPhotoPhotoInfo, face: dict[str, Any], db: iPhotoDB):
        self._face = face
        self._db = db
        self.photo = photo

        face_key = self._face["face_key"]
        for person in self._db._db_persons.values():
            if face_key == person["face_key"]:
                self._person = person
                break
        else:
            logger.debug(f"Didn't find person for face {face_key}")
            self._person = {}

    @property
    def name(self) -> str | None:
        """Name of person in the photo or None"""
        # self._person["name"] could be None
        return self._person.get("name") or _UNKNOWN_PERSON

    @property
    def center(self) -> tuple[int, int]:
        """Coordinates, in PIL format, for center of face

        Returns:
            tuple of coordinates in form (x, y)
        """
        return self._make_point((self.center_x, self.center_y))

    @property
    def center_x(self) -> float:
        """X coordinate for center of face as percent of width"""
        return self._face["topLeftX"] + self._face["width"] / 2

    @property
    def center_y(self) -> float:
        """Y coordinate for center of face as percent of height"""
        if self.photo._info["orientation"] == "portrait":
            # y coords are reversed for portraits
            return self._face["bottomRightY"] + self._face["height"] / 2
        return self._face["topLeftY"] + self._face["height"] / 2

    @property
    def quality(self) -> float:
        """Quality (confidence) of face detection"""
        return self._face["confidence"]

    def _make_point(self, xy: tuple[int, int]) -> tuple[int, int]:
        """Translate an (x, y) tuple based on image orientation
            and convert to image coordinates

        Arguments:
            xy: tuple of (x, y) coordinates for point to translate
                in format used by Photos (percent of height/width)

        Returns:
            (x, y) tuple of translated coordinates in pixels in PIL format/reference frame
        """

        x, y = xy

        photo = self.photo
        if photo.hasadjustments:
            # edited version
            dx = photo.width
            dy = photo.height
        else:
            # original version
            dx = photo.original_width
            dy = photo.original_height
        return (int(x * dx), int(y * dy))

    @property
    def size(self) -> float:
        """Size of face as percent of image width"""
        return self._face["width"]

    @property
    def size_pixels(self) -> int:
        """Size of face in pixels (centered around center_x, center_y)

        Returns:
            size, in int pixels, of a circle drawn around the center of the face
        """
        width = (
            self.photo.width if self.photo.hasadjustments else self.photo.original_width
        )
        return self._face["width"] * width

    @property
    def person_info(self) -> iPhotoPersonInfo:
        """iPhotoPersonInfo object for face"""
        return iPhotoPersonInfo(self._face, self._db)

    def roll_pitch_yaw(self) -> tuple[float, float, float]:
        """Roll, pitch, yaw of face in radians as tuple"""
        return (0, 0, 0)

    @property
    def roll(self) -> float:
        """Return roll angle in radians of the face region"""
        roll, _, _ = self.roll_pitch_yaw()
        return roll

    @property
    def pitch(self) -> float:
        """Return pitch angle in radians of the face region"""
        _, pitch, _ = self.roll_pitch_yaw()
        return pitch

    @property
    def yaw(self) -> float:
        """Return yaw angle in radians of the face region"""
        _, _, yaw = self.roll_pitch_yaw()
        return yaw

    @property
    def mwg_rs_area(self) -> MWG_RS_Area:
        """Get coordinates for Metadata Working Group Region Area.

        Returns:
            MWG_RS_Area named tuple with x, y, h, w where:
            x = stArea:x
            y = stArea:y
            h = stArea:h
            w = stArea:w

        Reference:
            https://photo.stackexchange.com/questions/106410/how-does-xmp-define-the-face-region
        """
        x, y = self.center_x, self.center_y
        w = self._face["width"]
        h = self._face["height"]

        return MWG_RS_Area(x, y, h, w)

    @property
    def mpri_reg_rect(self) -> MPRI_Reg_Rect:
        """Get coordinates for Microsoft Photo Region Rectangle.

        Returns:
            MPRI_Reg_Rect named tuple with x, y, h, w where:
            x = x coordinate of top left corner of rectangle
            y = y coordinate of top left corner of rectangle
            h = height of rectangle
            w = width of rectangle

        Reference:
            https://docs.microsoft.com/en-us/windows/win32/wic/-wic-people-tagging
        """
        # x, y = self.center_x, self.center_y

        photo = self.photo
        if photo.hasadjustments:
            # edited version
            image_width = photo.width
            image_height = photo.height
        else:
            # original version
            image_width = photo.original_width
            image_height = photo.original_height

        h = self.size_pixels / image_width
        w = self.size_pixels / image_height
        x = int(self._face["topLeftX"] * image_width)

        if photo._info["orientation"] == "portrait":
            # y coords are reversed for portraits
            y = int(self._face["bottomRightY"] * image_height)
        else:
            y = int(self._face["topLeftY"] * image_height)

        return MPRI_Reg_Rect(x, y, h, w)

    def face_rect(self) -> list[tuple[int, int]]:
        """Get face rectangle coordinates for current version of the associated image
            If image has been edited, rectangle applies to edited version, otherwise original version
            Coordinates in format and reference frame used by PIL

        Returns:
            list [(x0, x1), (y0, y1)] of coordinates in reference frame used by PIL
        """
        photo = self.photo
        if photo.hasadjustments:
            # edited version
            image_width = photo.width
            image_height = photo.height
        else:
            # original version
            image_width = photo.original_width
            image_height = photo.original_height

        # convert to PIL format
        # sourcery skip: hoist-statement-from-if
        if self.photo._info["orientation"] == "portrait":
            # y coordinates are reversed
            x0 = int(self._face["topLeftX"] * image_width)
            y0 = int(self._face["bottomRightY"] * image_height)
            x1 = int(self._face["bottomRightX"] * image_width)
            y1 = int(self._face["topLeftY"] * image_height)
        else:
            x0 = int(self._face["topLeftX"] * image_width)
            y0 = int(self._face["topLeftY"] * image_height)
            x1 = int(self._face["bottomRightX"] * image_width)
            y1 = int(self._face["bottomRightY"] * image_height)
        return [(x0, y0), (x1, y1)]

    def asdict(self) -> dict[str, Any]:
        """Returns dict representation of class instance"""
        # roll, pitch, yaw = self.roll_pitch_yaw()
        return {
            # "uuid": self.uuid,
            "name": self.name,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "center": self.center,
            "size": self.size,
            "face_rect": self.face_rect(),
            "mpri_reg_rect": self.mpri_reg_rect._asdict(),
            "mwg_rs_area": self.mwg_rs_area._asdict(),
            "quality": self.quality,
            # "source_width": self.source_width,
            # "source_height": self.source_height,
        }

    def json(self) -> str:
        """Return JSON representation of iPhotoFaceInfo instance"""
        return json.dumps(self.asdict())


class iPhotoAlbumInfo:
    """AlbumInfo class for iPhoto"""

    def __init__(self, album: dict[str, Any], db: iPhotoDB):
        self._album = album
        self._db = db
        self._album_id = album["albumId"]

    @property
    def uuid(self) -> str:
        """UUID of album"""
        return self._album["album_uuid"]

    @property
    def title(self) -> str:
        """Title of album"""
        return self._album["name"]

    @property
    def photos(self) -> list[iPhotoPhotoInfo]:
        """Return list of photos contained in the album"""
        photos = []
        for uuid, photo in self._db._db_photos.items():
            for album in photo["albums"]:
                if album["albumId"] == self._album_id:
                    photos.append(iPhotoPhotoInfo(uuid, self._db))
                    break
        return photos

    @property
    def folder_names(self) -> list[str]:
        """Return hierarchical list of folders the album is contained in
        the folder list is in form:
        ["Top level folder", "sub folder 1", "sub folder 2", ...]
        or empty list if album is not in any folders
        """
        path = self._album["path"]
        if path:
            path = path[:-1]  # remove album name from end of path
        return path

    @property
    def folder_list(self) -> list[iPhotoFolderInfo]:
        """Returns hierachical list of iPhotoFolderInfo objects for each folder the album is contained in
        or empty list if album is not in any folders
        """
        folder_list = []
        parent = self.parent
        while parent:
            folder_list.insert(0, parent)
            parent = parent.parent
        return folder_list

    @property
    def parent(self) -> iPhotoFolderInfo | None:
        """returns iPhotoFolderInfo object for parent folder or None if no parent (e.g. top-level album)"""
        parent_id = self._album["folder_id"]
        parent_folder = self._db._db_folders[parent_id]
        if bool(parent_folder["isMagic"]):
            return None
        return iPhotoFolderInfo(parent_folder, self._db)

    @property
    def sort_order(self) -> int:
        """Return sort order; not implemented, always 0"""
        logger.debug("Not implemented for iPhoto")
        return 0

    def photo_index(self, photo: iPhotoPhotoInfo) -> int:
        """Return index of photo in album; not implemented, always 0"""
        logger.debug("Not implemented for iPhoto")
        return 0

    def asdict(self) -> dict[str, Any]:
        """Return album info as a dict; does not include photos"""
        return {
            "uuid": self.uuid,
            "title": self.title,
            "folder_names": self.folder_names,
            "folder_list": [f.uuid for f in self.folder_list],
            "sort_order": self.sort_order,
            "parent": self.parent.uuid if self.parent else None,
        }

    def json(self) -> str:
        """JSON representation of album"""
        return json.dumps(self.asdict())

    def __len__(self) -> int:
        """return number of photos contained in album"""
        return len(self.photos)


class iPhotoFolderInfo:
    """
    Info about a specific folder, contains all the details about the folder
    including folders, albums, etc
    """

    def __init__(self, folder: dict[Any, Any], db: iPhotoDB):
        self._folder = folder
        self._folderid = folder["modelId"]
        self._db = db

    @property
    def title(self) -> str:
        """Title of folder"""
        return self._folder["name"]

    @property
    def uuid(self) -> str:
        """UUID of folder"""
        return self._folder["uuid"]

    @property
    def album_info(self) -> list[iPhotoAlbumInfo]:
        """Return list of albums (as iPhotoAlbumInfo objects) contained in the folder"""
        folder_albums = []
        for albums in self._db._db_albums.values():
            folder_albums.extend(
                iPhotoAlbumInfo(album, self._db)
                for album in albums
                if album["folder_id"] == self._folderid
            )
        return folder_albums

    @property
    def parent(self) -> iPhotoFolderInfo | None:
        """Return iPhotoFolderInfo object for parent or None if no parent (e.g. top-level folder)"""
        if parent_uuid := self._folder["parentFolderUuid"]:
            return next(
                (
                    None
                    if bool(folder["isMagic"])
                    else iPhotoFolderInfo(folder, self._db)
                    for folder in self._db._db_folders.values()
                    if folder["uuid"] == parent_uuid
                ),
                None,
            )
        else:
            return None

    @property
    def subfolders(self) -> list[iPhotoFolderInfo]:
        """Return list of folders (as FolderInfo objects) contained in the folder"""
        subfolders = []
        for folder in self._db._db_folders.values():
            if folder["parentFolderUuid"] == self.uuid:
                if bool(folder["isMagic"]):
                    # skip magic folders like "TopLevelAlbums"
                    continue
                subfolders.append(iPhotoFolderInfo(folder, self._db))
        return subfolders

    def asdict(self) -> dict[str, Any]:
        """Return folder info as a dict"""
        return {
            "title": self.title,
            "uuid": self.uuid,
            "parent": self.parent.uuid if self.parent is not None else None,
            "subfolders": [f.uuid for f in self.subfolders],
            "albums": [a.uuid for a in self.album_info],
        }

    def json(self) -> str:
        """Return folder info as json"""
        return json.dumps(self.asdict())

    def __len__(self) -> int:
        """returns count of folders + albums contained in the folder"""
        return len(self.subfolders) + len(self.album_info)


class iPhotoEventInfo:
    """iPhoto Event info"""

    def __init__(self, event: dict[Any, Any], db: iPhotoDB):
        self._event = event
        # self._folderid = folder["modelId"]
        self._db = db

    @property
    def pk(self) -> int:
        """Primary key of the event."""
        return int(self._event.get("modelId", 0))

    @property
    def location(self) -> tuple[None, None]:
        """Location of the event."""
        logger.debug("Not implemented for iPhoto")
        return None, None

    @property
    def title(self) -> str:
        """Title of the event."""
        return str(self._event.get("name", ""))

    @property
    def subtitle(self) -> str:
        """Subtitle of the event."""
        logger.debug("Not implemented for iPhoto")
        return ""

    @property
    def start_date(self) -> datetime.datetime | None:
        """Start date of the event."""
        return iphoto_date_to_datetime(
            self._event["min_image_date"],
            self._event["min_image_tz"],
        )

    @property
    def end_date(self) -> datetime.datetime | None:
        """Stop date of the event."""
        return iphoto_date_to_datetime(
            self._event["max_image_date"],
            self._event["max_image_tz"],
        )

    @property
    def date(self) -> datetime.datetime | None:
        """Date of the event."""
        # use end_date as iPhoto doesn't record a separate date
        return self.end_date

    @property
    def _date_created(self) -> datetime.datetime | None:
        """Date the event created in iPhoto."""
        # not common with Photos MomentInfo so leave private
        return naive_iphoto_date_to_datetime(self._event["date"])

    @property
    def modification_date(self) -> datetime.datetime | None:
        """Modification date of the event."""
        logger.debug("Not implemented for iPhoto")
        return None

    @property
    def photos(self) -> list[iPhotoPhotoInfo]:
        """All photos in this moment"""
        roll = self._event.get("modelId")
        photos = [p for p in self._db._db_photos.values() if p.get("roll") == roll]
        return [iPhotoPhotoInfo(p["uuid"], self._db) for p in photos]

    @property
    def note(self) -> str:
        """Return note associated with event"""
        roll = self._event.get("modelId")
        if note := self._db._db_event_notes.get(roll):
            return note.get("note", "")
        return ""

    def asdict(self) -> dict[str, Any]:
        """Returns all moment info as dictionary"""
        return {
            "pk": self.pk,
            "location": self.location,
            "title": self.title,
            "subtitle": self.subtitle,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "date": self.date.isoformat() if self.date else None,
            "modification_date": self.modification_date.isoformat()
            if self.modification_date
            else None,
            "note": self.note,
            # "photos": self.photos,
        }


class iPhotoMomentInfo(iPhotoEventInfo):
    """Info about a photo moment; iPhoto doesn't have moments but Events are close"""

    ...


@dataclasses.dataclass(frozen=True)
class iPhotoExifInfo:
    """EXIF info associated with a photo from the iPhoto library"""

    flash_fired: bool
    iso: int
    metering_mode: int
    sample_rate: int
    track_format: int
    white_balance: int
    aperture: float
    bit_rate: float
    duration: float
    exposure_bias: float
    focal_length: float
    fps: float
    latitude: float
    longitude: float
    shutter_speed: float
    camera_make: str
    camera_model: str
    codec: str
    lens_model: str
    software: str
    dict: dict[str, Any]


### Utility functions ###


def iphoto_date_to_datetime(
    date: int | None, tz: str | None = None
) -> datetime.datetime:
    """ "Convert iPhoto date to datetime; if tz provided, will be timezone aware

    Args:
        date: iPhoto date
        tz: timezone name

    Returns:
        datetime.datetime

    Note:
        If date is None or invalid, will return 1970-01-01 00:00:00
    """
    try:
        dt = datetime.datetime.fromtimestamp(date + TIME_DELTA)
    except (ValueError, TypeError):
        dt = datetime.datetime(1970, 1, 1)
    if tz:
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    return dt


def naive_iphoto_date_to_datetime(date: int) -> datetime.datetime:
    """ "Convert iPhoto date to datetime with local timezone

    Args:
        date: iPhoto date

    Returns:
        timezone aware datetime.datetime in local timezone

    Note:
        If date is invalid, will return 1970-01-01 00:00:00
    """
    try:
        dt = datetime.datetime.fromtimestamp(date + TIME_DELTA)
    except ValueError:
        dt = datetime.datetime(1970, 1, 1)
    return datetime_naive_to_local(dt)


def default_return_value(name: str) -> Any:
    """Inspect name and return default value if there is one otherwise None
    optimized for PhotoInfo may not work for other classes.

    If used to inspect a method or function that uses '|' to indicate a UnionType,
    requires Python 3.10 or greater because get_type_hints will fail on union types
    in earlier versions of Python.
    """
    if isinstance(name, property):
        hints = get_type_hints(name.fget)
    elif isinstance(name, functools.cached_property):
        hints = get_type_hints(name.func)
    else:
        hints = get_type_hints(name)
    return_type = hints.get("return")

    # inspect return_type and take best guess at default value
    # needs to run on Python 3.9 so can't depend on types.UnionType (3.10)
    return_type = str(return_type)
    if "| None" in return_type:
        return None
    elif return_type == str(bool):
        return False
    elif return_type == str(str):
        return ""
    elif return_type == str(int):
        return 0
    elif return_type == str(float):
        return 0.0
    elif return_type.startswith("list[") or return_type.startswith("List["):
        return []
    elif "tuple[None, None]" in return_type:
        return (None, None)
    elif return_type.startswith("tuple[") or return_type.startswith("Tuple["):
        return ()
    elif return_type.startswith("dict[") or return_type.startswith("Dict["):
        return dict()
    elif return_type.startswith("set[") or return_type.startswith("Set["):
        return set()
    else:
        logger.warning(f"Unknown return type: {return_type}")
    return None


def get_user_attributes(cls: Any) -> dict[str, Any]:
    """Get user attributes from a class"""
    # reference: https://stackoverflow.com/questions/4241171/inspect-python-class-attributes
    builtin_attributes = dir(type("dummy", (object,), {}))
    attrs = {}
    bases = reversed(inspect.getmro(cls))
    for base in bases:
        if hasattr(base, "__dict__"):
            attrs.update(base.__dict__)
        elif hasattr(base, "__slots__"):
            if hasattr(base, base.__slots__[0]):
                # We're dealing with a non-string sequence or one char string
                for item in base.__slots__:
                    attrs[item] = getattr(base, item)
            else:
                # We're dealing with a single identifier as a string
                attrs[base.__slots__] = getattr(base, base.__slots__)
    for key in builtin_attributes:
        del attrs[key]  # we can be sure it will be present so no need to guard this
    return attrs


def is_iphoto_library(library: str | pathlib.Path | os.PathLike) -> bool:
    """Return True if library is an iPhoto library, else False"""
    library = library if isinstance(library, pathlib.Path) else pathlib.Path(library)
    if not library.is_dir():
        return False
    if not library.joinpath("AlbumData.xml").is_file():
        return False
    return bool(library.joinpath("Database", "Library.apdb").is_file())
