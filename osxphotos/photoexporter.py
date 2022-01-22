""" PhotoExport class to export photos
"""

# TODO: the various sidecar_json, sidecar_xmp, etc args should all be collapsed to a sidecar param using a bit mask

import dataclasses
import glob
import hashlib
import json
import logging
import os
import pathlib
import re
import tempfile
from collections import namedtuple  # pylint: disable=syntax-error
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Callable, List, Optional

import photoscript
from mako.template import Template

from ._constants import (
    _MAX_IPTC_KEYWORD_LEN,
    _OSXPHOTOS_NONE_SENTINEL,
    _TEMPLATE_DIR,
    _UNKNOWN_PERSON,
    _XMP_TEMPLATE_NAME,
    _XMP_TEMPLATE_NAME_BETA,
    DEFAULT_PREVIEW_SUFFIX,
    LIVE_VIDEO_EXTENSIONS,
    SIDECAR_EXIFTOOL,
    SIDECAR_JSON,
    SIDECAR_XMP,
)
from ._version import __version__
from .datetime_utils import datetime_tz_to_utc
from .exiftool import ExifTool
from .export_db import ExportDB_ABC, ExportDBNoOp
from .fileutil import FileUtil
from .photokit import (
    PHOTOS_VERSION_CURRENT,
    PHOTOS_VERSION_ORIGINAL,
    PHOTOS_VERSION_UNADJUSTED,
    PhotoKitFetchFailed,
    PhotoLibrary,
)
from .phototemplate import RenderOptions
from .uti import get_preferred_uti_extension
from .utils import increment_filename, increment_filename_with_count, lineno

__all__ = [
    "ExportError",
    "ExportOptions",
    "ExportResults",
    "PhotoExporter",
    "hexdigest",
    "rename_jpeg_files",
]

if TYPE_CHECKING:
    from .photoinfo import PhotoInfo

# retry if download_missing/use_photos_export fails the first time (which sometimes it does)
MAX_PHOTOSCRIPT_RETRIES = 3


class ExportError(Exception):
    """error during export"""

    pass


@dataclass
class ExportOptions:
    """Options class for exporting photos with export2

    Attributes:
        convert_to_jpeg (bool): if True, converts non-jpeg images to jpeg
        description_template (str): optional template string that will be rendered for use as photo description
        download_missing: (bool, default=False): if True will attempt to export photo via applescript interaction with Photos if missing (see also use_photokit, use_photos_export)
        dry_run: (bool, default=False): set to True to run in "dry run" mode
        edited: (bool, default=False): if True will export the edited version of the photo otherwise exports the original version
        exiftool_flags (list of str): optional list of flags to pass to exiftool when using exiftool option, e.g ["-m", "-F"]
        exiftool: (bool, default = False): if True, will use exiftool to write metadata to export file
        export_as_hardlink: (bool, default=False): if True, will hardlink files instead of copying them
        export_db: (ExportDB_ABC): instance of a class that conforms to ExportDB_ABC with methods for getting/setting data related to exported files to compare update state
        fileutil: (FileUtilABC): class that conforms to FileUtilABC with various file utilities
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
        preview_suffix (str): optional string to append to end of filename for preview images
        preview (bool): if True, also exports preview image
        raw_photo (bool, default=False): if True, will also export the associated RAW photo
        render_options (RenderOptions): optional osxphotos.phototemplate.RenderOptions instance to specify options for rendering templates
        replace_keywords (bool): if True, keyword_template replaces any keywords, otherwise it's additive
        sidecar_drop_ext (bool, default=False): if True, drops the photo's extension from sidecar filename (e.g. 'IMG_1234.json' instead of 'IMG_1234.JPG.json')
        sidecar: bit field (int): set to one or more of SIDECAR_XMP, SIDECAR_JSON, SIDECAR_EXIFTOOL
            - SIDECAR_JSON: if set will write a json sidecar with data in format readable by exiftool sidecar filename will be dest/filename.json;
              includes exiftool tag group names (e.g. `exiftool -G -j`)
            - SIDECAR_EXIFTOOL: if set will write a json sidecar with data in format readable by exiftool sidecar filename will be dest/filename.json;
              does not include exiftool tag group names (e.g. `exiftool -j`)
            - SIDECAR_XMP: if set will write an XMP sidecar with IPTC data sidecar filename will be dest/filename.xmp
        strip (bool): if True, strip whitespace from rendered templates
        timeout (int, default=120): timeout in seconds used with use_photos_export
        touch_file (bool, default=False): if True, sets file's modification time upon photo date
        update (bool, default=False): if True export will run in update mode, that is, it will not export the photo if the current version already exists in the destination
        use_albums_as_keywords (bool, default = False): if True, will include album names in keywords when exporting metadata with exiftool or sidecar
        use_persons_as_keywords (bool, default = False): if True, will include person names in keywords when exporting metadata with exiftool or sidecar
        use_photos_export (bool, default=False): if True will attempt to export photo via applescript interaction with Photos even if not missing (see also use_photokit, download_missing)
        use_photokit (bool, default=False): if True, will use photokit to export photos when use_photos_export is True
        verbose (Callable): optional callable function to use for printing verbose text during processing; if None (default), does not print output.
    """

    convert_to_jpeg: bool = False
    description_template: Optional[str] = None
    download_missing: bool = False
    dry_run: bool = False
    edited: bool = False
    exiftool_flags: Optional[List] = None
    exiftool: bool = False
    export_as_hardlink: bool = False
    export_db: Optional[ExportDB_ABC] = None
    fileutil: Optional[FileUtil] = None
    ignore_date_modified: bool = False
    ignore_signature: bool = False
    increment: bool = True
    jpeg_ext: Optional[str] = None
    jpeg_quality: float = 1.0
    keyword_template: Optional[List[str]] = None
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
    sidecar_drop_ext: bool = False
    sidecar: int = 0
    strip: bool = False
    timeout: int = 120
    touch_file: bool = False
    update: bool = False
    use_albums_as_keywords: bool = False
    use_persons_as_keywords: bool = False
    use_photokit: bool = False
    use_photos_export: bool = False
    verbose: Optional[Callable] = None

    def asdict(self):
        return asdict(self)


class StagedFiles:
    """Represents files staged for export"""

    def __init__(
        self,
        original: Optional[str] = None,
        original_live: Optional[str] = None,
        edited: Optional[str] = None,
        edited_live: Optional[str] = None,
        preview: Optional[str] = None,
        raw: Optional[str] = None,
        error: Optional[List[str]] = None,
    ):
        self.original = original
        self.original_live = original_live
        self.edited = edited
        self.edited_live = edited_live
        self.preview = preview
        self.raw = raw
        self.error = error or []

        # TODO: bursts?

    def __ior__(self, other):
        self.original = self.original or other.original
        self.original_live = self.original_live or other.original_live
        self.edited = self.edited or other.edited
        self.edited_live = self.edited_live or other.edited_live
        self.preview = self.preview or other.preview
        self.raw = self.raw or other.raw
        self.error += other.error
        return self

    def __str__(self):
        return str(self.asdict())

    def asdict(self):
        return {
            "original": self.original,
            "original_live": self.original_live,
            "edited": self.edited,
            "edited_live": self.edited_live,
            "preview": self.preview,
            "raw": self.raw,
            "error": self.error,
        }


class ExportResults:
    """Results class which holds export results for export2"""

    def __init__(
        self,
        exported=None,
        new=None,
        updated=None,
        skipped=None,
        exif_updated=None,
        touched=None,
        converted_to_jpeg=None,
        sidecar_json_written=None,
        sidecar_json_skipped=None,
        sidecar_exiftool_written=None,
        sidecar_exiftool_skipped=None,
        sidecar_xmp_written=None,
        sidecar_xmp_skipped=None,
        missing=None,
        error=None,
        exiftool_warning=None,
        exiftool_error=None,
        xattr_written=None,
        xattr_skipped=None,
        deleted_files=None,
        deleted_directories=None,
        exported_album=None,
        skipped_album=None,
        missing_album=None,
    ):
        self.exported = exported or []
        self.new = new or []
        self.updated = updated or []
        self.skipped = skipped or []
        self.exif_updated = exif_updated or []
        self.touched = touched or []
        self.converted_to_jpeg = converted_to_jpeg or []
        self.sidecar_json_written = sidecar_json_written or []
        self.sidecar_json_skipped = sidecar_json_skipped or []
        self.sidecar_exiftool_written = sidecar_exiftool_written or []
        self.sidecar_exiftool_skipped = sidecar_exiftool_skipped or []
        self.sidecar_xmp_written = sidecar_xmp_written or []
        self.sidecar_xmp_skipped = sidecar_xmp_skipped or []
        self.missing = missing or []
        self.error = error or []
        self.exiftool_warning = exiftool_warning or []
        self.exiftool_error = exiftool_error or []
        self.xattr_written = xattr_written or []
        self.xattr_skipped = xattr_skipped or []
        self.deleted_files = deleted_files or []
        self.deleted_directories = deleted_directories or []
        self.exported_album = exported_album or []
        self.skipped_album = skipped_album or []
        self.missing_album = missing_album or []

    def all_files(self):
        """return all filenames contained in results"""
        files = (
            self.exported
            + self.new
            + self.updated
            + self.skipped
            + self.exif_updated
            + self.touched
            + self.converted_to_jpeg
            + self.sidecar_json_written
            + self.sidecar_json_skipped
            + self.sidecar_exiftool_written
            + self.sidecar_exiftool_skipped
            + self.sidecar_xmp_written
            + self.sidecar_xmp_skipped
            + self.missing
        )
        files += [x[0] for x in self.exiftool_warning]
        files += [x[0] for x in self.exiftool_error]
        files += [x[0] for x in self.error]

        files = list(set(files))
        return files

    def __iadd__(self, other):
        self.exported += other.exported
        self.new += other.new
        self.updated += other.updated
        self.skipped += other.skipped
        self.exif_updated += other.exif_updated
        self.touched += other.touched
        self.converted_to_jpeg += other.converted_to_jpeg
        self.sidecar_json_written += other.sidecar_json_written
        self.sidecar_json_skipped += other.sidecar_json_skipped
        self.sidecar_exiftool_written += other.sidecar_exiftool_written
        self.sidecar_exiftool_skipped += other.sidecar_exiftool_skipped
        self.sidecar_xmp_written += other.sidecar_xmp_written
        self.sidecar_xmp_skipped += other.sidecar_xmp_skipped
        self.missing += other.missing
        self.error += other.error
        self.exiftool_warning += other.exiftool_warning
        self.exiftool_error += other.exiftool_error
        self.deleted_files += other.deleted_files
        self.deleted_directories += other.deleted_directories
        self.exported_album += other.exported_album
        self.skipped_album += other.skipped_album
        self.missing_album += other.missing_album

        return self

    def __str__(self):
        return (
            "ExportResults("
            + f"exported={self.exported}"
            + f",new={self.new}"
            + f",updated={self.updated}"
            + f",skipped={self.skipped}"
            + f",exif_updated={self.exif_updated}"
            + f",touched={self.touched}"
            + f",converted_to_jpeg={self.converted_to_jpeg}"
            + f",sidecar_json_written={self.sidecar_json_written}"
            + f",sidecar_json_skipped={self.sidecar_json_skipped}"
            + f",sidecar_exiftool_written={self.sidecar_exiftool_written}"
            + f",sidecar_exiftool_skipped={self.sidecar_exiftool_skipped}"
            + f",sidecar_xmp_written={self.sidecar_xmp_written}"
            + f",sidecar_xmp_skipped={self.sidecar_xmp_skipped}"
            + f",missing={self.missing}"
            + f",error={self.error}"
            + f",exiftool_warning={self.exiftool_warning}"
            + f",exiftool_error={self.exiftool_error}"
            + f",deleted_files={self.deleted_files}"
            + f",deleted_directories={self.deleted_directories}"
            + f",exported_album={self.exported_album}"
            + f",skipped_album={self.skipped_album}"
            + f",missing_album={self.missing_album}"
            + ")"
        )


class PhotoExporter:
    def __init__(self, photo: "PhotoInfo"):
        self.photo = photo
        self._render_options = RenderOptions()
        self._verbose = self.photo._verbose

        # temp directory for staging downloaded missing files
        self._temp_dir = tempfile.TemporaryDirectory(
            prefix=f"osxphotos_photo_exporter_{self.photo.uuid}_"
        )
        self._temp_dir_path = pathlib.Path(self._temp_dir.name)

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
        download_missing=False,
        use_photos_export=False,
        use_photokit=True,
        timeout=120,
        exiftool=False,
        use_albums_as_keywords=False,
        use_persons_as_keywords=False,
        keyword_template=None,
        description_template=None,
        render_options: Optional[RenderOptions] = None,
    ):
        """export photo
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
        use_photos_export: (boolean, default=False); if True will attempt to export photo via AppleScript or PhotoKit interaction with Photos
        download_missing: (boolean, default=False); if True will attempt to export photo via AppleScript or PhotoKit interaction with Photos if missing
        use_photokit: (boolean, default=True); if True will attempt to export photo via photokit instead of AppleScript when used with use_photos_export or download_missing
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

        Returns: list of photos exported
        """

        # Implementation note: calls export2 to actually do the work

        sidecar = 0
        if sidecar_json:
            sidecar |= SIDECAR_JSON
        if sidecar_exiftool:
            sidecar |= SIDECAR_EXIFTOOL
        if sidecar_xmp:
            sidecar |= SIDECAR_XMP

        if not filename:
            if not edited:
                filename = self.photo.original_filename
            else:
                original_name = pathlib.Path(self.photo.original_filename)
                if self.photo.path_edited:
                    ext = pathlib.Path(self.photo.path_edited).suffix
                else:
                    uti = (
                        self.photo.uti_edited
                        if edited and self.photo.uti_edited
                        else self.photo.uti
                    )
                    ext = get_preferred_uti_extension(uti)
                    ext = "." + ext
                filename = original_name.stem + "_edited" + ext

        options = ExportOptions(
            description_template=description_template,
            download_missing=download_missing,
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
            use_photokit=use_photokit,
            use_photos_export=use_photos_export,
        )

        results = self.export2(
            dest,
            filename=filename,
            options=options,
        )

        return results.exported

    def export2(
        self,
        dest,
        filename=None,
        options: Optional[ExportOptions] = None,
    ):
        """export photo, like export but with update and dry_run options

        Args:
            dest: must be valid destination path or exception raised
            filename: (optional): name of exported picture; if not provided, will use current filename
                    **NOTE**: if provided, user must ensure file extension (suffix) is correct.
                    For example, if photo is .CR2 file, edited image may be .jpeg.
                    If you provide an extension different than what the actual file is,
                    will export the photo using the incorrect file extension (unless use_photos_export is true,
                    in which case export will use the extension provided by Photos upon export.
                    e.g. to get the extension of the edited photo,
                    reference PhotoInfo.path_edited
            options (ExportOptions): optional ExportOptions instance

        Returns: ExportResults instance

        Note: to use dry run mode, you must set options.dry_run=True and also pass in memory version of export_db,
            and no-op fileutil (e.g. ExportDBInMemory and FileUtilNoOp) in options.export_db and options.fileutil respectively
        """

        options = options or ExportOptions()

        verbose = options.verbose or self._verbose
        if verbose and not callable(verbose):
            raise TypeError("verbose must be callable")

        # can't use export_as_hardlink with download_missing, use_photos_export as can't hardlink the temporary files downloaded
        if options.export_as_hardlink and options.download_missing:
            raise ValueError(
                "Cannot use export_as_hardlink with download_missing or use_photos_export"
            )

        # when called from export(), won't get an export_db, so use no-op version
        options.export_db = options.export_db or ExportDBNoOp()
        export_db = options.export_db

        # ensure there's a FileUtil class to use
        options.fileutil = options.fileutil or FileUtil
        fileutil = options.fileutil

        self._render_options = options.render_options or RenderOptions()

        # export_original, and export_edited are just used for clarity in the code
        export_original = not options.edited
        export_edited = options.edited
        if export_edited and not self.photo.hasadjustments:
            raise ValueError(
                "Photo does not have adjustments, cannot export edited version"
            )

        # verify destination is a valid path
        if dest is None:
            raise ValueError("dest must not be None")
        elif not options.dry_run and not os.path.isdir(dest):
            raise FileNotFoundError("Invalid path passed to export")

        if export_edited:
            filename = filename or self._get_edited_filename(
                self.photo.original_filename
            )
        else:
            filename = filename or self.photo.original_filename
        dest = pathlib.Path(dest) / filename

        # Is there something to convert with convert_to_jpeg?
        if options.convert_to_jpeg and self.photo.isphoto:
            something_to_convert = False
            ext = "." + options.jpeg_ext if options.jpeg_ext else ".jpeg"
            if export_original and self.photo.uti_original != "public.jpeg":
                # not a jpeg but will convert to jpeg upon export so fix file extension
                something_to_convert = True
                dest = dest.parent / f"{dest.stem}{ext}"
            if export_edited and self.photo.uti != "public.jpeg":
                # in Big Sur+, edited HEICs are HEIC
                something_to_convert = True
                dest = dest.parent / f"{dest.stem}{ext}"
            convert_to_jpeg = something_to_convert
        else:
            convert_to_jpeg = False
        options = dataclasses.replace(options, convert_to_jpeg=convert_to_jpeg)

        dest, _ = self._validate_dest_path(
            dest,
            increment=options.increment,
            update=options.update,
            overwrite=options.overwrite,
        )
        dest = pathlib.Path(dest)
        self._render_options.filepath = str(dest)
        all_results = ExportResults()

        staged_files = self._stage_photos_for_export(options)

        src = staged_files.edited if options.edited else staged_files.original
        if src:
            # found source now try to find right destination
            if options.update and dest.exists():
                # destination exists, check to see if destination is the right UUID
                dest_uuid = export_db.get_uuid_for_file(dest)
                if dest_uuid is None and fileutil.cmp(src, dest):
                    # might be exporting into a pre-ExportDB folder or the DB got deleted
                    dest_uuid = self.photo.uuid
                    export_db.set_data(
                        filename=dest,
                        uuid=self.photo.uuid,
                        orig_stat=fileutil.file_sig(dest),
                        exif_stat=(None, None, None),
                        converted_stat=(None, None, None),
                        edited_stat=(None, None, None),
                        info_json=self.photo.json(),
                        exif_json=None,
                    )
                if dest_uuid != self.photo.uuid:
                    # not the right file, find the right one
                    glob_str = str(dest.parent / f"{dest.stem} (*{dest.suffix}")
                    dest_files = glob.glob(glob_str)
                    for file_ in dest_files:
                        dest_uuid = export_db.get_uuid_for_file(file_)
                        if dest_uuid == self.photo.uuid:
                            dest = pathlib.Path(file_)
                            break
                        elif dest_uuid is None and fileutil.cmp(src, file_):
                            # files match, update the UUID
                            dest = pathlib.Path(file_)
                            export_db.set_data(
                                filename=dest,
                                uuid=self.photo.uuid,
                                orig_stat=fileutil.file_sig(dest),
                                exif_stat=(None, None, None),
                                converted_stat=(None, None, None),
                                edited_stat=(None, None, None),
                                info_json=self.photo.json(),
                                exif_json=None,
                            )
                            break
                    else:
                        # increment the destination file
                        dest = pathlib.Path(increment_filename(dest))

            # export the dest file
            results = self._export_photo(
                src,
                dest,
                options=options,
            )
            all_results += results

        # copy live photo associated .mov if requested
        if (
            export_original
            and options.live_photo
            and self.photo.live_photo
            and staged_files.original_live
        ):
            live_name = dest.parent / f"{dest.stem}.mov"
            src_live = staged_files.original_live
            results = self._export_photo(
                src_live,
                live_name,
                # don't try to convert the live photo
                options=dataclasses.replace(options, convert_to_jpeg=False),
            )
            all_results += results

        if (
            export_edited
            and options.live_photo
            and self.photo.live_photo
            and staged_files.edited_live
        ):
            live_name = dest.parent / f"{dest.stem}.mov"
            src_live = staged_files.edited_live
            results = self._export_photo(
                src_live,
                live_name,
                # don't try to convert the live photo
                options=dataclasses.replace(options, convert_to_jpeg=False),
            )
            all_results += results

        # copy associated RAW image if requested
        if options.raw_photo and self.photo.has_raw and staged_files.raw:
            raw_path = pathlib.Path(staged_files.raw)
            raw_ext = raw_path.suffix
            raw_name = dest.parent / f"{dest.stem}{raw_ext}"
            if raw_path is not None:
                results = self._export_photo(
                    raw_path,
                    raw_name,
                    options=options,
                )
                all_results += results

        # copy preview image if requested
        if options.preview and staged_files.preview:
            # Photos keeps multiple different derivatives and path_derivatives returns list of them
            # first derivative is the largest so export that one
            preview_path = pathlib.Path(staged_files.preview)
            preview_ext = preview_path.suffix
            preview_name = (
                dest.parent / f"{dest.stem}{options.preview_suffix}{preview_ext}"
            )
            # if original is missing, the filename won't have been incremented so
            # need to check here to make sure there aren't duplicate preview files in
            # the export directory
            preview_name = (
                preview_name
                if options.overwrite or options.update
                else pathlib.Path(increment_filename(preview_name))
            )
            if preview_path is not None:
                results = self._export_photo(
                    preview_path,
                    preview_name,
                    options=options,
                )
                all_results += results

        results = self._write_sidecar_files(dest=dest, options=options)
        all_results += results

        # if exiftool, write the metadata
        if options.exiftool:
            exif_files = (
                all_results.new + all_results.updated + all_results.skipped
                if options.update
                else all_results.exported
            )
            for exported_file in exif_files:
                results = self._write_exif_metadata_to_files(
                    exported_file=exported_file, options=options
                )
                all_results += results

        if options.touch_file:
            for exif_file in all_results.exif_updated:
                verbose(f"Updating file modification time for {exif_file}")
                all_results.touched.append(exif_file)
                ts = int(self.photo.date.timestamp())
                fileutil.utime(exif_file, (ts, ts))

        all_results.touched = list(set(all_results.touched))

        return all_results

    def _get_edited_filename(self, original_filename):
        """Return the filename for the exported edited photo
        (used when filename isn't provided in call to export2)"""
        # need to get the right extension for edited file
        original_filename = pathlib.Path(original_filename)
        if self.photo.path_edited:
            ext = pathlib.Path(self.photo.path_edited).suffix
        else:
            uti = self.photo.uti_edited if self.photo.uti_edited else self.photo.uti
            ext = get_preferred_uti_extension(uti)
            ext = "." + ext
        edited_filename = original_filename.stem + "_edited" + ext
        return edited_filename

    def _validate_dest_path(self, dest, increment, update, overwrite, count=0):
        """If destination exists, add (1), (2), and so on to filename to get a valid destination

        Args:
            dest (str): Destination path
            increment (bool): Whether to increment the filename if it already exists
            update (bool): Whether running in update mode
            overwrite (bool): Whether running in overwrite mode
            count: optional counter to start from (if 0, start from 1)

        Returns:
            new dest path (pathlib.Path), increment count (int)
        """
        # check to see if file exists and if so, add (1), (2), etc until we find one that works
        # Photos checks the stem and adds (1), (2), etc which avoids collision with sidecars
        # e.g. exporting sidecar for file1.png and file1.jpeg
        # if file1.png exists and exporting file1.jpeg,
        # dest will be file1 (1).jpeg even though file1.jpeg doesn't exist to prevent sidecar collision
        if increment and not update and not overwrite:
            dest, count = increment_filename_with_count(dest, count=count)
            dest = pathlib.Path(dest)

        # if overwrite==False and #increment==False, export should fail if file exists
        if dest.exists() and all([not x for x in [increment, update, overwrite]]):
            raise FileExistsError(
                f"destination exists ({dest}); overwrite={overwrite}, increment={increment}"
            )
        return dest, count

    def _stage_photos_for_export(self, options: ExportOptions) -> StagedFiles:
        """Stages photos for export

        If photo is present on disk in the library, uses path to the photo on disk.
        If photo is missing and download_missing is true, downloads the photo from iCloud to temporary location.
        """

        staged = StagedFiles()

        if options.use_photos_export:
            # use Photos AppleScript or PhotoKit to do the export
            return (
                self._stage_photo_for_export_with_photokit(options=options)
                if options.use_photokit
                else self._stage_photo_for_export_with_applescript(options=options)
            )

        if options.raw_photo and self.photo.has_raw:
            staged.raw = self.photo.path_raw

        if options.preview and self.photo.path_derivatives:
            staged.preview = self.photo.path_derivatives[0]

        if not options.edited:
            # original file
            if self.photo.path:
                staged.original = self.photo.path
            if options.live_photo and self.photo.live_photo:
                staged.original_live = self.photo.path_live_photo

        if options.edited:
            # edited file
            staged.edited = self.photo.path_edited
            if options.live_photo and self.photo.live_photo:
                staged.edited_live = self.photo.path_edited_live_photo

        # download any missing files
        if options.download_missing:
            live_photo = staged.edited_live if options.edited else staged.original_live
            missing_options = ExportOptions(
                edited=options.edited,
                # TODO: missing previews are not generated/downloaded
                preview=options.preview and not staged.preview,
                raw_photo=options.raw_photo and not staged.raw,
                live_photo=options.live_photo and not live_photo,
            )
            if options.use_photokit:
                missing_staged = self._stage_photo_for_export_with_photokit(
                    options=missing_options
                )
            else:
                missing_staged = self._stage_photo_for_export_with_applescript(
                    options=missing_options
                )
            staged |= missing_staged
        return staged

    def _stage_photo_for_export_with_photokit(
        self,
        options: ExportOptions,
    ) -> StagedFiles:
        """Stage a photo for export with photokit to a temporary directory"""

        if options.edited and not self.photo.hasadjustments:
            raise ValueError("Edited version requested but photo has no adjustments")

        dest = self._temp_dir_path / self.photo.original_filename

        # export live_photo .mov file?
        live_photo = bool(options.live_photo and self.photo.live_photo)

        overwrite = options.overwrite or options.update

        # figure out which photo version to request
        if options.edited or self.photo.shared:
            # shared photos (in shared albums) show up as not having adjustments (not edited)
            # but Photos is unable to export the "original" as only a jpeg copy is shared in iCloud
            # so tell Photos to export the current version in this case
            photos_version = PHOTOS_VERSION_CURRENT
        elif self.photo.has_raw:
            # PhotoKit always returns the raw photo of raw+jpeg pair for PHOTOS_VERSION_ORIGINAL even if JPEG is the original
            photos_version = PHOTOS_VERSION_UNADJUSTED
        else:
            photos_version = PHOTOS_VERSION_ORIGINAL

        uti = (
            self.photo.uti_edited
            if options.edited and self.photo.uti_edited
            else self.photo.uti
        )
        ext = get_preferred_uti_extension(uti)
        dest = dest.parent / f"{dest.stem}.{ext}"

        photolib = PhotoLibrary()
        results = StagedFiles()
        photo = None
        try:
            photo = photolib.fetch_uuid(self.photo.uuid)
        except PhotoKitFetchFailed as e:
            # if failed to find UUID, might be a burst photo
            if self.photo.burst and self.photo._info["burstUUID"]:
                bursts = photolib.fetch_burst_uuid(
                    self.photo._info["burstUUID"], all=True
                )
                # PhotoKit UUIDs may contain "/L0/001" so only look at beginning
                photo = [p for p in bursts if p.uuid.startswith(self.photo.uuid)]
                photo = photo[0] if photo else None
            if not photo:
                results.error.append(
                    (
                        str(dest),
                        f"PhotoKitFetchFailed exception exporting photo {self.photo.uuid}: {e} ({lineno(__file__)})",
                    )
                )
                return results

        # now export the requested version of the photo
        try:
            exported = photo.export(
                dest.parent,
                dest.name,
                version=photos_version,
                overwrite=overwrite,
                video=live_photo,
            )
            if len(exported) == 1:
                results_attr = "edited" if options.edited else "original"
                setattr(results, results_attr, exported[0])
            elif len(exported) == 2:
                for exported_file in exported:
                    if exported_file.lower().endswith(".mov"):
                        # live photo
                        results_attr = (
                            "edited_live" if options.edited else "original_live"
                        )
                    else:
                        results_attr = "edited" if options.edited else "original"
                    setattr(results, results_attr, exported_file)
        except Exception as e:
            results.error.append((str(dest), f"{e} ({lineno(__file__)})"))

        if options.raw_photo and self.photo.has_raw:
            # also request the raw photo
            try:
                exported = photo.export(
                    dest.parent,
                    dest.name,
                    version=photos_version,
                    raw=True,
                    overwrite=overwrite,
                    video=live_photo,
                )
                if exported:
                    results.raw = exported[0]
            except Exception as e:
                results.error.append((str(dest), f"{e} ({lineno(__file__)})"))

        return results

    def _stage_photo_for_export_with_applescript(
        self,
        options: ExportOptions,
    ) -> StagedFiles:
        """Stage a photo for export with AppleScript to a temporary directory

        Note: If exporting an edited live photo, the associated live video will not be exported.
        This is a limitation of the Photos AppleScript interface and Photos behaves the same way."""

        if options.edited and not self.photo.hasadjustments:
            raise ValueError("Edited version requested but photo has no adjustments")

        dest = self._temp_dir_path / self.photo.original_filename
        dest = pathlib.Path(increment_filename(dest))

        # export live_photo .mov file?
        live_photo = bool(options.live_photo and self.photo.live_photo)
        overwrite = options.overwrite or options.update
        edited_version = options.edited or self.photo.shared
        # shared photos (in shared albums) show up as not having adjustments (not edited)
        # but Photos is unable to export the "original" as only a jpeg copy is shared in iCloud
        # so tell Photos to export the current version in this case
        uti = (
            self.photo.uti_edited
            if options.edited and self.photo.uti_edited
            else self.photo.uti
        )
        ext = get_preferred_uti_extension(uti)
        dest = dest.parent / f"{dest.stem}.{ext}"

        results = StagedFiles()

        try:
            exported = _export_photo_uuid_applescript(
                self.photo.uuid,
                dest.parent,
                filestem=dest.stem,
                original=not edited_version,
                edited=edited_version,
                live_photo=live_photo,
                timeout=options.timeout,
                burst=self.photo.burst,
                overwrite=overwrite,
            )
        except ExportError as e:
            results.error.append((str(dest), f"{e} ({lineno(__file__)})"))
            return results

        if len(exported) == 1:
            results_attr = "edited" if options.edited else "original"
            setattr(results, results_attr, exported[0])
        elif len(exported) == 2:
            # could be live or raw+jpeg
            for exported_file in exported:
                if exported_file.lower().endswith(".mov"):
                    # live photo
                    results_attr = (
                        "edited_live"
                        if live_photo and options.edited
                        else "original_live"
                        if live_photo
                        else None
                    )
                elif self.photo.has_raw and pathlib.Path(
                    exported_file.lower()
                ).suffix not in [
                    ".jpg",
                    ".jpeg",
                    ".heic",
                ]:
                    # assume raw photo if not a common non-raw image format
                    results_attr = "raw" if options.raw_photo else None
                else:
                    results_attr = "edited" if options.edited else "original"
                if results_attr:
                    setattr(results, results_attr, exported_file)

        return results

    def _is_temp_file(self, filepath: str) -> bool:
        """Returns True if file is in the PhotosExporter temp directory otherwise False"""
        filepath = pathlib.Path(filepath)
        return filepath.parent == self._temp_dir_path

    def _export_photo(
        self,
        src,
        dest,
        options,
    ):
        """Helper function for export()
            Does the actual copy or hardlink taking the appropriate
            action depending on update, overwrite, export_as_hardlink
            Assumes destination is the right destination (e.g. UUID matches)
            sets UUID and JSON info for exported file using set_uuid_for_file, set_info_for_uuid

        Args:
            src (str): src path
            dest (pathlib.Path): dest path
            options (ExportOptions): options for export

        Returns:
            ExportResults

        Raises:
            ValueError if export_as_hardlink and convert_to_jpeg both True
        """

        if options.export_as_hardlink and options.convert_to_jpeg:
            raise ValueError(
                "export_as_hardlink and convert_to_jpeg cannot both be True"
            )

        if options.export_as_hardlink and self._is_temp_file(src):
            raise ValueError("export_as_hardlink cannot be used with temp files")

        exported_files = []
        update_updated_files = []
        update_new_files = []
        update_skipped_files = []
        touched_files = []
        converted_to_jpeg_files = []

        dest_str = str(dest)
        dest_exists = dest.exists()

        fileutil = options.fileutil
        export_db = options.export_db

        if options.update:  # updating
            cmp_touch, cmp_orig = False, False
            if dest_exists:
                # update, destination exists, but we might not need to replace it...
                if options.ignore_signature:
                    cmp_orig = True
                    cmp_touch = fileutil.cmp(
                        src, dest, mtime1=int(self.photo.date.timestamp())
                    )
                elif options.exiftool:
                    sig_exif = export_db.get_stat_exif_for_file(dest_str)
                    cmp_orig = fileutil.cmp_file_sig(dest_str, sig_exif)
                    sig_exif = (
                        sig_exif[0],
                        sig_exif[1],
                        int(self.photo.date.timestamp()),
                    )
                    cmp_touch = fileutil.cmp_file_sig(dest_str, sig_exif)
                elif options.convert_to_jpeg:
                    sig_converted = export_db.get_stat_converted_for_file(dest_str)
                    cmp_orig = fileutil.cmp_file_sig(dest_str, sig_converted)
                    sig_converted = (
                        sig_converted[0],
                        sig_converted[1],
                        int(self.photo.date.timestamp()),
                    )
                    cmp_touch = fileutil.cmp_file_sig(dest_str, sig_converted)
                else:
                    cmp_orig = fileutil.cmp(src, dest)
                    cmp_touch = fileutil.cmp(
                        src, dest, mtime1=int(self.photo.date.timestamp())
                    )

                sig_cmp = cmp_touch if options.touch_file else cmp_orig

                if options.edited:
                    # requested edited version of photo
                    # need to see if edited version in Photos library has changed
                    # (e.g. it's been edited again)
                    sig_edited = export_db.get_stat_edited_for_file(dest_str)
                    cmp_edited = (
                        fileutil.cmp_file_sig(src, sig_edited)
                        if sig_edited != (None, None, None)
                        else False
                    )
                    sig_cmp = sig_cmp and cmp_edited

                if (options.export_as_hardlink and dest.samefile(src)) or (
                    not options.export_as_hardlink
                    and not dest.samefile(src)
                    and sig_cmp
                ):
                    # destination exists and signatures match, skip it
                    update_skipped_files.append(dest_str)
                elif options.touch_file and cmp_orig and not cmp_touch:
                    # destination exists, signature matches original but does not match expected touch time
                    # skip exporting but update touch time
                    update_skipped_files.append(dest_str)
                    touched_files.append(dest_str)
                elif not options.touch_file and cmp_touch and not cmp_orig:
                    # destination exists, signature matches expected touch but not original
                    # user likely exported with touch_file and is now exporting without touch_file
                    # don't update the file because it's same but leave touch time
                    update_skipped_files.append(dest_str)
                else:
                    # destination exists but is different
                    update_updated_files.append(dest_str)
                    if options.touch_file:
                        touched_files.append(dest_str)
            else:
                # update, destination doesn't exist (new file)
                update_new_files.append(dest_str)
                if options.touch_file:
                    touched_files.append(dest_str)
        else:
            # not update, export the file
            exported_files.append(dest_str)
            if options.touch_file:
                sig = fileutil.file_sig(src)
                sig = (sig[0], sig[1], int(self.photo.date.timestamp()))
                if not fileutil.cmp_file_sig(src, sig):
                    touched_files.append(dest_str)
        if not update_skipped_files:
            converted_stat = (None, None, None)
            edited_stat = (
                fileutil.file_sig(src) if options.edited else (None, None, None)
            )
            if dest_exists and (options.update or options.overwrite):
                # need to remove the destination first
                try:
                    fileutil.unlink(dest)
                except Exception as e:
                    raise ExportError(
                        f"Error removing file {dest}: {e} (({lineno(__file__)})"
                    ) from e
            if options.export_as_hardlink:
                try:
                    fileutil.hardlink(src, dest)
                except Exception as e:
                    raise ExportError(
                        f"Error hardlinking {src} to {dest}: {e} ({lineno(__file__)})"
                    ) from e
            elif options.convert_to_jpeg:
                # use convert_to_jpeg to export the file
                fileutil.convert_to_jpeg(
                    src, dest_str, compression_quality=options.jpeg_quality
                )
                converted_stat = fileutil.file_sig(dest_str)
                converted_to_jpeg_files.append(dest_str)
            else:
                try:
                    fileutil.copy(src, dest_str)
                except Exception as e:
                    raise ExportError(
                        f"Error copying file {src} to {dest_str}: {e} ({lineno(__file__)})"
                    ) from e

            export_db.set_data(
                filename=dest_str,
                uuid=self.photo.uuid,
                orig_stat=fileutil.file_sig(dest_str),
                exif_stat=(None, None, None),
                converted_stat=converted_stat,
                edited_stat=edited_stat,
                info_json=self.photo.json(),
                exif_json=None,
            )

        if touched_files:
            ts = int(self.photo.date.timestamp())
            fileutil.utime(dest, (ts, ts))

        return ExportResults(
            exported=exported_files + update_new_files + update_updated_files,
            new=update_new_files,
            updated=update_updated_files,
            skipped=update_skipped_files,
            touched=touched_files,
            converted_to_jpeg=converted_to_jpeg_files,
        )

    def _write_sidecar_files(
        self,
        dest: pathlib.Path,
        options: ExportOptions,
    ) -> ExportResults:
        """Write sidecar files for the photo."""

        export_db = options.export_db
        fileutil = options.fileutil
        verbose = options.verbose or self._verbose

        # export metadata
        sidecars = []
        sidecar_json_files_skipped = []
        sidecar_json_files_written = []
        sidecar_exiftool_files_skipped = []
        sidecar_exiftool_files_written = []
        sidecar_xmp_files_skipped = []
        sidecar_xmp_files_written = []

        dest_suffix = "" if options.sidecar_drop_ext else dest.suffix
        if options.sidecar & SIDECAR_JSON:
            sidecar_filename = dest.parent / pathlib.Path(
                f"{dest.stem}{dest_suffix}.json"
            )
            sidecar_str = self._exiftool_json_sidecar(
                filename=dest.name, options=options
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
            sidecar_str = self._exiftool_json_sidecar(
                tag_groups=False, filename=dest.name, options=options
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
            sidecar_str = self._xmp_sidecar(
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
            old_sidecar_digest, sidecar_sig = export_db.get_sidecar_for_file(
                sidecar_filename
            )
            write_sidecar = (
                not options.update
                or (options.update and not sidecar_filename.exists())
                or (
                    options.update
                    and (sidecar_digest != old_sidecar_digest)
                    or not fileutil.cmp_file_sig(sidecar_filename, sidecar_sig)
                )
            )
            if write_sidecar:
                verbose(f"Writing {sidecar_type} sidecar {sidecar_filename}")
                files_written.append(str(sidecar_filename))
                if not options.dry_run:
                    self._write_sidecar(sidecar_filename, sidecar_str)
                    export_db.set_sidecar_for_file(
                        sidecar_filename,
                        sidecar_digest,
                        fileutil.file_sig(sidecar_filename),
                    )
            else:
                verbose(f"Skipped up to date {sidecar_type} sidecar {sidecar_filename}")
                files_skipped.append(str(sidecar_filename))

        return ExportResults(
            sidecar_json_written=sidecar_json_files_written,
            sidecar_json_skipped=sidecar_json_files_skipped,
            sidecar_exiftool_written=sidecar_exiftool_files_written,
            sidecar_exiftool_skipped=sidecar_exiftool_files_skipped,
            sidecar_xmp_written=sidecar_xmp_files_written,
            sidecar_xmp_skipped=sidecar_xmp_files_skipped,
        )

    def _write_exif_metadata_to_files(
        self,
        exported_file: str,
        options: ExportOptions,
    ) -> ExportResults:
        """Write exif metadata to files using exiftool."""

        export_db = options.export_db
        fileutil = options.fileutil
        verbose = options.verbose or self._verbose

        results = ExportResults()
        if options.update:
            files_are_different = False
            old_data = export_db.get_exifdata_for_file(exported_file)
            if old_data is not None:
                old_data = json.loads(old_data)[0]
                current_data = json.loads(self._exiftool_json_sidecar(options=options))[
                    0
                ]
                if old_data != current_data:
                    files_are_different = True

            if old_data is None or files_are_different:
                # didn't have old data, assume we need to write it
                # or files were different
                verbose(f"Writing metadata with exiftool for {exported_file}")
                if not options.dry_run:
                    warning_, error_ = self._write_exif_data(
                        exported_file, options=options
                    )
                    if warning_:
                        results.exiftool_warning.append((exported_file, warning_))
                    if error_:
                        results.exiftool_error.append((exported_file, error_))
                        results.error.append((exported_file, error_))

                export_db.set_exifdata_for_file(
                    exported_file, self._exiftool_json_sidecar(options=options)
                )
                export_db.set_stat_exif_for_file(
                    exported_file, fileutil.file_sig(exported_file)
                )
                results.exif_updated.append(exported_file)
            else:
                verbose(f"Skipped up to date exiftool metadata for {exported_file}")
        else:
            verbose(f"Writing metadata with exiftool for {exported_file}")
            if not options.dry_run:
                warning_, error_ = self._write_exif_data(exported_file, options=options)
                if warning_:
                    results.exiftool_warning.append((exported_file, warning_))
                if error_:
                    results.exiftool_error.append((exported_file, error_))
                    results.error.append((exported_file, error_))

            export_db.set_exifdata_for_file(
                exported_file, self._exiftool_json_sidecar(options=options)
            )
            export_db.set_stat_exif_for_file(
                exported_file, fileutil.file_sig(exported_file)
            )
            results.exif_updated.append(exported_file)
        return results

    def _write_exif_data(self, filepath: str, options: ExportOptions):
        """write exif data to image file at filepath

        Args:
            filepath: full path to the image file

        Returns:
            (warning, error) of warning and error strings if exiftool produces warnings or errors
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Could not find file {filepath}")
        exif_info = self._exiftool_dict(options=options)

        with ExifTool(
            filepath,
            flags=options.exiftool_flags,
            exiftool=self.photo._db._exiftool_path,
        ) as exiftool:
            for exiftag, val in exif_info.items():
                if type(val) == list:
                    for v in val:
                        exiftool.setvalue(exiftag, v)
                else:
                    exiftool.setvalue(exiftag, val)
        return exiftool.warning, exiftool.error

    def _exiftool_dict(
        self, options: Optional[ExportOptions] = None, filename: Optional[str] = None
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
            QuickTime:CreateDate (UTC)
            QuickTime:ModifyDate (UTC)
            QuickTime:GPSCoordinates
            UserData:GPSCoordinates

        Reference:
            https://iptc.org/std/photometadata/specification/IPTC-PhotoMetadata-201610_1.pdf
        """

        options = options or ExportOptions()

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
                    logging.warning(
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
                self._verbose(
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

        # if self.favorite():
        #     exif["Rating"] = 5

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

    def _get_exif_keywords(self):
        """returns list of keywords found in the file's exif metadata"""
        keywords = []
        exif = self.photo.exiftool
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
        exif = self.photo.exiftool
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

    def _exiftool_json_sidecar(
        self,
        options: Optional[ExportOptions] = None,
        tag_groups: bool = True,
        filename: Optional[str] = None,
    ):
        """Return dict of EXIF details for building exiftool JSON sidecar or sending commands to ExifTool.
            Does not include all the EXIF fields as those are likely already in the image.

        Args:
            options (ExportOptions): options for export
            tag_groups (bool, default=True): if True, include tag groups in the output
            filename (str): name of source image file (without path); if not None, exiftool JSON signature will be included; if None, signature will not be included

        Returns: dict with exiftool tags / values

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

        options = options or ExportOptions()
        exif = self._exiftool_dict(filename=filename, options=options)

        if not tag_groups:
            # strip tag groups
            exif_new = {}
            for k, v in exif.items():
                k = re.sub(r".*:", "", k)
                exif_new[k] = v
            exif = exif_new

        return json.dumps([exif])

    def _xmp_sidecar(
        self, options: Optional[ExportOptions] = None, extension: Optional[str] = None
    ):
        """returns string for XMP sidecar

        Args:
            options (ExportOptions): options for export
            extension (Optional[str]): which extension to use for SidecarForExtension property
        """

        options = options or ExportOptions()

        xmp_template_file = (
            _XMP_TEMPLATE_NAME if not self.photo._db._beta else _XMP_TEMPLATE_NAME_BETA
        )
        xmp_template = Template(filename=os.path.join(_TEMPLATE_DIR, xmp_template_file))

        if extension is None:
            extension = pathlib.Path(self.photo.original_filename)
            extension = extension.suffix[1:] if extension.suffix else None

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
        else:
            description = (
                self.photo.description if self.photo.description is not None else ""
            )

        keyword_list = []
        if options.merge_exif_keywords:
            keyword_list.extend(self._get_exif_keywords())

        if self.photo.keywords and not options.replace_keywords:
            keyword_list.extend(self.photo.keywords)

        # TODO: keyword handling in this and _exiftool_json_sidecar is
        # good candidate for pulling out in a function

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
                    logging.warning(
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

        xmp_str = xmp_template.render(
            photo=self.photo,
            description=description,
            keywords=keyword_list,
            persons=person_list,
            subjects=subject_list,
            extension=extension,
            location=latlon,
            version=__version__,
        )

        # remove extra lines that mako inserts from template
        xmp_str = "\n".join(line for line in xmp_str.split("\n") if line.strip() != "")
        return xmp_str

    def _write_sidecar(self, filename, sidecar_str):
        """write sidecar_str to filename
        used for exporting sidecar info"""
        if not (filename or sidecar_str):
            raise (
                ValueError(
                    f"filename {filename} and sidecar_str {sidecar_str} must not be None"
                )
            )

        # TODO: catch exception?
        f = open(filename, "w")
        f.write(sidecar_str)
        f.close()


def hexdigest(strval):
    """hexdigest of a string, using blake2b"""
    h = hashlib.blake2b(digest_size=20)
    h.update(bytes(strval, "utf-8"))
    return h.hexdigest()


def _export_photo_uuid_applescript(
    uuid,
    dest,
    filestem=None,
    original=True,
    edited=False,
    live_photo=False,
    timeout=120,
    burst=False,
    dry_run=False,
    overwrite=False,
):
    """Export photo to dest path using applescript to control Photos
    If photo is a live photo, exports both the photo and associated .mov file

    Args:
        uuid: UUID of photo to export
        dest: destination path to export to
        filestem: (string) if provided, exported filename will be named stem.ext
                where ext is extension of the file exported by photos (e.g. .jpeg, .mov, etc)
                If not provided, file will be named with whatever name Photos uses
                If filestem.ext exists, it wil be overwritten
        original: (boolean) if True, export original image; default = True
        edited: (boolean) if True, export edited photo; default = False
                If photo not edited and edited=True, will still export the original image
                caller must verify image has been edited
        *Note*: must be called with either edited or original but not both,
                will raise error if called with both edited and original = True
        live_photo: (boolean) if True, export associated .mov live photo; default = False
        timeout: timeout value in seconds; export will fail if applescript run time exceeds timeout
        burst: (boolean) set to True if file is a burst image to avoid Photos export error
        dry_run: (boolean) set to True to run in "dry run" mode which will download file but not actually copy to destination

    Returns: list of paths to exported file(s) or None if export failed

    Raises: ExportError if error during export

    Note: For Live Photos, if edited=True, will export a jpeg but not the movie, even if photo
          has not been edited. This is due to how Photos Applescript interface works.
    """

    dest = pathlib.Path(dest)
    if not dest.is_dir():
        raise ValueError(f"dest {dest} must be a directory")

    if not original ^ edited:
        raise ValueError(f"edited or original must be True but not both")

    tmpdir = tempfile.TemporaryDirectory(prefix="osxphotos_")

    exported_files = []
    filename = None
    try:
        # I've seen intermittent failures with the PhotoScript export so retry if
        # export doesn't return anything
        retries = 0
        while not exported_files and retries < MAX_PHOTOSCRIPT_RETRIES:
            photo = photoscript.Photo(uuid)
            filename = photo.filename
            exported_files = photo.export(
                tmpdir.name, original=original, timeout=timeout
            )
            retries += 1
    except Exception as e:
        raise ExportError(e)

    if not exported_files or not filename:
        # nothing got exported
        raise ExportError(f"Could not export photo {uuid} ({lineno(__file__)})")

    # need to find actual filename as sometimes Photos renames JPG to jpeg on export
    # may be more than one file exported (e.g. if Live Photo, Photos exports both .jpeg and .mov)
    # TemporaryDirectory will cleanup on return
    filename_stem = pathlib.Path(filename).stem
    exported_paths = []
    for fname in exported_files:
        path = pathlib.Path(tmpdir.name) / fname
        if len(exported_files) > 1 and not live_photo and path.suffix.lower() == ".mov":
            # it's the .mov part of live photo but not requested, so don't export
            continue
        if len(exported_files) > 1 and burst and path.stem != filename_stem:
            # skip any burst photo that's not the one we asked for
            continue
        if filestem:
            # rename the file based on filestem, keeping original extension
            dest_new = dest / f"{filestem}{path.suffix}"
        else:
            # use the name Photos provided
            dest_new = dest / path.name
        if not dry_run:
            if overwrite and dest_new.exists():
                FileUtil.unlink(dest_new)
            FileUtil.copy(str(path), str(dest_new))
        exported_paths.append(str(dest_new))
    return exported_paths


def _check_export_suffix(src, dest, edited):
    """Helper function for exporting photos to check file extensions of destination path.

    Checks that dst file extension is appropriate for the src.
    If edited=True, will use src file extension of ".jpeg" if None provided for src.

    Args:
        src: path to source file or None.
        dest: path to destination file.
        edited: set to True if exporting an edited photo.

    Returns:
        True if src and dest extensions are OK, else False.

    Raises:
        ValueError if edited is False and src is None
    """

    # check extension of destination
    if src is not None:
        # use suffix from edited file
        actual_suffix = pathlib.Path(src).suffix
    elif edited:
        # use .jpeg as that's probably correct
        actual_suffix = ".jpeg"
    else:
        raise ValueError("src must not be None if edited=False")

    # Photo's often converts .JPG to .jpeg or .tif to .tiff on import
    dest_ext = dest.suffix.lower()
    actual_ext = actual_suffix.lower()
    suffixes = sorted([dest_ext, actual_ext])
    return (
        dest_ext == actual_ext
        or suffixes == [".jpeg", ".jpg"]
        or suffixes == [".tif", ".tiff"]
    )


def rename_jpeg_files(files, jpeg_ext, fileutil):
    """rename any jpeg files in files so that extension matches jpeg_ext

    Args:
        files: list of file paths
        jpeg_ext: extension to use for jpeg files found in files, e.g. "jpg"
        fileutil: a FileUtil object

    Returns:
        list of files with updated names

    Note: If non-jpeg files found, they will be ignore and returned in the return list
    """
    jpeg_ext = "." + jpeg_ext
    jpegs = [".jpeg", ".jpg"]
    new_files = []
    for file in files:
        path = pathlib.Path(file)
        if path.suffix.lower() in jpegs and path.suffix != jpeg_ext:
            new_file = path.parent / (path.stem + jpeg_ext)
            fileutil.rename(file, new_file)
            new_files.append(new_file)
        else:
            new_files.append(file)
    return new_files
