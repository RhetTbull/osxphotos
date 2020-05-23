"""
PhotoInfo class
Represents a single photo in the Photos library and provides access to the photo's attributes
PhotosDB.photos() returns a list of PhotoInfo objects
"""

import dataclasses
import glob
import json
import logging
import os
import os.path
import pathlib
import re
import subprocess
import sys
from datetime import timedelta, timezone
from pprint import pformat

import yaml

from .._constants import (
    _MOVIE_TYPE,
    _PHOTO_TYPE,
    _PHOTOS_4_VERSION,
    _PHOTOS_5_SHARED_PHOTO_PATH,
    _UNKNOWN_PERSON,
)
from ..albuminfo import AlbumInfo
from ..datetime_formatter import DateTimeFormatter
from ..placeinfo import PlaceInfo4, PlaceInfo5
from ..utils import _debug, _get_resource_loc, findfiles, get_preferred_uti_extension
from .template import (
    MULTI_VALUE_SUBSTITUTIONS,
    TEMPLATE_SUBSTITUTIONS,
    TEMPLATE_SUBSTITUTIONS_MULTI_VALUED,
)


class PhotoInfo:
    """
    Info about a specific photo, contains all the details about the photo
    including keywords, persons, albums, uuid, path, etc.
    """

    # import additional methods
    from ._photoinfo_searchinfo import (
        search_info,
        labels,
        labels_normalized,
        SearchInfo,
    )
    from ._photoinfo_exifinfo import exif_info, ExifInfo
    from ._photoinfo_exiftool import exiftool
    from ._photoinfo_export import (
        export,
        export2,
        _export_photo,
        _exiftool_json_sidecar,
        _write_exif_data,
        _write_sidecar,
        _xmp_sidecar,
        ExportResults,
    )

    def __init__(self, db=None, uuid=None, info=None):
        self._uuid = uuid
        self._info = info
        self._db = db

    @property
    def filename(self):
        """ filename of the picture """
        if self.has_raw and self.raw_original:
            # return name of the RAW file
            # TODO: not yet implemented
            return self._info["filename"]
        else:
            return self._info["filename"]

    @property
    def original_filename(self):
        """ original filename of the picture 
            Photos 5 mangles filenames upon import """
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
    def date_modified(self):
        """ image modification date as timezone aware datetime object
            or None if no modification date set """
        imagedate = self._info["lastmodifieddate"]
        if imagedate:
            seconds = self._info["imageTimeZoneOffsetSeconds"] or 0
            delta = timedelta(seconds=seconds)
            tz = timezone(delta)
            imagedate_utc = imagedate.astimezone(tz=tz)
            return imagedate_utc
        else:
            return None

    @property
    def tzoffset(self):
        """ timezone offset from UTC in seconds """
        return self._info["imageTimeZoneOffsetSeconds"]

    @property
    def path(self):
        """ absolute path on disk of the original picture """

        photopath = None
        if self._info["isMissing"] == 1:
            return photopath  # path would be meaningless until downloaded

        if self._db._db_version <= _PHOTOS_4_VERSION:
            vol = self._info["volume"]
            if vol is not None:
                photopath = os.path.join("/Volumes", vol, self._info["imagePath"])
            else:
                photopath = os.path.join(
                    self._db._masters_path, self._info["imagePath"]
                )
            return photopath
            # TODO: Is there a way to use applescript or PhotoKit to force the download in this

        if self._info["shared"]:
            # shared photo
            photopath = os.path.join(
                self._db._library_path,
                _PHOTOS_5_SHARED_PHOTO_PATH,
                self._info["directory"],
                self._info["filename"],
            )
            return photopath

        if self._info["directory"].startswith("/"):
            photopath = os.path.join(self._info["directory"], self._info["filename"])
        else:
            photopath = os.path.join(
                self._db._masters_path, self._info["directory"], self._info["filename"]
            )
        return photopath

    @property
    def path_edited(self):
        """ absolute path on disk of the edited picture """
        """ None if photo has not been edited """

        # TODO: break this code into a _path_edited_4 and _path_edited_5
        # version to simplify the big if/then; same for path_live_photo

        photopath = None

        if self._db._db_version <= _PHOTOS_4_VERSION:
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
                        library,
                        "resources",
                        "media",
                        "version",
                        folder_id,
                        "00",
                        filename,
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
                filename = None
                if self._info["type"] == _PHOTO_TYPE:
                    # it's a photo
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

            # logging.debug(photopath)

        return photopath

    @property
    def path_raw(self):
        """ absolute path of associated RAW image or None if there is not one """

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
        else:
            filestem = pathlib.Path(self._info["filename"]).stem
            raw_ext = get_preferred_uti_extension(self._info["UTI_raw"])

            if self._info["directory"].startswith("/"):
                filepath = self._info["directory"]
            else:
                filepath = os.path.join(self._db._masters_path, self._info["directory"])

            glob_str = f"{filestem}*.{raw_ext}"
            raw_file = findfiles(glob_str, filepath)
            if len(raw_file) != 1:
                # Note: In Photos Version 5.0 (141.19.150), images not copied to Photos Library
                # that are missing do not always trigger is_missing = True as happens
                # in earlier version so it's possible for this check to fail, if so, return None
                logging.debug(f"Error getting path to RAW file: {filepath}/{glob_str}")
                photopath = None
            else:
                photopath = os.path.join(filepath, raw_file[0])
                if not os.path.isfile(photopath):
                    logging.debug(
                        f"MISSING PATH: RAW photo for UUID {self._uuid} should be at {photopath} but does not appear to exist"
                    )
                    photopath = None

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
            if not self._db._dbalbum_details[album]["intrash"]:
                albums.append(self._db._dbalbum_details[album]["title"])
        return albums

    @property
    def album_info(self):
        """ list of AlbumInfo objects representing albums the photos is contained in """
        albums = []
        for album in self._info["albums"]:
            if not self._db._dbalbum_details[album]["intrash"]:
                albums.append(AlbumInfo(db=self._db, uuid=album))

        return albums

    @property
    def keywords(self):
        """ list of keywords for picture """
        return self._info["keywords"]

    @property
    def title(self):
        """ name / title of picture """
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

    @property
    def shared(self):
        """ returns True if photos is in a shared iCloud album otherwise false
            Only valid on Photos 5; returns None on older versions """
        if self._db._db_version > _PHOTOS_4_VERSION:
            return self._info["shared"]
        else:
            return None

    @property
    def uti(self):
        """ Returns Uniform Type Identifier (UTI) for the image
            for example: public.jpeg or com.apple.quicktime-movie
        """
        return self._info["UTI"]

    @property
    def uti_raw(self):
        """ Returns Uniform Type Identifier (UTI) for the RAW image if there is one
            for example: com.canon.cr2-raw-image
            Returns None if no associated RAW image
        """
        return self._info["UTI_raw"]

    @property
    def ismovie(self):
        """ Returns True if file is a movie, otherwise False
        """
        return True if self._info["type"] == _MOVIE_TYPE else False

    @property
    def isphoto(self):
        """ Returns True if file is an image, otherwise False
        """
        return True if self._info["type"] == _PHOTO_TYPE else False

    @property
    def incloud(self):
        """ Returns True if photo is cloud asset and is synched to cloud
                    False if photo is cloud asset and not yet synched to cloud
                    None if photo is not cloud asset
        """
        return self._info["incloud"]

    @property
    def iscloudasset(self):
        """ Returns True if photo is a cloud asset (in an iCloud library),
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
    def burst(self):
        """ Returns True if photo is part of a Burst photo set, otherwise False """
        return self._info["burst"]

    @property
    def burst_photos(self):
        """ If photo is a burst photo, returns list of PhotoInfo objects 
            that are part of the same burst photo set; otherwise returns empty list.
            self is not included in the returned list """
        if self._info["burst"]:
            burst_uuid = self._info["burstUUID"]
            burst_photos = [
                PhotoInfo(db=self._db, uuid=u, info=self._db._dbphotos[u])
                for u in self._db._dbphotos_burst[burst_uuid]
                if u != self._uuid
            ]
            return burst_photos
        else:
            return []

    @property
    def live_photo(self):
        """ Returns True if photo is a live photo, otherwise False """
        return self._info["live_photo"]

    @property
    def path_live_photo(self):
        """ Returns path to the associated video file for a live photo
            If photo is not a live photo, returns None
            If photo is missing, returns None """

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
    def panorama(self):
        """ Returns True if photo is a panorama, otherwise False """
        return self._info["panorama"]

    @property
    def slow_mo(self):
        """ Returns True if photo is a slow motion video, otherwise False """
        return self._info["slow_mo"]

    @property
    def time_lapse(self):
        """ Returns True if photo is a time lapse video, otherwise False """
        return self._info["time_lapse"]

    @property
    def hdr(self):
        """ Returns True if photo is an HDR photo, otherwise False """
        return self._info["hdr"]

    @property
    def screenshot(self):
        """ Returns True if photo is an HDR photo, otherwise False """
        return self._info["screenshot"]

    @property
    def portrait(self):
        """ Returns True if photo is a portrait, otherwise False """
        return self._info["portrait"]

    @property
    def selfie(self):
        """ Returns True if photo is a selfie (front facing camera), otherwise False """
        return self._info["selfie"]

    @property
    def place(self):
        """ Returns PlaceInfo object containing reverse geolocation info """

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
        """ returns True if photo has an associated RAW image, otherwise False """
        return self._info["has_raw"]

    @property
    def raw_original(self):
        """ returns True if associated RAW image and the RAW image is selected in Photos
            via "Use RAW as Original "
            otherwise returns False """
        return self._info["raw_is_original"]

    def render_template(self, template, none_str="_", path_sep=None):
        """ render a filename or directory template 
            template: str template 
            none_str: str to use default for None values, default is '_' 
            path_sep: optional character to use as path separator, default is os.path.sep """

        if path_sep is None:
            path_sep = os.path.sep
        elif path_sep is not None and len(path_sep) != 1:
            raise ValueError(f"path_sep must be single character: {path_sep}")

        # the rendering happens in two phases:
        # phase 1: handle all the single-value template substitutions
        #          results in a single string with all the template fields replaced
        # phase 2: loop through all the multi-value template substitutions
        #          could result in multiple strings
        #          e.g. if template is "{album}/{person}" and there are 2 albums and 3 persons in the photo
        #          there would be 6 possible renderings (2 albums x 3 persons)

        # regex to find {template_field,optional_default} in strings
        # for explanation of regex see https://regex101.com/r/4JJg42/1
        # pylint: disable=anomalous-backslash-in-string
        regex = r"(?<!\{)\{([^\\,}]+)(,{0,1}(([\w\-. ]+))?)(?=\}(?!\}))\}"
        if type(template) is not str:
            raise TypeError(f"template must be type str, not {type(template)}")

        def make_subst_function(self, none_str, get_func=self.get_template_value):
            """ returns: substitution function for use in re.sub 
                none_str: value to use if substitution lookup is None and no default provided
                get_func: function that gets the substitution value for a given template field
                        default is get_template_value which handles the single-value fields """

            # closure to capture photo, none_str in subst
            def subst(matchobj):
                groups = len(matchobj.groups())
                if groups == 4:
                    try:
                        val = get_func(matchobj.group(1))
                    except KeyError:
                        return matchobj.group(0)

                    if val is None:
                        return (
                            matchobj.group(3)
                            if matchobj.group(3) is not None
                            else none_str
                        )
                    else:
                        return val
                else:
                    raise ValueError(
                        f"Unexpected number of groups: expected 4, got {groups}"
                    )

            return subst

        subst_func = make_subst_function(self, none_str)

        # do the replacements
        rendered = re.sub(regex, subst_func, template)

        # do multi-valued placements
        # start with the single string from phase 1 above then loop through all
        # multi-valued fields and all values for each of those fields
        # rendered_strings will be updated as each field is processed
        # for example: if two albums, two keywords, and one person and template is:
        # "{created.year}/{album}/{keyword}/{person}"
        # rendered strings would do the following:
        # start (created.year filled in phase 1)
        #   ['2011/{album}/{keyword}/{person}']
        # after processing albums:
        #   ['2011/Album1/{keyword}/{person}',
        #    '2011/Album2/{keyword}/{person}',]
        # after processing keywords:
        #   ['2011/Album1/keyword1/{person}',
        #    '2011/Album1/keyword2/{person}',
        #    '2011/Album2/keyword1/{person}',
        #    '2011/Album2/keyword2/{person}',]
        # after processing person:
        #   ['2011/Album1/keyword1/person1',
        #    '2011/Album1/keyword2/person1',
        #    '2011/Album2/keyword1/person1',
        #    '2011/Album2/keyword2/person1',]

        rendered_strings = set([rendered])
        for field in MULTI_VALUE_SUBSTITUTIONS:
            if field == "album":
                values = self.albums
            elif field == "keyword":
                values = self.keywords
            elif field == "person":
                values = self.persons
                # remove any _UNKNOWN_PERSON values
                values = [val for val in values if val != _UNKNOWN_PERSON]
            elif field == "label":
                values = self.labels
            elif field == "label_normalized":
                values = self.labels_normalized
            elif field == "folder_album":
                values = []
                # photos must be in an album to be in a folder
                for album in self.album_info:
                    if album.folder_names:
                        # album in folder
                        folder = path_sep.join(album.folder_names)
                        folder += path_sep + album.title
                        values.append(folder)
                    else:
                        # album not in folder
                        values.append(album.title)
            else:
                raise ValueError(f"Unhandleded template value: {field}")

            # If no values, insert None so code below will substite none_str for None
            values = values or [None]

            # Build a regex that matches only the field being processed
            re_str = r"(?<!\\)\{(" + field + r")(,(([\w\-. ]{0,})))?\}"
            regex_multi = re.compile(re_str)

            # holds each of the new rendered_strings, set() to avoid duplicates
            new_strings = set()

            for str_template in rendered_strings:
                for val in values:

                    def get_template_value_multi(lookup_value):
                        """ Closure passed to make_subst_function get_func 
                            Capture val and field in the closure 
                            Allows make_subst_function to be re-used w/o modification """
                        if lookup_value == field:
                            return val
                        else:
                            raise KeyError(f"Unexpected value: {lookup_value}")

                    subst = make_subst_function(
                        self, none_str, get_func=get_template_value_multi
                    )
                    new_string = regex_multi.sub(subst, str_template)
                    new_strings.add(new_string)

            # update rendered_strings for the next field to process
            rendered_strings = new_strings

        # find any {fields} that weren't replaced
        unmatched = []
        for rendered_str in rendered_strings:
            unmatched.extend(
                [
                    no_match[0]
                    for no_match in re.findall(regex, rendered_str)
                    if no_match[0] not in unmatched
                ]
            )

        # fix any escaped curly braces
        rendered_strings = [
            rendered_str.replace("{{", "{").replace("}}", "}")
            for rendered_str in rendered_strings
        ]

        return rendered_strings, unmatched

    def get_template_value(self, lookup):
        """ lookup template value (single-value template substitutions) for use in make_subst_function
            lookup: value to find a match for
            returns: either the matching template value (which may be None)
            raises: KeyError if no rule exists for lookup """

        # must be a valid keyword
        if lookup == "name":
            return pathlib.Path(self.filename).stem

        if lookup == "original_name":
            return pathlib.Path(self.original_filename).stem

        if lookup == "title":
            return self.title

        if lookup == "descr":
            return self.description

        if lookup == "created.date":
            return DateTimeFormatter(self.date).date

        if lookup == "created.year":
            return DateTimeFormatter(self.date).year

        if lookup == "created.yy":
            return DateTimeFormatter(self.date).yy

        if lookup == "created.mm":
            return DateTimeFormatter(self.date).mm

        if lookup == "created.month":
            return DateTimeFormatter(self.date).month

        if lookup == "created.mon":
            return DateTimeFormatter(self.date).mon

        if lookup == "created.doy":
            return DateTimeFormatter(self.date).doy

        if lookup == "modified.date":
            return (
                DateTimeFormatter(self.date_modified).date
                if self.date_modified
                else None
            )

        if lookup == "modified.year":
            return (
                DateTimeFormatter(self.date_modified).year
                if self.date_modified
                else None
            )

        if lookup == "modified.yy":
            return (
                DateTimeFormatter(self.date_modified).yy if self.date_modified else None
            )

        if lookup == "modified.mm":
            return (
                DateTimeFormatter(self.date_modified).mm if self.date_modified else None
            )

        if lookup == "modified.month":
            return (
                DateTimeFormatter(self.date_modified).month
                if self.date_modified
                else None
            )

        if lookup == "modified.mon":
            return (
                DateTimeFormatter(self.date_modified).mon
                if self.date_modified
                else None
            )

        if lookup == "modified.doy":
            return (
                DateTimeFormatter(self.date_modified).doy
                if self.date_modified
                else None
            )

        if lookup == "place.name":
            return self.place.name if self.place else None

        if lookup == "place.country_code":
            return self.place.country_code if self.place else None

        if lookup == "place.name.country":
            return (
                self.place.names.country[0]
                if self.place and self.place.names.country
                else None
            )

        if lookup == "place.name.state_province":
            return (
                self.place.names.state_province[0]
                if self.place and self.place.names.state_province
                else None
            )

        if lookup == "place.name.city":
            return (
                self.place.names.city[0]
                if self.place and self.place.names.city
                else None
            )

        if lookup == "place.name.area_of_interest":
            return (
                self.place.names.area_of_interest[0]
                if self.place and self.place.names.area_of_interest
                else None
            )

        if lookup == "place.address":
            return (
                self.place.address_str
                if self.place and self.place.address_str
                else None
            )

        if lookup == "place.address.street":
            return (
                self.place.address.street
                if self.place and self.place.address.street
                else None
            )

        if lookup == "place.address.city":
            return (
                self.place.address.city
                if self.place and self.place.address.city
                else None
            )

        if lookup == "place.address.state_province":
            return (
                self.place.address.state_province
                if self.place and self.place.address.state_province
                else None
            )

        if lookup == "place.address.postal_code":
            return (
                self.place.address.postal_code
                if self.place and self.place.address.postal_code
                else None
            )

        if lookup == "place.address.country":
            return (
                self.place.address.country
                if self.place and self.place.address.country
                else None
            )

        if lookup == "place.address.country_code":
            return (
                self.place.address.iso_country_code
                if self.place and self.place.address.iso_country_code
                else None
            )

        # if here, didn't get a match
        raise KeyError(f"No rule for processing {lookup}")

    @property
    def _longitude(self):
        """ Returns longitude, in degrees """
        return self._info["longitude"]

    @property
    def _latitude(self):
        """ Returns latitude, in degrees """
        return self._info["latitude"]

    def __repr__(self):
        return f"osxphotos.{self.__class__.__name__}(db={self._db}, uuid='{self._uuid}', info={self._info})"

    def __str__(self):
        """ string representation of PhotoInfo object """

        date_iso = self.date.isoformat()
        date_modified_iso = (
            self.date_modified.isoformat() if self.date_modified else None
        )

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
        }
        return yaml.dump(info, sort_keys=False)

    def json(self):
        """ return JSON representation """

        date_modified_iso = (
            self.date_modified.isoformat() if self.date_modified else None
        )
        folders = {album.title: album.folder_names for album in self.album_info}
        exif = dataclasses.asdict(self.exif_info) if self.exif_info else {}
        place = self.place.as_dict() if self.place else {}

        pic = {
            "uuid": self.uuid,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "date": self.date.isoformat(),
            "description": self.description,
            "title": self.title,
            "keywords": self.keywords,
            "labels": self.labels,
            "keywords": self.keywords,
            "albums": self.albums,
            "folders": folders,
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
            "place": place,
            "exif": exif,
        }
        return json.dumps(pic)

    # compare two PhotoInfo objects for equality
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__

        return False

    def __ne__(self, other):
        return not self.__eq__(other)
