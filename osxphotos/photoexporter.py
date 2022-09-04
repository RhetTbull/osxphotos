""" PhotoExport class to export photos
"""

import dataclasses
import json
import logging
import os
import pathlib
import re
import typing as t
from collections import namedtuple  # pylint: disable=syntax-error
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum

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
from .exiftool import ExifTool, exiftool_can_write
from .export_db import ExportDB, ExportDBTemp
from .fileutil import FileUtil
from .photokit import (
    PHOTOS_VERSION_CURRENT,
    PHOTOS_VERSION_ORIGINAL,
    PHOTOS_VERSION_UNADJUSTED,
    PhotoKitFetchFailed,
    PhotoLibrary,
)
from .phototemplate import RenderOptions
from .rich_utils import add_rich_markup_tag
from .uti import get_preferred_uti_extension
from .utils import (
    hexdigest,
    increment_filename,
    increment_filename_with_count,
    lineno,
    list_directory,
)

__all__ = [
    "ExportError",
    "ExportOptions",
    "ExportResults",
    "PhotoExporter",
    "rename_jpeg_files",
]

if t.TYPE_CHECKING:
    from .photoinfo import PhotoInfo

# retry if download_missing/use_photos_export fails the first time (which sometimes it does)
MAX_PHOTOSCRIPT_RETRIES = 3

# return values for _should_update_photo
class ShouldUpdate(Enum):
    NOT_IN_DATABASE = 1
    HARDLINK_DIFFERENT_FILES = 2
    NOT_HARDLINK_SAME_FILES = 3
    DEST_SIG_DIFFERENT = 4
    EXPORT_OPTIONS_DIFFERENT = 5
    EXIFTOOL_DIFFERENT = 6
    EDITED_SIG_DIFFERENT = 7
    DIGEST_DIFFERENT = 8


class ExportError(Exception):
    """error during export"""

    pass


@dataclass
class ExportOptions:
    """Options class for exporting photos with export

    Attributes:
        convert_to_jpeg (bool): if True, converts non-jpeg images to jpeg
        description_template (str): t.Optional template string that will be rendered for use as photo description
        download_missing: (bool, default=False): if True will attempt to export photo via applescript interaction with Photos if missing (see also use_photokit, use_photos_export)
        dry_run: (bool, default=False): set to True to run in "dry run" mode
        edited: (bool, default=False): if True will export the edited version of the photo otherwise exports the original version
        exiftool_flags (list of str): t.Optional list of flags to pass to exiftool when using exiftool option, e.g ["-m", "-F"]
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
        preview_suffix (str): t.Optional string to append to end of filename for preview images
        preview (bool): if True, also exports preview image
        raw_photo (bool, default=False): if True, will also export the associated RAW photo
        render_options (RenderOptions): t.Optional osxphotos.phototemplate.RenderOptions instance to specify options for rendering templates
        replace_keywords (bool): if True, keyword_template replaces any keywords, otherwise it's additive
        rich (bool): if True, will use rich markup with verbose output
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
        use_albums_as_keywords (bool, default = False): if True, will include album names in keywords when exporting metadata with exiftool or sidecar
        use_persons_as_keywords (bool, default = False): if True, will include person names in keywords when exporting metadata with exiftool or sidecar
        use_photos_export (bool, default=False): if True will attempt to export photo via applescript interaction with Photos even if not missing (see also use_photokit, download_missing)
        use_photokit (bool, default=False): if True, will use photokit to export photos when use_photos_export is True
        verbose (callable): optional callable function to use for printing verbose text during processing; if None (default), does not print output.
        tmpdir: (str, default=None): Optional directory to use for temporary files, if None (default) uses system tmp directory
        favorite_rating (bool): if True, set XMP:Rating=5 for favorite images and XMP:Rating=0 for non-favorites

    """

    convert_to_jpeg: bool = False
    description_template: t.Optional[str] = None
    download_missing: bool = False
    dry_run: bool = False
    edited: bool = False
    exiftool_flags: t.Optional[t.List] = None
    exiftool: bool = False
    export_as_hardlink: bool = False
    export_db: t.Optional[ExportDB] = None
    face_regions: bool = True
    fileutil: t.Optional[FileUtil] = None
    force_update: bool = False
    ignore_date_modified: bool = False
    ignore_signature: bool = False
    increment: bool = True
    jpeg_ext: t.Optional[str] = None
    jpeg_quality: float = 1.0
    keyword_template: t.Optional[t.List[str]] = None
    live_photo: bool = False
    location: bool = True
    merge_exif_keywords: bool = False
    merge_exif_persons: bool = False
    overwrite: bool = False
    persons: bool = True
    preview_suffix: str = DEFAULT_PREVIEW_SUFFIX
    preview: bool = False
    raw_photo: bool = False
    render_options: t.Optional[RenderOptions] = None
    replace_keywords: bool = False
    rich: bool = False
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
    verbose: t.Optional[t.Callable] = None
    tmpdir: t.Optional[str] = None
    favorite_rating: bool = False

    def asdict(self):
        return asdict(self)

    @property
    def bit_flags(self):
        """Return bit flags representing options that affect export"""
        # currently only exiftool makes a difference
        return self.exiftool << 1


class StagedFiles:
    """Represents files staged for export"""

    def __init__(
        self,
        original: t.Optional[str] = None,
        original_live: t.Optional[str] = None,
        edited: t.Optional[str] = None,
        edited_live: t.Optional[str] = None,
        preview: t.Optional[str] = None,
        raw: t.Optional[str] = None,
        error: t.Optional[t.List[str]] = None,
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
    """Results class which holds export results for export"""

    __slots__ = [
        "_datetime",
        "converted_to_jpeg",
        "deleted_directories",
        "deleted_files",
        "error",
        "exif_updated",
        "exiftool_error",
        "exiftool_warning",
        "exported",
        "exported_album",
        "metadata_changed",
        "missing",
        "missing_album",
        "new",
        "sidecar_exiftool_skipped",
        "sidecar_exiftool_written",
        "sidecar_json_skipped",
        "sidecar_json_written",
        "sidecar_xmp_skipped",
        "sidecar_xmp_written",
        "skipped",
        "skipped_album",
        "to_touch",
        "touched",
        "updated",
        "xattr_skipped",
        "xattr_written",
    ]

    def __init__(
        self,
        converted_to_jpeg=None,
        deleted_directories=None,
        deleted_files=None,
        error=None,
        exif_updated=None,
        exiftool_error=None,
        exiftool_warning=None,
        exported=None,
        exported_album=None,
        metadata_changed=None,
        missing=None,
        missing_album=None,
        new=None,
        sidecar_exiftool_skipped=None,
        sidecar_exiftool_written=None,
        sidecar_json_skipped=None,
        sidecar_json_written=None,
        sidecar_xmp_skipped=None,
        sidecar_xmp_written=None,
        skipped=None,
        skipped_album=None,
        to_touch=None,
        touched=None,
        updated=None,
        xattr_skipped=None,
        xattr_written=None,
    ):

        local_vars = locals()
        self._datetime = datetime.now().isoformat()
        for attr in self.attributes:
            setattr(self, attr, local_vars.get(attr) or [])

    @property
    def attributes(self) -> t.List[str]:
        """Return list of attributes tracked by ExportResults"""
        return [attr for attr in self.__slots__ if not attr.startswith("_")]

    @property
    def datetime(self) -> str:
        """Return datetime when ExportResults was created"""
        return self._datetime

    def all_files(self) -> t.List[str]:
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

        return list(set(files))

    def __iadd__(self, other) -> "ExportResults":
        if type(other) != ExportResults:
            raise TypeError("Can only add ExportResults to ExportResults")

        for attribute in self.attributes:
            setattr(
                self, attribute, getattr(self, attribute) + getattr(other, attribute)
            )
        return self

    def __str__(self) -> str:
        return (
            "ExportResults("
            + f"datetime={self._datetime}, "
            + ", ".join([f"{attr}={getattr(self, attr)}" for attr in self.attributes])
            + ")"
        )


class PhotoExporter:
    """Export a photo"""

    def __init__(self, photo: "PhotoInfo", tmpdir: t.Optional[str] = None):
        self.photo = photo
        self._render_options = RenderOptions()
        self._verbose = self.photo._verbose

        # define functions for adding markup
        self._filepath = add_rich_markup_tag("filepath", rich=False)
        self._filename = add_rich_markup_tag("filename", rich=False)
        self._uuid = add_rich_markup_tag("uuid", rich=False)
        self._num = add_rich_markup_tag("num", rich=False)

        # temp directory for staging downloaded missing files
        self._temp_dir = None
        self._temp_dir_path = None
        self.fileutil = FileUtil

    def export(
        self,
        dest,
        filename=None,
        options: t.Optional[ExportOptions] = None,
    ) -> ExportResults:
        """Export photo

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
            options (`ExportOptions`): t.Optional ExportOptions instance

        Returns:
            ExportResults instance

        Note:
            To use dry run mode, you must set options.dry_run=True and also pass in memory version of export_db,
              and no-op fileutil (e.g. `ExportDBInMemory` and `FileUtilNoOp`) in options.export_db and options.fileutil respectively
        """

        options = options or ExportOptions()

        # temp dir must be initialized before any of the methods called by export() are called
        self._init_temp_dir(options)

        verbose = options.verbose or self._verbose
        if verbose and not callable(verbose):
            raise TypeError("verbose must be callable")

        # define functions for adding markup
        self._filepath = add_rich_markup_tag("filepath", rich=options.rich)
        self._filename = add_rich_markup_tag("filename", rich=options.rich)
        self._uuid = add_rich_markup_tag("uuid", rich=options.rich)
        self._num = add_rich_markup_tag("num", rich=options.rich)

        # can't use export_as_hardlink with download_missing, use_photos_export as can't hardlink the temporary files downloaded
        if options.export_as_hardlink and options.download_missing:
            raise ValueError(
                "Cannot use export_as_hardlink with download_missing or use_photos_export"
            )

        # when called from export(), won't get an export_db, so use temp version
        options.export_db = options.export_db or ExportDBTemp()

        # ensure there's a FileUtil class to use
        options.fileutil = options.fileutil or FileUtil
        self.fileutil = options.fileutil

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
        dest, options = self._should_convert_to_jpeg(dest, options)

        # stage files for export by finding path in local library or downloading from iCloud as appropriate
        staged_files = self._stage_photos_for_export(options)
        src = staged_files.edited if options.edited else staged_files.original

        # get the right destination path depending on options.update, etc.
        dest = self._get_dest_path(dest, options)

        self._render_options.filepath = str(dest)
        all_results = ExportResults()

        if src:
            # export the dest file
            all_results += self._export_photo(
                src,
                dest,
                options=options,
            )
        else:
            verbose(
                f"Skipping missing {'edited' if options.edited else 'original'} photo {self._filename(self.photo.original_filename)} ({self._uuid(self.photo.uuid)})"
            )
            all_results.missing.append(dest)

        # copy live photo associated .mov if requested
        if export_original and options.live_photo and self.photo.live_photo:
            live_name = dest.parent / f"{dest.stem}.mov"
            if staged_files.original_live:
                src_live = staged_files.original_live
                all_results += self._export_photo(
                    src_live,
                    live_name,
                    # don't try to convert the live photo
                    options=dataclasses.replace(options, convert_to_jpeg=False),
                )
            else:
                verbose(
                    f"Skipping missing live photo for {self._filename(self.photo.original_filename)} ({self._uuid(self.photo.uuid)})"
                )
                all_results.missing.append(live_name)

        if export_edited and options.live_photo and self.photo.live_photo:
            live_name = dest.parent / f"{dest.stem}.mov"
            if staged_files.edited_live:
                src_live = staged_files.edited_live
                all_results += self._export_photo(
                    src_live,
                    live_name,
                    # don't try to convert the live photo
                    options=dataclasses.replace(options, convert_to_jpeg=False),
                )
            else:
                verbose(
                    f"Skipping missing edited live photo for {self._filename(self.photo.original_filename)} ({self._uuid(self.photo.uuid)})"
                )
                all_results.missing.append(live_name)

        # copy associated RAW image if requested
        if options.raw_photo and self.photo.has_raw:
            if staged_files.raw:
                raw_path = pathlib.Path(staged_files.raw)
                raw_ext = raw_path.suffix
                raw_name = dest.parent / f"{dest.stem}{raw_ext}"
                all_results += self._export_photo(
                    raw_path,
                    raw_name,
                    options=options,
                )
            else:
                # guess at most likely raw name
                raw_ext = get_preferred_uti_extension(self.photo.uti_raw) or "raw"
                raw_name = dest.parent / f"{dest.stem}.{raw_ext}"
                all_results.missing.append(raw_name)
                verbose(
                    f"Skipping missing raw photo for {self._filename(self.photo.original_filename)} ({self._uuid(self.photo.uuid)})"
                )

        # copy preview image if requested
        if options.preview:
            if staged_files.preview:
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
                    if any([options.overwrite, options.update, options.force_update])
                    else pathlib.Path(increment_filename(preview_name))
                )
                all_results += self._export_photo(
                    preview_path,
                    preview_name,
                    options=options,
                )
            else:
                # don't know what actual preview suffix would be but most likely jpeg
                preview_name = dest.parent / f"{dest.stem}{options.preview_suffix}.jpeg"
                all_results.missing.append(preview_name)
                verbose(
                    f"Skipping missing preview photo for {self._filename(self.photo.original_filename)} ({self._uuid(self.photo.uuid)})"
                )

        all_results += self._write_sidecar_files(dest=dest, options=options)

        return all_results

    def _init_temp_dir(self, options: ExportOptions):
        """Initialize (if necessary) the object's temporary directory.

        Args:
            options: ExportOptions object
        """
        if self._temp_dir is not None:
            return

        fileutil = options.fileutil or FileUtil
        self._temp_dir = fileutil.tmpdir(prefix="osxphotos_export_", dir=options.tmpdir)
        self._temp_dir_path = pathlib.Path(self._temp_dir.name)
        return

    def _touch_files(
        self, touch_files: t.List, options: ExportOptions
    ) -> ExportResults:
        """touch file date/time to match photo creation date/time; only touches files if needed"""
        fileutil = options.fileutil
        touch_results = []
        for touch_file in set(touch_files):
            ts = int(self.photo.date.timestamp())
            try:
                stat = os.stat(touch_file)
                if stat.st_mtime != ts:
                    fileutil.utime(touch_file, (ts, ts))
                    touch_results.append(touch_file)
            except FileNotFoundError as e:
                # ignore errors if in dry_run as file may not be present
                if not options.dry_run:
                    raise e from e
        return ExportResults(touched=touch_results)

    def _get_edited_filename(self, original_filename):
        """Return the filename for the exported edited photo
        (used when filename isn't provided in call to export)"""
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

    def _get_dest_path(
        self, dest: pathlib.Path, options: ExportOptions
    ) -> pathlib.Path:
        """If destination exists find match in ExportDB, on disk, or add (1), (2), and so on to filename to get a valid destination

        Args:
            dest (str): destination path
            options (ExportOptions): Export options

        Returns:
            new dest path (pathlib.Path)
        """

        # if overwrite==False and #increment==False, export should fail if file exists
        if dest.exists() and not any(
            [options.increment, options.update, options.force_update, options.overwrite]
        ):
            raise FileExistsError(
                f"destination exists ({dest}); overwrite={options.overwrite}, increment={options.increment}"
            )

        # if overwrite, we don't care if the file exists or not
        if options.overwrite:
            return dest

        # if not update or overwrite, check to see if file exists and if so, add (1), (2), etc
        # until we find one that works
        # Photos checks the stem and adds (1), (2), etc which avoids collision with sidecars
        # e.g. exporting sidecar for file1.png and file1.jpeg
        # if file1.png exists and exporting file1.jpeg,
        # dest will be file1 (1).jpeg even though file1.jpeg doesn't exist to prevent sidecar collision
        if options.increment and not any(
            [options.update, options.force_update, options.overwrite]
        ):
            return pathlib.Path(increment_filename(dest))

        # if update and file exists, need to check to see if it's the right file by checking export db
        if options.update or options.force_update:
            export_db = options.export_db
            dest_uuid = export_db.get_uuid_for_file(dest)
            if dest_uuid is None and not dest.exists():
                # destination doesn't exist in export db and doesn't exist on disk
                # so we can just use it
                return dest

            if dest_uuid == self.photo.uuid:
                # destination is the right file
                return dest

            # either dest_uuid is wrong or file exists and there's no associated UUID, so find a name that matches
            # or create a new name if no match
            # find files that match "dest_name (*.ext" (e.g. "dest_name (1).jpg", "dest_name (2).jpg)", ...)
            # first, find all matching files in export db and see if there's a match
            if dest_target := export_db.get_target_for_file(self.photo.uuid, dest):
                # there's a match so use that
                return pathlib.Path(dest_target)

            # no match so need to create a new name
            # increment the destination file until we find one that doesn't exist and doesn't match another uuid in the database
            count = 0
            dest, count = increment_filename_with_count(dest, count)
            count += 1
            while export_db.get_uuid_for_file(dest) is not None:
                dest, count = increment_filename_with_count(dest, count)
            return pathlib.Path(dest)

        # fail safe...I can't think of a case that gets here
        return dest

    def _should_update_photo(
        self, src: pathlib.Path, dest: pathlib.Path, options: ExportOptions
    ) -> t.Literal[True, False]:
        """Return True if photo should be updated, else False"""
        export_db = options.export_db
        fileutil = options.fileutil

        file_record = export_db.get_file_record(dest)

        if not file_record:
            # photo doesn't exist in database, should update
            return ShouldUpdate.NOT_IN_DATABASE

        if options.export_as_hardlink and not dest.samefile(src):
            # different files, should update
            return ShouldUpdate.HARDLINK_DIFFERENT_FILES

        if not options.export_as_hardlink and dest.samefile(src):
            # same file but not exporting as hardlink, should update
            return ShouldUpdate.NOT_HARDLINK_SAME_FILES

        if not options.ignore_signature and not fileutil.cmp_file_sig(
            dest, file_record.dest_sig
        ):
            # destination file doesn't match what was last exported
            return ShouldUpdate.DEST_SIG_DIFFERENT

        if file_record.export_options != options.bit_flags:
            # exporting with different set of options (e.g. exiftool), should update
            # need to check this before exiftool in case exiftool options are different
            # and export database is missing; this will always be True if database is missing
            # as it'll be None and bit_flags will be an int
            return ShouldUpdate.EXPORT_OPTIONS_DIFFERENT

        if options.exiftool:
            current_exifdata = self.exiftool_json_sidecar(options=options)
            rv = current_exifdata != file_record.exifdata
            # if using exiftool, don't need to continue checking edited below
            # as exiftool will be used to update edited file
            return ShouldUpdate.EXIFTOOL_DIFFERENT if rv else False

        if options.edited and not fileutil.cmp_file_sig(src, file_record.src_sig):
            # edited file in Photos doesn't match what was last exported
            return ShouldUpdate.EDITED_SIG_DIFFERENT

        if options.force_update:
            current_digest = self.photo.hexdigest
            if current_digest != file_record.digest:
                # metadata in Photos changed, force update
                return ShouldUpdate.DIGEST_DIFFERENT

        # photo should not be updated
        return False

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

        overwrite = any([options.overwrite, options.update, options.force_update])

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

        if options.preview and self.photo.path_derivatives:
            results.preview = self.photo.path_derivatives[0]

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
        overwrite = any([options.overwrite, options.update, options.force_update])
        edited_version = bool(options.edited or self.photo.shared)
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
            exported = self._export_photo_uuid_applescript(
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

        if options.preview and self.photo.path_derivatives:
            results.preview = self.photo.path_derivatives[0]

        return results

    def _should_convert_to_jpeg(
        self, dest: pathlib.Path, options: ExportOptions
    ) -> t.Tuple[pathlib.Path, ExportOptions]:
        """Determine if a file really should be converted to jpeg or not
        and return the new destination and ExportOptions instance with the convert_to_jpeg flag set appropriately
        """
        if not (options.convert_to_jpeg and self.photo.isphoto):
            # nothing to convert
            return dest, dataclasses.replace(options, convert_to_jpeg=False)

        convert_to_jpeg = False
        ext = "." + options.jpeg_ext if options.jpeg_ext else ".jpeg"
        if not options.edited and self.photo.uti_original != "public.jpeg":
            # not a jpeg but will convert to jpeg upon export so fix file extension
            convert_to_jpeg = True
            dest = dest.parent / f"{dest.stem}{ext}"
        elif options.edited and self.photo.uti != "public.jpeg":
            # in Big Sur+, edited HEICs are HEIC
            convert_to_jpeg = True
            dest = dest.parent / f"{dest.stem}{ext}"
        return dest, dataclasses.replace(options, convert_to_jpeg=convert_to_jpeg)

    def _is_temp_file(self, filepath: str) -> bool:
        """Returns True if file is in the PhotosExporter temp directory otherwise False"""
        filepath = pathlib.Path(filepath)
        return filepath.parent == self._temp_dir_path

    def _copy_to_temp_file(self, filepath: str) -> str:
        """Copies filepath to a temp file preserving access and modification times"""
        filepath = pathlib.Path(filepath)
        dest = self._temp_dir_path / filepath.name
        dest = increment_filename(dest)
        self.fileutil.copy(filepath, dest)
        stat = os.stat(filepath)
        self.fileutil.utime(dest, (stat.st_atime, stat.st_mtime))
        return str(dest)

    def _export_photo(
        self,
        src: str,
        dest: pathlib.Path,
        options: ExportOptions,
    ):
        """Helper function for export()
            Does the actual copy or hardlink taking the appropriate
            action depending on update, overwrite, export_as_hardlink
            Assumes destination is the right destination (e.g. UUID matches)
            Sets UUID and JSON info for exported file using set_uuid_for_file, set_info_for_uuid
            Expects that src is a temporary file (as set by _stage_photos_for_export) and
            may modify the src (e.g. for convert_to_jpeg or exiftool)

        Args:
            src (str): src path
            dest (pathlib.Path): dest path
            options (ExportOptions): options for export

        Returns:
            ExportResults

        Raises:
            ValueError if export_as_hardlink and convert_to_jpeg both True
        """

        verbose = options.verbose or self._verbose
        if options.export_as_hardlink and options.convert_to_jpeg:
            raise ValueError(
                "export_as_hardlink and convert_to_jpeg cannot both be True"
            )

        if options.export_as_hardlink and self._is_temp_file(src):
            raise ValueError("export_as_hardlink cannot be used with temp files")

        exported_files = []
        update_updated_files = []
        update_new_files = []
        update_skipped_files = []  # skip files that are already up to date
        converted_to_jpeg_files = []
        exif_results = ExportResults()

        dest_str = str(dest)
        dest_exists = dest.exists()

        fileutil = options.fileutil
        export_db = options.export_db

        if options.update or options.force_update:  # updating
            if dest_exists:
                if self._should_update_photo(src, dest, options):
                    update_updated_files.append(dest_str)
                else:
                    update_skipped_files.append(dest_str)
            else:
                # update, destination doesn't exist (new file)
                update_new_files.append(dest_str)
        else:
            # not update, export the file
            exported_files.append(dest_str)

        export_files = update_new_files + update_updated_files + exported_files
        for export_dest in export_files:
            # set src_sig before any modifications by convert_to_jpeg or exiftool
            export_record = export_db.create_or_get_file_record(
                export_dest, self.photo.uuid
            )
            export_record.src_sig = fileutil.file_sig(src)
            if dest_exists and any(
                [options.overwrite, options.update, options.force_update]
            ):
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
            else:
                if options.convert_to_jpeg:
                    # use convert_to_jpeg to export the file
                    # convert to a temp file before copying
                    tmp_file = increment_filename(
                        self._temp_dir_path
                        / f"{pathlib.Path(src).stem}_converted_to_jpeg.jpeg"
                    )
                    fileutil.convert_to_jpeg(
                        src, tmp_file, compression_quality=options.jpeg_quality
                    )
                    src = tmp_file
                    converted_to_jpeg_files.append(dest_str)

                if options.exiftool:
                    # if exiftool, write the metadata
                    # need to copy the file to a temp file before writing metadata
                    src = pathlib.Path(src)
                    tmp_file = increment_filename(
                        self._temp_dir_path / f"{src.stem}_exiftool{src.suffix}"
                    )
                    fileutil.copy(src, tmp_file)
                    # point src to the tmp_file so that the original source is not modified
                    # and the export grabs the new file
                    src = tmp_file
                    exif_results = self.write_exiftool_metadata_to_file(
                        src, dest, options=options
                    )

                try:
                    fileutil.copy(src, dest_str)
                    verbose(
                        f"Exported {self._filename(self.photo.original_filename)} to {self._filepath(dest_str)}"
                    )
                except Exception as e:
                    raise ExportError(
                        f"Error copying file {src} to {dest_str}: {e} ({lineno(__file__)})"
                    ) from e

        results = ExportResults(
            converted_to_jpeg=converted_to_jpeg_files,
            error=exif_results.error,
            exif_updated=exif_results.exif_updated,
            exiftool_error=exif_results.exiftool_error,
            exiftool_warning=exif_results.exiftool_warning,
            exported=exported_files + update_new_files + update_updated_files,
            new=update_new_files,
            skipped=update_skipped_files,
            updated=update_updated_files,
        )

        # touch files if needed
        if options.touch_file:
            results += self._touch_files(
                exported_files
                + update_new_files
                + update_updated_files
                + update_skipped_files,
                options,
            )

        # set data in the database
        with export_db.create_or_get_file_record(dest_str, self.photo.uuid) as rec:
            photoinfo = self.photo.json()
            rec.photoinfo = photoinfo
            rec.export_options = options.bit_flags
            # don't set src_sig as that is set above before any modifications by convert_to_jpeg or exiftool
            if not options.ignore_signature:
                rec.dest_sig = fileutil.file_sig(dest)
            if options.exiftool:
                rec.exifdata = self.exiftool_json_sidecar(options)
            if self.photo.hexdigest != rec.digest:
                results.metadata_changed = [dest_str]
            rec.digest = self.photo.hexdigest

        return results

    def _export_photo_uuid_applescript(
        self,
        uuid: str,
        dest: str,
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
            raise ValueError("edited or original must be True but not both")

        # export to a subdirectory of tmpdir
        tmpdir = self.fileutil.tmpdir(
            "osxphotos_applescript_export_", dir=self._temp_dir_path
        )

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
            if (
                len(exported_files) > 1
                and not live_photo
                and path.suffix.lower() == ".mov"
            ):
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
            sidecar_str = self.exiftool_json_sidecar(
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
            sidecar_str = self.exiftool_json_sidecar(
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
                verbose(
                    f"Writing {sidecar_type} sidecar {self._filepath(sidecar_filename)}"
                )
                files_written.append(str(sidecar_filename))
                if not options.dry_run:
                    self._write_sidecar(sidecar_filename, sidecar_str)
                    sidecar_record.digest = sidecar_digest
                    sidecar_record.dest_sig = fileutil.file_sig(sidecar_filename)
            else:
                verbose(
                    f"Skipped up to date {sidecar_type} sidecar {self._filepath(sidecar_filename)}"
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
            results += self._touch_files(all_sidecars, options)

            # update destination signatures in database
            for sidecar_filename in all_sidecars:
                sidecar_record = export_db.create_or_get_file_record(
                    sidecar_filename, self.photo.uuid
                )
                sidecar_record.dest_sig = fileutil.file_sig(sidecar_filename)

        return results

    def write_exiftool_metadata_to_file(
        self,
        src,
        dest,
        options: ExportOptions,
    ) -> ExportResults:
        """Write exif metadata to src file using exiftool

        Caution: This method modifies *src*, not *dest*,
        so src must be a copy of the original file if you don't want the source modified;
        it also does not write to dest (dest is the intended destination for purposes of
        referencing the export database. This allows the exiftool update to be done on the
        local machine prior to being copied to the export destination which may be on a
        network drive or other slower external storage)."""

        verbose = options.verbose or self._verbose
        exiftool_results = ExportResults()

        # don't try to write if unsupported file type for exiftool
        if not exiftool_can_write(os.path.splitext(src)[-1]):
            exiftool_results.exiftool_warning.append(
                (
                    dest,
                    f"Unsupported file type for exiftool, skipping exiftool for {dest}",
                )
            )
            # set file signature so the file doesn't get re-exported with --update
            return exiftool_results

        # determine if we need to write the exif metadata
        # if we are not updating, we always write
        # else, need to check the database to determine if we need to write
        verbose(
            f"Writing metadata with exiftool for {self._filepath(pathlib.Path(dest).name)}"
        )
        if not options.dry_run:
            warning_, error_ = self._write_exif_data(src, options=options)
            if warning_:
                exiftool_results.exiftool_warning.append((dest, warning_))
            if error_:
                exiftool_results.exiftool_error.append((dest, error_))
                exiftool_results.error.append((dest, error_))

        exiftool_results.exif_updated.append(dest)
        exiftool_results.to_touch.append(dest)
        return exiftool_results

    def _should_run_exiftool(self, dest, options: ExportOptions) -> bool:
        """Return True if exiftool should be run to update metadata"""
        run_exiftool = not options.update and not options.force_update
        if options.update or options.force_update:
            files_are_different = False
            exif_record = options.export_db.get_file_record(dest)
            old_data = exif_record.exifdata if exif_record else None
            if old_data is not None:
                old_data = json.loads(old_data)[0]
                current_data = json.loads(self.exiftool_json_sidecar(options=options))
                current_data = current_data[0]
                if old_data != current_data:
                    files_are_different = True

            if old_data is None or files_are_different:
                # didn't have old data, assume we need to write it
                # or files were different
                run_exiftool = True
        return run_exiftool

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
        self,
        options: t.Optional[ExportOptions] = None,
        filename: t.Optional[str] = None,
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
            XMP:Rating

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

    def exiftool_json_sidecar(
        self,
        options: t.Optional[ExportOptions] = None,
        tag_groups: bool = True,
        filename: t.Optional[str] = None,
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
        self,
        options: t.Optional[ExportOptions] = None,
        extension: t.Optional[str] = None,
    ):
        """returns string for XMP sidecar

        Args:
            options (ExportOptions): options for export
            extension (t.Optional[str]): which extension to use for SidecarForExtension property
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

        if options.favorite_rating:
            rating = 5 if self.photo.favorite else 0
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
