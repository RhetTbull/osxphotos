"""
PhotoInfo class
Represents a single photo in the Photos library and provides access to the photo's attributes
PhotosDB.photos() returns a list of PhotoInfo objects
"""
import dataclasses
import datetime
import json
import logging
import os
import os.path
import pathlib
from datetime import timedelta, timezone
from typing import Optional

import yaml
from osxmetadata import OSXMetaData

from .._constants import (
    _MOVIE_TYPE,
    _PHOTO_TYPE,
    _PHOTOS_4_ALBUM_KIND,
    _PHOTOS_4_ROOT_FOLDER,
    _PHOTOS_4_VERSION,
    _PHOTOS_5_ALBUM_KIND,
    _PHOTOS_5_IMPORT_SESSION_ALBUM_KIND,
    _PHOTOS_5_SHARED_ALBUM_KIND,
    _PHOTOS_5_SHARED_PHOTO_PATH,
    _PHOTOS_5_VERSION,
    BURST_DEFAULT_PICK,
    BURST_KEY,
    BURST_NOT_SELECTED,
    BURST_SELECTED,
    TEXT_DETECTION_CONFIDENCE_THRESHOLD,
)
from ..adjustmentsinfo import AdjustmentsInfo
from ..albuminfo import AlbumInfo, ImportInfo
from ..personinfo import FaceInfo, PersonInfo
from ..phototemplate import PhotoTemplate, RenderOptions
from ..placeinfo import PlaceInfo4, PlaceInfo5
from ..query_builder import get_query
from ..text_detection import detect_text
from ..uti import get_preferred_uti_extension, get_uti_for_extension
from ..utils import _debug, _get_resource_loc, findfiles


class PhotoInfo:
    """
    Info about a specific photo, contains all the details about the photo
    including keywords, persons, albums, uuid, path, etc.
    """

    # import additional methods
    from ._photoinfo_comments import comments, likes
    from ._photoinfo_exifinfo import ExifInfo, exif_info
    from ._photoinfo_exiftool import exiftool
    from ._photoinfo_export import (
        ExportResults,
        _exiftool_dict,
        _exiftool_json_sidecar,
        _export_photo,
        _export_photo_with_photos_export,
        _get_exif_keywords,
        _get_exif_persons,
        _write_exif_data,
        _write_sidecar,
        _xmp_sidecar,
        export,
        export2,
    )
    from ._photoinfo_scoreinfo import ScoreInfo, score
    from ._photoinfo_searchinfo import (
        SearchInfo,
        labels,
        labels_normalized,
        search_info,
        search_info_normalized,
    )

    def __init__(self, db=None, uuid=None, info=None):
        self._uuid = uuid
        self._info = info
        self._db = db
        self._verbose = self._db._verbose

        # TODO: remove this once refactor of PhotoExporter is done
        self._render_options = RenderOptions()

    @property
    def filename(self):
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
    def original_filename(self):
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
    def date(self):
        """image creation date as timezone aware datetime object"""
        return self._info["imageDate"]

    @property
    def date_modified(self):
        """image modification date as timezone aware datetime object
        or None if no modification date set"""

        # Photos <= 4 provides no way to get date of adjustment and will update
        # lastmodifieddate anytime photo database record is updated (e.g. adding tags)
        # only report lastmodified date for Photos <=4 if photo is edited;
        # even in this case, the date could be incorrect
        if not self.hasadjustments and self._db._db_version <= _PHOTOS_4_VERSION:
            return None

        imagedate = self._info["lastmodifieddate"]
        if imagedate:
            seconds = self._info["imageTimeZoneOffsetSeconds"] or 0
            delta = timedelta(seconds=seconds)
            tz = timezone(delta)
            return imagedate.astimezone(tz=tz)
        else:
            return None

    @property
    def tzoffset(self):
        """timezone offset from UTC in seconds"""
        return self._info["imageTimeZoneOffsetSeconds"]

    @property
    def path(self):
        """absolute path on disk of the original picture"""
        try:
            return self._path
        except AttributeError:
            self._path = None
            photopath = None
            if self._info["isMissing"] == 1:
                return photopath  # path would be meaningless until downloaded

            if self._db._db_version <= _PHOTOS_4_VERSION:
                return self._path_4()

            if self._info["shared"]:
                # shared photo
                photopath = os.path.join(
                    self._db._library_path,
                    _PHOTOS_5_SHARED_PHOTO_PATH,
                    self._info["directory"],
                    self._info["filename"],
                )
                if not os.path.isfile(photopath):
                    photopath = None
                self._path = photopath
                return photopath

            if self._info["directory"].startswith("/"):
                photopath = os.path.join(
                    self._info["directory"], self._info["filename"]
                )
            else:
                photopath = os.path.join(
                    self._db._masters_path,
                    self._info["directory"],
                    self._info["filename"],
                )
            if not os.path.isfile(photopath):
                photopath = None
            self._path = photopath
            return photopath

    def _path_4(self):
        """return path for photo on Photos <= version 4"""
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
        if not os.path.isfile(photopath):
            photopath = None
        self._path = photopath
        return photopath

    @property
    def path_edited(self):
        """absolute path on disk of the edited picture"""
        """ None if photo has not been edited """

        try:
            return self._path_edited
        except AttributeError:
            if self._db._db_version <= _PHOTOS_4_VERSION:
                self._path_edited = self._path_edited_4()
            else:
                self._path_edited = self._path_edited_5()

            return self._path_edited

    def _path_edited_5(self):
        """return path_edited for Photos >= 5"""
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
                logging.debug(f"WARNING: unknown type {self._info['type']}")
                return None

            photopath = os.path.join(
                library, "resources", "renders", directory, filename
            )

            if not os.path.isfile(photopath):
                logging.debug(
                    f"edited file for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                )
                photopath = None
        else:
            photopath = None

        # TODO: might be possible for original/master to be missing but edit to still be there
        # if self._info["isMissing"] == 1:
        #     photopath = None  # path would be meaningless until downloaded

        return photopath

    def _path_edited_4(self):
        """return path_edited for Photos <= 4"""

        if self._db._db_version > _PHOTOS_4_VERSION:
            raise RuntimeError("Wrong database format!")

        photopath = None
        if self._info["hasAdjustments"]:
            edit_id = self._info["edit_resource_id"]
            if edit_id is not None:
                library = self._db._library_path
                folder_id, file_id = _get_resource_loc(edit_id)
                # todo: is this always true or do we need to search file file_id under folder_id
                # figure out what kind it is and build filename
                filename = None
                if self._info["type"] == _PHOTO_TYPE:
                    # it's a photo
                    filename = f"fullsizeoutput_{file_id}.jpeg"
                elif self._info["type"] == _MOVIE_TYPE:
                    # it's a movie
                    filename = f"fullsizeoutput_{file_id}.mov"
                else:
                    # don't know what it is!
                    logging.debug(f"WARNING: unknown type {self._info['type']}")
                    return None

                # photopath appears to usually be in "00" subfolder but
                # could be elsewhere--I haven't figured out this logic yet
                # first see if it's in 00
                photopath = os.path.join(
                    library, "resources", "media", "version", folder_id, "00", filename
                )

                if not os.path.isfile(photopath):
                    rootdir = os.path.join(
                        library, "resources", "media", "version", folder_id
                    )

                    for dirname, _, filelist in os.walk(rootdir):
                        if filename in filelist:
                            photopath = os.path.join(dirname, filename)
                            break

                # check again to see if we found a valid file
                if not os.path.isfile(photopath):
                    logging.debug(
                        f"MISSING PATH: edited file for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                    )
                    photopath = None
            else:
                logging.debug(
                    f"{self.uuid} hasAdjustments but edit_resource_id is None"
                )
                photopath = None
        else:
            photopath = None

        return photopath

    @property
    def path_edited_live_photo(self):
        """return path to edited version of live photo movie; only valid for Photos 5+"""
        if self._db._db_version < _PHOTOS_5_VERSION:
            return None

        try:
            return self._path_edited_live_photo
        except AttributeError:
            self._path_edited_live_photo = self._path_edited_5_live_photo()
            return self._path_edited_live_photo

    def _path_edited_5_live_photo(self):
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
    def path_raw(self):
        """absolute path of associated RAW image or None if there is not one"""

        # In Photos 5, raw is in same folder as original but with _4.ext
        # Unless "Copy Items to the Photos Library" is not checked
        # then RAW image is not renamed but has same name is jpeg buth with raw extension
        # Current implementation uses findfiles to find images with the correct raw UTI extension
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

            # raw files have same name as original but with _4.raw_ext appended
            # I believe the _4 maps to PHAssetResourceTypeAlternatePhoto = 4
            # see: https://developer.apple.com/documentation/photokit/phassetresourcetype/phassetresourcetypealternatephoto?language=objc
            glob_str = f"{filestem}_4*"
            raw_file = findfiles(glob_str, filepath)
            if not raw_file:
                photopath = None
            else:
                photopath = pathlib.Path(filepath) / raw_file[0]
                photopath = str(photopath) if photopath.is_file() else None
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

    def _path_raw_4(self):
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
            logging.debug(
                f"MISSING PATH: RAW photo for UUID {self._uuid} should be at {photopath} but does not appear to exist"
            )
            photopath = None

    @property
    def description(self):
        """long / extended description of picture"""
        return self._info["extendedDescription"]

    @property
    def persons(self):
        """list of persons in picture"""
        return [self._db._dbpersons_pk[pk]["fullname"] for pk in self._info["persons"]]

    @property
    def person_info(self):
        """list of PersonInfo objects for person in picture"""
        try:
            return self._personinfo
        except AttributeError:
            self._personinfo = [
                PersonInfo(db=self._db, pk=pk) for pk in self._info["persons"]
            ]
            return self._personinfo

    @property
    def face_info(self):
        """list of FaceInfo objects for faces in picture"""
        try:
            return self._faceinfo
        except AttributeError:
            try:
                faces = self._db._db_faceinfo_uuid[self._uuid]
                self._faceinfo = [FaceInfo(db=self._db, pk=pk) for pk in faces]
            except KeyError:
                # no faces
                self._faceinfo = []
            return self._faceinfo

    @property
    def albums(self):
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
    def burst_albums(self):
        """If photo is burst photo, list of albums it is contained in as well as any albums the key photo is contained in, otherwise returns self.albums"""
        try:
            return self._burst_albums
        except AttributeError:
            burst_albums = list(self.albums)
            for photo in self.burst_photos:
                if photo.burst_key:
                    burst_albums.extend(photo.albums)
            self._burst_albums = list(set(burst_albums))
            return self._burst_albums

    @property
    def album_info(self):
        """list of AlbumInfo objects representing albums the photo is contained in"""
        try:
            return self._album_info
        except AttributeError:
            album_uuids = self._get_album_uuids()
            self._album_info = [
                AlbumInfo(db=self._db, uuid=album) for album in album_uuids
            ]
            return self._album_info

    @property
    def burst_album_info(self):
        """If photo is a burst photo, returns list of AlbumInfo objects representing albums the photo is contained in as well as albums the burst key photo is contained in, otherwise returns self.album_info."""
        try:
            return self._burst_album_info
        except AttributeError:
            burst_album_info = list(self.album_info)
            for photo in self.burst_photos:
                if photo.burst_key:
                    burst_album_info.extend(photo.album_info)
            self._burst_album_info = list(set(burst_album_info))
            return self._burst_album_info

    @property
    def import_info(self):
        """ImportInfo object representing import session for the photo or None if no import session"""
        try:
            return self._import_info
        except AttributeError:
            self._import_info = (
                ImportInfo(db=self._db, uuid=self._info["import_uuid"])
                if self._info["import_uuid"] is not None
                else None
            )
            return self._import_info

    @property
    def keywords(self):
        """list of keywords for picture"""
        return self._info["keywords"]

    @property
    def title(self):
        """name / title of picture"""
        # if user sets then deletes title, Photos sets it to empty string in DB instead of NULL
        # in this case, return None so result is the same as if title had never been set (which returns NULL)
        # issue #512
        title = self._info["name"]
        title = None if title == "" else title
        return title

    @property
    def uuid(self):
        """UUID of picture"""
        return self._uuid

    @property
    def ismissing(self):
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
    def hasadjustments(self):
        """True if picture has adjustments / edits"""
        return self._info["hasAdjustments"] == 1

    @property
    def adjustments(self):
        """Returns AdjustmentsInfo class for adjustment data or None if no adjustments; Photos 5+ only"""
        if self._db._db_version <= _PHOTOS_4_VERSION:
            return None

        if self.hasadjustments:
            try:
                return self._adjustmentinfo
            except AttributeError:
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
                self._adjustmentinfo = AdjustmentsInfo(plist_file)
                return self._adjustmentinfo

    @property
    def external_edit(self):
        """Returns True if picture was edited outside of Photos using external editor"""
        return self._info["adjustmentFormatID"] == "com.apple.Photos.externalEdit"

    @property
    def favorite(self):
        """True if picture is marked as favorite"""
        return self._info["favorite"] == 1

    @property
    def hidden(self):
        """True if picture is hidden"""
        return self._info["hidden"] == 1

    @property
    def visible(self):
        """True if picture is visble"""
        return self._info["visible"]

    @property
    def intrash(self):
        """True if picture is in trash ('Recently Deleted' folder)"""
        return self._info["intrash"]

    @property
    def date_trashed(self):
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
    def date_added(self):
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
    def location(self):
        """returns (latitude, longitude) as float in degrees or None"""
        return (self._latitude, self._longitude)

    @property
    def shared(self):
        """returns True if photos is in a shared iCloud album otherwise false
        Only valid on Photos 5; returns None on older versions"""
        if self._db._db_version > _PHOTOS_4_VERSION:
            return self._info["shared"]
        else:
            return None

    @property
    def uti(self):
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
    def uti_original(self):
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
                self._uti_original = get_uti_for_extension(
                    pathlib.Path(self.original_filename).suffix
                )
            else:
                self._uti_original = self._info["UTI_original"]

            return self._uti_original

    @property
    def uti_edited(self):
        """Returns Uniform Type Identifier (UTI) for the edited image
        if the photo has been edited, otherwise None;
        for example: public.jpeg
        """
        if self._db._db_version >= _PHOTOS_5_VERSION:
            return self.uti if self.hasadjustments else None
        else:
            return self._info["UTI_edited"]

    @property
    def uti_raw(self):
        """Returns Uniform Type Identifier (UTI) for the RAW image if there is one
        for example: com.canon.cr2-raw-image
        Returns None if no associated RAW image
        """
        if self._db._photos_ver < 7:
            return self._info["UTI_raw"]

        rawpath = self.path_raw
        if rawpath:
            return get_uti_for_extension(pathlib.Path(rawpath).suffix)
        else:
            return None

    @property
    def ismovie(self):
        """Returns True if file is a movie, otherwise False"""
        return self._info["type"] == _MOVIE_TYPE

    @property
    def isphoto(self):
        """Returns True if file is an image, otherwise False"""
        return self._info["type"] == _PHOTO_TYPE

    @property
    def incloud(self):
        """Returns True if photo is cloud asset and is synched to cloud
        False if photo is cloud asset and not yet synched to cloud
        None if photo is not cloud asset
        """
        return self._info["incloud"]

    @property
    def iscloudasset(self):
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
    def isreference(self):
        """Returns True if photo is a reference (not copied to the Photos library), otherwise False"""
        return self._info["isreference"]

    @property
    def burst(self):
        """Returns True if photo is part of a Burst photo set, otherwise False"""
        return self._info["burst"]

    @property
    def burst_selected(self):
        """Returns True if photo is a burst photo and has been selected from the burst set by the user, otherwise False"""
        return bool(self._info["burstPickType"] & BURST_SELECTED)

    @property
    def burst_key(self):
        """Returns True if photo is a burst photo and is the key image for the burst set (the image that Photos shows on top of the burst stack), otherwise False"""
        return bool(self._info["burstPickType"] & BURST_KEY)

    @property
    def burst_default_pick(self):
        """Returns True if photo is a burst image and is the photo that Photos selected as the default image for the burst set, otherwise False"""
        return bool(self._info["burstPickType"] & BURST_DEFAULT_PICK)

    @property
    def burst_photos(self):
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
    def live_photo(self):
        """Returns True if photo is a live photo, otherwise False"""
        return self._info["live_photo"]

    @property
    def path_live_photo(self):
        """Returns path to the associated video file for a live photo
        If photo is not a live photo, returns None
        If photo is missing, returns None"""

        photopath = None
        if self._db._db_version <= _PHOTOS_4_VERSION:
            if self.live_photo and not self.ismissing:
                live_model_id = self._info["live_model_id"]
                if live_model_id == None:
                    logging.debug(f"missing live_model_id: {self._uuid}")
                    photopath = None
                else:
                    folder_id, file_id = _get_resource_loc(live_model_id)
                    library_path = self._db.library_path
                    photopath = os.path.join(
                        library_path,
                        "resources",
                        "media",
                        "master",
                        folder_id,
                        "00",
                        f"jpegvideocomplement_{file_id}.mov",
                    )
                    if not os.path.isfile(photopath):
                        # In testing, I've seen occasional missing movie for live photo
                        # These appear to be valid -- e.g. live component hasn't been downloaded from iCloud
                        # photos 4 has "isOnDisk" column we could check
                        # or could do the actual check with "isfile"
                        # TODO: should this be a warning or debug?
                        logging.debug(
                            f"MISSING PATH: live photo path for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                        )
                        photopath = None
            else:
                photopath = None
        else:
            # Photos 5
            if self.live_photo and not self.ismissing:
                filename = pathlib.Path(self.path)
                photopath = filename.parent.joinpath(f"{filename.stem}_3.mov")
                photopath = str(photopath)
                if not os.path.isfile(photopath):
                    # In testing, I've seen occasional missing movie for live photo
                    # these appear to be valid -- e.g. video component not yet downloaded from iCloud
                    # TODO: should this be a warning or debug?
                    logging.debug(
                        f"MISSING PATH: live photo path for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                    )
                    photopath = None
            else:
                photopath = None

        return photopath

    @property
    def path_derivatives(self):
        """Return any derivative (preview) images associated with the photo as a list of paths, sorted by file size (largest first)"""
        try:
            return self._path_derivatives
        except AttributeError:
            if self._db._db_version <= _PHOTOS_4_VERSION:
                self._path_derivatives = self._path_derivatives_4()
                return self._path_derivatives

            directory = self._uuid[0]  # first char of uuid
            derivative_path = (
                pathlib.Path(self._db._library_path)
                / "resources"
                / "derivatives"
                / directory
            )
            files = derivative_path.glob(f"{self.uuid}*.*")
            files = sorted(files, reverse=True, key=lambda f: f.stat().st_size)
            # return list of filename but skip .THM files (these are actually low-res thumbnails in JPEG format but with .THM extension)
            derivatives = [
                str(filename) for filename in files if filename.suffix != ".THM"
            ]
            if (
                self.isphoto
                and len(derivatives) > 1
                and derivatives[0].endswith(".mov")
            ):
                derivatives[1], derivatives[0] = derivatives[0], derivatives[1]

            self._path_derivatives = derivatives
            return self._path_derivatives

    def _path_derivatives_4(self):
        """Return paths to all derivative (preview) files for Photos <= 4"""
        modelid = self._info["modelID"]
        if modelid is None:
            return []
        folder_id, file_id = _get_resource_loc(modelid)
        derivatives_root = (
            pathlib.Path(self._db._library_path)
            / "resources"
            / "proxies"
            / "derivatives"
            / folder_id
        )

        # photos appears to usually be in "00" subfolder but
        # could be elsewhere--I haven't figured out this logic yet
        # first see if it's in 00

        derivatives_path = derivatives_root / "00" / file_id
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

    @property
    def panorama(self):
        """Returns True if photo is a panorama, otherwise False"""
        return self._info["panorama"]

    @property
    def slow_mo(self):
        """Returns True if photo is a slow motion video, otherwise False"""
        return self._info["slow_mo"]

    @property
    def time_lapse(self):
        """Returns True if photo is a time lapse video, otherwise False"""
        return self._info["time_lapse"]

    @property
    def hdr(self):
        """Returns True if photo is an HDR photo, otherwise False"""
        return self._info["hdr"]

    @property
    def screenshot(self):
        """Returns True if photo is an HDR photo, otherwise False"""
        return self._info["screenshot"]

    @property
    def portrait(self):
        """Returns True if photo is a portrait, otherwise False"""
        return self._info["portrait"]

    @property
    def selfie(self):
        """Returns True if photo is a selfie (front facing camera), otherwise False"""
        return self._info["selfie"]

    @property
    def place(self):
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
    def has_raw(self):
        """returns True if photo has an associated raw image (that is, it's a RAW+JPEG pair), otherwise False"""
        return self._info["has_raw"]

    @property
    def israw(self):
        """returns True if photo is a raw image. For images with an associated RAW+JPEG pair, see has_raw"""
        return "raw-image" in self.uti_original

    @property
    def raw_original(self):
        """returns True if associated raw image and the raw image is selected in Photos
        via "Use RAW as Original "
        otherwise returns False"""
        return self._info["raw_is_original"]

    @property
    def height(self):
        """returns height of the current photo version in pixels"""
        return self._info["height"]

    @property
    def width(self):
        """returns width of the current photo version in pixels"""
        return self._info["width"]

    @property
    def orientation(self):
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
    def original_height(self):
        """returns height of the original photo version in pixels"""
        return self._info["original_height"]

    @property
    def original_width(self):
        """returns width of the original photo version in pixels"""
        return self._info["original_width"]

    @property
    def original_orientation(self):
        """returns EXIF orientation of the original photo version as int"""
        return self._info["original_orientation"]

    @property
    def original_filesize(self):
        """returns filesize of original photo in bytes as int"""
        return self._info["original_filesize"]

    @property
    def duplicates(self):
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
    def owner(self):
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

    def render_template(
        self, template_str: str, options: Optional[RenderOptions] = None
    ):
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

    def detected_text(self, confidence_threshold=TEXT_DETECTION_CONFIDENCE_THRESHOLD):
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
        path = (
            self.path_edited if self.hasadjustments and self.path_edited else self.path
        )
        path = path or self.path_derivatives[0] if self.path_derivatives else None
        if not path:
            return []

        md = OSXMetaData(path)
        detected_text = md.get_attribute("osxphotos_detected_text")
        if detected_text is None:
            orientation = self.orientation or None
            detected_text = detect_text(path, orientation)
            md.set_attribute("osxphotos_detected_text", detected_text)
        return detected_text

    @property
    def _longitude(self):
        """Returns longitude, in degrees"""
        return self._info["longitude"]

    @property
    def _latitude(self):
        """Returns latitude, in degrees"""
        return self._info["latitude"]

    def _get_album_uuids(self):
        """Return list of album UUIDs this photo is found in

            Filters out albums in the trash and any special album types

        Returns: list of album UUIDs
        """
        if self._db._db_version <= _PHOTOS_4_VERSION:
            version4 = True
            album_kind = [_PHOTOS_4_ALBUM_KIND]
        else:
            version4 = False
            album_kind = [_PHOTOS_5_SHARED_ALBUM_KIND, _PHOTOS_5_ALBUM_KIND]

        album_list = []
        for album in self._info["albums"]:
            detail = self._db._dbalbum_details[album]
            if (
                detail["kind"] in album_kind
                and not detail["intrash"]
                and (
                    not version4
                    # in Photos <= 4, special albums like "printAlbum" have kind _PHOTOS_4_ALBUM_KIND
                    # but should not be listed here; they can be distinguished by looking
                    # for folderUuid of _PHOTOS_4_ROOT_FOLDER as opposed to _PHOTOS_4_TOP_LEVEL_ALBUM
                    or (version4 and detail["folderUuid"] != _PHOTOS_4_ROOT_FOLDER)
                )
            ):
                album_list.append(album)
        return album_list

    def __repr__(self):
        return f"osxphotos.{self.__class__.__name__}(db={self._db}, uuid='{self._uuid}', info={self._info})"

    def __str__(self):
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

    def asdict(self):
        """return dict representation"""

        folders = {album.title: album.folder_names for album in self.album_info}
        exif = dataclasses.asdict(self.exif_info) if self.exif_info else {}
        place = self.place.asdict() if self.place else {}
        score = dataclasses.asdict(self.score) if self.score else {}
        comments = [comment.asdict() for comment in self.comments]
        likes = [like.asdict() for like in self.likes]
        faces = [face.asdict() for face in self.face_info]
        search_info = self.search_info.asdict() if self.search_info else {}

        return {
            "library": self._db._library_path,
            "uuid": self.uuid,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "date": self.date,
            "description": self.description,
            "title": self.title,
            "keywords": self.keywords,
            "labels": self.labels,
            "keywords": self.keywords,
            "albums": self.albums,
            "folders": folders,
            "persons": self.persons,
            "faces": faces,
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
            "uti_original": self.uti_original,
            "burst": self.burst,
            "live_photo": self.live_photo,
            "path_live_photo": self.path_live_photo,
            "iscloudasset": self.iscloudasset,
            "incloud": self.incloud,
            "isreference": self.isreference,
            "date_modified": self.date_modified,
            "portrait": self.portrait,
            "screenshot": self.screenshot,
            "slow_mo": self.slow_mo,
            "time_lapse": self.time_lapse,
            "hdr": self.hdr,
            "selfie": self.selfie,
            "panorama": self.panorama,
            "has_raw": self.has_raw,
            "israw": self.israw,
            "raw_original": self.raw_original,
            "uti_raw": self.uti_raw,
            "path_raw": self.path_raw,
            "place": place,
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
            "comments": comments,
            "likes": likes,
            "search_info": search_info,
        }

    def json(self):
        """Return JSON representation"""

        def default(o):
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()

        return json.dumps(self.asdict(), sort_keys=True, default=default)

    def __eq__(self, other):
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

    def __ne__(self, other):
        """Compare two PhotoInfo objects for inequality"""
        return not self.__eq__(other)

    def __hash__(self):
        """Make PhotoInfo hashable"""
        return hash(self.uuid)


class PhotoInfoNone:
    """mock class that returns None for all attributes"""

    def __init__(self):
        pass

    def __getattribute__(self, name):
        return None
