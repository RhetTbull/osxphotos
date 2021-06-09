""" Export methods for PhotoInfo 
    The following methods are defined and must be imported into PhotoInfo as instance methods:
    export
    export2
    _export_photo
    _write_exif_data
    _exiftool_json_sidecar
    _get_exif_keywords
    _get_exif_persons
    _exiftool_dict
    _xmp_sidecar
    _write_sidecar
    """

# TODO: should this be its own PhotoExporter class?
# TODO: the various sidecar_json, sidecar_xmp, etc args should all be collapsed to a sidecar param using a bit mask

import glob
import hashlib
import json
import logging
import os
import pathlib
import re
import tempfile
from collections import namedtuple  # pylint: disable=syntax-error

import photoscript
from mako.template import Template

# from .._applescript import AppleScript
from .._constants import (
    _MAX_IPTC_KEYWORD_LEN,
    _OSXPHOTOS_NONE_SENTINEL,
    _TEMPLATE_DIR,
    _UNKNOWN_PERSON,
    _XMP_TEMPLATE_NAME,
    _XMP_TEMPLATE_NAME_BETA,
    SIDECAR_EXIFTOOL,
    SIDECAR_JSON,
    SIDECAR_XMP,
    LIVE_VIDEO_EXTENSIONS,
)
from .._version import __version__
from ..datetime_utils import datetime_tz_to_utc
from ..exiftool import ExifTool
from ..export_db import ExportDBNoOp
from ..fileutil import FileUtil
from ..photokit import (
    PHOTOS_VERSION_CURRENT,
    PHOTOS_VERSION_ORIGINAL,
    PhotoKitFetchFailed,
    PhotoLibrary,
)
from ..utils import findfiles, get_preferred_uti_extension, lineno, noop

# retry if use_photos_export fails the first time (which sometimes it does)
MAX_PHOTOSCRIPT_RETRIES = 3


class ExportError(Exception):
    """error during export"""

    pass


class ExportResults:
    """holds export results for export2"""

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


# hexdigest is not a class method, don't import this into PhotoInfo
def hexdigest(strval):
    """hexdigest of a string, using blake2b"""
    h = hashlib.blake2b(digest_size=20)
    h.update(bytes(strval, "utf-8"))
    return h.hexdigest()


# _export_photo_uuid_applescript is not a class method, don't import this into PhotoInfo
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
        raise ExportError(f"Could not export photo {uuid}")

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
            FileUtil.copy(str(path), str(dest_new))
        exported_paths.append(str(dest_new))
    return exported_paths


# _check_export_suffix is not a class method, don't import this into PhotoInfo
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


# not a class method, don't import into PhotoInfo
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


def export(
    self,
    dest,
    *filename,
    edited=False,
    live_photo=False,
    raw_photo=False,
    export_as_hardlink=False,
    overwrite=False,
    increment=True,
    sidecar_json=False,
    sidecar_exiftool=False,
    sidecar_xmp=False,
    use_photos_export=False,
    timeout=120,
    exiftool=False,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
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
    edited: (boolean, default=False); if True will export the edited version of the photo
            (or raise exception if no edited version)
    live_photo: (boolean, default=False); if True, will also export the associted .mov for live photos
    raw_photo: (boolean, default=False); if True, will also export the associted RAW photo
    export_as_hardlink: (boolean, default=False); if True, will hardlink files instead of copying them
    overwrite: (boolean, default=False); if True will overwrite files if they alreay exist
    increment: (boolean, default=True); if True, will increment file name until a non-existant name is found
                if overwrite=False and increment=False, export will fail if destination file already exists
    sidecar_json: if set will write a json sidecar with data in format readable by exiftool
                sidecar filename will be dest/filename.json; includes exiftool tag group names (e.g. `exiftool -G -j`)
    sidecar_exiftool: if set will write a json sidecar with data in format readable by exiftool
                sidecar filename will be dest/filename.json; does not include exiftool tag group names (e.g. `exiftool -j`)
    sidecar_xmp: if set will write an XMP sidecar with IPTC data
                sidecar filename will be dest/filename.xmp
    use_photos_export: (boolean, default=False); if True will attempt to export photo via applescript interaction with Photos
    timeout: (int, default=120) timeout in seconds used with use_photos_export
    exiftool: (boolean, default = False); if True, will use exiftool to write metadata to export file
    returns list of full paths to the exported files
    use_albums_as_keywords: (boolean, default = False); if True, will include album names in keywords
    when exporting metadata with exiftool or sidecar
    use_persons_as_keywords: (boolean, default = False); if True, will include person names in keywords
    when exporting metadata with exiftool or sidecar
    keyword_template: (list of strings); list of template strings that will be rendered as used as keywords
    description_template: string; optional template string that will be rendered for use as photo description

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

    results = self.export2(
        dest,
        *filename,
        edited=edited,
        live_photo=live_photo,
        raw_photo=raw_photo,
        export_as_hardlink=export_as_hardlink,
        overwrite=overwrite,
        increment=increment,
        sidecar=sidecar,
        use_photos_export=use_photos_export,
        timeout=timeout,
        exiftool=exiftool,
        use_albums_as_keywords=use_albums_as_keywords,
        use_persons_as_keywords=use_persons_as_keywords,
        keyword_template=keyword_template,
        description_template=description_template,
    )

    return results.exported


def export2(
    self,
    dest,
    *filename,
    edited=False,
    live_photo=False,
    raw_photo=False,
    export_as_hardlink=False,
    overwrite=False,
    increment=True,
    sidecar=0,
    sidecar_drop_ext=False,
    use_photos_export=False,
    timeout=120,
    exiftool=False,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
    update=False,
    ignore_signature=False,
    export_db=None,
    fileutil=FileUtil,
    dry_run=False,
    touch_file=False,
    convert_to_jpeg=False,
    jpeg_quality=1.0,
    ignore_date_modified=False,
    use_photokit=False,
    verbose=None,
    exiftool_flags=None,
    merge_exif_keywords=False,
    merge_exif_persons=False,
    jpeg_ext=None,
    persons=True,
    location=True,
    replace_keywords=False,
):
    """export photo, like export but with update and dry_run options
    dest: must be valid destination path or exception raised
    filename: (optional): name of exported picture; if not provided, will use current filename
                **NOTE**: if provided, user must ensure file extension (suffix) is correct.
                For example, if photo is .CR2 file, edited image may be .jpeg.
                If you provide an extension different than what the actual file is,
                will export the photo using the incorrect file extension (unless use_photos_export is true,
                in which case export will use the extension provided by Photos upon export.
                e.g. to get the extension of the edited photo,
                reference PhotoInfo.path_edited
    edited: (boolean, default=False); if True will export the edited version of the photo
            (or raise exception if no edited version)
    live_photo: (boolean, default=False); if True, will also export the associated .mov for live photos
    raw_photo: (boolean, default=False); if True, will also export the associated RAW photo
    export_as_hardlink: (boolean, default=False); if True, will hardlink files instead of copying them
    overwrite: (boolean, default=False); if True will overwrite files if they already exist
    increment: (boolean, default=True); if True, will increment file name until a non-existant name is found
                if overwrite=False and increment=False, export will fail if destination file already exists
    sidecar: bit field: set to one or more of SIDECAR_XMP, SIDECAR_JSON, SIDECAR_EXIFTOOL
             SIDECAR_JSON: if set will write a json sidecar with data in format readable by exiftool
                sidecar filename will be dest/filename.json; includes exiftool tag group names (e.g. `exiftool -G -j`)
             SIDECAR_EXIFTOOL: if set will write a json sidecar with data in format readable by exiftool
                sidecar filename will be dest/filename.json; does not include exiftool tag group names (e.g. `exiftool -j`)
             SIDECAR_XMP: if set will write an XMP sidecar with IPTC data
                sidecar filename will be dest/filename.xmp
    sidecar_drop_ext: (boolean, default=False); if True, drops the photo's extension from sidecar filename (e.g. 'IMG_1234.json' instead of 'IMG_1234.JPG.json')
    use_photos_export: (boolean, default=False); if True will attempt to export photo via applescript interaction with Photos
    timeout: (int, default=120) timeout in seconds used with use_photos_export
    exiftool: (boolean, default = False); if True, will use exiftool to write metadata to export file
    use_albums_as_keywords: (boolean, default = False); if True, will include album names in keywords
    when exporting metadata with exiftool or sidecar
    use_persons_as_keywords: (boolean, default = False); if True, will include person names in keywords
    when exporting metadata with exiftool or sidecar
    keyword_template: (list of strings); list of template strings that will be rendered as used as keywords
    description_template: string; optional template string that will be rendered for use as photo description
    update: (boolean, default=False); if True export will run in update mode, that is, it will
            not export the photo if the current version already exists in the destination
    ignore_signature: (bool, default=False), ignore file signature when used with update (look only at filename)
    export_db: (ExportDB_ABC); instance of a class that conforms to ExportDB_ABC with methods
            for getting/setting data related to exported files to compare update state
    fileutil: (FileUtilABC); class that conforms to FileUtilABC with various file utilities
    dry_run: (boolean, default=False); set to True to run in "dry run" mode
    touch_file: (boolean, default=False); if True, sets file's modification time upon photo date
    convert_to_jpeg: boolean; if True, converts non-jpeg images to jpeg
    jpeg_quality: float in range 0.0 <= jpeg_quality <= 1.0.  A value of 1.0 specifies use best quality, a value of 0.0 specifies use maximum compression.
    ignore_date_modified: for use with sidecar and exiftool; if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set
    verbose: optional callable function to use for printing verbose text during processing; if None (default), does not print output.
    exiftool_flags: optional list of flags to pass to exiftool when using exiftool option, e.g ["-m", "-F"]
    merge_exif_keywords: boolean; if True, merged keywords found in file's exif data (requires exiftool)
    merge_exif_persons: boolean; if True, merged persons found in file's exif data (requires exiftool)
    jpeg_ext: if set, will use this value for extension on jpegs converted to jpeg with convert_to_jpeg; if not set, uses jpeg; do not include the leading "."
    persons: if True, include persons in exported metadata
    location: if True, include location in exported metadata
    replace_keywords: if True, keyword_template replaces any keywords, otherwise it's additive

    Returns: ExportResults class
        ExportResults has attributes:
        "exported",
        "new",
        "updated",
        "skipped",
        "exif_updated",
        "touched",
        "converted_to_jpeg",
        "sidecar_json_written",
        "sidecar_json_skipped",
        "sidecar_exiftool_written",
        "sidecar_exiftool_skipped",
        "sidecar_xmp_written",
        "sidecar_xmp_skipped",
        "missing",
        "error",
        "error_str",
        "exiftool_warning",
        "exiftool_error",


    Note: to use dry run mode, you must set dry_run=True and also pass in memory version of export_db,
          and no-op fileutil (e.g. ExportDBInMemory and FileUtilNoOp)
    """

    # NOTE: This function is very complex and does a lot of things.
    # Don't modify this code if you don't fully understand everything it does.
    # TODO: This is a good candidate for refactoring.

    # when called from export(), won't get an export_db, so use no-op version
    if export_db is None:
        export_db = ExportDBNoOp()

    if verbose and not callable(verbose):
        raise TypeError("verbose must be callable")

    if verbose is None:
        verbose = self._verbose

    # suffix to add to edited files
    # e.g. name will be filename_edited.jpg
    edited_identifier = "_edited"

    # check edited and raise exception trying to export edited version of
    # photo that hasn't been edited
    if edited and not self.hasadjustments:
        raise ValueError(
            "Photo does not have adjustments, cannot export edited version"
        )

    # check arguments and get destination path and filename (if provided)
    if filename and len(filename) > 2:
        raise TypeError(
            "Too many positional arguments.  Should be at most two: destination, filename."
        )

    # verify destination is a valid path
    if dest is None:
        raise ValueError("Destination must not be None")
    elif not dry_run and not os.path.isdir(dest):
        raise FileNotFoundError("Invalid path passed to export")

    if filename and len(filename) == 1:
        # if filename passed, use it
        fname = filename[0]
    else:
        # no filename provided so use the default
        # if edited file requested, use filename but add _edited
        # need to use file extension from edited file as Photos saves a jpeg once edited
        if edited and not use_photos_export:
            # verify we have a valid path_edited and use that to get filename
            if not self.path_edited:
                raise FileNotFoundError(
                    "edited=True but path_edited is none; hasadjustments: "
                    f" {self.hasadjustments}"
                )
            edited_name = pathlib.Path(self.path_edited).name
            edited_suffix = pathlib.Path(edited_name).suffix
            fname = (
                pathlib.Path(self.original_filename).stem
                + edited_identifier
                + edited_suffix
            )
        else:
            fname = self.original_filename

    uti = self.uti if edited else self.uti_original
    if convert_to_jpeg and self.isphoto and uti != "public.jpeg":
        # not a jpeg but will convert to jpeg upon export so fix file extension
        fname_new = pathlib.Path(fname)
        ext = "." + jpeg_ext if jpeg_ext else ".jpeg"
        fname = str(fname_new.parent / f"{fname_new.stem}{ext}")
    else:
        # nothing to convert
        convert_to_jpeg = False

    # check destination path
    dest = pathlib.Path(dest)
    fname = pathlib.Path(fname)
    dest = dest / fname

    # check to see if file exists and if so, add (1), (2), etc until we find one that works
    # Photos checks the stem and adds (1), (2), etc which avoids collision with sidecars
    # e.g. exporting sidecar for file1.png and file1.jpeg
    # if file1.png exists and exporting file1.jpeg,
    # dest will be file1 (1).jpeg even though file1.jpeg doesn't exist to prevent sidecar collision
    if not update and increment and not overwrite:
        count = 1
        dest_files = findfiles(f"{dest.stem}*", str(dest.parent))
        dest_files = [pathlib.Path(f).stem.lower() for f in dest_files]
        dest_new = dest.stem
        while dest_new.lower() in dest_files:
            dest_new = f"{dest.stem} ({count})"
            count += 1
        dest = dest.parent / f"{dest_new}{dest.suffix}"

    # if overwrite==False and #increment==False, export should fail if file exists
    if dest.exists() and not update and not overwrite and not increment:
        raise FileExistsError(
            f"destination exists ({dest}); overwrite={overwrite}, increment={increment}"
        )

    all_results = ExportResults()
    if not use_photos_export:
        # find the source file on disk and export
        # get path to source file and verify it's not None and is valid file
        # TODO: how to handle ismissing or not hasadjustments and edited=True cases?
        if edited:
            if self.path_edited is not None:
                src = self.path_edited
            else:
                raise FileNotFoundError(
                    f"Cannot export edited photo if path_edited is None"
                )
        else:
            if self.path is not None:
                src = self.path
            else:
                raise FileNotFoundError("Cannot export photo if path is None")

        if not os.path.isfile(src):
            raise FileNotFoundError(f"{src} does not appear to exist")

        # found source now try to find right destination
        if update and dest.exists():
            # destination exists, check to see if destination is the right UUID
            dest_uuid = export_db.get_uuid_for_file(dest)
            if dest_uuid is None and fileutil.cmp(src, dest):
                # might be exporting into a pre-ExportDB folder or the DB got deleted
                dest_uuid = self.uuid
                export_db.set_data(
                    filename=dest,
                    uuid=self.uuid,
                    orig_stat=fileutil.file_sig(dest),
                    exif_stat=(None, None, None),
                    converted_stat=(None, None, None),
                    edited_stat=(None, None, None),
                    info_json=self.json(),
                    exif_json=None,
                )
            if dest_uuid != self.uuid:
                # not the right file, find the right one
                count = 1
                glob_str = str(dest.parent / f"{dest.stem} (*{dest.suffix}")
                dest_files = glob.glob(glob_str)
                found_match = False
                for file_ in dest_files:
                    dest_uuid = export_db.get_uuid_for_file(file_)
                    if dest_uuid == self.uuid:
                        dest = pathlib.Path(file_)
                        found_match = True
                        break
                    elif dest_uuid is None and fileutil.cmp(src, file_):
                        # files match, update the UUID
                        dest = pathlib.Path(file_)
                        found_match = True
                        export_db.set_data(
                            filename=dest,
                            uuid=self.uuid,
                            orig_stat=fileutil.file_sig(dest),
                            exif_stat=(None, None, None),
                            converted_stat=(None, None, None),
                            edited_stat=(None, None, None),
                            info_json=self.json(),
                            exif_json=None,
                        )
                        break

                if not found_match:
                    # increment the destination file
                    count = 1
                    glob_str = str(dest.parent / f"{dest.stem}*")
                    dest_files = glob.glob(glob_str)
                    dest_files = [pathlib.Path(f).stem for f in dest_files]
                    dest_new = dest.stem
                    while dest_new in dest_files:
                        dest_new = f"{dest.stem} ({count})"
                        count += 1
                    dest = dest.parent / f"{dest_new}{dest.suffix}"

        # export the dest file
        results = self._export_photo(
            src,
            dest,
            update,
            export_db,
            overwrite,
            export_as_hardlink,
            exiftool,
            touch_file,
            convert_to_jpeg,
            fileutil=fileutil,
            edited=edited,
            jpeg_quality=jpeg_quality,
            ignore_signature=ignore_signature,
        )
        all_results += results

        # copy live photo associated .mov if requested
        if live_photo and self.live_photo:
            live_name = dest.parent / f"{dest.stem}.mov"
            src_live = self.path_live_photo

            if src_live is not None:
                results = self._export_photo(
                    src_live,
                    live_name,
                    update,
                    export_db,
                    overwrite,
                    export_as_hardlink,
                    exiftool,
                    touch_file,
                    False,
                    fileutil=fileutil,
                    ignore_signature=ignore_signature,
                )
                all_results += results

        # copy associated RAW image if requested
        if raw_photo and self.has_raw:
            raw_path = pathlib.Path(self.path_raw)
            raw_ext = raw_path.suffix
            raw_name = dest.parent / f"{dest.stem}{raw_ext}"
            if raw_path is not None:
                results = self._export_photo(
                    raw_path,
                    raw_name,
                    update,
                    export_db,
                    overwrite,
                    export_as_hardlink,
                    exiftool,
                    touch_file,
                    convert_to_jpeg,
                    fileutil=fileutil,
                    jpeg_quality=jpeg_quality,
                    ignore_signature=ignore_signature,
                )
                all_results += results
    else:
        self._export_photo_with_photos_export(
            dest,
            filename,
            all_results,
            fileutil,
            export_db,
            use_photokit=use_photokit,
            dry_run=dry_run,
            timeout=timeout,
            jpeg_ext=jpeg_ext,
            touch_file=touch_file,
            update=update,
            overwrite=overwrite,
            live_photo=live_photo,
            edited=edited,
            edited_identifier=edited_identifier,
            convert_to_jpeg=convert_to_jpeg,
            jpeg_quality=jpeg_quality,
        )

    # export metadata
    sidecars = []
    sidecar_json_files_skipped = []
    sidecar_json_files_written = []
    sidecar_exiftool_files_skipped = []
    sidecar_exiftool_files_written = []
    sidecar_xmp_files_skipped = []
    sidecar_xmp_files_written = []

    dest_suffix = "" if sidecar_drop_ext else dest.suffix
    if sidecar & SIDECAR_JSON:
        sidecar_filename = dest.parent / pathlib.Path(f"{dest.stem}{dest_suffix}.json")
        sidecar_str = self._exiftool_json_sidecar(
            use_albums_as_keywords=use_albums_as_keywords,
            use_persons_as_keywords=use_persons_as_keywords,
            keyword_template=keyword_template,
            description_template=description_template,
            ignore_date_modified=ignore_date_modified,
            merge_exif_keywords=merge_exif_keywords,
            merge_exif_persons=merge_exif_persons,
            filename=dest.name,
            persons=persons,
            location=location,
            replace_keywords=replace_keywords,
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

    if sidecar & SIDECAR_EXIFTOOL:
        sidecar_filename = dest.parent / pathlib.Path(f"{dest.stem}{dest_suffix}.json")
        sidecar_str = self._exiftool_json_sidecar(
            use_albums_as_keywords=use_albums_as_keywords,
            use_persons_as_keywords=use_persons_as_keywords,
            keyword_template=keyword_template,
            description_template=description_template,
            ignore_date_modified=ignore_date_modified,
            tag_groups=False,
            merge_exif_keywords=merge_exif_keywords,
            merge_exif_persons=merge_exif_persons,
            filename=dest.name,
            persons=persons,
            location=location,
            replace_keywords=replace_keywords,
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

    if sidecar & SIDECAR_XMP:
        sidecar_filename = dest.parent / pathlib.Path(f"{dest.stem}{dest_suffix}.xmp")
        sidecar_str = self._xmp_sidecar(
            use_albums_as_keywords=use_albums_as_keywords,
            use_persons_as_keywords=use_persons_as_keywords,
            keyword_template=keyword_template,
            description_template=description_template,
            extension=dest.suffix[1:] if dest.suffix else None,
            persons=persons,
            location=location,
            replace_keywords=replace_keywords,
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
            not update
            or (update and not sidecar_filename.exists())
            or (
                update
                and (sidecar_digest != old_sidecar_digest)
                or not fileutil.cmp_file_sig(sidecar_filename, sidecar_sig)
            )
        )
        if write_sidecar:
            verbose(f"Writing {sidecar_type} sidecar {sidecar_filename}")
            files_written.append(str(sidecar_filename))
            if not dry_run:
                self._write_sidecar(sidecar_filename, sidecar_str)
                export_db.set_sidecar_for_file(
                    sidecar_filename,
                    sidecar_digest,
                    fileutil.file_sig(sidecar_filename),
                )
        else:
            verbose(f"Skipped up to date {sidecar_type} sidecar {sidecar_filename}")
            files_skipped.append(str(sidecar_filename))

    # if exiftool, write the metadata
    if update:
        exif_files = all_results.new + all_results.updated + all_results.skipped
    else:
        exif_files = all_results.exported

    # TODO: remove duplicative code from below
    if exiftool and update and exif_files:
        for exported_file in exif_files:
            files_are_different = False
            old_data = export_db.get_exifdata_for_file(exported_file)
            if old_data is not None:
                old_data = json.loads(old_data)[0]
                current_data = json.loads(
                    self._exiftool_json_sidecar(
                        use_albums_as_keywords=use_albums_as_keywords,
                        use_persons_as_keywords=use_persons_as_keywords,
                        keyword_template=keyword_template,
                        description_template=description_template,
                        ignore_date_modified=ignore_date_modified,
                        merge_exif_keywords=merge_exif_keywords,
                        merge_exif_persons=merge_exif_persons,
                        persons=persons,
                        location=location,
                        replace_keywords=replace_keywords,
                    )
                )[0]
                if old_data != current_data:
                    files_are_different = True

            if old_data is None or files_are_different:
                # didn't have old data, assume we need to write it
                # or files were different
                verbose(f"Writing metadata with exiftool for {exported_file}")
                if not dry_run:
                    warning_, error_ = self._write_exif_data(
                        exported_file,
                        use_albums_as_keywords=use_albums_as_keywords,
                        use_persons_as_keywords=use_persons_as_keywords,
                        keyword_template=keyword_template,
                        description_template=description_template,
                        ignore_date_modified=ignore_date_modified,
                        flags=exiftool_flags,
                        merge_exif_keywords=merge_exif_keywords,
                        merge_exif_persons=merge_exif_persons,
                        persons=persons,
                        location=location,
                        replace_keywords=replace_keywords,
                    )
                    if warning_:
                        all_results.exiftool_warning.append((exported_file, warning_))
                    if error_:
                        all_results.exiftool_error.append((exported_file, error_))
                        all_results.error.append((exported_file, error_))

                export_db.set_exifdata_for_file(
                    exported_file,
                    self._exiftool_json_sidecar(
                        use_albums_as_keywords=use_albums_as_keywords,
                        use_persons_as_keywords=use_persons_as_keywords,
                        keyword_template=keyword_template,
                        description_template=description_template,
                        ignore_date_modified=ignore_date_modified,
                        merge_exif_keywords=merge_exif_keywords,
                        merge_exif_persons=merge_exif_persons,
                        persons=persons,
                        location=location,
                        replace_keywords=replace_keywords,
                    ),
                )
                export_db.set_stat_exif_for_file(
                    exported_file, fileutil.file_sig(exported_file)
                )
                all_results.exif_updated.append(exported_file)
            else:
                verbose(f"Skipped up to date exiftool metadata for {exported_file}")
    elif exiftool and exif_files:
        for exported_file in exif_files:
            verbose(f"Writing metadata with exiftool for {exported_file}")
            if not dry_run:
                warning_, error_ = self._write_exif_data(
                    exported_file,
                    use_albums_as_keywords=use_albums_as_keywords,
                    use_persons_as_keywords=use_persons_as_keywords,
                    keyword_template=keyword_template,
                    description_template=description_template,
                    ignore_date_modified=ignore_date_modified,
                    flags=exiftool_flags,
                    merge_exif_keywords=merge_exif_keywords,
                    merge_exif_persons=merge_exif_persons,
                    persons=persons,
                    location=location,
                    replace_keywords=replace_keywords,
                )
                if warning_:
                    all_results.exiftool_warning.append((exported_file, warning_))
                if error_:
                    all_results.exiftool_error.append((exported_file, error_))
                    all_results.error.append((exported_file, error_))

            export_db.set_exifdata_for_file(
                exported_file,
                self._exiftool_json_sidecar(
                    use_albums_as_keywords=use_albums_as_keywords,
                    use_persons_as_keywords=use_persons_as_keywords,
                    keyword_template=keyword_template,
                    description_template=description_template,
                    ignore_date_modified=ignore_date_modified,
                    merge_exif_keywords=merge_exif_keywords,
                    merge_exif_persons=merge_exif_persons,
                    persons=persons,
                    location=location,
                    replace_keywords=replace_keywords,
                ),
            )
            export_db.set_stat_exif_for_file(
                exported_file, fileutil.file_sig(exported_file)
            )
            all_results.exif_updated.append(exported_file)

    if touch_file:
        for exif_file in all_results.exif_updated:
            verbose(f"Updating file modification time for {exif_file}")
            all_results.touched.append(exif_file)
            ts = int(self.date.timestamp())
            fileutil.utime(exif_file, (ts, ts))

    all_results.touched = list(set(all_results.touched))

    all_results.sidecar_json_written = sidecar_json_files_written
    all_results.sidecar_json_skipped = sidecar_json_files_skipped
    all_results.sidecar_exiftool_written = sidecar_exiftool_files_written
    all_results.sidecar_exiftool_skipped = sidecar_exiftool_files_skipped
    all_results.sidecar_xmp_written = sidecar_xmp_files_written
    all_results.sidecar_xmp_skipped = sidecar_xmp_files_skipped

    return all_results


def _export_photo_with_photos_export(
    self,
    dest,
    filename,
    all_results,
    fileutil,
    export_db,
    use_photokit=None,
    dry_run=None,
    timeout=None,
    jpeg_ext=None,
    touch_file=None,
    update=None,
    overwrite=None,
    live_photo=None,
    edited=None,
    edited_identifier=None,
    convert_to_jpeg=None,
    jpeg_quality=1.0,
):
    # TODO: duplicative code with the if edited/else--remove it
    # export live_photo .mov file?
    live_photo = bool(live_photo and self.live_photo)
    overwrite = overwrite or update
    if edited or self.shared:
        # exported edited version and not original
        # shared photos (in shared albums) show up as not having adjustments (not edited)
        # but Photos is unable to export the "original" as only a jpeg copy is shared in iCloud
        # so tell Photos to export the current version in this case
        if filename:
            # use filename stem provided
            filestem = dest.stem
        else:
            # didn't get passed a filename, add _edited
            filestem = f"{dest.stem}{edited_identifier}"
            uti = self.uti_edited if edited and self.uti_edited else self.uti
            ext = get_preferred_uti_extension(uti)
            dest = dest.parent / f"{filestem}{ext}"

        if use_photokit:
            photolib = PhotoLibrary()
            photo = None
            try:
                photo = photolib.fetch_uuid(self.uuid)
            except PhotoKitFetchFailed as e:
                # if failed to find UUID, might be a burst photo
                if self.burst and self._info["burstUUID"]:
                    bursts = photolib.fetch_burst_uuid(
                        self._info["burstUUID"], all=True
                    )
                    # PhotoKit UUIDs may contain "/L0/001" so only look at beginning
                    photo = [p for p in bursts if p.uuid.startswith(self.uuid)]
                    photo = photo[0] if photo else None
                if not photo:
                    all_results.error.append(
                        (
                            str(dest),
                            f"PhotoKitFetchFailed exception exporting photo {self.uuid}: {e} ({lineno(__file__)})",
                        )
                    )
            if photo:
                if dry_run:
                    # dry_run, don't actually export
                    all_results.exported.append(str(dest))
                else:
                    try:
                        exported = photo.export(
                            dest.parent, dest.name, version=PHOTOS_VERSION_CURRENT, overwrite=overwrite
                        )
                        all_results.exported.extend(exported)
                    except Exception as e:
                        all_results.error.append(
                            (str(dest), f"{e} ({lineno(__file__)})")
                        )
        else:
            try:
                exported = _export_photo_uuid_applescript(
                    self.uuid,
                    dest.parent,
                    filestem=filestem,
                    original=False,
                    edited=True,
                    live_photo=live_photo,
                    timeout=timeout,
                    burst=self.burst,
                    dry_run=dry_run,
                )
                all_results.exported.extend(exported)
            except ExportError as e:
                all_results.error.append((str(dest), f"{e} ({lineno(__file__)})"))
    else:
        # export original version and not edited
        filestem = dest.stem
        if use_photokit:
            photolib = PhotoLibrary()
            photo = None
            try:
                photo = photolib.fetch_uuid(self.uuid)
            except PhotoKitFetchFailed:
                # if failed to find UUID, might be a burst photo
                if self.burst and self._info["burstUUID"]:
                    bursts = photolib.fetch_burst_uuid(
                        self._info["burstUUID"], all=True
                    )
                    # PhotoKit UUIDs may contain "/L0/001" so only look at beginning
                    photo = [p for p in bursts if p.uuid.startswith(self.uuid)]
                    photo = photo[0] if photo else None
            if photo:
                if not dry_run:
                    try:
                        exported = photo.export(
                            dest.parent, dest.name, version=PHOTOS_VERSION_ORIGINAL, overwrite=overwrite
                        )
                        all_results.exported.extend(exported)
                    except Exception as e:
                        all_results.error.append(
                            (str(dest), f"{e} ({lineno(__file__)})")
                        )
                else:
                    # dry_run, don't actually export
                    all_results.exported.append(str(dest))
        else:
            try:
                exported = _export_photo_uuid_applescript(
                    self.uuid,
                    dest.parent,
                    filestem=filestem,
                    original=True,
                    edited=False,
                    live_photo=live_photo,
                    timeout=timeout,
                    burst=self.burst,
                    dry_run=dry_run,
                )
                all_results.exported.extend(exported)
            except ExportError as e:
                all_results.error.append((str(dest), f"{e} ({lineno(__file__)})"))
    if all_results.exported:
        for idx, photopath in enumerate(all_results.exported):
            converted_stat = (None, None, None)
            photopath = pathlib.Path(photopath)
            if convert_to_jpeg and self.isphoto:
                # if passed convert_to_jpeg=True, will assume the photo is a photo and not already a jpeg
                if photopath.suffix.lower() not in LIVE_VIDEO_EXTENSIONS:
                    dest_str = photopath.parent / f"{photopath.stem}.jpeg"
                    fileutil.convert_to_jpeg(
                        photopath, dest_str, compression_quality=jpeg_quality
                    )
                    converted_stat = fileutil.file_sig(dest_str)
                    fileutil.unlink(photopath)
                    all_results.exported[idx] = dest_str
                    all_results.converted_to_jpeg.append(dest_str)
                    photopath = dest_str

            photopath = str(photopath)
            export_db.set_data(
                filename=photopath,
                uuid=self.uuid,
                orig_stat=fileutil.file_sig(photopath),
                exif_stat=(None, None, None),
                converted_stat=converted_stat,
                edited_stat=(None, None, None),
                info_json=self.json(),
                exif_json=None,
            )

            # todo: handle signatures
        if jpeg_ext:
            # use_photos_export (both PhotoKit and AppleScript) don't use the
            # file extension provided (instead they use extension for UTI)
            # so if jpeg_ext is set, rename any non-conforming jpegs
            all_results.exported = rename_jpeg_files(
                all_results.exported, jpeg_ext, fileutil
            )
        if touch_file:
            for exported_file in all_results.exported:
                all_results.touched.append(exported_file)
                ts = int(self.date.timestamp())
                fileutil.utime(exported_file, (ts, ts))
        if update:
            all_results.new.extend(all_results.exported)


def _export_photo(
    self,
    src,
    dest,
    update,
    export_db,
    overwrite,
    export_as_hardlink,
    exiftool,
    touch_file,
    convert_to_jpeg,
    fileutil=FileUtil,
    edited=False,
    jpeg_quality=1.0,
    ignore_signature=None,
):
    """Helper function for export()
        Does the actual copy or hardlink taking the appropriate
        action depending on update, overwrite, export_as_hardlink
        Assumes destination is the right destination (e.g. UUID matches)
        sets UUID and JSON info foo exported file using set_uuid_for_file, set_inf_for_uuido

    Args:
        src: src path (string)
        dest: dest path (pathlib.Path)
        update: bool
        export_db: instance of ExportDB that conforms to ExportDB_ABC interface
        overwrite: bool
        export_as_hardlink: bool
        exiftool: bool
        touch_file: bool
        convert_to_jpeg: bool; if True, convert file to jpeg on export
        fileutil: FileUtil class that conforms to fileutil.FileUtilABC
        edited: bool; set to True if exporting edited version of photo
        jpeg_quality: float in range 0.0 <= jpeg_quality <= 1.0.  A value of 1.0 specifies use best quality, a value of 0.0 specifies use maximum compression.
        ignore_signature: bool, ignore file signature when used with update (look only at filename)

    Returns:
        ExportResults

    Raises:
        ValueError if export_as_hardlink and convert_to_jpeg both True
    """

    if export_as_hardlink and convert_to_jpeg:
        raise ValueError("export_as_hardlink and convert_to_jpeg cannot both be True")

    exported_files = []
    update_updated_files = []
    update_new_files = []
    update_skipped_files = []
    touched_files = []
    converted_to_jpeg_files = []

    dest_str = str(dest)
    dest_exists = dest.exists()

    if update:  # updating
        cmp_touch, cmp_orig = False, False
        if dest_exists:
            # update, destination exists, but we might not need to replace it...
            if ignore_signature:
                cmp_orig = True
                cmp_touch = fileutil.cmp(src, dest, mtime1=int(self.date.timestamp()))
            elif exiftool:
                sig_exif = export_db.get_stat_exif_for_file(dest_str)
                cmp_orig = fileutil.cmp_file_sig(dest_str, sig_exif)
                sig_exif = (sig_exif[0], sig_exif[1], int(self.date.timestamp()))
                cmp_touch = fileutil.cmp_file_sig(dest_str, sig_exif)
            elif convert_to_jpeg:
                sig_converted = export_db.get_stat_converted_for_file(dest_str)
                cmp_orig = fileutil.cmp_file_sig(dest_str, sig_converted)
                sig_converted = (
                    sig_converted[0],
                    sig_converted[1],
                    int(self.date.timestamp()),
                )
                cmp_touch = fileutil.cmp_file_sig(dest_str, sig_converted)
            else:
                cmp_orig = fileutil.cmp(src, dest)
                cmp_touch = fileutil.cmp(src, dest, mtime1=int(self.date.timestamp()))

            sig_cmp = cmp_touch if touch_file else cmp_orig

            if edited:
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

            if (export_as_hardlink and dest.samefile(src)) or (
                not export_as_hardlink and not dest.samefile(src) and sig_cmp
            ):
                # destination exists and signatures match, skip it
                update_skipped_files.append(dest_str)
            else:
                # destination exists but signature is different
                if touch_file and cmp_orig and not cmp_touch:
                    # destination exists, signature matches original but does not match expected touch time
                    # skip exporting but update touch time
                    update_skipped_files.append(dest_str)
                    touched_files.append(dest_str)
                elif not touch_file and cmp_touch and not cmp_orig:
                    # destination exists, signature matches expected touch but not original
                    # user likely exported with touch_file and is now exporting without touch_file
                    # don't update the file because it's same but leave touch time
                    update_skipped_files.append(dest_str)
                else:
                    # destination exists but is different
                    update_updated_files.append(dest_str)
                    if touch_file:
                        touched_files.append(dest_str)

        else:
            # update, destination doesn't exist (new file)
            update_new_files.append(dest_str)
            if touch_file:
                touched_files.append(dest_str)
    else:
        # not update, export the file
        exported_files.append(dest_str)
        if touch_file:
            sig = fileutil.file_sig(src)
            sig = (sig[0], sig[1], int(self.date.timestamp()))
            if not fileutil.cmp_file_sig(src, sig):
                touched_files.append(dest_str)
    if not update_skipped_files:
        converted_stat = (None, None, None)
        edited_stat = fileutil.file_sig(src) if edited else (None, None, None)
        if dest_exists and (update or overwrite):
            # need to remove the destination first
            fileutil.unlink(dest)
        if export_as_hardlink:
            fileutil.hardlink(src, dest)
        elif convert_to_jpeg:
            # use convert_to_jpeg to export the file
            fileutil.convert_to_jpeg(src, dest_str, compression_quality=jpeg_quality)
            converted_stat = fileutil.file_sig(dest_str)
            converted_to_jpeg_files.append(dest_str)
        else:
            fileutil.copy(src, dest_str)

        export_db.set_data(
            filename=dest_str,
            uuid=self.uuid,
            orig_stat=fileutil.file_sig(dest_str),
            exif_stat=(None, None, None),
            converted_stat=converted_stat,
            edited_stat=edited_stat,
            info_json=self.json(),
            exif_json=None,
        )

    if touched_files:
        ts = int(self.date.timestamp())
        fileutil.utime(dest, (ts, ts))

    return ExportResults(
        exported=exported_files + update_new_files + update_updated_files,
        new=update_new_files,
        updated=update_updated_files,
        skipped=update_skipped_files,
        exif_updated=[],
        touched=touched_files,
        converted_to_jpeg=converted_to_jpeg_files,
        sidecar_json_written=[],
        sidecar_json_skipped=[],
        sidecar_exiftool_written=[],
        sidecar_exiftool_skipped=[],
        sidecar_xmp_written=[],
        sidecar_xmp_skipped=[],
        missing=[],
        error=[],
    )


def _write_exif_data(
    self,
    filepath,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
    ignore_date_modified=False,
    flags=None,
    merge_exif_keywords=False,
    merge_exif_persons=False,
    persons=True,
    location=True,
    replace_keywords=False,
):
    """write exif data to image file at filepath

    Args:
        filepath: full path to the image file
        use_albums_as_keywords: treat album names as keywords
        use_persons_as_keywords: treat person names as keywords
        keyword_template: (list of strings); list of template strings to render as keywords
        ignore_date_modified: if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set
        flags: optional list of exiftool flags to prepend to exiftool command when writing metadata (e.g. -m or -F)
        persons: if True, write person data to metadata
        location: if True, write location data to metadata
        replace_keywords: if True, keyword_template replaces any keywords, otherwise it's additive

    Returns:
        (warning, error) of warning and error strings if exiftool produces warnings or errors
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Could not find file {filepath}")
    exif_info = self._exiftool_dict(
        use_albums_as_keywords=use_albums_as_keywords,
        use_persons_as_keywords=use_persons_as_keywords,
        keyword_template=keyword_template,
        description_template=description_template,
        ignore_date_modified=ignore_date_modified,
        merge_exif_keywords=merge_exif_keywords,
        merge_exif_persons=merge_exif_persons,
        persons=persons,
        location=location,
        replace_keywords=replace_keywords,
    )

    with ExifTool(filepath, flags=flags, exiftool=self._db._exiftool_path) as exiftool:
        for exiftag, val in exif_info.items():
            if type(val) == list:
                for v in val:
                    exiftool.setvalue(exiftag, v)
            else:
                exiftool.setvalue(exiftag, val)
    return exiftool.warning, exiftool.error


def _exiftool_dict(
    self,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
    ignore_date_modified=False,
    merge_exif_keywords=False,
    merge_exif_persons=False,
    filename=None,
    persons=True,
    location=True,
    replace_keywords=False,
):
    """Return dict of EXIF details for building exiftool JSON sidecar or sending commands to ExifTool.
        Does not include all the EXIF fields as those are likely already in the image.

    Args:
        filename: name of source image file (without path); if not None, exiftool JSON signature will be included; if None, signature will not be included
        use_albums_as_keywords: treat album names as keywords
        use_persons_as_keywords: treat person names as keywords
        keyword_template: (list of strings); list of template strings to render as keywords
        description_template: (list of strings); list of template strings to render for the description
        ignore_date_modified: if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set
        merge_exif_keywords: merge keywords in the file's exif metadata (requires exiftool)
        merge_exif_persons: merge persons in the file's exif metadata (requires exiftool)
        persons: if True, include person data
        location: if True, include location data
        replace_keywords: if True, keyword_template replaces any keywords, otherwise it's additive

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

    exif = (
        {
            "SourceFile": filename,
            "ExifTool:ExifToolVersion": "12.00",
            "File:FileName": filename,
        }
        if filename is not None
        else {}
    )

    if description_template is not None:
        rendered = self.render_template(
            description_template, expand_inplace=True, inplace_sep=", "
        )[0]
        description = " ".join(rendered) if rendered else ""
        exif["EXIF:ImageDescription"] = description
        exif["XMP:Description"] = description
        exif["IPTC:Caption-Abstract"] = description
    elif self.description:
        exif["EXIF:ImageDescription"] = self.description
        exif["XMP:Description"] = self.description
        exif["IPTC:Caption-Abstract"] = self.description

    if self.title:
        exif["XMP:Title"] = self.title
        exif["IPTC:ObjectName"] = self.title

    keyword_list = []
    if merge_exif_keywords:
        keyword_list.extend(self._get_exif_keywords())

    if self.keywords and not replace_keywords:
        keyword_list.extend(self.keywords)

    person_list = []
    if persons:
        if merge_exif_persons:
            person_list.extend(self._get_exif_persons())

        if self.persons:
            # filter out _UNKNOWN_PERSON
            person_list.extend([p for p in self.persons if p != _UNKNOWN_PERSON])

        if use_persons_as_keywords and person_list:
            keyword_list.extend(person_list)

    if use_albums_as_keywords and self.albums:
        keyword_list.extend(self.albums)

    if keyword_template:
        rendered_keywords = []
        for template_str in keyword_template:
            rendered, unmatched = self.render_template(
                template_str, none_str=_OSXPHOTOS_NONE_SENTINEL, path_sep="/"
            )
            if unmatched:
                logging.warning(
                    f"Unmatched template substitution for template: {template_str} {unmatched}"
                )
            rendered_keywords.extend(rendered)

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
        keyword_list = sorted(list(set([str(keyword) for keyword in keyword_list])))
        exif["IPTC:Keywords"] = keyword_list.copy()
        exif["XMP:Subject"] = keyword_list.copy()
        exif["XMP:TagsList"] = keyword_list.copy()

    if persons and person_list:
        person_list = sorted(list(set(person_list)))
        exif["XMP:PersonInImage"] = person_list.copy()

    # if self.favorite():
    #     exif["Rating"] = 5

    if location:
        (lat, lon) = self.location
        if lat is not None and lon is not None:
            if self.isphoto:
                exif["EXIF:GPSLatitude"] = lat
                exif["EXIF:GPSLongitude"] = lon
                lat_ref = "N" if lat >= 0 else "S"
                lon_ref = "E" if lon >= 0 else "W"
                exif["EXIF:GPSLatitudeRef"] = lat_ref
                exif["EXIF:GPSLongitudeRef"] = lon_ref
            elif self.ismovie:
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

    date = self.date
    offsettime = date.strftime("%z")
    # find timezone offset in format "-04:00"
    offset = re.findall(r"([+-]?)([\d]{2})([\d]{2})", offsettime)
    offset = offset[0]  # findall returns list of tuples
    offsettime = f"{offset[0]}{offset[1]}:{offset[2]}"

    # exiftool expects format to "2015:01:18 12:00:00"
    datetimeoriginal = date.strftime("%Y:%m:%d %H:%M:%S")

    if self.isphoto:
        exif["EXIF:DateTimeOriginal"] = datetimeoriginal
        exif["EXIF:CreateDate"] = datetimeoriginal
        exif["EXIF:OffsetTimeOriginal"] = offsettime

        dateoriginal = date.strftime("%Y:%m:%d")
        exif["IPTC:DateCreated"] = dateoriginal

        timeoriginal = date.strftime(f"%H:%M:%S{offsettime}")
        exif["IPTC:TimeCreated"] = timeoriginal

        if self.date_modified is not None and not ignore_date_modified:
            exif["EXIF:ModifyDate"] = self.date_modified.strftime("%Y:%m:%d %H:%M:%S")
        else:
            exif["EXIF:ModifyDate"] = self.date.strftime("%Y:%m:%d %H:%M:%S")
    elif self.ismovie:
        # QuickTime spec specifies times in UTC
        # QuickTime:CreateDate and ModifyDate are in UTC w/ no timezone
        # QuickTime:CreationDate must include time offset or Photos shows invalid values
        # reference: https://exiftool.org/TagNames/QuickTime.html#Keys
        #            https://exiftool.org/forum/index.php?topic=11927.msg64369#msg64369
        exif["QuickTime:CreationDate"] = f"{datetimeoriginal}{offsettime}"

        date_utc = datetime_tz_to_utc(date)
        creationdate = date_utc.strftime("%Y:%m:%d %H:%M:%S")
        exif["QuickTime:CreateDate"] = creationdate
        if self.date_modified is None or ignore_date_modified:
            exif["QuickTime:ModifyDate"] = creationdate
        else:
            exif["QuickTime:ModifyDate"] = datetime_tz_to_utc(
                self.date_modified
            ).strftime("%Y:%m:%d %H:%M:%S")

    # remove any new lines in any fields
    for field, val in exif.items():
        if type(val) == str:
            exif[field] = val.replace("\n", " ")
        elif type(val) == list:
            exif[field] = [str(v).replace("\n", " ") for v in val if v is not None]
    return exif


def _get_exif_keywords(self):
    """returns list of keywords found in the file's exif metadata"""
    keywords = []
    exif = self.exiftool
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
    exif = self.exiftool
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
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
    ignore_date_modified=False,
    tag_groups=True,
    merge_exif_keywords=False,
    merge_exif_persons=False,
    filename=None,
    persons=True,
    location=True,
    replace_keywords=False,
):
    """Return dict of EXIF details for building exiftool JSON sidecar or sending commands to ExifTool.
        Does not include all the EXIF fields as those are likely already in the image.

    Args:
        use_albums_as_keywords: treat album names as keywords
        use_persons_as_keywords: treat person names as keywords
        keyword_template: (list of strings); list of template strings to render as keywords
        description_template: (list of strings); list of template strings to render for the description
        ignore_date_modified: if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set
        tag_groups: if True, tags are in form Group:TagName, e.g. IPTC:Keywords, otherwise group name is omitted, e.g. Keywords
        merge_exif_keywords: boolean; if True, merged keywords found in file's exif data (requires exiftool)
        merge_exif_persons: boolean; if True, merged persons found in file's exif data (requires exiftool)
        filename: filename of the destination image file for including in exiftool signature in JSON sidecar
        persons: if True, include person data
        location: if True, include location data
        replace_keywords: if True, keyword_template replaces any keywords, otherwise it's additive

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
    exif = self._exiftool_dict(
        use_albums_as_keywords=use_albums_as_keywords,
        use_persons_as_keywords=use_persons_as_keywords,
        keyword_template=keyword_template,
        description_template=description_template,
        ignore_date_modified=ignore_date_modified,
        merge_exif_keywords=merge_exif_keywords,
        merge_exif_persons=merge_exif_persons,
        filename=filename,
        persons=persons,
        location=location,
        replace_keywords=replace_keywords,
    )

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
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
    extension=None,
    merge_exif_keywords=False,
    merge_exif_persons=False,
    persons=True,
    location=True,
    replace_keywords=False,
):
    """returns string for XMP sidecar
    use_albums_as_keywords: treat album names as keywords
    use_persons_as_keywords: treat person names as keywords
    keyword_template: (list of strings); list of template strings to render as keywords
    description_template: string; optional template string that will be rendered for use as photo description
    extension: which extension to use for SidecarForExtension property
    merge_exif_keywords: boolean; if True, merged keywords found in file's exif data (requires exiftool)
    merge_exif_persons: boolean; if True, merged persons found in file's exif data (requires exiftool)
    persons: if True, include person data
    location: if True, include location data
    replace_keywords: if True, keyword_template replaces any keywords, otherwise it's additive
    """

    xmp_template_file = (
        _XMP_TEMPLATE_NAME if not self._db._beta else _XMP_TEMPLATE_NAME_BETA
    )
    xmp_template = Template(filename=os.path.join(_TEMPLATE_DIR, xmp_template_file))

    if extension is None:
        extension = pathlib.Path(self.original_filename)
        extension = extension.suffix[1:] if extension.suffix else None

    if description_template is not None:
        rendered = self.render_template(
            description_template, expand_inplace=True, inplace_sep=", "
        )[0]
        description = " ".join(rendered) if rendered else ""
    else:
        description = self.description if self.description is not None else ""

    keyword_list = []
    if merge_exif_keywords:
        keyword_list.extend(self._get_exif_keywords())

    if self.keywords and not replace_keywords:
        keyword_list.extend(self.keywords)

    # TODO: keyword handling in this and _exiftool_json_sidecar is
    # good candidate for pulling out in a function

    person_list = []
    if persons:
        if merge_exif_persons:
            person_list.extend(self._get_exif_persons())

        if self.persons:
            # filter out _UNKNOWN_PERSON
            person_list.extend([p for p in self.persons if p != _UNKNOWN_PERSON])

        if use_persons_as_keywords and person_list:
            keyword_list.extend(person_list)

    if use_albums_as_keywords and self.albums:
        keyword_list.extend(self.albums)

    if keyword_template:
        rendered_keywords = []
        for template_str in keyword_template:
            rendered, unmatched = self.render_template(
                template_str, none_str=_OSXPHOTOS_NONE_SENTINEL, path_sep="/"
            )
            if unmatched:
                logging.warning(
                    f"Unmatched template substitution for template: {template_str} {unmatched}"
                )
            rendered_keywords.extend(rendered)

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
    if persons and person_list:
        person_list = sorted(list(set(person_list)))

    subject_list = keyword_list

    if location:
        latlon = self.location

    xmp_str = xmp_template.render(
        photo=self,
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
