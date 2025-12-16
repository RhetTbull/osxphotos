"""Write sidecars for PhotoInfo objects"""

from __future__ import annotations

import dataclasses
import logging
import os
import pathlib
from functools import cache
from typing import TYPE_CHECKING, Callable

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
from .metadata_reader import get_sidecar_for_file
from .photoinfo_file import render_photo_template_from_filepath, strip_edited_suffix
from .phototemplate import PhotoTemplate, RenderOptions
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

__all__ = [
    "SidecarWriter",
    "exiftool_json_sidecar",
    "xmp_sidecar",
    "get_sidecar_file_with_template",
]


class UserSidecarError(Exception):
    """Generated if there's an error in user sidecar template so it can be handled by export CLI"""

    pass


@dataclasses.dataclass
class SidecarVars:
    description: str | None = None
    extension: str | None = None
    keywords: list[str] = dataclasses.field(default_factory=list)
    persons: list[str] = dataclasses.field(default_factory=list)
    subjects: list[str] = dataclasses.field(default_factory=list)
    location: tuple[float | None, float | None] = dataclasses.field(
        default_factory=lambda: (None, None)
    )
    rating: int | None = None


@cache
def _get_template(template: str) -> Template:
    """Get template from cache or load from file"""
    return Template(filename=template)


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
        export_results: ExportResults,
    ) -> ExportResults:
        """Write sidecar files for the photo.

        Args:
            dest: destination path for photo that sidecars are being written for
            options: ExportOptions object that configures the sidecars
            export_results: ExportResults object containing information about the exported photo

        Returns: An ExportResults object containing information about the exported sidecar files

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
        # write user sidecar files if specified
        if options.sidecar_template:
            results += self.write_user_sidecar_files(
                dest=dest, options=options, export_results=export_results
            )

        if options.touch_file:
            all_sidecars = (
                sidecar_json_files_written
                + sidecar_exiftool_files_written
                + sidecar_xmp_files_written
                + sidecar_json_files_skipped
                + sidecar_exiftool_files_skipped
                + sidecar_xmp_files_skipped
                + results.sidecar_user_written
                + results.sidecar_user_skipped
            )
            results += touch_files(self.photo, all_sidecars, options)

            # update destination signatures in database
            for sidecar_filename in all_sidecars:
                sidecar_record = export_db.create_or_get_file_record(
                    sidecar_filename, self.photo.uuid
                )
                sidecar_record.dest_sig = fileutil.file_sig(sidecar_filename)

        return results

    def write_user_sidecar_files(
        self,
        dest: pathlib.Path,
        options: ExportOptions,
        export_results: ExportResults,
    ) -> ExportResults:
        """Write user sidecar files for the photo.

        Args:
            dest: destination path for photo that sidecars are being written for
            options: ExportOptions object that configures the sidecars
            export_results: ExportResults object with information about the exorted photos

        Returns: An ExportResults object containing information about the exported sidecar files
        """
        verbose = options.verbose or self._verbose

        # define functions for adding markup
        _filepath = add_rich_markup_tag("filepath", rich=options.rich)

        sidecar_user_written = []
        sidecar_user_skipped = []
        sidecar_user_error = []

        exif_options = exif_options_from_options(options)

        for (
            template_file,
            filename_template,
            template_options,
        ) in options.sidecar_template:
            strip_whitespace = "strip_whitespace" in template_options
            strip_lines = "strip_lines" in template_options
            write_skipped = "write_skipped" in template_options
            skip_zero = "skip_zero" in template_options
            catch_errors = "catch_errors" in template_options
            # Render the sidecar filename
            template_filename = self._render_sidecar_filename(
                filepath=str(dest),
                filename_template=filename_template,
                export_dir=str(dest.parent),
                exiftool_path=options.exiftool_path,
            )

            if not template_filename:
                logger.error(
                    f"Invalid SIDECAR_FILENAME_TEMPLATE for --sidecar-template '{filename_template}'"
                )
                continue

            sidecar_path = pathlib.Path(template_filename)

            if not write_skipped and str(dest) in export_results.skipped:
                sidecar_user_skipped.append(str(sidecar_path))
                verbose(f"Skipping existing sidecar file [filepath]{sidecar_path}[/]")
                continue

            try:
                result = self._render_user_sidecar(
                    template_file=template_file,
                    sidecar_path=sidecar_path,
                    photo_path=dest,
                    strip_whitespace=strip_whitespace,
                    strip_lines=strip_lines,
                    skip_zero=skip_zero,
                    catch_errors=catch_errors,
                    options=options,
                    exif_options=exif_options,
                )
            except ValueError as e:
                logger.warning(f"Error writing sidecar {sidecar_path}: {e}")
                sidecar_user_error.append((str(sidecar_path), str(e)))
                continue

            if result is None:
                # skip_zero triggered, skip this sidecar
                continue

            sidecar_str = result
            verbose(f"Writing sidecar file {_filepath(sidecar_path)}")
            sidecar_user_written.append(str(sidecar_path))
            if not options.dry_run:
                try:
                    with open(sidecar_path, "w") as f:
                        f.write(sidecar_str)
                except Exception as e:
                    sidecar_user_error.append(str(e))

        results = ExportResults(
            sidecar_user_written=sidecar_user_written,
            sidecar_user_skipped=sidecar_user_skipped,
            sidecar_user_error=sidecar_user_error,
        )
        return results

    def _render_sidecar_filename(
        self,
        filepath: str,
        filename_template: str,
        export_dir: str,
        exiftool_path: str | None,
    ) -> str | None:
        """Render sidecar filename template"""
        render_options = RenderOptions(export_dir=export_dir, filepath=filepath)
        photo_template = PhotoTemplate(self.photo, exiftool_path=exiftool_path)
        template_filename, _ = photo_template.render(
            filename_template, options=render_options
        )
        template_filename = template_filename[0] if template_filename else None
        return template_filename

    def _render_user_sidecar(
        self,
        template_file: str,
        sidecar_path: pathlib.Path,
        photo_path: pathlib.Path,
        strip_whitespace: bool,
        strip_lines: bool,
        skip_zero: bool,
        catch_errors: bool,
        options: ExportOptions,
        exif_options: ExifOptions,
    ) -> str | None:
        """Render user sidecar template and return data

        Returns:
            str: rendered sidecar data
            None: if skip_zero is True and sidecar is empty
            Exception: if catch_errors is True and an error occurred

        Raises:
            Raises ValueError if error and catch_errors is False
        """

        vars = self._sidecar_variables(options, None)

        # Render the template
        try:
            sidecar_template = _get_template(template_file)
            sidecar_data = sidecar_template.render(
                photo=self.photo,
                sidecar_path=sidecar_path,
                photo_path=photo_path,
                description=vars.description,
                keywords=vars.keywords,
                persons=vars.persons,
                subjects=vars.subjects,
                extension=vars.extension,
                location=vars.location,
                version=__version__,
                rating=vars.rating,
            )
        except Exception as e:
            if catch_errors:
                raise ValueError(f"Error rendering sidecar template: {e}") from e
            raise UserSidecarError(e) from e

        if strip_whitespace:
            # strip whitespace
            sidecar_data = "\n".join(line.strip() for line in sidecar_data.split("\n"))
        if strip_lines:
            # strip blank lines
            sidecar_data = "\n".join(
                line for line in sidecar_data.split("\n") if line.strip()
            )

        if skip_zero and not sidecar_data:
            verbose = options.verbose or self._verbose
            _filepath = add_rich_markup_tag("filepath", rich=options.rich)
            verbose(f"Skipping empty sidecar file {_filepath(sidecar_path)}")
            return None

        return sidecar_data

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
        xmp_template = self._xmp_template()
        vars = self._sidecar_variables(options, extension)
        xmp_str = xmp_template.render(
            photo=self.photo,
            description=vars.description,
            keywords=vars.keywords,
            persons=vars.persons,
            subjects=vars.subjects,
            extension=vars.extension,
            location=vars.location,
            version=__version__,
            rating=vars.rating,
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

    def _sidecar_variables(
        self,
        options: ExportOptions | None = None,
        extension: str | None = None,
    ) -> SidecarVars:
        """Render sidecar variables"""

        render_options = options.render_options or RenderOptions()

        if extension is None:
            extension_path = pathlib.Path(self.photo.original_filename)
            extension = extension_path.suffix[1:] if extension_path.suffix else None

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

        return SidecarVars(
            description=description,
            extension=extension,
            keywords=keyword_list,
            persons=person_list,
            subjects=subject_list,
            location=latlon,
            rating=rating,
        )

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


def get_sidecar_file_with_template(
    filepath: pathlib.Path,
    sidecar: bool,
    sidecar_filename_template: str | None,
    edited_suffix: str | None,
    exiftool_path: str | None,
) -> pathlib.Path | None:
    """Find sidecar file for photo with optional template for the sidecar and/or edited suffix"""
    if not (sidecar or sidecar_filename_template):
        return None
    sidecar_file = None
    if sidecar_filename_template:
        if sidecars := render_photo_template_from_filepath(
            filepath,
            None,
            sidecar_filename_template,
            exiftool_path,
            None,
        ):
            # allow multiple values to be rendered and checked
            # but only one will be used if more than one is valid
            for f in sidecars:
                sidecar_file = pathlib.Path(f)
                if sidecar_file.exists():
                    break
                else:
                    sidecar_file = None
        else:
            logger.warning(
                f"Could not render sidecar template '{sidecar_filename_template}' for '{filepath}'"
            )
    else:
        sidecar_file = get_sidecar_for_file(filepath)
    if not sidecar_file or not sidecar_file.exists():
        if edited_suffix:
            # try again with the edited suffix removed
            filepath = strip_edited_suffix(filepath, edited_suffix, exiftool_path)
            return get_sidecar_file_with_template(
                filepath,
                sidecar,
                sidecar_filename_template,
                None,
                exiftool_path,
            )
        return None
    return sidecar_file
