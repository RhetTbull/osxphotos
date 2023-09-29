"""Support for iPhoto libraries

This code is based on https://github.com/jensb/iphoto2xmp by @jensb
who kindly gave permission to use the derived code under the MIT license.
The original iphoto2xmp is licensed under the GPL v3 license.

The following code largely follows the structure of the original iphoto2xmp code
with adaptaptions to convert it to python, break into functions for readability,
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
"""

from __future__ import annotations

import datetime
import functools
import inspect
import json
import logging
import pathlib
import shutil
import sqlite3
from typing import Any, Callable, get_type_hints
from zoneinfo import ZoneInfo

from ._constants import TIME_DELTA
from .photoinfo import PhotoInfo
from .scoreinfo import ScoreInfo
from .unicode import normalize_unicode
from .utils import noop

logger = logging.getLogger("osxphotos")


class iPhotoDB:
    """Read an iPhoto library database"""

    def __init__(self, library_path: str, verbose: Callable[..., None] = None):
        """Initialize iPhotoDB object"""
        self.library_path: pathlib.Path = pathlib.Path(library_path).absolute()
        if not self.library_path.is_dir():
            raise FileNotFoundError(f"Invalid iPhoto library path: {self.library_path}")
        if not self.library_path.joinpath("Database").is_dir():
            raise FileNotFoundError(f"Invalid iPhoto library path: {self.library_path}")
        self.verbose = verbose or noop

        # initialize database dictionaries
        self._db_photos = {}  # mapping of uuid to photo data
        self._db_event_notes = {}  # mapping of modelId to event notes
        self._db_places = {}  # mapping of modelId to places
        self._db_properties = {}  # mapping of versionId to properties
        self._db_persons = {}  # mapping of modelId to persons
        self._db_faces = {}  # mapping of modelID to face info
        self._db_faces_edited = {}  # mapping of modelID to face info for edited photos
        self._db_folders = {}  # mapping of modelId to folders
        self._db_albums = {}  # mapping of modelId to albums
        self._db_volumes = {}  # mapping of volume uuid to volume name

        self._load_library()

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

        logger.debug(f"{self._db_photos=}")
        logger.debug(f"{self._db_event_notes=}")
        logger.debug(f"{self._db_places=}")
        logger.debug(f"{self._db_properties=}")
        logger.debug(f"{self._db_persons=}")
        logger.debug(f"{self._db_faces=}")
        logger.debug(f"{self._db_faces_edited=}")
        logger.debug(f"{self._db_folders=}")
        logger.debug(f"{self._db_albums=}")
        logger.debug(f"{self._db_volumes=}")

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
        -- will be written to SQL script to optionally update digikam4.db
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
        RKMaster.isInTrash as in_trash,
        RKMaster.fileIsReference AS is_reference
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
            RKFolder.name AS name
            FROM RKNote
            LEFT JOIN RKFolder on RKNote.attachedToUuid = RKFolder.uuid
            WHERE RKFolder.name IS NOT NULL AND RKFolder.name != ''
            ORDER BY RKFolder.modelId
        """
        logger.debug(f"Executing query: {query}")

        self.verbose("Loading event notes from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            self._db_event_notes[int(row["modelId"])] = dict(row)
        conn.close()

        # normalize unicode
        for model_id in self._db_event_notes:
            self._db_event_notes[model_id]["note"] = normalize_unicode(
                self._db_event_notes[model_id]["note"]
            )
            self._db_event_notes[model_id]["name"] = normalize_unicode(
                self._db_event_notes[model_id]["name"]
            )

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
            RKDetectedFace.confidence,
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
                face_key = row["face_key"]
                for person in self._db_persons.values():
                    if face_key == person["face_key"]:
                        row["name"] = person["name"]
                        row["email"] = person["email"]
                        row["full_name"] = ""
                        break
                else:
                    logger.debug(f"Didn't find person for edited photo face {face_key}")
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
            isMagic
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
            RKAlbum.uuid,
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

            if photo["hasadjustments"]:
                # build edited path
                image_path = pathlib.Path(photo["imagepath"])
                path_edited = self.library_path.joinpath(
                    "Previews", image_path.parent, uuid
                )
                edited_files = list(path_edited.glob("*"))
                # edited image named with Photo's title not imagepath.stem
                edited_files = [
                    x
                    for x in edited_files
                    if normalize_unicode(x.stem) == photo["title"]
                ]
                if edited_files:
                    photo["path_edited"] = edited_files[0]
                else:
                    photo["path_edited"] = ""
            else:
                photo["path_edited"] = ""

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

    def photos(
        self, uuid: list[str] | None = None, images: bool = True, movies: bool = True
    ) -> list[iPhotoPhotoInfo]:
        """Return list of photos in library"""
        photos = [iPhotoPhotoInfo(uuid, self) for uuid in self._db_photos]
        if uuid:
            photos = [photo for photo in photos if photo.uuid in uuid]
        if not images:
            photos = [photo for photo in photos if not photo.isphoto]
        if not movies:
            photos = [photo for photo in photos if not photo.ismovie]
        return photos

    def get_photo(self, uuid: str) -> iPhotoPhotoInfo:
        """Return photo by uuid"""
        if uuid not in self._db_photos:
            raise ValueError(f"Photo with uuid {uuid} not found")
        return iPhotoPhotoInfo(uuid, self)


class iPhotoPhotoInfo:
    """PhotoInfo implementation for iPhoto"""

    def __init__(self, uuid: str, db: iPhotoDB):
        self._uuid = uuid
        self._db = db
        self._info = self._db._db_photos[self._uuid]
        self._attributes = get_user_attributes(PhotoInfo)

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
    def ismissing(self) -> bool:
        """Return True if asset is missing"""
        return self._db._db_photos[self._uuid]["ismissing"]

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
        if pathlib.Path(path).exists():
            return path
        logger.debug(f"Photo path {path} does not exist")
        return None

    @property
    def path_edited(self) -> str | None:
        """Path to edited asset in library"""
        path = self._db._db_photos[self._uuid]["path_edited"]
        if pathlib.Path(path).exists():
            return path
        logger.debug(f"Edited photo path {path} does not exist")
        return None

    @property
    def description(self) -> str:
        """Description of photo"""
        return self._db._db_photos[self._uuid].get("description", "")

    @property
    def title(self) -> str | None:
        """Title of photo"""
        return self._db._db_photos[self._uuid].get("title", None)

    @property
    def persons(self) -> list[str]:
        """List of persons in photo"""
        faces = self._get_faces()
        return [face["name"] for face in faces]

    @property
    def person_info(self) -> list[iPhotoPersonInfo]:
        """List of PersonInfo objects for photo"""
        faces = self._get_faces()
        return [iPhotoPersonInfo(face, self._db) for face in faces]

    @property
    def face_info(self) -> list[iPhotoFaceInfo]:
        """List of FaceInfo objects for photo"""
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
    def albums(self) -> list[str]:
        """List of albums photo is contained in"""
        albums = []
        for album in self._db._db_photos[self._uuid].get("albums", []):
            albums.append(album["name"])
        return albums

    @property
    def album_info(self) -> list[iPhotoAlbumInfo]:
        """ "Return list of AlbumInfo objects for photo"""
        albums = []
        for album in self._db._db_photos[self._uuid].get("albums", []):
            albums.append(iPhotoAlbumInfo(album, self._db))
        return albums

    @property
    def hexdigest(self) -> str:
        """Hexdigest of photo"""
        return ""

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
        self, dest: str, filename: str | None = None, edited: bool = False
    ) -> list[str]:
        """Export photo"""
        if not filename:
            filename = self.original_filename
        path = self.path_edited if edited else self.path
        if not path:
            raise ValueError(f"Photo {self.uuid} does not have a path")
        dest = pathlib.Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        dest_path = dest.joinpath(filename)
        shutil.copy(path, dest_path)
        return [str(dest_path)]

    def _get_faces(self) -> list[dict[str, Any]]:
        """Get faces for photo"""
        if self.hasadjustments:
            faces = self._db._db_photos[self._uuid].get("edited_faces", [])
        else:
            faces = self._db._db_photos[self._uuid].get("faces", [])
        return faces

    def __getattr__(self, name: str):
        """If attribute is not found in iPhotoPhotoInfo, look at PhotoInfo and return default type"""
        if name in self._attributes:
            return default_return_value(self._attributes[name])
        else:
            raise AttributeError(f"Invalid attribute: {name}")


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
            self._person = None

    @property
    def uuid(self) -> str:
        """UUID of person"""
        return self._person["uuid"]

    @property
    def name(self) -> str:
        """Name of person"""
        return self._person["name"]

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
            for face in photo["faces"]:
                if face["face_key"] == self._face["face_key"]:
                    photos.append(iPhotoPhotoInfo(uuid, self._db))
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
            self._person = None

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

        # orientation = self.photo.orientation
        # x, y = self._fix_orientation(xy)
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
    def size(self) -> int:
        ...

    @property
    def size_pixels(self) -> int:
        """Size of face in pixels (centered around center_x, center_y)

        Returns:
            size, in int pixels, of a circle drawn around the center of the face
        """
        photo = self.photo
        size_reference = photo.width if photo.width > photo.height else photo.height
        return self.size * size_reference

    @property
    def person_info(self) -> iPhotoPersonInfo:
        """PersonInfo object for face"""
        return iPhotoPersonInfo(self._face, self._db)

    def face_rect(self) -> list[tuple[int, int], tuple[int, int]]:
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


class iPhotoAlbumInfo:
    """AlbumInfo class for iPhoto"""

    def __init__(self, album: dict[str, Any], db: iPhotoDB):
        self._album = album
        self._db = db
        self._album_id = album["albumId"]

    @property
    def uuid(self) -> str:
        """UUID of album"""
        return self._album["uuid"]

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
        return self._album["path"]

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
    def parent(self):
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

    def asdict(self):
        """Return album info as a dict; does not include photos"""
        return {
            "uuid": self.uuid,
            "title": self.title,
            "folder_names": self.folder_names,
            "folder_list": [f.uuid for f in self.folder_list],
            "sort_order": self.sort_order,
            "parent": self.parent.uuid if self.parent else None,
        }

    def __len__(self):
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
    def album_info(self):
        """Return list of albums (as AlbumInfo objects) contained in the folder"""
        folder_albums = []
        for albums in self._db._db_albums.values():
            for album in albums:
                if album["folder_id"] == self._folderid:
                    folder_albums.append(iPhotoAlbumInfo(album, self._db))
        return folder_albums

    @property
    def parent(self):
        """Return FolderInfo object for parent or None if no parent (e.g. top-level folder)"""
        parent_uuid = self._folder["parentFolderUuid"]
        if not parent_uuid:
            return None
        for folder in self._db._db_folders.values():
            if folder["uuid"] == parent_uuid:
                if bool(folder["isMagic"]):
                    # skip magic folders like "TopLevelAlbums"
                    return None
                return iPhotoFolderInfo(folder, self._db)
        return None

    @property
    def subfolders(self):
        """Return list of folders (as FolderInfo objects) contained in the folder"""
        subfolders = []
        for folder in self._db._db_folders.values():
            if folder["parentFolderUuid"] == self.uuid:
                if bool(folder["isMagic"]):
                    # skip magic folders like "TopLevelAlbums"
                    continue
                subfolders.append(iPhotoFolderInfo(folder, self._db))
        return subfolders

    def asdict(self):
        """Return folder info as a dict"""
        return {
            "title": self.title,
            "uuid": self.uuid,
            "parent": self.parent.uuid if self.parent is not None else None,
            "subfolders": [f.uuid for f in self.subfolders],
            "albums": [a.uuid for a in self.album_info],
        }

    def __len__(self):
        """returns count of folders + albums contained in the folder"""
        return len(self.subfolders) + len(self.album_info)


def iphoto_date_to_datetime(date: int, tz: str | None = None) -> datetime.datetime:
    """ "Convert iPhoto date to datetime; if tz provided, will be timezone aware

    Args:
        date: iPhoto date
        tz: timezone name

    Returns:
        datetime.datetime

    Note:
        If date is invalid, will return 1970-01-01 00:00:00
    """
    try:
        date = datetime.datetime.fromtimestamp(date + TIME_DELTA)
    except ValueError:
        date = datetime.datetime(1970, 1, 1)
    if tz:
        date = date.replace(tzinfo=ZoneInfo(tz))
    return date


def default_return_value(name):
    """Inspect name and return default value if there is one otherwis None
    optimized for PhotoInfo may not work for other classes
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


def get_user_attributes(cls):
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
