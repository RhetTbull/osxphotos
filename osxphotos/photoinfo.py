""" PhotoInfo class: Represents a single photo in the Photos library and provides access to the photo's attributes
PhotosDB.photos() returns a list of PhotoInfo objects
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime
import json
import logging
import os
import os.path
import pathlib
import plistlib
import re
from datetime import timedelta, timezone
from functools import cached_property
from types import SimpleNamespace
from typing import Any, Dict, Optional

import yaml

import osxphotos

from ._constants import (
    _DB_TABLE_NAMES,
    _MOVIE_TYPE,
    _PHOTO_TYPE,
    _PHOTOS_4_ALBUM_KIND,
    _PHOTOS_4_ALBUM_TYPE_ALBUM,
    _PHOTOS_4_ALBUM_TYPE_PROJECT,
    _PHOTOS_4_ALBUM_TYPE_SLIDESHOW,
    _PHOTOS_4_ROOT_FOLDER,
    _PHOTOS_4_VERSION,
    _PHOTOS_5_ALBUM_KIND,
    _PHOTOS_5_IMPORT_SESSION_ALBUM_KIND,
    _PHOTOS_5_PROJECT_ALBUM_KIND,
    _PHOTOS_5_SHARED_ALBUM_KIND,
    _PHOTOS_5_SHARED_DERIVATIVE_PATH,
    _PHOTOS_5_SHARED_PHOTO_PATH,
    _PHOTOS_5_VERSION,
    _PHOTOS_8_SHARED_DERIVATIVE_PATH,
    _PHOTOS_8_SHARED_PHOTO_PATH,
    BURST_DEFAULT_PICK,
    BURST_KEY,
    BURST_NOT_SELECTED,
    BURST_SELECTED,
    SIDECAR_EXIFTOOL,
    SIDECAR_JSON,
    SIDECAR_XMP,
    TEXT_DETECTION_CONFIDENCE_THRESHOLD,
)
from .adjustmentsinfo import AdjustmentsInfo
from .albuminfo import AlbumInfo, ImportInfo, ProjectInfo
from .commentinfo import CommentInfo, LikeInfo
from .exifinfo import ExifInfo
from .exiftool import ExifToolCaching, get_exiftool_path
from .exportoptions import ExportOptions
from .momentinfo import MomentInfo
from .personinfo import FaceInfo, PersonInfo
from .photoexporter import PhotoExporter
from .phototables import PhotoTables
from .phototemplate import PhotoTemplate, RenderOptions
from .placeinfo import PlaceInfo4, PlaceInfo5
from .platform import assert_macos, is_macos
from .query_builder import get_query
from .scoreinfo import ScoreInfo
from .searchinfo import SearchInfo
from .shareinfo import ShareInfo, get_moment_share_info, get_share_info
from .shareparticipant import ShareParticipant, get_share_participants
from .uti import get_preferred_uti_extension, get_uti_for_extension
from .utils import _get_resource_loc, hexdigest, list_directory, path_exists

if is_macos:
    from osxmetadata import OSXMetaData

    from .text_detection import detect_text


__all__ = ["PhotoInfo", "PhotoInfoNone", "frozen_photoinfo_factory"]

logger = logging.getLogger("osxphotos")


class PhotoInfo:
    """
    Info about a specific photo, contains all the details about the photo
    including keywords, persons, albums, uuid, path, etc.
    """

    def __init__(self, db: "osxphotos.PhotosDB", uuid: str, info: dict[str, Any]):
        self._uuid: str = uuid
        self._info: dict[str, Any] = info
        self._db: "osxphotos.PhotosDB" = db
        self._verbose = self._db._verbose

    @property
    def _exiftool_path(self) -> str | None:
        """Path to exiftool as set in PhotosDB instance"""
        return self._db._exiftool_path

    @property
    def filename(self) -> str:
        """filename of the picture"""
        if (
            self._db._db_version <= _PHOTOS_4_VERSION
            and self.has_raw
            and self.raw_original
        ):
            # return the JPEG version as that's what Photos 5+ does
            return self._info["raw_pair_info"]["filename"]
        else:
            return self._info["filename"]

    @property
    def original_filename(self) -> str:
        """original filename of the picture
        Photos 5 mangles filenames upon import"""
        if (
            self._db._db_version <= _PHOTOS_4_VERSION
            and self.has_raw
            and self.raw_original
        ):
            # return the JPEG version as that's what Photos 5+ does
            original_name = self._info["raw_pair_info"]["originalFilename"]
        else:
            original_name = self._info["originalFilename"]
        return original_name or self.filename

    @property
    def date(self) -> datetime.datetime:
        """image creation date as timezone aware datetime object"""
        return self._info["imageDate"]

    @property
    def date_modified(self) -> datetime.datetime | None:
        """image modification date as timezone aware datetime object
        or None if no modification date set"""

        # Photos <= 4 provides no way to get date of adjustment and will update
        # lastmodifieddate anytime photo database record is updated (e.g. adding tags)
        # only report lastmodified date for Photos <=4 if photo is edited;
        # even in this case, the date could be incorrect
        if not self.hasadjustments and self._db._db_version <= _PHOTOS_4_VERSION:
            return None

        if imagedate := self._info["lastmodifieddate"]:
            seconds = self._info["imageTimeZoneOffsetSeconds"] or 0
            delta = timedelta(seconds=seconds)
            tz = timezone(delta)
            return imagedate.astimezone(tz=tz)
        else:
            return None

    @property
    def tzoffset(self) -> int:
        """timezone offset from UTC in seconds"""
        return self._info["imageTimeZoneOffsetSeconds"]

    @property
    def path(self) -> str | None:
        """absolute path on disk of the original picture"""
        try:
            return self._path
        except AttributeError:
            self._path = None
            photopath = None
            if self._info["isMissing"] == 1:
                return photopath  # path would be meaningless until downloaded

            if self._db._db_version <= _PHOTOS_4_VERSION:
                photopath = self._path_4()
            else:
                photopath = self._path_5()
            if photopath is not None and not os.path.isfile(photopath):
                photopath = None
            self._path = photopath
            return photopath

    def _path_5(self) -> str | None:
        """Returns candidate path for original photo on Photos >= version 5"""
        if self._info["shared"]:
            return self._path_5_shared()
        if (
            self.shared_moment
            and self._db.photos_version >= 7
            and self._path_shared_moment()
        ):
            # path for photos in shared moments if it's in the shared moment folder
            # the file may also be in the originals folder which the next check will catch
            # check shared_moment first as a photo can be both a shared moment and syndicated
            # and if so, will be in the shared moment folder
            return self._path_shared_moment()
        if self.syndicated and not self.saved_to_library:
            # path for "shared with you" syndicated photos that have not yet been saved to the library
            return self._path_syndication()
        return (
            os.path.join(self._info["directory"], self._info["filename"])
            if self._info["directory"].startswith("/")
            else os.path.join(
                self._db._masters_path,
                self._info["directory"],
                self._info["filename"],
            )
        )

    def _path_5_shared(self) -> str | None:
        """Returns candidate path for shared photo on Photos >= version 5"""
        # shared library path differs on Photos 5-7, Photos 8+
        shared_path = (
            _PHOTOS_8_SHARED_PHOTO_PATH
            if self._db._photos_ver >= 8
            else _PHOTOS_5_SHARED_PHOTO_PATH
        )

        if self.isphoto:
            return os.path.join(
                self._db._library_path,
                shared_path,
                self._info["directory"],
                self._info["filename"],
            )

        # a shared video has two files, the poster image and the video
        # the poster (image frame shown in Photos) is named UUID.poster.JPG
        # the video file is named UUID.medium.MP4
        # this method returns the path to the video file
        filename = f"{self.uuid}.medium.MP4"
        return os.path.join(
            self._db._library_path,
            shared_path,
            self._info["directory"],
            filename,
        )

    def _path_syndication(self) -> str | None:
        """Return path for syndicated photo on Photos >= version 7"""
        # Photos 7+ stores syndicated photos in a separate directory
        # in ~/Photos Library.photoslibrary/scopes/syndication/originals/X/UUID.ext
        # where X is first digit of UUID
        syndication_path = "scopes/syndication/originals"
        uuid_dir = self.uuid[0]
        path = os.path.join(
            self._db._library_path,
            syndication_path,
            uuid_dir,
            self.filename,
        )
        return path if os.path.isfile(path) else None

    def _path_shared_moment(self) -> str | None:
        """Return path for shared moment photo on Photos >= version 7"""
        # Photos 7+ stores shared moment photos in a separate directory
        # in ~/Photos Library.photoslibrary/scopes/momentshared/originals/X/UUID.ext
        # where X is first digit of UUID
        momentshared_path = "scopes/momentshared/originals"
        uuid_dir = self.uuid[0]
        path = os.path.join(
            self._db._library_path,
            momentshared_path,
            uuid_dir,
            self.filename,
        )
        return path if os.path.isfile(path) else None

    def _path_4(self) -> str | None:
        """Returns candidate path for original photo on Photos <= version 4"""
        if self._info["has_raw"]:
            # return the path to JPEG even if RAW is original
            vol = (
                self._db._dbvolumes[self._info["raw_pair_info"]["volumeId"]]
                if self._info["raw_pair_info"]["volumeId"] is not None
                else None
            )
            if vol is not None:
                photopath = os.path.join(
                    "/Volumes", vol, self._info["raw_pair_info"]["imagePath"]
                )
            else:
                photopath = os.path.join(
                    self._db._masters_path,
                    self._info["raw_pair_info"]["imagePath"],
                )
        else:
            vol = self._info["volume"]
            if vol is not None:
                photopath = os.path.join("/Volumes", vol, self._info["imagePath"])
            else:
                photopath = os.path.join(
                    self._db._masters_path, self._info["imagePath"]
                )
        return photopath

    @property
    def path_edited(self) -> str | None:
        """absolute path on disk of the edited picture"""
        """ None if photo has not been edited """

        try:
            return self._path_edited
        except AttributeError:
            if self._db._db_version <= _PHOTOS_4_VERSION:
                photopath = self._path_edited_4()
            else:
                photopath = self._path_edited_5()

            if photopath is not None and not os.path.isfile(photopath):
                logger.debug(
                    f"edited file for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                )
                photopath = None
            self._path_edited = photopath
            return self._path_edited

    def _path_edited_5(self) -> str | None:
        """Returns candidate path_edited for Photos >= 5 or None if cannot be determined"""
        # In Photos 5.0 / Catalina / MacOS 10.15:
        # edited photos appear to always be converted to .jpeg and stored in
        # library_name/resources/renders/X/UUID_1_201_a.jpeg
        # where X = first letter of UUID
        # and UUID = UUID of image
        # this seems to be true even for photos not copied to Photos library and
        # where original format was not jpg/jpeg
        # if more than one edit, previous edit is stored as UUID_p.jpeg
        #
        # In Photos 6.0 / Big Sur, the edited image is a .heic if the photo isn't a jpeg,
        # otherwise it's a jpeg.  It could also be a jpeg if photo library upgraded from earlier
        # version.

        if self._db._db_version < _PHOTOS_5_VERSION:
            raise RuntimeError("Wrong database format!")

        if self._info["hasAdjustments"]:
            library = self._db._library_path
            directory = self._uuid[0]  # first char of uuid
            filename = None
            if self._info["type"] == _PHOTO_TYPE:
                # it's a photo
                if self._db._photos_ver != 5 and self.uti == "public.heic":
                    filename = f"{self._uuid}_1_201_a.heic"
                else:
                    filename = f"{self._uuid}_1_201_a.jpeg"
            elif self._info["type"] == _MOVIE_TYPE:
                # it's a movie
                filename = f"{self._uuid}_2_0_a.mov"
            else:
                # don't know what it is!
                logger.debug(f"WARNING: unknown type {self._info['type']}")
                return None

            return os.path.join(library, "resources", "renders", directory, filename)

        return None

    def _get_predicted_path_edited_4(self) -> str | None:
        """return predicted path_edited for Photos <= 4"""
        edit_id = self._info["edit_resource_id_photo"]
        folder_id, file_id, nn_id = _get_resource_loc(edit_id)
        # figure out what kind it is and build filename
        library = self._db._library_path
        if uti_edited := self.uti_edited:
            ext = get_preferred_uti_extension(uti_edited)
            if ext is not None:
                filename = f"fullsizeoutput_{file_id}.{ext}"
                return os.path.join(
                    library, "resources", "media", "version", folder_id, nn_id, filename
                )

        # if we get here, we couldn't figure out the extension
        # so try to figure out the type and build the filename
        type_ = self._info["type"]
        if type_ == _PHOTO_TYPE:
            # it's a photo
            filename = f"fullsizeoutput_{file_id}.jpeg"
        elif type_ == _MOVIE_TYPE:
            # it's a movie
            filename = f"fullsizeoutput_{file_id}.mov"
        else:
            raise ValueError(f"Unknown type {type_}")

        return os.path.join(
            library, "resources", "media", "version", folder_id, nn_id, filename
        )

    def _path_edited_4(self) -> str | None:
        """return path_edited for Photos <= 4; #859"""

        if not self._info["hasAdjustments"]:
            return None

        if edit_id := self._info["edit_resource_id"]:
            try:
                photopath = self._get_predicted_path_edited_4()
            except ValueError as e:
                logger.debug(f"ERROR: {e}")
                photopath = None

            if photopath is not None and not os.path.isfile(photopath):
                # the heuristic failed, so try to find the file
                rootdir = pathlib.Path(photopath).parent.parent
                filename = pathlib.Path(photopath).name
                for dirname, _, filelist in os.walk(rootdir):
                    if filename in filelist:
                        photopath = os.path.join(dirname, filename)
                        break

            # check again to see if we found a valid file
            if photopath is not None and not os.path.isfile(photopath):
                logger.debug(
                    f"MISSING PATH: edited file for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                )
                photopath = None
        else:
            logger.debug(f"{self.uuid} hasAdjustments but edit_resource_id is None")
            photopath = None

        return photopath

    @property
    def path_edited_live_photo(self) -> str | None:
        """return path to edited version of live photo movie"""
        try:
            return self._path_edited_live_photo
        except AttributeError:
            if self._db._db_version < _PHOTOS_5_VERSION:
                self._path_edited_live_photo = self._path_edited_4_live_photo()
            else:
                self._path_edited_live_photo = self._path_edited_5_live_photo()
            return self._path_edited_live_photo

    def _get_predicted_path_edited_live_photo_4(self) -> str | None:
        """return predicted path_edited for Photos <= 4"""
        # need the resource id for the video, not the photo (edit_resource_id is for photo)
        if edit_id := self._info["edit_resource_id_video"]:
            folder_id, file_id, nn_id = _get_resource_loc(edit_id)
            # figure out what kind it is and build filename
            library = self._db._library_path
            filename = f"videocomplementoutput_{file_id}.mov"
            return os.path.join(
                library, "resources", "media", "version", folder_id, nn_id, filename
            )
        else:
            return None

    def _path_edited_4_live_photo(self) -> str | None:
        """return path_edited_live_photo for Photos <= 4"""
        if self._db._db_version > _PHOTOS_4_VERSION:
            raise RuntimeError("Wrong database format!")
        if not self.live_photo:
            return None
        photopath = self._get_predicted_path_edited_live_photo_4()
        if photopath is not None and not os.path.isfile(photopath):
            # the heuristic failed, so try to find the file
            rootdir = pathlib.Path(photopath).parent.parent
            filename = pathlib.Path(photopath).name
            photopath = next(
                (
                    os.path.join(dirname, filename)
                    for dirname, _, filelist in os.walk(rootdir)
                    if filename in filelist
                ),
                None,
            )
        return photopath

    def _path_edited_5_live_photo(self) -> str | None:
        """return path_edited_live_photo for Photos >= 5"""
        if self._db._db_version < _PHOTOS_5_VERSION:
            raise RuntimeError("Wrong database format!")

        if self.live_photo and self._info["hasAdjustments"]:
            library = self._db._library_path
            directory = self._uuid[0]  # first char of uuid
            filename = f"{self._uuid}_2_100_a.mov"
            photopath = os.path.join(
                library, "resources", "renders", directory, filename
            )
            if not os.path.isfile(photopath):
                photopath = None
        else:
            photopath = None

        return photopath

    @property
    def path_raw(self) -> str | None:
        """absolute path of associated RAW image or None if there is not one"""

        # In Photos 5, raw is in same folder as original but with _4.ext
        # Unless "Copy Items to the Photos Library" is not checked
        # then RAW image is not renamed but has same name is jpeg but with raw extension
        # Current implementation finds images with the correct raw UTI extension
        # in same folder as the original and with same stem as original in form: original_stem*.raw_ext
        # TODO: I don't like this -- would prefer a more deterministic approach but until I have more
        # data on how Photos stores and retrieves RAW images, this seems to be working

        if self._info["isMissing"] == 1:
            return None  # path would be meaningless until downloaded

        if not self.has_raw:
            return None  # no raw image to get path for

        # if self._info["shared"]:
        #     # shared photo
        #     photopath = os.path.join(
        #         self._db._library_path,
        #         _PHOTOS_5_SHARED_PHOTO_PATH,
        #         self._info["directory"],
        #         self._info["filename"],
        #     )
        #     return photopath

        if self._db._db_version <= _PHOTOS_4_VERSION:
            return self._path_raw_4()

        if not self.isreference:
            filestem = pathlib.Path(self._info["filename"]).stem
            # raw_ext = get_preferred_uti_extension(self._info["UTI_raw"])

            if self._info["directory"].startswith("/"):
                filepath = self._info["directory"]
            else:
                filepath = os.path.join(self._db._masters_path, self._info["directory"])

            if raw_file := list_directory(filepath, startswith=f"{filestem}_4"):
                photopath = pathlib.Path(filepath) / raw_file[0]
                photopath = str(photopath) if photopath.is_file() else None
            else:
                photopath = None
        else:
            # is a reference
            try:
                photopath = (
                    pathlib.Path("/Volumes")
                    / self._info["raw_volume"]
                    / self._info["raw_relative_path"]
                )
                photopath = str(photopath) if photopath.is_file() else None
            except KeyError:
                # don't have the path details
                photopath = None

        return photopath

    def _path_raw_4(self) -> str | None:
        """Return path_raw for Photos <= version 4"""
        vol = self._info["raw_info"]["volume"]
        if vol is not None:
            photopath = os.path.join(
                "/Volumes", vol, self._info["raw_info"]["imagePath"]
            )
        else:
            photopath = os.path.join(
                self._db._masters_path, self._info["raw_info"]["imagePath"]
            )
        if not os.path.isfile(photopath):
            logger.debug(
                f"MISSING PATH: RAW photo for UUID {self._uuid} should be at {photopath} but does not appear to exist"
            )
            photopath = None
        return photopath

    @property
    def description(self) -> str:
        """long / extended description of picture"""
        return self._info["extendedDescription"]

    @property
    def persons(self) -> list[str]:
        """list of persons in picture"""
        return [self._db._dbpersons_pk[pk]["fullname"] for pk in self._info["persons"]]

    @property
    def person_info(self) -> list[PersonInfo]:
        """list of PersonInfo objects for person in picture"""
        return [PersonInfo(db=self._db, pk=pk) for pk in self._info["persons"]]

    @property
    def face_info(self) -> list[FaceInfo]:
        """list of FaceInfo objects for faces in picture"""
        try:
            faces = self._db._db_faceinfo_uuid[self._uuid]
            self._faceinfo = [FaceInfo(db=self._db, pk=pk) for pk in faces]
        except KeyError:
            # no faces
            self._faceinfo = []
        return self._faceinfo

    @property
    def moment_info(self) -> MomentInfo | None:
        """Moment photo belongs to"""
        try:
            return MomentInfo(db=self._db, moment_pk=self._info["momentID"])
        except ValueError:
            return None

    @property
    def albums(self) -> list[str]:
        """list of albums picture is contained in"""
        try:
            return self._albums
        except AttributeError:
            album_uuids = self._get_album_uuids()
            self._albums = list(
                {self._db._dbalbum_details[album]["title"] for album in album_uuids}
            )
            return self._albums

    @property
    def burst_albums(self) -> list[str]:
        """If photo is burst photo, list of albums it is contained in as well as any albums the key photo is contained in, otherwise returns self.albums"""
        burst_albums = list(self.albums)
        for photo in self.burst_photos:
            if photo.burst_key:
                burst_albums.extend(photo.albums)
        return list(set(burst_albums))

    @property
    def album_info(self) -> list[AlbumInfo]:
        """list of AlbumInfo objects representing albums the photo is contained in"""
        album_uuids = self._get_album_uuids()
        return [AlbumInfo(db=self._db, uuid=album) for album in album_uuids]

    @property
    def burst_album_info(self) -> list[AlbumInfo]:
        """If photo is a burst photo, returns list of AlbumInfo objects representing albums the photo is contained in as well as albums the burst key photo is contained in, otherwise returns self.album_info."""
        burst_album_info = list(self.album_info)
        for photo in self.burst_photos:
            if photo.burst_key:
                burst_album_info.extend(photo.album_info)
        return list(set(burst_album_info))

    @property
    def import_info(self) -> ImportInfo | None:
        """ImportInfo object representing import session for the photo or None if no import session"""
        return (
            ImportInfo(db=self._db, uuid=self._info["import_uuid"])
            if self._info["import_uuid"] is not None
            else None
        )

    @property
    def project_info(self) -> list[ProjectInfo]:
        """list of ProjectInfo objects representing projects for the photo or None if no projects"""
        project_uuids = self._get_album_uuids(project=True)
        return [ProjectInfo(db=self._db, uuid=album) for album in project_uuids]

    @property
    def keywords(self) -> list[str]:
        """list of keywords for picture"""
        return self._info["keywords"]

    @property
    def title(self) -> str | None:
        """name / title of picture"""
        # if user sets then deletes title, Photos sets it to empty string in DB instead of NULL
        # in this case, return None so result is the same as if title had never been set (which returns NULL)
        # issue #512
        title = self._info["name"]
        return None if title == "" else title

    @property
    def uuid(self) -> str:
        """UUID of picture"""
        return self._uuid

    @property
    def ismissing(self) -> bool:
        """returns true if photo is missing from disk (which means it's not been downloaded from iCloud)

        NOTE:   the photos.db database uses an asynchrounous write-ahead log so changes in Photos
                do not immediately get written to disk. In particular, I've noticed that downloading
                an image from the cloud does not force the database to be updated until something else
                e.g. an edit, keyword, etc. occurs forcing a database synch
                The exact process / timing is a mystery to be but be aware that if some photos were recently
                downloaded from cloud to local storate their status in the database might still show
                isMissing = 1
        """
        return self._info["isMissing"] == 1

    @property
    def hasadjustments(self) -> bool:
        """True if picture has adjustments / edits"""
        return self._info["hasAdjustments"] == 1

    @property
    def adjustments_path(self) -> pathlib.Path | None:
        """Returns path to adjustments file or none if file doesn't exist"""
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return None

        if not self.hasadjustments:
            return None

        library = self._db._library_path
        directory = self._uuid[0]  # first char of uuid
        plist_file = (
            pathlib.Path(library)
            / "resources"
            / "renders"
            / directory
            / f"{self._uuid}.plist"
        )
        if not plist_file.is_file():
            return None
        return plist_file

    @property
    def adjustments(self) -> AdjustmentsInfo | None:
        """Returns AdjustmentsInfo class for adjustment data or None if no adjustments; Photos 5+ only"""
        try:
            return self._adjustmentinfo
        except AttributeError:
            plist_file = self.adjustments_path
            if plist_file is None:
                return None
            self._adjustmentinfo = AdjustmentsInfo(plist_file)
            return self._adjustmentinfo

    @property
    def external_edit(self) -> bool:
        """Returns True if picture was edited outside of Photos using external editor"""
        return self._info["adjustmentFormatID"] == "com.apple.Photos.externalEdit"

    @property
    def favorite(self) -> bool:
        """True if picture is marked as favorite"""
        return self._info["favorite"] == 1

    @property
    def flagged(self) -> bool:
        """Returns True if photo is flagged; iPhoto only; on Photos always returns False"""
        return False

    @property
    def rating(self) -> int:
        """Star rating of photo as int from 0 to 5; for iPhoto, returns star rating; for Photos, returns 5 if favorite, else 0"""
        return 5 if self.favorite else 0

    @property
    def hidden(self) -> bool:
        """True if picture is hidden"""
        return self._info["hidden"] == 1

    @property
    def visible(self) -> bool:
        """True if picture is visble"""
        return self._info["visible"]

    @property
    def intrash(self) -> bool:
        """True if picture is in trash ('Recently Deleted' folder)"""
        return self._info["intrash"]

    @property
    def date_trashed(self) -> datetime.datetime | None:
        """Date asset was placed in the trash or None"""
        # TODO: add add_timezone(dt, offset_seconds) to datetime_utils
        # also update date_modified
        trasheddate = self._info["trasheddate"]
        if trasheddate:
            seconds = self._info["imageTimeZoneOffsetSeconds"] or 0
            delta = timedelta(seconds=seconds)
            tz = timezone(delta)
            return trasheddate.astimezone(tz=tz)
        else:
            return None

    @property
    def date_added(self) -> datetime.datetime | None:
        """Date photo was added to the database"""
        try:
            return self._date_added
        except AttributeError:
            added_date = self._info["added_date"]
            if added_date:
                seconds = self._info["imageTimeZoneOffsetSeconds"] or 0
                delta = timedelta(seconds=seconds)
                tz = timezone(delta)
                self._date_added = added_date.astimezone(tz=tz)
            else:
                self._date_added = None

            return self._date_added

    @property
    def location(self) -> tuple[float, float] | tuple[None, None]:
        """Returns (latitude, longitude) as float in degrees or None"""
        return (self._latitude, self._longitude)

    @property
    def latitude(self) -> float | None:
        """Returns latitude as float in degrees or None"""
        return self._latitude

    @property
    def longitude(self) -> float | None:
        """Returns longitude as float in degrees or None"""
        return self._longitude

    @property
    def shared(self) -> bool | None:
        """returns True if photos is in a shared iCloud album otherwise false
        Only valid on Photos 5; returns None on older versions"""
        if self._db._db_version > _PHOTOS_4_VERSION:
            return self._info["shared"]
        else:
            return None

    @property
    def uti(self) -> str:
        """Returns Uniform Type Identifier (UTI) for the image
        for example: public.jpeg or com.apple.quicktime-movie
        """
        if self._db._db_version <= _PHOTOS_4_VERSION and self.hasadjustments:
            return self._info["UTI_edited"]
        elif (
            self._db._db_version <= _PHOTOS_4_VERSION
            and self.has_raw
            and self.raw_original
        ):
            # return UTI of the non-raw image to match Photos 5+ behavior
            return self._info["raw_pair_info"]["UTI"]
        else:
            return self._info["UTI"]

    @property
    def uti_original(self) -> str:
        """Returns Uniform Type Identifier (UTI) for the original image
        for example: public.jpeg or com.apple.quicktime-movie
        """
        try:
            return self._uti_original
        except AttributeError:
            if self._db._db_version <= _PHOTOS_4_VERSION and self._info["has_raw"]:
                self._uti_original = self._info["raw_pair_info"]["UTI"]
            elif self.shared:
                # TODO: need reliable way to get original UTI for shared
                self._uti_original = self.uti
            elif self._db._photos_ver >= 7:
                # Monterey+
                # there are some cases with UTI_original is None (photo imported with no extension) so fallback to UTI and hope it's right
                self._uti_original = (
                    get_uti_for_extension(pathlib.Path(self.original_filename).suffix)
                    or self.uti
                )
            else:
                self._uti_original = self._info["UTI_original"]

            return self._uti_original

    @property
    def uti_edited(self) -> str | None:
        """Returns Uniform Type Identifier (UTI) for the edited image
        if the photo has been edited, otherwise None;
        for example: public.jpeg
        """
        if self._db._db_version >= _PHOTOS_5_VERSION:
            return self.uti if self.hasadjustments else None
        else:
            return self._info["UTI_edited"]

    @property
    def uti_raw(self) -> str | None:
        """Returns Uniform Type Identifier (UTI) for the RAW image if there is one
        for example: com.canon.cr2-raw-image
        Returns None if no associated RAW image
        """
        if self._db._photos_ver < 7:
            return self._info["UTI_raw"]

        if rawpath := self.path_raw:
            return get_uti_for_extension(pathlib.Path(rawpath).suffix)
        else:
            return None

    @property
    def ismovie(self) -> bool:
        """Returns True if file is a movie, otherwise False"""
        return self._info["type"] == _MOVIE_TYPE

    @property
    def isphoto(self) -> bool:
        """Returns True if file is an image, otherwise False"""
        return self._info["type"] == _PHOTO_TYPE

    @property
    def incloud(self) -> bool | None:
        """Returns True if photo is cloud asset and is synched to cloud
        False if photo is cloud asset and not yet synched to cloud
        None if photo is not cloud asset
        """
        return self._info["incloud"]

    @property
    def iscloudasset(self) -> bool:
        """Returns True if photo is a cloud asset (in an iCloud library),
        otherwise False
        """
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return (
                True
                if self._info["cloudLibraryState"] is not None
                and self._info["cloudLibraryState"] != 0
                else False
            )
        else:
            return True if self._info["cloudAssetGUID"] is not None else False

    @property
    def isreference(self) -> bool:
        """Returns True if photo is a reference (not copied to the Photos library), otherwise False"""
        return self._info["isreference"]

    @property
    def burst(self) -> bool:
        """Returns True if photo is part of a Burst photo set, otherwise False"""
        return self._info["burst"]

    @property
    def burst_selected(self) -> bool:
        """Returns True if photo is a burst photo and has been selected from the burst set by the user, otherwise False"""
        return bool(self._info["burstPickType"] & BURST_SELECTED)

    @property
    def burst_key(self) -> bool:
        """Returns True if photo is a burst photo and is the key image for the burst set (the image that Photos shows on top of the burst stack), otherwise False"""
        return bool(self._info["burstPickType"] & BURST_KEY)

    @property
    def burst_default_pick(self) -> bool:
        """Returns True if photo is a burst image and is the photo that Photos selected as the default image for the burst set, otherwise False"""
        return bool(self._info["burstPickType"] & BURST_DEFAULT_PICK)

    @property
    def burst_photos(self) -> list[PhotoInfo]:
        """If photo is a burst photo, returns list of PhotoInfo objects
        that are part of the same burst photo set; otherwise returns empty list.
        self is not included in the returned list"""
        if self._info["burst"]:
            burst_uuid = self._info["burstUUID"]
            return [
                PhotoInfo(db=self._db, uuid=u, info=self._db._dbphotos[u])
                for u in self._db._dbphotos_burst[burst_uuid]
                if u != self._uuid
            ]
        else:
            return []

    @property
    def live_photo(self) -> bool:
        """Returns True if photo is a live photo, otherwise False"""
        return self._info["live_photo"]

    @property
    def path_live_photo(self) -> str | None:
        """Returns path to the associated video file for a live photo
        If photo is not a live photo, returns None
        If photo is missing, returns None"""

        photopath = None
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return self._path_live_photo_4()
        elif self.live_photo and self.path and not self.ismissing:
            if self.shared:
                return self._path_live_photo_shared_5()
            if self.shared_moment and self._db.photos_version >= 7:
                return self._path_live_shared_moment()
            if self.syndicated and not self.saved_to_library:
                # syndicated ("Shared with you") photos not yet saved to library
                return self._path_live_syndicated()

            filename = pathlib.Path(self.path)
            photopath = filename.parent.joinpath(f"{filename.stem}_3.mov")
            photopath = str(photopath)
            if not os.path.isfile(photopath):
                # In testing, I've seen occasional missing movie for live photo
                # these appear to be valid -- e.g. video component not yet downloaded from iCloud
                # TODO: should this be a warning or debug?
                photopath = None
        else:
            photopath = None

        return photopath

    def _path_live_photo_shared_5(self) -> str | None:
        """Return path for live photo for shared photos"""
        if not self.shared:
            raise ValueError(f"photo {self.uuid} is not a shared photo")
        if not self.live_photo:
            raise ValueError(f"photo {self.uuid} is not a live photo")

        photopath = self._path_5_shared()
        if photopath:
            photopath = pathlib.Path(photopath).with_suffix(".MOV")
            if not path_exists(photopath):
                photopath = None
        return photopath

    def _path_live_photo_4(self) -> str | None:
        """Return path for live edited photo for Photos <= 4"""
        if self.live_photo and not self.ismissing:
            live_model_id = self._info["live_model_id"]
            if live_model_id is None:
                logger.debug(f"missing live_model_id: {self._uuid}")
                photopath = None
            else:
                folder_id, file_id, nn_id = _get_resource_loc(live_model_id)
                library_path = self._db.library_path
                photopath = os.path.join(
                    library_path,
                    "resources",
                    "media",
                    "master",
                    folder_id,
                    nn_id,
                    f"jpegvideocomplement_{file_id}.mov",
                )
                if not os.path.isfile(photopath):
                    # In testing, I've seen occasional missing movie for live photo
                    # These appear to be valid -- e.g. live component hasn't been downloaded from iCloud
                    # photos 4 has "isOnDisk" column we could check
                    # or could do the actual check with "isfile"
                    # TODO: should this be a warning or debug?
                    photopath = None
        else:
            photopath = None
        return photopath

    def _path_live_syndicated(self) -> str | None:
        """Return path for live syndicated photo on Photos >= version 7"""
        # Photos 7+ stores live syndicated photos in a separate directory
        # in ~/Photos Library.photoslibrary/scopes/syndication/originals/X/UUID_3.mov
        # where X is first digit of UUID
        syndication_path = "scopes/syndication/originals"
        uuid_dir = self.uuid[0]
        filename = f"{pathlib.Path(self.filename).stem}_3.mov"
        live_photo = os.path.join(
            self._db._library_path,
            syndication_path,
            uuid_dir,
            filename,
        )
        return live_photo if os.path.isfile(live_photo) else None

    def _path_live_shared_moment(self) -> str | None:
        """Return path for live shared moment photo on Photos >= version 7"""
        # Photos 7+ stores live shared moment photos in a separate directory
        # in ~/Photos Library.photoslibrary/scopes/momentshared/originals/X/UUID_3.mov
        # where X is first digit of UUID
        shared_moment_path = "scopes/momentshared/originals"
        uuid_dir = self.uuid[0]
        filename = f"{pathlib.Path(self.filename).stem}_3.mov"
        live_photo = os.path.join(
            self._db._library_path,
            shared_moment_path,
            uuid_dir,
            filename,
        )
        return live_photo if os.path.isfile(live_photo) else None

    @cached_property
    def path_derivatives(self) -> list[str]:
        """Return any derivative (preview) images associated with the photo as a list of paths, sorted by file size (largest first)"""
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return self._path_derivatives_4()

        if self.shared:
            return self._path_derivatives_5_shared()

        directory = self._uuid[0]  # first char of uuid
        if self.shared_moment and self._db.photos_version >= 7:
            # shared moments
            derivative_path = "scopes/momentshared/resources/derivatives"
            thumb_path = (
                f"{derivative_path}/masters/{directory}/{self.uuid}_4_5005_c.jpeg"
            )
        elif self.syndicated and not self.saved_to_library:
            # syndicated ("Shared with you") photos not yet saved to library
            derivative_path = "scopes/syndication/resources/derivatives"
            thumb_path = (
                f"{derivative_path}/masters/{directory}/{self.uuid}_4_5005_c.jpeg"
            )
        else:
            derivative_path = "resources/derivatives"
            thumb_path = (
                f"resources/derivatives/masters/{directory}/{self.uuid}_4_5005_c.jpeg"
            )

        derivative_path = (
            pathlib.Path(self._db._library_path)
            .joinpath(derivative_path)
            .joinpath(directory)
        )
        thumb_path = pathlib.Path(self._db._library_path).joinpath(thumb_path)

        # find all files that start with uuid in derivative path
        files = list(derivative_path.glob(f"{self.uuid}*.*"))

        # previews may be missing from derivatives path
        # there are what appear to be low res thumbnails in the "masters" subfolder
        if path_exists(thumb_path):
            files.append(thumb_path)

        # sort by file size, largest first
        files = sorted(files, reverse=True, key=lambda f: f.stat().st_size)

        # return list of filename but skip .THM files (these are actually low-res thumbnails in JPEG format but with .THM extension)
        derivatives = [str(filename) for filename in files if filename.suffix != ".THM"]
        if self.isphoto and len(derivatives) > 1 and derivatives[0].endswith(".mov"):
            # ensure .mov is first in list as poster image could be larger than the movie preview
            derivatives[1], derivatives[0] = derivatives[0], derivatives[1]

        return derivatives

    def _path_derivatives_4(self) -> list[str]:
        """Return paths to all derivative (preview) files for Photos <= 4"""
        modelid = self._info["modelID"]
        if modelid is None:
            return []
        folder_id, file_id, nn_id = _get_resource_loc(modelid)
        derivatives_root = (
            pathlib.Path(self._db._library_path)
            / f"resources/proxies/derivatives/{folder_id}"
        )

        derivatives_path = derivatives_root / nn_id / file_id
        if derivatives_path.is_dir():
            files = derivatives_path.glob("*")
            files = sorted(files, reverse=True, key=lambda f: f.stat().st_size)
            return [str(filename) for filename in files]

        # didn't find derivatives path
        for subdir in derivatives_root.glob("*"):
            if subdir.is_dir():
                derivatives_path = derivatives_root / subdir / file_id
                if derivatives_path.is_dir():
                    files = derivatives_path.glob("*")
                    files = sorted(files, reverse=True, key=lambda f: f.stat().st_size)
                    return [str(filename) for filename in files]

        # didn't find a derivatives path
        return []

    def _path_derivatives_5_shared(self) -> list[str]:
        """Return paths to all derivative (preview) files for shared iCloud photos in Photos >= 5"""
        directory = self._uuid[0]  # first char of uuid
        # only 1 derivative for shared photos and it's called 'UUID_4_5005_c.jpeg'
        derivative_path = (
            _PHOTOS_8_SHARED_DERIVATIVE_PATH
            if self._db._photos_ver >= 8
            else _PHOTOS_5_SHARED_DERIVATIVE_PATH
        )
        derivative_path = (
            pathlib.Path(self._db._library_path)
            / derivative_path
            / f"{directory}/{self.uuid}_4_5005_c.jpeg"
        )
        return [str(derivative_path)] if path_exists(derivative_path) else []

    @property
    def panorama(self) -> bool:
        """Returns True if photo is a panorama, otherwise False"""
        return self._info["panorama"]

    @property
    def slow_mo(self) -> bool:
        """Returns True if photo is a slow motion video, otherwise False"""
        return self._info["slow_mo"]

    @property
    def time_lapse(self) -> bool:
        """Returns True if photo is a time lapse video, otherwise False"""
        return self._info["time_lapse"]

    @property
    def hdr(self) -> bool:
        """Returns True if photo is an HDR photo, otherwise False"""
        return self._info["hdr"]

    @property
    def screenshot(self) -> bool:
        """Returns True if photo is an HDR photo, otherwise False"""
        return self._info["screenshot"]

    @property
    def portrait(self) -> bool:
        """Returns True if photo is a portrait, otherwise False"""
        return self._info["portrait"]

    @property
    def selfie(self) -> bool:
        """Returns True if photo is a selfie (front facing camera), otherwise False"""
        return self._info["selfie"]

    @property
    def place(self) -> PlaceInfo4 | PlaceInfo5 | None:
        """Returns PlaceInfo object containing reverse geolocation info"""

        # implementation note: doesn't create the PlaceInfo object until requested
        # then memoizes the object in self._place to avoid recreating the object

        if self._db._db_version <= _PHOTOS_4_VERSION:
            try:
                return self._place  # pylint: disable=access-member-before-definition
            except AttributeError:
                if self._info["placeNames"]:
                    self._place = PlaceInfo4(
                        self._info["placeNames"], self._info["countryCode"]
                    )
                else:
                    self._place = None
                return self._place
        else:
            try:
                return self._place  # pylint: disable=access-member-before-definition
            except AttributeError:
                if self._info["reverse_geolocation"]:
                    self._place = PlaceInfo5(self._info["reverse_geolocation"])
                else:
                    self._place = None
                return self._place

    @property
    def has_raw(self) -> bool:
        """returns True if photo has an associated raw image (that is, it's a RAW+JPEG pair), otherwise False"""
        return self._info["has_raw"]

    @property
    def israw(self) -> bool:
        """returns True if photo is a raw image. For images with an associated RAW+JPEG pair, see has_raw"""
        return "raw-image" in self.uti_original if self.uti_original else False

    @property
    def raw_original(self) -> bool:
        """returns True if associated raw image and the raw image is selected in Photos
        via "Use RAW as Original "
        otherwise returns False"""
        return self._info["raw_is_original"]

    @property
    def height(self) -> int:
        """returns height of the current photo version in pixels"""
        return self._info["height"]

    @property
    def width(self) -> int:
        """returns width of the current photo version in pixels"""
        return self._info["width"]

    @property
    def orientation(self) -> int:
        """returns EXIF orientation of the current photo version as int or 0 if current orientation cannot be determined"""
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return self._info["orientation"]

        # For Photos 5+, try to get the adjusted orientation
        if not self.hasadjustments:
            return self._info["orientation"]

        if self.adjustments:
            return self.adjustments.adj_orientation
        else:
            # can't reliably determine orientation for edited photo if adjustmentinfo not available
            return 0

    @property
    def original_height(self) -> int:
        """returns height of the original photo version in pixels"""
        return self._info["original_height"]

    @property
    def original_width(self) -> int:
        """returns width of the original photo version in pixels"""
        return self._info["original_width"]

    @property
    def original_orientation(self) -> int:
        """returns EXIF orientation of the original photo version as int"""
        return self._info["original_orientation"]

    @property
    def original_filesize(self) -> int:
        """returns filesize of original photo in bytes as int"""
        return self._info["original_filesize"]

    @property
    def duplicates(self) -> list[PhotoInfo]:
        """return list of PhotoInfo objects for possible duplicates (matching signature of original size, date, height, width) or empty list if no matching duplicates"""
        signature = self._db._duplicate_signature(self.uuid)
        duplicates = []
        try:
            for uuid in self._db._db_signatures[signature]:
                if uuid != self.uuid:
                    # found a possible duplicate
                    duplicates.append(self._db.get_photo(uuid))
        except KeyError:
            # don't expect this to happen as the signature should be in db
            logging.warning(f"Did not find signature for {self.uuid} in _db_signatures")
        return duplicates

    @property
    def owner(self) -> str | None:
        """Return name of photo owner for shared photos (Photos 5+ only), or None if not shared"""
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return None

        try:
            return self._owner
        except AttributeError:
            try:
                personid = self._info["cloudownerhashedpersonid"]
                self._owner = (
                    self._db._db_hashed_person_id[personid]["full_name"]
                    if personid
                    else None
                )
            except KeyError:
                self._owner = None
            return self._owner

    @property
    def score(self) -> ScoreInfo:
        """Computed score information for a photo

        Returns:
            ScoreInfo instance
        """

        if self._db._db_version <= _PHOTOS_4_VERSION:
            return None

        try:
            return self._scoreinfo  # pylint: disable=access-member-before-definition
        except AttributeError:
            try:
                scores = self._db._db_scoreinfo_uuid[self.uuid]
                self._scoreinfo = ScoreInfo(
                    overall=scores["overall_aesthetic"],
                    curation=scores["curation"],
                    promotion=scores["promotion"],
                    highlight_visibility=scores["highlight_visibility"],
                    behavioral=scores["behavioral"],
                    failure=scores["failure"],
                    harmonious_color=scores["harmonious_color"],
                    immersiveness=scores["immersiveness"],
                    interaction=scores["interaction"],
                    interesting_subject=scores["interesting_subject"],
                    intrusive_object_presence=scores["intrusive_object_presence"],
                    lively_color=scores["lively_color"],
                    low_light=scores["low_light"],
                    noise=scores["noise"],
                    pleasant_camera_tilt=scores["pleasant_camera_tilt"],
                    pleasant_composition=scores["pleasant_composition"],
                    pleasant_lighting=scores["pleasant_lighting"],
                    pleasant_pattern=scores["pleasant_pattern"],
                    pleasant_perspective=scores["pleasant_perspective"],
                    pleasant_post_processing=scores["pleasant_post_processing"],
                    pleasant_reflection=scores["pleasant_reflection"],
                    pleasant_symmetry=scores["pleasant_symmetry"],
                    sharply_focused_subject=scores["sharply_focused_subject"],
                    tastefully_blurred=scores["tastefully_blurred"],
                    well_chosen_subject=scores["well_chosen_subject"],
                    well_framed_subject=scores["well_framed_subject"],
                    well_timed_shot=scores["well_timed_shot"],
                )
                return self._scoreinfo
            except KeyError:
                self._scoreinfo = ScoreInfo(
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
                return self._scoreinfo

    @property
    def search_info(self) -> SearchInfo | None:
        """returns SearchInfo object for photo
        only valid on Photos 5, on older libraries, returns None
        """
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return None

        # memoize SearchInfo object
        try:
            return self._search_info
        except AttributeError:
            self._search_info = SearchInfo(self)
            return self._search_info

    @property
    def search_info_normalized(self) -> SearchInfo | None:
        """returns SearchInfo object for photo that produces normalized results
        only valid on Photos 5, on older libraries, returns None
        """
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return None

        # memoize SearchInfo object
        try:
            return self._search_info_normalized
        except AttributeError:
            self._search_info_normalized = SearchInfo(self, normalized=True)
            return self._search_info_normalized

    @cached_property
    def syndicated(self) -> bool | None:
        """Return true if photo was shared via syndication (e.g. via Messages, etc.);
        these are photos that appear in "Shared with you" album.
        Photos 7+ only; returns None if not Photos 7+.
        """
        if self._db.photos_version < 7:
            return None

        try:
            return (
                self._db._db_syndication_uuid[self.uuid]["syndication_identifier"]
                is not None
            )
        except KeyError:
            return False

    @cached_property
    def saved_to_library(self) -> bool | None:
        """Return True if syndicated photo has been saved to library;
        returns False if photo is not syndicated or has not been saved to the library.
        Returns None if not Photos 7+.
        Syndicated photos are photos that appear in "Shared with you" album; Photos 7+ only.
        """
        if self._db.photos_version < 7:
            return None

        try:
            return self._db._db_syndication_uuid[self.uuid]["syndication_history"] != 0
        except KeyError:
            return False

    @cached_property
    def shared_moment(self) -> bool:
        """Returns True if photo is part of a shared moment otherwise False (Photos 7+ only)"""
        return bool(self._info["moment_share"])

    @cached_property
    def shared_moment_info(self) -> ShareInfo | None:
        """Returns ShareInfo object with information about the shared moment the photo is part of (Photos 7+ only)"""
        if self._db.photos_version < 7:
            return None

        try:
            return get_moment_share_info(self._db, self.uuid)
        except ValueError:
            return None

    @cached_property
    def share_info(self) -> ShareInfo | None:
        """Returns ShareInfo object with information about the shared photo in a shared iCloud library (Photos 8+ only) (currently experimental)"""
        if self._db.photos_version < 8:
            return None

        try:
            return get_share_info(self._db, self.uuid)
        except ValueError:
            return None

    @cached_property
    def shared_library(self) -> bool:
        """Returns True if photo is in a shared iCloud library otherwise False (Photos 8+ only)"""
        # TODO: this is just a guess right now as I don't currently use shared libraries
        return bool(self._info["active_library_participation_state"])

    @cached_property
    def share_participant_info(self) -> list[ShareParticipant]:
        """Returns list of ShareParticipant objects with information on who the photo is shared with (Photos 8+ only)"""
        if self._db.photos_version < 8:
            return []
        return get_share_participants(self._db, self.uuid)

    @cached_property
    def share_participants(self) -> list[str]:
        """Returns list of names of people the photo is shared with (Photos 8+ only)"""
        if self._db.photos_version < 8:
            return []
        return [
            f"{p.name_components.given_name} {p.name_components.family_name}"
            for p in self.share_participant_info
        ]

    @property
    def labels(self) -> list[str]:
        """returns list of labels applied to photo by Photos image categorization
        only valid on Photos 5, on older libraries returns empty list
        """
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return []

        return self.search_info.labels

    @property
    def labels_normalized(self) -> list[str]:
        """returns normalized list of labels applied to photo by Photos image categorization
        only valid on Photos 5, on older libraries returns empty list
        """
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return []

        return self.search_info_normalized.labels

    @property
    def comments(self) -> list[CommentInfo]:
        """Returns list of CommentInfo objects for any comments on the photo (sorted by date)"""
        try:
            return self._db._db_comments_uuid[self.uuid]["comments"]
        except:
            return []

    @property
    def likes(self) -> list[LikeInfo]:
        """Returns list of LikeInfo objects for any likes on the photo (sorted by date)"""
        try:
            return self._db._db_comments_uuid[self.uuid]["likes"]
        except:
            return []

    @property
    def exif_info(self) -> ExifInfo | None:
        """Returns an ExifInfo object with the EXIF data for photo
        Note: the returned EXIF data is the data Photos stores in the database on import;
        ExifInfo does not provide access to the EXIF info in the actual image file
        Some or all of the fields may be None
        Only valid for Photos 5; on earlier database returns None
        """

        if self._db._db_version <= _PHOTOS_4_VERSION:
            return None

        try:
            exif = self._db._db_exifinfo_uuid[self.uuid]
            exif_info = ExifInfo(
                iso=exif["ZISO"],
                flash_fired=True if exif["ZFLASHFIRED"] == 1 else False,
                metering_mode=exif["ZMETERINGMODE"],
                sample_rate=exif["ZSAMPLERATE"],
                track_format=exif["ZTRACKFORMAT"],
                white_balance=exif["ZWHITEBALANCE"],
                aperture=exif["ZAPERTURE"],
                bit_rate=exif["ZBITRATE"],
                duration=exif["ZDURATION"],
                exposure_bias=exif["ZEXPOSUREBIAS"],
                focal_length=exif["ZFOCALLENGTH"],
                fps=exif["ZFPS"],
                latitude=exif["ZLATITUDE"],
                longitude=exif["ZLONGITUDE"],
                shutter_speed=exif["ZSHUTTERSPEED"],
                camera_make=exif["ZCAMERAMAKE"],
                camera_model=exif["ZCAMERAMODEL"],
                codec=exif["ZCODEC"],
                lens_model=exif["ZLENSMODEL"],
            )
        except KeyError:
            logger.debug(f"Could not find exif record for uuid {self.uuid}")
            exif_info = ExifInfo(
                iso=None,
                flash_fired=None,
                metering_mode=None,
                sample_rate=None,
                track_format=None,
                white_balance=None,
                aperture=None,
                bit_rate=None,
                duration=None,
                exposure_bias=None,
                focal_length=None,
                fps=None,
                latitude=None,
                longitude=None,
                shutter_speed=None,
                camera_make=None,
                camera_model=None,
                codec=None,
                lens_model=None,
            )

        return exif_info

    @property
    def exiftool(self) -> ExifToolCaching | None:
        """Returns a ExifToolCaching (read-only instance of ExifTool) object for the photo.
        Requires that exiftool (https://exiftool.org/) be installed
        If exiftool not installed, logs warning and returns None
        If photo path is missing, returns None
        """
        try:
            # return the memoized instance if it exists
            return self._exiftool
        except AttributeError:
            try:
                exiftool_path = self._db._exiftool_path or get_exiftool_path()
                if self.path is not None and os.path.isfile(self.path):
                    exiftool = ExifToolCaching(self.path, exiftool=exiftool_path)
                else:
                    exiftool = None
            except FileNotFoundError:
                # get_exiftool_path raises FileNotFoundError if exiftool not found
                exiftool = None
                logging.warning(
                    "exiftool not in path; download and install from https://exiftool.org/"
                )

            self._exiftool = exiftool
            return self._exiftool

    @cached_property
    def hexdigest(self) -> str:
        """Returns a unique digest of the photo's properties and metadata;
        useful for detecting changes in any property/metadata of the photo"""
        return hexdigest(self._json_hexdigest())

    @cached_property
    def cloud_metadata(self) -> dict[Any, Any]:
        """Returns contents of ZCLOUDMASTERMEDIAMETADATA as dict; Photos 5+ only"""
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return {}

        # This is a large blob of data so don't load it unless requested
        asset_table = _DB_TABLE_NAMES[self._db._photos_ver]["ASSET"]
        sql_cloud_metadata = f"""
            SELECT ZCLOUDMASTERMEDIAMETADATA.ZDATA
            FROM ZCLOUDMASTERMEDIAMETADATA
            JOIN ZCLOUDMASTER ON ZCLOUDMASTER.Z_PK = ZCLOUDMASTERMEDIAMETADATA.ZCLOUDMASTER
            JOIN {asset_table} on  {asset_table}.ZMASTER = ZCLOUDMASTER.Z_PK
            WHERE {asset_table}.ZUUID = ?
        """

        _, cursor = self._db.get_db_connection()
        metadata = {}
        if results := cursor.execute(sql_cloud_metadata, (self.uuid,)).fetchone():
            with contextlib.suppress(Exception):
                metadata = plistlib.loads(results[0])
        return metadata

    @cached_property
    def cloud_guid(self) -> str:
        """Returns the GUID of the photo in iCloud (Photos 5+ only)"""
        return self._info["cloudMasterGUID"]

    @cached_property
    def cloud_owner_hashed_id(self) -> str:
        """Returns the hashed iCloud ID of the owner of the shared photo (Photos 5+ only)"""
        return self._info["cloudownerhashedpersonid"]

    @cached_property
    def fingerprint(self) -> str:
        """Returns fingerprint of original photo as a string"""
        return self._info["masterFingerprint"]

    def detected_text(
        self, confidence_threshold=TEXT_DETECTION_CONFIDENCE_THRESHOLD
    ) -> list[tuple[str, float]]:
        """Detects text in photo and returns lists of results as (detected text, confidence)

        confidence_threshold: float between 0.0 and 1.0. If text detection confidence is below this threshold,
        text will not be returned. Default is TEXT_DETECTION_CONFIDENCE_THRESHOLD

        If photo is edited, uses the edited photo, otherwise the original; falls back to the preview image if neither edited or original is available

        Returns: list of (detected text, confidence) tuples
        """

        try:
            return self._detected_text_cache[confidence_threshold]
        except (AttributeError, KeyError) as e:
            if isinstance(e, AttributeError):
                self._detected_text_cache = {}

            try:
                detected_text = self._detected_text()
            except Exception as e:
                logging.warning(f"Error detecting text in photo {self.uuid}: {e}")
                detected_text = []

            self._detected_text_cache[confidence_threshold] = [
                (text, confidence)
                for text, confidence in detected_text
                if confidence >= confidence_threshold
            ]
            return self._detected_text_cache[confidence_threshold]

    def _detected_text(self):
        """detect text in photo, either from cached extended attribute or by attempting text detection"""
        assert_macos()

        path = (
            self.path_edited if self.hasadjustments and self.path_edited else self.path
        )
        path = path or self.path_derivatives[0] if self.path_derivatives else None
        if not path:
            return []

        md = OSXMetaData(path)
        try:

            def decoder(val):
                """Decode value from JSON"""
                return json.loads(val.decode("utf-8"))

            detected_text = md.get_xattr(
                "osxphotos.metadata:detected_text", decode=decoder
            )
        except KeyError:
            detected_text = None
        if detected_text is None:
            orientation = self.orientation or None
            detected_text = detect_text(path, orientation)

            def encoder(obj):
                """Encode value as JSON"""
                val = json.dumps(obj)
                return val.encode("utf-8")

            md.set_xattr(
                "osxphotos.metadata:detected_text", detected_text, encode=encoder
            )
        return detected_text

    @property
    def _longitude(self) -> float:
        """Returns longitude, in degrees"""
        return self._info["longitude"]

    @property
    def _latitude(self) -> float:
        """Returns latitude, in degrees"""
        return self._info["latitude"]

    def render_template(
        self, template_str: str, options: Optional[RenderOptions] = None
    ) -> tuple[list[str], list[str]]:
        """Renders a template string for PhotoInfo instance using PhotoTemplate

        Args:
            template_str: a template string with fields to render
            options: a RenderOptions instance

        Returns:
            ([rendered_strings], [unmatched]): tuple of list of rendered strings and list of unmatched template values
        """
        options = options or RenderOptions()
        template = PhotoTemplate(self, exiftool_path=self._db._exiftool_path)
        return template.render(template_str, options)

    def export(
        self,
        dest,
        filename=None,
        edited=False,
        live_photo=False,
        raw_photo=False,
        export_as_hardlink=False,
        overwrite=False,
        increment=True,
        sidecar_json=False,
        sidecar_exiftool=False,
        sidecar_xmp=False,
        use_photos_export=False,
        timeout=120,
        exiftool=False,
        use_albums_as_keywords=False,
        use_persons_as_keywords=False,
        keyword_template=None,
        description_template=None,
        render_options: Optional[RenderOptions] = None,
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
              reference PhotoInfo.path_edited
            edited: (boolean, default=False); if True will export the edited version of the photo, otherwise exports the original version
              (or raise exception if no edited version)
            live_photo: (boolean, default=False); if True, will also export the associated .mov for live photos
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
            use_photos_export: (boolean, default=False); if True will attempt to export photo via applescript interaction with Photos
            timeout: (int, default=120) timeout in seconds used with use_photos_export
            exiftool: (boolean, default = False); if True, will use exiftool to write metadata to export file
            returns list of full paths to the exported files
            use_albums_as_keywords: (boolean, default = False); if True, will include album names in keywords
            when exporting metadata with exiftool or sidecar
            use_persons_as_keywords: (boolean, default = False); if True, will include person names in keywords
            when exporting metadata with exiftool or sidecar
            keyword_template: (list of strings); list of template strings that will be rendered as used as keywords
            description_template: string; optional template string that will be rendered for use as photo description
            render_options: an optional osxphotos.phototemplate.RenderOptions instance with options to pass to template renderer

        Returns:
            list of photos exported
        """

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
            live_photo=live_photo,
            overwrite=overwrite,
            raw_photo=raw_photo,
            render_options=render_options,
            sidecar=sidecar,
            timeout=timeout,
            use_albums_as_keywords=use_albums_as_keywords,
            use_persons_as_keywords=use_persons_as_keywords,
            use_photos_export=use_photos_export,
        )

        results = exporter.export(dest, filename=filename, options=options)
        return results.exported

    def _get_album_uuids(self, project=False) -> list[str]:
        """Return list of album UUIDs this photo is found in

            Filters out albums in the trash and any special album types

            if project is True, returns special "My Project" albums (e.g. cards, calendars, slideshows)

        Returns: list of album UUIDs
        """
        if self._db._db_version <= _PHOTOS_4_VERSION:
            album_kind = [_PHOTOS_4_ALBUM_KIND]
            album_type = (
                [_PHOTOS_4_ALBUM_TYPE_PROJECT, _PHOTOS_4_ALBUM_TYPE_SLIDESHOW]
                if project
                else [_PHOTOS_4_ALBUM_TYPE_ALBUM]
            )
            album_list = []
            for album in self._info["albums"]:
                detail = self._db._dbalbum_details[album]
                if (
                    detail["kind"] in album_kind
                    and detail["albumType"] in album_type
                    and not detail["intrash"]
                    and detail["folderUuid"] != _PHOTOS_4_ROOT_FOLDER
                    # in Photos <= 4, special albums like "printAlbum" have kind _PHOTOS_4_ALBUM_KIND
                    # but should not be listed here; they can be distinguished by looking
                    # for folderUuid of _PHOTOS_4_ROOT_FOLDER as opposed to _PHOTOS_4_TOP_LEVEL_ALBUM
                ):
                    album_list.append(album)
            return album_list

        # Photos 5+
        album_kind = (
            [_PHOTOS_5_PROJECT_ALBUM_KIND]
            if project
            else [_PHOTOS_5_SHARED_ALBUM_KIND, _PHOTOS_5_ALBUM_KIND]
        )

        album_list = []
        for album in self._info["albums"]:
            detail = self._db._dbalbum_details[album]
            if detail["kind"] in album_kind and not detail["intrash"]:
                album_list.append(album)
        return album_list

    def __repr__(self) -> str:
        return f"osxphotos.{self.__class__.__name__}(db={self._db}, uuid='{self._uuid}', info={self._info})"

    def __str__(self) -> str:
        """string representation of PhotoInfo object"""

        date_iso = self.date.isoformat()
        date_modified_iso = (
            self.date_modified.isoformat() if self.date_modified else None
        )
        exif = str(self.exif_info) if self.exif_info else None
        score = str(self.score) if self.score else None

        info = {
            "uuid": self.uuid,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "date": date_iso,
            "description": self.description,
            "title": self.title,
            "keywords": self.keywords,
            "albums": self.albums,
            "persons": self.persons,
            "path": self.path,
            "ismissing": self.ismissing,
            "hasadjustments": self.hasadjustments,
            "external_edit": self.external_edit,
            "favorite": self.favorite,
            "hidden": self.hidden,
            "latitude": self._latitude,
            "longitude": self._longitude,
            "path_edited": self.path_edited,
            "shared": self.shared,
            "isphoto": self.isphoto,
            "ismovie": self.ismovie,
            "uti": self.uti,
            "burst": self.burst,
            "live_photo": self.live_photo,
            "path_live_photo": self.path_live_photo,
            "iscloudasset": self.iscloudasset,
            "incloud": self.incloud,
            "date_modified": date_modified_iso,
            "portrait": self.portrait,
            "screenshot": self.screenshot,
            "slow_mo": self.slow_mo,
            "time_lapse": self.time_lapse,
            "hdr": self.hdr,
            "selfie": self.selfie,
            "panorama": self.panorama,
            "has_raw": self.has_raw,
            "uti_raw": self.uti_raw,
            "path_raw": self.path_raw,
            "place": self.place,
            "exif": exif,
            "score": score,
            "intrash": self.intrash,
            "height": self.height,
            "width": self.width,
            "orientation": self.orientation,
            "original_height": self.original_height,
            "original_width": self.original_width,
            "original_orientation": self.original_orientation,
            "original_filesize": self.original_filesize,
        }
        return yaml.dump(info, sort_keys=False)

    def asdict(self, shallow: bool = True) -> dict[str, Any]:
        """Return dict representation of PhotoInfo object.

        Args:
            shallow: if True, return shallow representation (does not contain folder_info, person_info, etc.)

        Returns:
            dict representation of PhotoInfo object

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

    def tables(self) -> PhotoTables | None:
        """Return PhotoTables object to provide access database tables associated with this photo (Photos 5+)"""
        return None if self._db._photos_ver < 5 else PhotoTables(self)

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

    def __eq__(self, other) -> bool:
        """Compare two PhotoInfo objects for equality"""
        # Can't just compare the two __dicts__ because some methods (like albums)
        # memoize their value once called in an instance variable (e.g. self._albums)
        if isinstance(other, self.__class__):
            return (
                self._db.db_path == other._db.db_path
                and self.uuid == other.uuid
                and self._info == other._info
            )
        return False

    def __ne__(self, other) -> bool:
        """Compare two PhotoInfo objects for inequality"""
        return not self.__eq__(other)

    def __hash__(self) -> int:
        """Make PhotoInfo hashable"""
        return hash(self.uuid)


class PhotoInfoNone:
    """Mock class that returns None for all attributes"""

    def __init__(self):
        pass

    def __getattribute__(self, name):
        return None


def frozen_photoinfo_factory(photo: PhotoInfo) -> SimpleNamespace:
    """Return a frozen SimpleNamespace object for a PhotoInfo object"""
    photo_json = photo.json()

    def _object_hook(d: dict[Any, Any]):
        if not d:
            return d

        # if d key matches a ISO 8601 datetime ('2023-03-24T06:46:57.690786', '2019-07-04T16:24:01-07:00', '2019-07-04T16:24:01+07:00'), convert to datetime
        # fromisoformat will also handle dates with timezone offset in form +0700, etc.
        for k, v in d.items():
            if isinstance(v, str) and re.match(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[.]?\d*[+-]?\d{2}[:]?\d{2}?", v
            ):
                d[k] = datetime.datetime.fromisoformat(v)
        return SimpleNamespace(**d)

    frozen = json.loads(photo_json, object_hook=lambda d: _object_hook(d))

    # add on json() method to frozen object
    def _json(*args):
        return photo_json

    frozen.json = _json

    # add hexdigest property to frozen object
    frozen.hexdigest = photo.hexdigest

    def detected_text(confidence_threshold=TEXT_DETECTION_CONFIDENCE_THRESHOLD):
        """Detects text in photo and returns lists of results as (detected text, confidence)

        confidence_threshold: float between 0.0 and 1.0. If text detection confidence is below this threshold,
        text will not be returned. Default is TEXT_DETECTION_CONFIDENCE_THRESHOLD

        If photo is edited, uses the edited photo, otherwise the original; falls back to the preview image if neither edited or original is available

        Returns: list of (detected text, confidence) tuples
        """

        try:
            return frozen._detected_text_cache[confidence_threshold]
        except (AttributeError, KeyError) as e:
            if isinstance(e, AttributeError):
                frozen._detected_text_cache = {}

            try:
                detected_text = frozen._detected_text()
            except Exception as e:
                logging.warning(f"Error detecting text in photo {frozen.uuid}: {e}")
                detected_text = []

            frozen._detected_text_cache[confidence_threshold] = [
                (text, confidence)
                for text, confidence in detected_text
                if confidence >= confidence_threshold
            ]
            return frozen._detected_text_cache[confidence_threshold]

    def _detected_text():
        """detect text in photo, either from cached extended attribute or by attempting text detection"""
        path = (
            frozen.path_edited
            if frozen.hasadjustments and frozen.path_edited
            else frozen.path
        )
        path = path or frozen.path_derivatives[0] if frozen.path_derivatives else None
        if not path:
            return []

        md = OSXMetaData(path)
        try:

            def decoder(val):
                """Decode value from JSON"""
                return json.loads(val.decode("utf-8"))

            detected_text = md.get_xattr(
                "osxphotos.metadata:detected_text", decode=decoder
            )
        except KeyError:
            detected_text = None
        if detected_text is None:
            orientation = frozen.orientation or None
            detected_text = detect_text(path, orientation)

            def encoder(obj):
                """Encode value as JSON"""
                val = json.dumps(obj)
                return val.encode("utf-8")

            md.set_xattr(
                "osxphotos.metadata:detected_text", detected_text, encode=encoder
            )
        return detected_text

    frozen.detected_text = detected_text
    frozen._detected_text = _detected_text

    return frozen
