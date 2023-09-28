"""Support for iPhoto libraries;
This code is based on https://github.com/jensb/iphoto2xmp to by @jensb
who kindly gave permission to use the derived code under the MIT license.
"""

from __future__ import annotations

import logging
import pathlib
import sqlite3
from typing import Any, Callable

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
        self._db_faces_face_key = {}  # mapping of face_key to face info
        self._db_library_folders = {}  # mapping of modelId to folders
        self._db_library_albums = {}  # mapping of modelId to albums
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
        logger.debug(f"{self._db_library_folders=}")
        logger.debug(f"{self._db_library_albums=}")
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
        RKMaster.isMissing AS missing,
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
                self._db_photos[uuid]["descripton"] = data["string"]

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
            ORDER BY RKDetectedFace.modelId
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
                self._db_faces_face_key[row["face_key"]] = row
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
                # normalize unicode
                row = dict(row)
                face_key = row["face_key"]
                if face_key in self._db_faces_face_key:
                    face_info = self._db_faces_face_key[face_key]
                    row["name"] = face_info["name"]
                    row["full_name"] = face_info["full_name"]
                    row["email"] = face_info["email"]
                else:
                    logging.debug(
                        f"Face key {face_key} not found in _db_faces_face_key"
                    )
                    row["name"] = ""
                    row["full_name"] = ""
                    row["email"] = ""
                # assign to library data for matching uuid
                photo["edited_faces"].append(row)
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
            folderPath
            FROM RKFolder
            WHERE folderType = 1
        """
        logger.debug(f"Executing query: {query}")

        conn = sqlite3.connect(library_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        self.verbose("Loading folders from iPhoto library")
        results = cursor.execute(query).fetchall()
        for row in results:
            self._db_library_folders[row["modelID"]] = dict(row)

        # normalize unicode
        for model_id in self._db_library_folders:
            self._db_library_folders[model_id]["name"] = normalize_unicode(
                self._db_library_folders[model_id]["name"]
            )
            self._db_library_folders[model_id]["folderPath"] = normalize_unicode(
                self._db_library_folders[model_id]["folderPath"]
            )

        # folderPath is a string like "modelId1/modelId2/...".
        # convert these using the real folder names to get the path strings.
        # the top level libray folder is always modelId 1 and has name ''
        for model_id in self._db_library_folders:
            folder_list = []
            for folder_id in self._db_library_folders[model_id]["folderPath"].split(
                "/"
            ):
                if folder_id == "":
                    continue
                folder_name = self._db_library_folders[int(folder_id)]["name"]
                if folder_name == "":
                    continue
                folder_list.append(folder_name)
            self._db_library_folders[model_id]["folderlist"] = folder_list

        conn.close()

    def _load_albums(self):
        """Load albums from iPhoto library"""
        library_db = self.library_path.joinpath("Database/apdb/Library.apdb")

        query = """
            SELECT
            RKAlbumVersion.modelId,
            RKAlbumVersion.versionId,
            RKAlbumVersion.albumId,
            RKAlbum.name,
            RKFolder.modelId AS f_id,
            RKFolder.uuid AS f_uuid
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
            self._db_library_albums[int(row["modelId"])] = dict(row)

        # normalize unicode
        for model_id in self._db_library_albums:
            self._db_library_albums[model_id]["name"] = normalize_unicode(
                self._db_library_albums[model_id]["name"]
            )

        # get album hierarchy
        for model_id, album in self._db_library_albums.items():
            album["path"] = [
                *self._db_library_folders[album["f_id"]]["folderlist"],
                album["name"],
            ]

        # add album data to library data
        for uuid, library in self._db_photos.items():
            if library["id"] in self._db_library_albums:
                self._db_photos[uuid]["album"] = self._db_library_albums[library["id"]]

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
