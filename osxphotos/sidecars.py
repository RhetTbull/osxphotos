"""Write sidecars for PhotoInfo objects"""

from __future__ import annotations

import dataclasses
import logging
import os
import pathlib
from typing import TYPE_CHECKING

from mako.template import Template

from ._constants import (
    _OSXPHOTOS_NONE_SENTINEL,
    _TEMPLATE_DIR,
    _UNKNOWN_PERSON,
    _XMP_TEMPLATE_NAME,
    _XMP_TEMPLATE_NAME_BETA,
    SIDECAR_EXIFTOOL,
    SIDECAR_JSON,
    SIDECAR_XMP,
)
from ._version import __version__
from .exifwriter import ExifOptions, ExifWriter, _ExifMixin, exif_options_from_options
from .export_db import ExportDBTemp
from .exportoptions import ExportOptions, ExportResults
from .fileutil import FileUtilMacOS, FileUtilShUtil
from .phototemplate import RenderOptions
from .platform import is_macos
from .rich_utils import add_rich_markup_tag
from .touch_files import touch_files
from .utils import hexdigest

if TYPE_CHECKING:
    from .photoinfo import PhotoInfo

# Global to hold the compiled XMP template
# This is expensive to compile so we only want to do it once
_global_xmp_template: Template | None = None

logger = logging.getLogger("osxphotos")

__all__ = ["SidecarWriter", "exiftool_json_sidecar", "xmp_sidecar"]


class SidecarWriter(_ExifMixin):
    """Write sidecars for PhotoInfo objects

    Can write XMP, JSON, and exiftool sidecars

    Args:
        photo: PhotoInfo object

    Note:
        Sidecars are written by calling write_sidecar_files() which returns an ExportResults object
    """

    def __init__(self, photo: PhotoInfo):
        super().__init__(photo)
        self._verbose = photo._verbose

    def write_sidecar_files(
        self,
        dest: pathlib.Path,
        options: ExportOptions,
    ) -> ExportResults:
        """Write sidecar files for the photo.

        Args:
            dest: destination path for photo that sidecars are being written for
            options: ExportOptions object that configures the sidecars

        Returns:
            An ExportResults object containing information about the exported sidecar files in the
            following attributes:
                - sidecar_json_written: list of JSON sidecar files written
                - sidecar_json_skipped: list of JSON sidecar files skipped
                - sidecar_exiftool_written: list of exiftool JSON sidecar files written
                - sidecar_exiftool_skipped: list of exiftool JSON sidecar files skipped
                - sidecar_xmp_written: list of XMP sidecar files written
                - sidecar_xmp_skipped: list of XMP sidecar files skipped

        Note:
            dest is the path to the the sidecar belongs to. THe sidecar filename will be
            dest.ext where ext is the extension for sidecar (e.g. xmp or json)
            If dest is "img_1234.jpg", XMP sidecar would be "img_1234.jpg.xmp"
            Use ExportOptions(sidecar_drop_ext) to drop the image extension from the sidecar filename
            (e.g. "img_1234.xmp")
        """

        # if ExportDB isn't provided, use a temporary in-memory database
        # this allows SidecarWriter to be used independently of PhotoExporter
        export_db = options.export_db or ExportDBTemp()

        # likewise, if FileUtil isn't provided, use default
        fileutil = options.fileutil or FileUtilMacOS() if is_macos else FileUtilShUtil()
        verbose = options.verbose or self._verbose

        # define functions for adding markup
        _filepath = add_rich_markup_tag("filepath", rich=options.rich)

        # export metadata
        sidecars = []
        sidecar_json_files_skipped = []
        sidecar_json_files_written = []
        sidecar_exiftool_files_skipped = []
        sidecar_exiftool_files_written = []
        sidecar_xmp_files_skipped = []
        sidecar_xmp_files_written = []

        dest_suffix = "" if options.sidecar_drop_ext else dest.suffix
        exif_options = exif_options_from_options(options)
        if options.sidecar & SIDECAR_JSON:
            sidecar_filename = dest.parent / pathlib.Path(
                f"{dest.stem}{dest_suffix}.json"
            )
            sidecar_str = exiftool_json_sidecar(
                photo=self.photo,
                filename=dest.name,
                options=exif_options,
            )
            sidecars.append(
                (
                    sidecar_filename,
                    sidecar_str,
                    sidecar_json_files_written,
                    sidecar_json_files_skipped,
                    "JSON",
                )
            )

        if options.sidecar & SIDECAR_EXIFTOOL:
            sidecar_filename = dest.parent / pathlib.Path(
                f"{dest.stem}{dest_suffix}.json"
            )
            sidecar_str = exiftool_json_sidecar(
                photo=self.photo,
                tag_groups=False,
                filename=dest.name,
                options=exif_options,
            )
            sidecars.append(
                (
                    sidecar_filename,
                    sidecar_str,
                    sidecar_exiftool_files_written,
                    sidecar_exiftool_files_skipped,
                    "exiftool",
                )
            )

        if options.sidecar & SIDECAR_XMP:
            sidecar_filename = dest.parent / pathlib.Path(
                f"{dest.stem}{dest_suffix}.xmp"
            )
            sidecar_str = self.xmp_sidecar(
                extension=dest.suffix[1:] if dest.suffix else None, options=options
            )
            sidecars.append(
                (
                    sidecar_filename,
                    sidecar_str,
                    sidecar_xmp_files_written,
                    sidecar_xmp_files_skipped,
                    "XMP",
                )
            )

        for data in sidecars:
            sidecar_filename = data[0]
            sidecar_str = data[1]
            files_written = data[2]
            files_skipped = data[3]
            sidecar_type = data[4]

            sidecar_digest = hexdigest(sidecar_str)
            sidecar_record = export_db.create_or_get_file_record(
                sidecar_filename, self.photo.uuid
            )
            write_sidecar = (
                not (options.update or options.force_update)
                or (
                    (options.update or options.force_update)
                    and not sidecar_filename.exists()
                )
                or (
                    (options.update or options.force_update)
                    and (sidecar_digest != sidecar_record.digest)
                    or not fileutil.cmp_file_sig(
                        sidecar_filename, sidecar_record.dest_sig
                    )
                )
            )
            if write_sidecar:
                verbose(f"Writing {sidecar_type} sidecar {_filepath(sidecar_filename)}")
                files_written.append(str(sidecar_filename))
                if not options.dry_run:
                    self._write_sidecar(sidecar_filename, sidecar_str)
                    sidecar_record.digest = sidecar_digest
                    sidecar_record.dest_sig = fileutil.file_sig(sidecar_filename)
            else:
                verbose(
                    f"Skipped up to date {sidecar_type} sidecar {_filepath(sidecar_filename)}"
                )
                files_skipped.append(str(sidecar_filename))

        results = ExportResults(
            sidecar_json_written=sidecar_json_files_written,
            sidecar_json_skipped=sidecar_json_files_skipped,
            sidecar_exiftool_written=sidecar_exiftool_files_written,
            sidecar_exiftool_skipped=sidecar_exiftool_files_skipped,
            sidecar_xmp_written=sidecar_xmp_files_written,
            sidecar_xmp_skipped=sidecar_xmp_files_skipped,
        )

        if options.touch_file:
            all_sidecars = (
                sidecar_json_files_written
                + sidecar_exiftool_files_written
                + sidecar_xmp_files_written
                + sidecar_json_files_skipped
                + sidecar_exiftool_files_skipped
                + sidecar_xmp_files_skipped
            )
            results += touch_files(self.photo, all_sidecars, options)

            # update destination signatures in database
            for sidecar_filename in all_sidecars:
                sidecar_record = export_db.create_or_get_file_record(
                    sidecar_filename, self.photo.uuid
                )
                sidecar_record.dest_sig = fileutil.file_sig(sidecar_filename)

        return results

    def xmp_sidecar(
        self,
        options: ExportOptions | None = None,
        extension: str | None = None,
    ):
        """returns string for XMP sidecar

        Args:
            options (ExportOptions): options for export
            extension (Optional[str]): which extension to use for SidecarForExtension property
        """

        options = options or ExportOptions()
        render_options = options.render_options or RenderOptions()

        xmp_template = self._xmp_template()

        if extension is None:
            extension = pathlib.Path(self.photo.original_filename)
            extension = extension.suffix[1:] if extension.suffix else None

        if options.description_template is not None:
            render_options_description = dataclasses.replace(
                render_options, expand_inplace=True, inplace_sep=", "
            )
            rendered = self.photo.render_template(
                options.description_template, render_options_description
            )[0]
            description = " ".join(rendered) if rendered else ""
            if options.strip:
                description = description.strip()
        else:
            description = (
                self.photo.description if self.photo.description is not None else ""
            )

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
            render_options_keywords = dataclasses.replace(
                render_options, none_str=_OSXPHOTOS_NONE_SENTINEL, path_sep="/"
            )
            for template_str in options.keyword_template:
                rendered, unmatched = self.photo.render_template(
                    template_str, render_options_keywords
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
                for keyword in rendered_keywords
                if _OSXPHOTOS_NONE_SENTINEL not in keyword
            ]

            keyword_list.extend(rendered_keywords)

        # remove duplicates
        # sorted mainly to make testing the XMP file easier
        if keyword_list:
            keyword_list = sorted(list(set(keyword_list)))
        if options.persons and person_list:
            person_list = sorted(list(set(person_list)))

        subject_list = keyword_list

        latlon = self.photo.location if options.location else (None, None)

        if options.favorite_rating:
            rating = 5 if self.photo.favorite else 0
        elif self.photo._db._source == "iPhoto":
            rating = self.photo.rating
        else:
            rating = None

        xmp_str = xmp_template.render(
            photo=self.photo,
            description=description,
            keywords=keyword_list,
            persons=person_list,
            subjects=subject_list,
            extension=extension,
            location=latlon,
            version=__version__,
            rating=rating,
        )

        # remove extra lines that mako inserts from template
        xmp_str = "\n".join(line for line in xmp_str.split("\n") if line.strip() != "")
        return xmp_str

    def _xmp_template(self):
        """Return the mako template for XMP sidecar, creating it if necessary"""
        global _global_xmp_template
        if _global_xmp_template is not None:
            return _global_xmp_template

        xmp_template_file = (
            _XMP_TEMPLATE_NAME_BETA if self.photo._db._beta else _XMP_TEMPLATE_NAME
        )
        _global_xmp_template = Template(
            filename=os.path.join(_TEMPLATE_DIR, xmp_template_file)
        )
        return _global_xmp_template

    def _write_sidecar(self, filename, sidecar_str):
        """write sidecar_str to filename
        used for exporting sidecar info"""
        if not (filename or sidecar_str):
            raise (
                ValueError(
                    f"filename {filename} and sidecar_str {sidecar_str} must not be None"
                )
            )

        with open(filename, "w") as f:
            f.write(sidecar_str)


def xmp_sidecar(
    photo: PhotoInfo,
    options: ExportOptions | None = None,
    extension: str | None = None,
) -> str:
    """Returns string for XMP sidecar

    Args:
        photo: PhotoInfo object to generate sidecar for
        options (ExportOptions): options for export
        extension (Optional[str]): which extension to use for SidecarForExtension property

    Returns:
        str: string containing XMP sidecar
    """

    writer = SidecarWriter(photo)
    return writer.xmp_sidecar(options=options, extension=extension)


def exiftool_json_sidecar(
    photo: PhotoInfo,
    options: ExportOptions | ExifOptions = None,
    tag_groups: bool = True,
    filename: str | None = None,
) -> str:
    """Return JSON string for EXIF details for building exiftool JSON sidecar or sending commands to ExifTool.
        Does not include all the EXIF fields as those are likely already in the image.

    Args:
        options (ExportOptions or ExifOptions): options for export
        tag_groups (bool, default=True): if True, include tag groups in the output
        filename (str): name of target image file (without path); if not None, exiftool JSON signature will be included; if None, signature will not be included

    Returns: JSON str for dict of exiftool tags / values
    """
    exif_options = (
        exif_options_from_options(options)
        if isinstance(options, ExportOptions)
        else options
    )
    return ExifWriter(photo).exiftool_json_sidecar(
        options=exif_options,
        tag_groups=tag_groups,
        filename=filename,
    )
