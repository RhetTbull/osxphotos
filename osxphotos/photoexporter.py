""" PhotoExport class to export photos
"""

from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import typing as t
from enum import Enum

from ._version import __version__
from .exiftool import exiftool_can_write
from .exifwriter import ExifWriter, exif_options_from_options
from .export_db import ExportDBTemp
from .exportoptions import ExportOptions, ExportResults
from .fileutil import FileUtil
from .phototemplate import RenderOptions
from .platform import is_macos
from .rich_utils import add_rich_markup_tag
from .sidecars import SidecarWriter, exiftool_json_sidecar
from .touch_files import touch_files
from .unicode import normalize_fs_path
from .uti import get_preferred_uti_extension
from .utils import (
    increment_filename,
    increment_filename_with_count,
    lineno,
    lock_filename,
    unlock_filename,
)

if is_macos:
    import photoscript

    from .photokit import (
        PHOTOS_VERSION_CURRENT,
        PHOTOS_VERSION_ORIGINAL,
        PHOTOS_VERSION_UNADJUSTED,
        PhotoKitFetchFailed,
        PhotoLibrary,
    )


__all__ = [
    "ExportError",
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
    UPDATE_ERRORS = 9


class ExportError(Exception):
    """error during export"""

    pass


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

    def __repr__(self):
        return f"StagedFiles({self.asdict()})"

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


class PhotoExporter:
    """Export a photo"""

    def __init__(self, photo: "PhotoInfo", tmpdir: t.Optional[str] = None):
        self.photo = photo
        self._render_options = RenderOptions()
        self._verbose = photo._verbose

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
        # for `--download-missing` and `--update` case, this may cause unnecessary downloads
        # as it will download the file even if it's not needed (won't be checked until the _should_update_photo() call from _export_photo()
        # fixing this will require major refactoring of the export code, see #1086
        # leaving it for now as this should not be a common use case
        # (if using `--update` it is much better to be using "Download originals to this Mac" in Photos)
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
            unlock_filename(dest)

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
                raw_ext = (
                    get_preferred_uti_extension(self.photo.uti_raw)
                    if self.photo.uti_raw
                    else "raw"
                )
                raw_ext = raw_ext or "raw"
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
                    else pathlib.Path(
                        increment_filename(preview_name, lock=not options.dry_run)
                    )
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

        if options.export_aae:
            all_results += self._write_aae_file(dest=dest, options=options)
        sidecar_writer = SidecarWriter(self.photo)
        all_results += sidecar_writer.write_sidecar_files(dest=dest, options=options)

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

    def _get_edited_filename(self, original_filename):
        """Return the filename for the exported edited photo
        (used when filename isn't provided in call to export)"""
        # need to get the right extension for edited file
        original_filename = pathlib.Path(original_filename)
        if self.photo.path_edited:
            ext = pathlib.Path(self.photo.path_edited).suffix
        else:
            uti = self.photo.uti_edited or self.photo.uti
            ext = get_preferred_uti_extension(uti)
            ext = f".{ext}"
        return f"{original_filename.stem}_edited{ext}"

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

        # lock files are used to minimize chance of name collision when in parallel mode
        # don't create lock files if in dry_run mode
        lock = not options.dry_run

        def _lock_filename(filename):
            """Lock filename if not in dry_run mode"""
            return lock_filename(filename) if lock else filename

        # if overwrite==False and #increment==False, export should fail if file exists
        if (
            not any(
                [
                    options.increment,
                    options.update,
                    options.force_update,
                    options.overwrite,
                ]
            )
            and dest.exists()
        ):
            raise FileExistsError(
                f"destination exists ({dest}); overwrite={options.overwrite}, increment={options.increment}"
            )

        # if overwrite, we don't care if the file exists or not
        if options.overwrite and _lock_filename(dest):
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
            return pathlib.Path(increment_filename(dest, lock=lock))

        # if update and file exists, need to check to see if it's the right file by checking export db
        if options.update or options.force_update:
            export_db = options.export_db
            dest_uuid = export_db.get_uuid_for_file(dest)
            if dest_uuid is None and not dest.exists() and _lock_filename(dest):
                # destination doesn't exist in export db and doesn't exist on disk
                # so we can just use it
                return dest

            if dest_uuid == self.photo.uuid:
                # destination is the right file
                # will use it even if locked so don't check return value of _lock_filename
                _lock_filename(dest)
                return dest

            # either dest_uuid is wrong or file exists and there's no associated UUID, so find a name that matches
            # or create a new name if no match
            # find files that match "dest_name (*.ext" (e.g. "dest_name (1).jpg", "dest_name (2).jpg)", ...)
            # first, find all matching files in export db and see if there's a match
            if dest_target := export_db.get_target_for_file(self.photo.uuid, dest):
                # there's a match so use that
                _lock_filename(dest_target)
                return pathlib.Path(dest_target)

            # no match so need to create a new name
            # increment the destination file until we find one that doesn't exist and doesn't match another uuid in the database
            count = 0
            dest, count = increment_filename_with_count(dest, count, lock=lock)
            count += 1
            while export_db.get_uuid_for_file(dest) is not None:
                dest, count = increment_filename_with_count(dest, count, lock=lock)
            return pathlib.Path(dest)

        # fail safe...I can't think of a case that gets here
        _lock_filename(dest)
        return dest

    def _should_update_photo(
        self, src: pathlib.Path | None, dest: pathlib.Path, options: ExportOptions
    ) -> bool | ShouldUpdate:
        """Return True if photo should be updated, else False

        Args:
            src (pathlib.Path | None): source path; if None, photo is missing and
                any checks that require src will return True
            dest (pathlib.Path): destination path

        Returns:
            False if photo should not be updated otherwise a truthy ShouldUpdate value
        """

        # NOTE: The order of certain checks is important
        # read the comments below to understand why before changing

        export_db = options.export_db
        fileutil = options.fileutil

        file_record = export_db.get_file_record(dest)

        if not file_record:
            # photo doesn't exist in database, should update
            return ShouldUpdate.NOT_IN_DATABASE

        if options.export_as_hardlink and (not src or not dest.samefile(src)):
            # different files, should update
            return ShouldUpdate.HARDLINK_DIFFERENT_FILES

        if not options.export_as_hardlink and (not src or dest.samefile(src)):
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

        if options.update_errors and file_record.error is not None:
            # files that were exported but generated an error
            # won't be updated unless --update-errors is specified
            # for example, an exiftool error due to bad metadata
            # that the user subsequently fixed should be updated; see #872
            # this must be checked before exiftool which will return False if exif data matches
            return ShouldUpdate.UPDATE_ERRORS

        if options.exiftool:
            current_exifdata = exiftool_json_sidecar(photo=self.photo, options=options)
            rv = current_exifdata != file_record.exifdata
            # if using exiftool, don't need to continue checking edited below
            # as exiftool will be used to update edited file
            return ShouldUpdate.EXIFTOOL_DIFFERENT if rv else False

        if options.edited and (
            not src or not fileutil.cmp_file_sig(src, file_record.src_sig)
        ):
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
            staged |= self._stage_missing_photos_for_export(
                staged=staged, options=options
            )

        return staged

    def _stage_missing_photos_for_export(
        self, staged: StagedFiles, options: ExportOptions
    ) -> StagedFiles:
        """Download and stage any missing files for export"""

        # if live photo and requesting edited version need the edited live photo
        live_photo = staged.edited_live if options.edited else staged.original_live

        # is there actually a missing file? (#1086)
        something_to_download = (
            (self.photo.hasadjustments and options.edited and not staged.edited)
            or (self.photo.live_photo and options.live_photo and not live_photo)
            or (self.photo.has_raw and options.raw_photo and not staged.raw)
            or (options.preview and not staged.preview)
            or (not options.edited and not staged.original)
        )
        if not something_to_download:
            return staged

        missing_options = ExportOptions(
            edited=options.edited,
            preview=options.preview and not staged.preview,
            raw_photo=self.photo.has_raw and options.raw_photo and not staged.raw,
            live_photo=self.photo.live_photo and options.live_photo and not live_photo,
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
        This is a limitation of the Photos AppleScript interface and Photos behaves the same way.
        """

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
                        f"Exported {self._filename(self.photo.original_filename)} to {self._filepath(normalize_fs_path(dest_str))}"
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
            results += touch_files(
                self.photo,
                exported_files
                + update_new_files
                + update_updated_files
                + update_skipped_files,
                options,
            )

        # set data in the database
        with export_db.create_or_get_file_record(dest_str, self.photo.uuid) as rec:
            rec.photoinfo = self.photo.json(shallow=True)
            rec.export_options = options.bit_flags
            # don't set src_sig as that is set above before any modifications by convert_to_jpeg or exiftool
            if not options.ignore_signature:
                rec.dest_sig = fileutil.file_sig(dest)
            if options.exiftool:
                rec.exifdata = exiftool_json_sidecar(photo=self.photo, options=options)
            if self.photo.hexdigest != rec.digest:
                results.metadata_changed = [dest_str]
            rec.digest = self.photo.hexdigest
            # save errors to the export database (#872)
            if (
                results.error
                or exif_results.exiftool_error
                or exif_results.exiftool_warning
            ):
                rec.error = {
                    "error": results.error,
                    "exiftool_error": exif_results.exiftool_error,
                    "exiftool_warning": exif_results.exiftool_warning,
                }

        # clean up lock file
        unlock_filename(dest_str)

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

    def _write_aae_file(
        self,
        dest: pathlib.Path,
        options: ExportOptions,
    ) -> ExportResults:
        """Write AAE file for the photo."""

        # AAE files describe adjustments to originals, so they don't make sense
        # for edited files
        if options.edited:
            return ExportResults()

        verbose = options.verbose or self._verbose

        aae_src = self.photo.adjustments_path
        if aae_src is None:
            return ExportResults()
        aae_dest = dest.with_suffix(".AAE")

        if options.export_as_hardlink:
            try:
                if aae_dest.exists() and any(
                    [options.overwrite, options.update, options.force_update]
                ):
                    try:
                        options.fileutil.unlink(aae_dest)
                    except Exception as e:
                        raise ExportError(
                            f"Error removing file {aae_dest}: {e} (({lineno(__file__)})"
                        ) from e
                options.fileutil.hardlink(aae_src, aae_dest)
            except Exception as e:
                raise ExportError(
                    f"Error hardlinking {aae_src} to {aae_dest}: {e} ({lineno(__file__)})"
                ) from e
        else:
            try:
                options.fileutil.copy(aae_src, aae_dest)
                verbose(
                    f"Exported adjustments of {self._filename(self.photo.original_filename)} to {self._filepath(normalize_fs_path(aae_dest))}"
                )
            except Exception as e:
                raise ExportError(
                    f"Error copying file {aae_src} to {aae_dest}: {e} ({lineno(__file__)})"
                ) from e

        return ExportResults(aae_written=[aae_dest])

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
            writer = ExifWriter(self.photo)
            warning_, error_ = writer.write_exif_data(
                src, options=exif_options_from_options(options)
            )
            if warning_:
                exiftool_results.exiftool_warning.append((str(dest), str(warning_)))
            if error_:
                exiftool_results.exiftool_error.append((str(dest), str(error_)))
                exiftool_results.error.append((str(dest), str(error_)))

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
                current_data = json.loads(
                    exiftool_json_sidecar(photo=self.photo, options=options)
                )
                current_data = current_data[0]
                if old_data != current_data:
                    files_are_different = True

            if old_data is None or files_are_different:
                # didn't have old data, assume we need to write it
                # or files were different
                run_exiftool = True
        return run_exiftool


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
