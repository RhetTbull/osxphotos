"""Write metadata to files using exiftool"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import pathlib
import re
from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, Callable, Optional

from ._constants import (
    _MAX_IPTC_KEYWORD_LEN,
    _OSXPHOTOS_NONE_SENTINEL,
    _UNKNOWN_PERSON,
    DEFAULT_PREVIEW_SUFFIX,
)
from .datetime_utils import datetime_tz_to_utc
from .exiftool import ExifTool, ExifToolCaching, get_exiftool_path
from .phototemplate import RenderOptions
from .utils import noop

if TYPE_CHECKING:
    from .photoexporter import ExportOptions
    from .photoinfo import PhotoInfo

logger = logging.getLogger("osxphotos")


@dataclass
class ExifOptions:
    """Options class for writing metadata to files using exiftool

    Attributes:
        convert_to_jpeg (bool): if True, converts non-jpeg images to jpeg
        description_template (str): Optional template string that will be rendered for use as photo description
        download_missing: (bool, default=False): if True will attempt to export photo via applescript interaction with Photos if missing (see also use_photokit, use_photos_export)
        dry_run: (bool, default=False): set to True to run in "dry run" mode
        edited: (bool, default=False): if True will export the edited version of the photo otherwise exports the original version
        exiftool_flags (list of str): Optional list of flags to pass to exiftool when using exiftool option, e.g ["-m", "-F"]
        exiftool: (bool, default = False): if True, will use exiftool to write metadata to export file
        export_as_hardlink: (bool, default=False): if True, will hardlink files instead of copying them
        export_db: (ExportDB): instance of a class that conforms to ExportDB with methods for getting/setting data related to exported files to compare update state
        face_regions: (bool, default=True): if True, will export face regions
        fileutil: (FileUtilABC): class that conforms to FileUtilABC with various file utilities
        force_update: (bool, default=False): if True, will export photo if any metadata has changed but export otherwise would not be triggered (e.g. metadata changed but not using exiftool)
        ignore_date_modified (bool): for use with sidecar and exiftool; if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set
        ignore_signature (bool, default=False): ignore file signature when used with update (look only at filename)
        increment (bool, default=True): if True, will increment file name until a non-existant name is found if overwrite=False and increment=False, export will fail if destination file already exists
        jpeg_ext (str): if set, will use this value for extension on jpegs converted to jpeg with convert_to_jpeg; if not set, uses jpeg; do not include the leading "."
        jpeg_quality (float in range 0.0 <= jpeg_quality <= 1.0): a value of 1.0 specifies use best quality, a value of 0.0 specifies use maximum compression.
        keyword_template (list of str): list of template strings that will be rendered as used as keywords
        live_photo (bool, default=False): if True, will also export the associated .mov for live photos
        location (bool): if True, include location in exported metadata
        merge_exif_keywords (bool): if True, merged keywords found in file's exif data (requires exiftool)
        merge_exif_persons (bool): if True, merged persons found in file's exif data (requires exiftool)
        overwrite (bool, default=False): if True will overwrite files if they already exist
        persons (bool): if True, include persons in exported metadata
        preview_suffix (str): Optional string to append to end of filename for preview images
        preview (bool): if True, also exports preview image
        raw_photo (bool, default=False): if True, will also export the associated RAW photo
        render_options (RenderOptions): Optional osxphotos.phototemplate.RenderOptions instance to specify options for rendering templates
        replace_keywords (bool): if True, keyword_template replaces any keywords, otherwise it's additive
        rich (bool): if True, will use rich markup with verbose output
        export_aae (bool): if True, also exports adjustments as .AAE file
        sidecar_drop_ext (bool, default=False): if True, drops the photo's extension from sidecar filename (e.g. 'IMG_1234.json' instead of 'IMG_1234.JPG.json')
        sidecar: bit field (int): set to one or more of `SIDECAR_XMP`, `SIDECAR_JSON`, `SIDECAR_EXIFTOOL`
          - SIDECAR_JSON: if set will write a json sidecar with data in format readable by exiftool sidecar filename will be dest/filename.json;
          includes exiftool tag group names (e.g. `exiftool -G -j`)
          - SIDECAR_EXIFTOOL: if set will write a json sidecar with data in format readable by exiftool sidecar filename will be dest/filename.json;
          does not include exiftool tag group names (e.g. `exiftool -j`)
          - SIDECAR_XMP: if set will write an XMP sidecar with IPTC data sidecar filename will be dest/filename.xmp
        strip (bool): if True, strip whitespace from rendered templates
        timeout (int, default=120): timeout in seconds used with use_photos_export
        touch_file (bool, default=False): if True, sets file's modification time upon photo date
        update (bool, default=False): if True export will run in update mode, that is, it will not export the photo if the current version already exists in the destination
        update_errors (bool, default=False): if True photos that previously produced a warning or error will be re-exported; otherwise they will note be
        use_albums_as_keywords (bool, default = False): if True, will include album names in keywords when exporting metadata with exiftool or sidecar
        use_persons_as_keywords (bool, default = False): if True, will include person names in keywords when exporting metadata with exiftool or sidecar
        use_photos_export (bool, default=False): if True will attempt to export photo via applescript interaction with Photos even if not missing (see also use_photokit, download_missing)
        use_photokit (bool, default=False): if True, will use photokit to export photos when use_photos_export is True
        verbose (callable): optional callable function to use for printing verbose text during processing; if None (default), does not print output.
        tmpdir: (str, default=None): Optional directory to use for temporary files, if None (default) uses system tmp directory
        favorite_rating (bool): if True, set XMP:Rating=5 for favorite images and XMP:Rating=0 for non-favorites

    """

    convert_to_jpeg: bool = False
    description_template: Optional[str] = None
    download_missing: bool = False
    dry_run: bool = False
    edited: bool = False
    exiftool_flags: Optional[t.List] = None
    exiftool: bool = False
    export_as_hardlink: bool = False
    export_db: Optional[ExportDB] = None
    face_regions: bool = True
    fileutil: Optional[FileUtil] = None
    force_update: bool = False
    ignore_date_modified: bool = False
    ignore_signature: bool = False
    increment: bool = True
    jpeg_ext: Optional[str] = None
    jpeg_quality: float = 1.0
    keyword_template: Optional[t.List[str]] = None
    live_photo: bool = False
    location: bool = True
    merge_exif_keywords: bool = False
    merge_exif_persons: bool = False
    overwrite: bool = False
    persons: bool = True
    preview_suffix: str = DEFAULT_PREVIEW_SUFFIX
    preview: bool = False
    raw_photo: bool = False
    render_options: Optional[RenderOptions] = None
    replace_keywords: bool = False
    rich: bool = False
    export_aae: bool = False
    sidecar_drop_ext: bool = False
    sidecar: int = 0
    strip: bool = False
    timeout: int = 120
    touch_file: bool = False
    update: bool = False
    update_errors: bool = False
    use_albums_as_keywords: bool = False
    use_persons_as_keywords: bool = False
    use_photokit: bool = False
    use_photos_export: bool = False
    verbose: Optional[Callable] = None
    tmpdir: Optional[str] = None
    favorite_rating: bool = False

    def asdict(self):
        return dataclasses.asdict(self)

    @property
    def bit_flags(self):
        """Return bit flags representing options that affect export"""
        # currently only exiftool makes a difference
        return self.exiftool << 1


class ExifWriter:
    """Write EXIF & other metadata to files using exiftool for a Photo asset"""

    def __init__(self, photo: PhotoInfo):
        """Create instance of ExifWriter

        Args:
            photo: PhotoInfo instance
        """
        self.photo = photo
        self._render_options = RenderOptions()

    def write_exif_data(self, filepath: str | pathlib.Path, options: ExportOptions):
        """write exif data to image file at filepath

        Args:
            filepath: full path to the image file

        Returns:
            (warning, error) of warning and error strings if exiftool produces warnings or errors
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Could not find file {filepath}")
        exif_info = self.exiftool_dict(options=options)

        with ExifTool(
            filepath,
            flags=options.exiftool_flags,
            exiftool=self.photo._exiftool_path,
        ) as exiftool:
            for exiftag, val in exif_info.items():
                if type(val) == list:
                    for v in val:
                        exiftool.setvalue(exiftag, v)
                else:
                    exiftool.setvalue(exiftag, val)
        return exiftool.warning, exiftool.error

    def exiftool_dict(
        self,
        options: Optional[ExportOptions] = None,
        filename: Optional[str] = None,
    ):
        """Return dict of EXIF details for building exiftool JSON sidecar or sending commands to ExifTool.
            Does not include all the EXIF fields as those are likely already in the image.

        Args:
            options (ExportOptions): options for export
            filename (str): name of source image file (without path); if not None, exiftool JSON signature will be included; if None, signature will not be included

        Returns: dict with exiftool tags / values

        Exports the following:
            EXIF:ImageDescription (may include template)
            XMP:Description (may include template)
            XMP:Title
            IPTC:ObjectName
            XMP:TagsList (may include album name, person name, or template)
            IPTC:Keywords (may include album name, person name, or template)
            IPTC:Caption-Abstract
            XMP:Subject (set to keywords + persons)
            XMP:PersonInImage
            EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef
            EXIF:GPSLatitude, EXIF:GPSLongitude
            EXIF:GPSPosition
            EXIF:DateTimeOriginal
            EXIF:OffsetTimeOriginal
            EXIF:ModifyDate
            IPTC:DateCreated
            IPTC:TimeCreated
            QuickTime:CreationDate
            QuickTime:ContentCreateDate
            QuickTime:CreateDate (UTC)
            QuickTime:ModifyDate (UTC)
            QuickTime:GPSCoordinates
            UserData:GPSCoordinates
            XMP:Rating

        Reference:
            https://iptc.org/std/photometadata/specification/IPTC-PhotoMetadata-201610_1.pdf
        """

        options = options or ExifOptions()
        self._render_options = options.render_options or self._render_options

        exif = (
            {
                "SourceFile": filename,
                "ExifTool:ExifToolVersion": "12.00",
                "File:FileName": filename,
            }
            if filename is not None
            else {}
        )

        if options.description_template is not None:
            render_options = dataclasses.replace(
                self._render_options, expand_inplace=True, inplace_sep=", "
            )
            rendered = self.photo.render_template(
                options.description_template, render_options
            )[0]
            description = " ".join(rendered) if rendered else ""
            if options.strip:
                description = description.strip()
            exif["EXIF:ImageDescription"] = description
            exif["XMP:Description"] = description
            exif["IPTC:Caption-Abstract"] = description
        elif self.photo.description:
            exif["EXIF:ImageDescription"] = self.photo.description
            exif["XMP:Description"] = self.photo.description
            exif["IPTC:Caption-Abstract"] = self.photo.description

        if self.photo.title:
            exif["XMP:Title"] = self.photo.title
            exif["IPTC:ObjectName"] = self.photo.title

        keyword_list = []
        if options.merge_exif_keywords:
            keyword_list.extend(self._get_exif_keywords())

        if self.photo.keywords and not options.replace_keywords:
            keyword_list.extend(self.photo.keywords)

        person_list = []
        if options.persons:
            if options.merge_exif_persons:
                person_list.extend(self._get_exif_persons())

            if self.photo.persons:
                # filter out _UNKNOWN_PERSON
                person_list.extend(
                    [p for p in self.photo.persons if p != _UNKNOWN_PERSON]
                )

            if options.use_persons_as_keywords and person_list:
                keyword_list.extend(person_list)

        if options.use_albums_as_keywords and self.photo.albums:
            keyword_list.extend(self.photo.albums)

        if options.keyword_template:
            rendered_keywords = []
            render_options = dataclasses.replace(
                self._render_options, none_str=_OSXPHOTOS_NONE_SENTINEL, path_sep="/"
            )
            for template_str in options.keyword_template:
                rendered, unmatched = self.photo.render_template(
                    template_str, render_options
                )
                if unmatched:
                    logger.warning(
                        f"Unmatched template substitution for template: {template_str} {unmatched}"
                    )
                rendered_keywords.extend(rendered)

            if options.strip:
                rendered_keywords = [keyword.strip() for keyword in rendered_keywords]

            # filter out any template values that didn't match by looking for sentinel
            rendered_keywords = [
                keyword
                for keyword in sorted(rendered_keywords)
                if _OSXPHOTOS_NONE_SENTINEL not in keyword
            ]

            # check to see if any keywords too long
            long_keywords = [
                long_str
                for long_str in rendered_keywords
                if len(long_str) > _MAX_IPTC_KEYWORD_LEN
            ]
            if long_keywords:
                logger.warning(
                    f"Warning: some keywords exceed max IPTC Keyword length of {_MAX_IPTC_KEYWORD_LEN} (exiftool will truncate these): {long_keywords}"
                )

            keyword_list.extend(rendered_keywords)

        if keyword_list:
            # remove duplicates
            keyword_list = sorted(list(set(str(keyword) for keyword in keyword_list)))
            exif["IPTC:Keywords"] = keyword_list.copy()
            exif["XMP:Subject"] = keyword_list.copy()
            exif["XMP:TagsList"] = keyword_list.copy()

        if options.persons and person_list:
            person_list = sorted(list(set(person_list)))
            exif["XMP:PersonInImage"] = person_list.copy()

        if options.face_regions and self.photo.face_info:
            exif.update(self._get_mwg_face_regions_exiftool())

        if options.favorite_rating:
            exif["XMP:Rating"] = 5 if self.photo.favorite else 0

        if options.location:
            (lat, lon) = self.photo.location
            if lat is not None and lon is not None:
                if self.photo.isphoto:
                    exif["EXIF:GPSLatitude"] = lat
                    exif["EXIF:GPSLongitude"] = lon
                    lat_ref = "N" if lat >= 0 else "S"
                    lon_ref = "E" if lon >= 0 else "W"
                    exif["EXIF:GPSLatitudeRef"] = lat_ref
                    exif["EXIF:GPSLongitudeRef"] = lon_ref
                elif self.photo.ismovie:
                    exif["Keys:GPSCoordinates"] = f"{lat} {lon}"
                    exif["UserData:GPSCoordinates"] = f"{lat} {lon}"
        # process date/time and timezone offset
        # Photos exports the following fields and sets modify date to creation date
        # [EXIF]    Modify Date             : 2020:10:30 00:00:00
        # [EXIF]    Date/Time Original      : 2020:10:30 00:00:00
        # [EXIF]    Create Date             : 2020:10:30 00:00:00
        # [IPTC]    Digital Creation Date   : 2020:10:30
        # [IPTC]    Date Created            : 2020:10:30
        #
        # for videos:
        # [QuickTime]     CreateDate                      : 2020:12:11 06:10:10
        # [QuickTime]     ModifyDate                      : 2020:12:11 06:10:10
        # [Keys]          CreationDate                    : 2020:12:10 22:10:10-08:00
        # This code deviates from Photos in one regard:
        # if photo has modification date, use it otherwise use creation date

        date = self.photo.date
        offsettime = date.strftime("%z")
        # find timezone offset in format "-04:00"
        offset = re.findall(r"([+-]?)([\d]{2})([\d]{2})", offsettime)
        offset = offset[0]  # findall returns list of tuples
        offsettime = f"{offset[0]}{offset[1]}:{offset[2]}"

        # exiftool expects format to "2015:01:18 12:00:00"
        datetimeoriginal = date.strftime("%Y:%m:%d %H:%M:%S")

        if self.photo.isphoto:
            exif["EXIF:DateTimeOriginal"] = datetimeoriginal
            exif["EXIF:CreateDate"] = datetimeoriginal
            exif["EXIF:OffsetTimeOriginal"] = offsettime

            dateoriginal = date.strftime("%Y:%m:%d")
            exif["IPTC:DateCreated"] = dateoriginal

            timeoriginal = date.strftime(f"%H:%M:%S{offsettime}")
            exif["IPTC:TimeCreated"] = timeoriginal

            if (
                self.photo.date_modified is not None
                and not options.ignore_date_modified
            ):
                exif["EXIF:ModifyDate"] = self.photo.date_modified.strftime(
                    "%Y:%m:%d %H:%M:%S"
                )
            else:
                exif["EXIF:ModifyDate"] = self.photo.date.strftime("%Y:%m:%d %H:%M:%S")
        elif self.photo.ismovie:
            # QuickTime spec specifies times in UTC
            # QuickTime:CreateDate and ModifyDate are in UTC w/ no timezone
            # QuickTime:CreationDate must include time offset or Photos shows invalid values
            # reference: https://exiftool.org/TagNames/QuickTime.html#Keys
            #            https://exiftool.org/forum/index.php?topic=11927.msg64369#msg64369
            exif["QuickTime:CreationDate"] = f"{datetimeoriginal}{offsettime}"

            # also add QuickTime:ContentCreateDate
            # reference: https://github.com/RhetTbull/osxphotos/pull/888
            # exiftool writes this field with timezone so include it here
            exif["QuickTime:ContentCreateDate"] = f"{datetimeoriginal}{offsettime}"

            date_utc = datetime_tz_to_utc(date)
            creationdate = date_utc.strftime("%Y:%m:%d %H:%M:%S")
            exif["QuickTime:CreateDate"] = creationdate
            if self.photo.date_modified is None or options.ignore_date_modified:
                exif["QuickTime:ModifyDate"] = creationdate
            else:
                exif["QuickTime:ModifyDate"] = datetime_tz_to_utc(
                    self.photo.date_modified
                ).strftime("%Y:%m:%d %H:%M:%S")

        return exif

    def _get_mwg_face_regions_exiftool(self):
        """Return a dict with MWG face regions for use by exiftool"""
        if self.photo.orientation in [5, 6, 7, 8]:
            w = self.photo.height
            h = self.photo.width
        else:
            w = self.photo.width
            h = self.photo.height
        exif = {}
        exif["XMP:RegionAppliedToDimensionsW"] = w
        exif["XMP:RegionAppliedToDimensionsH"] = h
        exif["XMP:RegionAppliedToDimensionsUnit"] = "pixel"
        exif["XMP:RegionName"] = []
        exif["XMP:RegionType"] = []
        exif["XMP:RegionAreaX"] = []
        exif["XMP:RegionAreaY"] = []
        exif["XMP:RegionAreaW"] = []
        exif["XMP:RegionAreaH"] = []
        exif["XMP:RegionAreaUnit"] = []
        exif["XMP:RegionPersonDisplayName"] = []
        # exif["XMP:RegionRectangle"] = []
        for face in self.photo.face_info:
            if not face.name:
                continue
            area = face.mwg_rs_area
            exif["XMP:RegionName"].append(face.name)
            exif["XMP:RegionType"].append("Face")
            exif["XMP:RegionAreaX"].append(area.x)
            exif["XMP:RegionAreaY"].append(area.y)
            exif["XMP:RegionAreaW"].append(area.w)
            exif["XMP:RegionAreaH"].append(area.h)
            exif["XMP:RegionAreaUnit"].append("normalized")
            exif["XMP:RegionPersonDisplayName"].append(face.name)
            # exif["XMP:RegionRectangle"].append(f"{area.x},{area.y},{area.h},{area.w}")
        return exif

    def _get_exif_keywords(self):
        """returns list of keywords found in the file's exif metadata"""
        keywords = []
        exif = exiftool_caching(self.photo)
        if exif:
            exifdict = exif.asdict()
            for field in ["IPTC:Keywords", "XMP:TagsList", "XMP:Subject"]:
                try:
                    kw = exifdict[field]
                    if kw and type(kw) != list:
                        kw = [kw]
                    kw = [str(k) for k in kw]
                    keywords.extend(kw)
                except KeyError:
                    pass
        return keywords

    def _get_exif_persons(self):
        """returns list of persons found in the file's exif metadata"""
        persons = []
        exif = exiftool_caching(self.photo)
        if exif:
            exifdict = exif.asdict()
            try:
                p = exifdict["XMP:PersonInImage"]
                if p and type(p) != list:
                    p = [p]
                p = [str(p_) for p_ in p]
                persons.extend(p)
            except KeyError:
                pass
        return persons

    def exiftool_json_sidecar(
        self,
        options: Optional[ExportOptions] = None,
        tag_groups: bool = True,
        filename: Optional[str] = None,
    ) -> str:
        """Return JSON dict of EXIF details for building exiftool JSON sidecar or sending commands to ExifTool.
            Does not include all the EXIF fields as those are likely already in the image.

        Args:
            options (ExportOptions): options for export
            tag_groups (bool, default=True): if True, include tag groups in the output
            filename (str): name of source image file (without path); if not None, exiftool JSON signature will be included; if None, signature will not be included

        Returns: JSON dict with exiftool tags / values

        Exports the following:
            EXIF:ImageDescription
            XMP:Description (may include template)
            IPTC:CaptionAbstract
            XMP:Title
            IPTC:ObjectName
            XMP:TagsList
            IPTC:Keywords (may include album name, person name, or template)
            XMP:Subject (set to keywords + person)
            XMP:PersonInImage
            EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef
            EXIF:GPSLatitude, EXIF:GPSLongitude
            EXIF:GPSPosition
            EXIF:DateTimeOriginal
            EXIF:OffsetTimeOriginal
            EXIF:ModifyDate
            IPTC:DigitalCreationDate
            IPTC:DateCreated
            QuickTime:CreationDate
            QuickTime:CreateDate (UTC)
            QuickTime:ModifyDate (UTC)
            QuickTime:GPSCoordinates
            UserData:GPSCoordinates
        """

        options = options or ExifOptions()
        exif = self.exiftool_dict(filename=filename, options=options)

        if not tag_groups:
            # strip tag groups
            exif_new = {}
            for k, v in exif.items():
                k = re.sub(r".*:", "", k)
                exif_new[k] = v
            exif = exif_new

        return json.dumps([exif])


def exiftool_caching(photo: SimpleNamespace) -> ExifToolCaching:
    """Return ExifToolCaching object for photo

    Args:
        photo: SimpleNamespace object with photo info

    Returns:
        ExifToolCaching object
    """
    try:
        return photo._exiftool_caching
    except AttributeError:
        try:
            exiftool_path = photo._exiftool_path or get_exiftool_path()
            if photo.path is not None and os.path.isfile(photo.path):
                exiftool = ExifToolCaching(photo.path, exiftool=exiftool_path)
            else:
                exiftool = None
        except FileNotFoundError:
            # get_exiftool_path raises FileNotFoundError if exiftool not found
            exiftool = None
            logger.warning(
                "exiftool not in path; download and install from https://exiftool.org/"
            )

        photo._exiftool_caching = exiftool
        return photo._exiftool_caching
