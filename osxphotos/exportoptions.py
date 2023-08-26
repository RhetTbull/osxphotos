"""Options class and results class for PhotoExporter """

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any, Callable, Optional

from ._constants import DEFAULT_PREVIEW_SUFFIX
from .export_db import ExportDB
from .fileutil import FileUtil
from .phototemplate import RenderOptions

# These two classes are in a separate file as classes other than PhotoExporter need to use them

__all__ = ["ExportOptions", "ExportResults"]


@dataclasses.dataclass
class ExportOptions:
    """Options class for exporting photos with export

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
    exiftool_flags: Optional[list[str]] = None
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
    keyword_template: Optional[list[str]] = None
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
    verbose: Optional[Callable[[Any], Any]] = None
    tmpdir: Optional[str] = None
    favorite_rating: bool = False

    def asdict(self):
        return dataclasses.asdict(self)

    @property
    def bit_flags(self):
        """Return bit flags representing options that affect export"""
        # currently only exiftool makes a difference
        return self.exiftool << 1


class ExportResults:
    """Results class which holds export results for export

    Args:
        converted_to_jpeg: list of files converted to jpeg
        deleted_directories: list of directories deleted
        deleted_files: list of files deleted
        error: list of tuples of (filename, error) for any errors generated during export
        exif_updated: list of files where exif data was updated with exiftool
        exiftool_error: list of tuples of (filename, error) for any errors generated by exiftool
        exiftool_warning: list of tuples of (filename, warning) for any warnings generated by exiftool
        exported: list of files exported
        exported_album: list of tuples of (file, album) for any files exported to an album
        metadata_changed: list of filenames that had metadata changes since last export
        missing: list of files that were missing
        missing_album: list of tuples of (file, album) for any files that were missing from an album
        new: list of files that were new
        aae_written: list of files where .AAE file was written
        sidecar_exiftool_skipped: list of files where exiftool sidecar was skipped
        sidecar_exiftool_written: list of files where exiftool sidecar was written
        sidecar_json_skipped: list of files where json sidecar was skipped
        sidecar_json_written: list of files where json sidecar was written
        sidecar_xmp_skipped: list of files where xmp sidecar was skipped
        sidecar_xmp_written: list of files where xmp sidecar was written
        sidecar_user_written: list of files where user sidecar was written
        sidecar_user_skipped: list of files where user sidecar was skipped
        sidecar_user_error: list of tuples of (filename, error) for any errors generated by user sidecar
        skipped: list of files that were skipped
        skipped_album: list of tuples of (file, album) for any files that were skipped from an album
        to_touch: list of files that were touched
        touched: list of files that were touched
        updated: list of files that were updated
        xattr_skipped: list of files where xattr was skipped
        xattr_written: list of files where xattr was written
        user_written: list of files written by user post_function
        user_skipped: list of files skipped by user post_function
        user_error: list of tuples of (filename, error) for any errors generated by user post_function

    Notes:
        Each attribute is a list of files or None if no files for that attribute.
        Error and warning attributes are a list of tuples of (filename, error) where filename is the file that caused the error and error is the error message.
        Album attributes are a list of tuples of (file, album) where file is the file exported and album is the album it was exported to.
        ExportResults can be added together with the += operator to combine results as the export progresses.
    """

    # Note: __init__ docs above added in the class docstring so they are picked up by sphinx

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
        "aae_written",
        "sidecar_exiftool_skipped",
        "sidecar_exiftool_written",
        "sidecar_json_skipped",
        "sidecar_json_written",
        "sidecar_xmp_skipped",
        "sidecar_xmp_written",
        "sidecar_user_written",
        "sidecar_user_skipped",
        "sidecar_user_error",
        "skipped",
        "skipped_album",
        "to_touch",
        "touched",
        "updated",
        "xattr_skipped",
        "xattr_written",
        "user_written",
        "user_skipped",
        "user_error",
    ]

    def __init__(
        self,
        converted_to_jpeg: list[str] | None = None,
        deleted_directories: list[str] | None = None,
        deleted_files: list[str] | None = None,
        error: list[str] | None = None,
        exif_updated: list[str] | None = None,
        exiftool_error: list[tuple[str, str]] | None = None,
        exiftool_warning: list[tuple[str, str]] | None = None,
        exported: list[str] | None = None,
        exported_album: list[tuple[str, str]] | None = None,
        metadata_changed: list[str] | None = None,
        missing: list[str] | None = None,
        missing_album: list[tuple[str, str]] | None = None,
        new: list[str] | None = None,
        aae_written: list[str] | None = None,
        sidecar_exiftool_skipped: list[str] | None = None,
        sidecar_exiftool_written: list[str] | None = None,
        sidecar_json_skipped: list[str] | None = None,
        sidecar_json_written: list[str] | None = None,
        sidecar_xmp_skipped: list[str] | None = None,
        sidecar_xmp_written: list[str] | None = None,
        sidecar_user_written: list[str] | None = None,
        sidecar_user_skipped: list[str] | None = None,
        sidecar_user_error: list[tuple[str, str]] | None = None,
        skipped: list[str] | None = None,
        skipped_album: list[tuple[str, str]] | None = None,
        to_touch: list[str] | None = None,
        touched: list[str] | None = None,
        updated: list[str] | None = None,
        xattr_skipped: list[str] | None = None,
        xattr_written: list[str] | None = None,
        user_written: list[str] | None = None,
        user_skipped: list[str] | None = None,
        user_error: list[tuple[str, str]] | None = None,
    ):
        """ExportResults data class to hold results of export.

        See class docstring for details.
        """
        local_vars = locals()
        self._datetime = datetime.now().isoformat()
        for attr in self.attributes:
            setattr(self, attr, local_vars.get(attr) or [])

    @property
    def attributes(self) -> list[str]:
        """Return list of attributes tracked by ExportResults"""
        return [attr for attr in self.__slots__ if not attr.startswith("_")]

    @property
    def datetime(self) -> str:
        """Return datetime when ExportResults was created"""
        return self._datetime

    def all_files(self) -> list[str]:
        """return all filenames contained in results"""
        files = (
            self.exported
            + self.new
            + self.updated
            + self.skipped
            + self.exif_updated
            + self.touched
            + self.converted_to_jpeg
            + self.aae_written
            + self.sidecar_json_written
            + self.sidecar_json_skipped
            + self.sidecar_exiftool_written
            + self.sidecar_exiftool_skipped
            + self.sidecar_xmp_written
            + self.sidecar_xmp_skipped
            + self.sidecar_user_written
            + self.sidecar_user_skipped
            + self.missing
            + self.user_written
            + self.user_skipped
        )
        files += [x[0] for x in self.exiftool_warning]
        files += [x[0] for x in self.exiftool_error]
        files += [x[0] for x in self.error]
        files += [x[0] for x in self.sidecar_user_error]
        files += [x[0] for x in self.user_error]

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
