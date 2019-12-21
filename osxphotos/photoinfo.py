"""
PhotoInfo class
Represents a single photo in the Photos library and provides access to the photo's attributes
PhotosDB.photos() returns a list of PhotoInfo objects
"""

import json
import logging
import os.path
import pathlib
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from ._constants import _PHOTOS_5_VERSION
from .utils import _get_resource_loc, dd_to_dms_str


class PhotoInfo:
    """
    Info about a specific photo, contains all the details about the photo
    including keywords, persons, albums, uuid, path, etc.
    """

    def __init__(self, db=None, uuid=None, info=None):
        self._uuid = uuid
        self._info = info
        self._db = db

    @property
    def filename(self):
        """ filename of the picture """
        return self._info["filename"]

    @property
    def original_filename(self):
        """ original filename of the picture """
        """ Photos 5 mangles filenames upon import """
        return self._info["originalFilename"]

    @property
    def date(self):
        """ image creation date as timezone aware datetime object """
        imagedate = self._info["imageDate"]
        seconds = self._info["imageTimeZoneOffsetSeconds"] or 0
        delta = timedelta(seconds=seconds)
        tz = timezone(delta)
        imagedate_utc = imagedate.astimezone(tz=tz)
        return imagedate_utc

    @property
    def tzoffset(self):
        """ timezone offset from UTC in seconds """
        return self._info["imageTimeZoneOffsetSeconds"]

    @property
    def path(self):
        """ absolute path on disk of the original picture """
        photopath = ""

        if self._db._db_version < _PHOTOS_5_VERSION:
            vol = self._info["volume"]
            if vol is not None:
                photopath = os.path.join("/Volumes", vol, self._info["imagePath"])
            else:
                photopath = os.path.join(
                    self._db._masters_path, self._info["imagePath"]
                )

            if self._info["isMissing"] == 1:
                photopath = None  # path would be meaningless until downloaded
                # TODO: Is there a way to use applescript or PhotoKit to force the download in this
        else:
            if self._info["masterFingerprint"]:
                # if masterFingerprint is not null, path appears to be valid
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
            else:
                photopath = None
                logging.debug(f"WARNING: masterFingerprint null {pformat(self._info)}")

            # TODO: fix the logic for isMissing
            if self._info["isMissing"] == 1:
                photopath = None  # path would be meaningless until downloaded

            logging.debug(photopath)

        return photopath

    @property
    def path_edited(self):
        """ absolute path on disk of the edited picture """
        """ None if photo has not been edited """
        photopath = ""

        if self._db._db_version < _PHOTOS_5_VERSION:
            if self._info["hasAdjustments"]:
                edit_id = self._info["edit_resource_id"]
                if edit_id is not None:
                    library = self._db._library_path
                    folder_id, file_id = _get_resource_loc(edit_id)
                    # todo: is this always true or do we need to search file file_id under folder_id
                    photopath = os.path.join(
                        library,
                        "resources",
                        "media",
                        "version",
                        folder_id,
                        "00",
                        f"fullsizeoutput_{file_id}.jpeg",
                    )
                    if not os.path.isfile(photopath):
                        logging.warning(
                            f"edited file for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                        )
                        photopath = None
                else:
                    logging.warning(
                        f"{self.uuid} hasAdjustments but edit_model_id is None"
                    )
            else:
                photopath = None

            # if self._info["isMissing"] == 1:
            #     photopath = None  # path would be meaningless until downloaded
        else:
            # in Photos 5.0 / Catalina / MacOS 10.15:
            # edited photos appear to always be converted to .jpeg and stored in
            # library_name/resources/renders/X/UUID_1_201_a.jpeg
            # where X = first letter of UUID
            # and UUID = UUID of image
            # this seems to be true even for photos not copied to Photos library and
            # where original format was not jpg/jpeg
            # if more than one edit, previous edit is stored as UUID_p.jpeg

            if self._info["hasAdjustments"]:
                library = self._db._library_path
                directory = self._uuid[0]  # first char of uuid
                photopath = os.path.join(
                    library,
                    "resources",
                    "renders",
                    directory,
                    f"{self._uuid}_1_201_a.jpeg",
                )

                if not os.path.isfile(photopath):
                    logging.warning(
                        f"edited file for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                    )
                    photopath = None
            else:
                photopath = None

            # TODO: might be possible for original/master to be missing but edit to still be there
            # if self._info["isMissing"] == 1:
            #     photopath = None  # path would be meaningless until downloaded

            logging.debug(photopath)

        return photopath

    @property
    def description(self):
        """ long / extended description of picture """
        return self._info["extendedDescription"]

    @property
    def persons(self):
        """ list of persons in picture """
        return self._info["persons"]

    @property
    def albums(self):
        """ list of albums picture is contained in """
        albums = []
        for album in self._info["albums"]:
            albums.append(self._db._dbalbum_details[album]["title"])
        return albums

    @property
    def keywords(self):
        """ list of keywords for picture """
        return self._info["keywords"]

    @property
    def title(self):
        """ name / title of picture """
        # TODO: Update documentation and tests to use title
        return self._info["name"]

    @property
    def uuid(self):
        """ UUID of picture """
        return self._uuid

    @property
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
        return True if self._info["isMissing"] == 1 else False

    @property
    def hasadjustments(self):
        """ True if picture has adjustments / edits """
        return True if self._info["hasAdjustments"] == 1 else False

    @property
    def external_edit(self):
        """ Returns True if picture was edited outside of Photos using external editor """
        return (
            True
            if self._info["adjustmentFormatID"] == "com.apple.Photos.externalEdit"
            else False
        )

    @property
    def favorite(self):
        """ True if picture is marked as favorite """
        return True if self._info["favorite"] == 1 else False

    @property
    def hidden(self):
        """ True if picture is hidden """
        return True if self._info["hidden"] == 1 else False

    @property
    def location(self):
        """ returns (latitude, longitude) as float in degrees or None """
        return (self._latitude, self._longitude)

    def export(
        self,
        dest,
        *filename,
        edited=False,
        overwrite=False,
        increment=True,
        sidecar=False,
    ):
        """ export photo """
        """ first argument must be valid destination path (or exception raised) """
        """ second argument (optional): name of picture; if not provided, will use current filename """
        """ if edited=True (default=False), will export the edited version of the photo (or raise exception if no edited version) """
        """ if overwrite=True (default=False), will overwrite files if they alreay exist """
        """ if increment=True (default=True), will increment file name until a non-existant name is found """
        """ if overwrite=False and increment=False, export will fail if destination file already exists """
        """ if sidecar=True, will also write a json sidecar with EXIF data in format readable by exiftool """
        """ sidecar filename will be dest/filename.ext.json where ext is suffix of the image file (e.g. jpeg or jpg) """
        """ returns the full path to the exported file """

        # TODO: add this docs:
        #  ( for jpeg in *.jpeg; do exiftool -v -json=$jpeg.json $jpeg; done )

        # check arguments and get destination path and filename (if provided)
        if filename and len(filename) > 2:
            raise TypeError(
                "Too many positional arguments.  Should be at most two: destination, filename."
            )
        else:
            # verify destination is a valid path
            if dest is None:
                raise ValueError("Destination must not be None")
            elif not os.path.isdir(dest):
                raise FileNotFoundError("Invalid path passed to export")

            if filename and len(filename) == 1:
                # second arg is filename of picture
                filename = filename[0]
            else:
                # no filename provided so use the default
                # if edited file requested, use filename but add _edited
                # need to use file extension from edited file as Photos saves a jpeg once edited
                if edited:
                    # verify we have a valid path_edited and use that to get filename
                    if not self.path_edited:
                        raise FileNotFoundError(
                            f"edited=True but path_edited is none; hasadjustments: {self.hasadjustments}"
                        )
                    edited_name = Path(self.path_edited).name
                    edited_suffix = Path(edited_name).suffix
                    filename = Path(self.filename).stem + "_edited" + edited_suffix
                else:
                    filename = self.filename

        # get path to source file and verify it's not None and is valid file
        # TODO: how to handle ismissing or not hasadjustments and edited=True cases?
        if edited:
            if not self.hasadjustments:
                logging.warning(
                    "Attempting to export edited photo but hasadjustments=False"
                )

            if self.path_edited is not None:
                src = self.path_edited
            else:
                raise FileNotFoundError(
                    f"edited=True but path_edited is none; hasadjustments: {self.hasadjustments}"
                )
        else:
            if self.ismissing:
                logging.warning(
                    f"Attempting to export photo with ismissing=True: path = {self.path}"
                )

            if self.path is None:
                logging.warning(
                    f"Attempting to export photo but path is None: ismissing = {self.ismissing}"
                )
                raise FileNotFoundError("Cannot export photo if path is None")
            else:
                src = self.path

        if not os.path.isfile(src):
            raise FileNotFoundError(f"{src} does not appear to exist")

        dest = pathlib.Path(dest)
        filename = pathlib.Path(filename)
        dest = dest / filename

        # check to see if file exists and if so, add (1), (2), etc until we find one that works
        if increment and not overwrite:
            count = 1
            dest_new = dest
            while dest_new.exists():
                dest_new = dest.parent / f"{dest.stem} ({count}){dest.suffix}"
                count += 1
            dest = dest_new

        logging.debug(
            f"exporting {src} to {dest}, overwrite={overwrite}, incremetn={increment}, dest exists: {dest.exists()}"
        )

        # if overwrite==False and #increment==False, export should fail if file exists
        if dest.exists() and not overwrite and not increment:
            raise FileExistsError(
                f"destination exists ({dest}); overwrite={overwrite}, increment={increment}"
            )

        # if error on copy, subprocess will raise CalledProcessError
        try:
            subprocess.run(
                ["/usr/bin/ditto", src, dest], check=True, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            logging.critical(
                f"ditto returned error: {e.returncode} {e.stderr.decode(sys.getfilesystemencoding()).rstrip()}"
            )
            raise e

        if sidecar:
            logging.debug("writing exiftool_json_sidecar")
            sidecar_filename = f"{dest}.json"
            json_sidecar_str = self._exiftool_json_sidecar()
            try:
                self._write_sidecar_car(sidecar_filename, json_sidecar_str)
            except Exception as e:
                logging.critical(f"Error writing json sidecar to {sidecar_filename}")
                raise e

        return str(dest)

    def _exiftool_json_sidecar(self):
        """ return json string of EXIF details in exiftool sidecar format """
        exif = {}
        exif["FileName"] = self.filename

        if self.description:
            exif["ImageDescription"] = self.description
            exif["Description"] = self.description

        if self.title:
            exif["Title"] = self.title

        if self.keywords:
            exif["TagsList"] = exif["Keywords"] = self.keywords

        if self.persons:
            exif["PersonInImage"] = self.persons

        # if self.favorite():
        #     exif["Rating"] = 5

        (lat, lon) = self.location
        if lat is not None and lon is not None:
            lat_str, lon_str = dd_to_dms_str(lat, lon)
            exif["GPSLatitude"] = lat_str
            exif["GPSLongitude"] = lon_str
            exif["GPSPosition"] = f"{lat_str}, {lon_str}"
            lat_ref = "North" if lat >= 0 else "South"
            lon_ref = "East" if lon >= 0 else "West"
            exif["GPSLatitudeRef"] = lat_ref
            exif["GPSLongitudeRef"] = lon_ref

        # process date/time and timezone offset
        date = self.date
        # exiftool expects format to "2015:01:18 12:00:00"
        datetimeoriginal = date.strftime("%Y:%m:%d %H:%M:%S")
        offsettime = date.strftime("%z")
        # find timezone offset in format "-04:00"
        offset = re.findall(r"([+-]?)([\d]{2})([\d]{2})", offsettime)
        offset = offset[0]  # findall returns list of tuples
        offsettime = f"{offset[0]}{offset[1]}:{offset[2]}"
        exif["DateTimeOriginal"] = datetimeoriginal
        exif["OffsetTimeOriginal"] = offsettime

        json_str = json.dumps([exif])
        return json_str

    def _write_sidecar_car(self, filename, json_str):
        if not filename and not json_str:
            raise (
                ValueError(
                    f"filename {filename} and json_str {json_str} must not be None"
                )
            )

        # TODO: catch exception?
        f = open(filename, "w")
        f.write(json_str)
        f.close()

    @property
    def _longitude(self):
        """ Returns longitude, in degrees """
        return self._info["longitude"]

    @property
    def _latitude(self):
        """ Returns latitude, in degrees """
        return self._info["latitude"]

    def __repr__(self):
        # TODO: update to use __class__ and __name__
        return f"osxphotos.PhotoInfo(db={self._db}, uuid='{self._uuid}', info={self._info})"

    def __str__(self):
        info = {
            "uuid": self.uuid,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "date": str(self.date),
            "description": self.description,
            "name": self.name,
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
        }
        return yaml.dump(info, sort_keys=False)

    def json(self):
        """ return JSON representation """
        # TODO: Add additional details here
        pic = {
            "uuid": self.uuid,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "date": str(self.date),
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
