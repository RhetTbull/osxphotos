""" Export methods for PhotoInfo 
    The following methods are defined and must be imported into PhotoInfo as instance methods:
    export
    export2
    _export_photo
    _write_exif_data
    _exiftool_json_sidecar
    _exiftool_dict
    _xmp_sidecar
    _write_sidecar
    """

# TODO: should this be its own PhotoExporter class?

import glob
import json
import logging
import os
import pathlib
import re
import tempfile
from collections import namedtuple  # pylint: disable=syntax-error

from mako.template import Template

from .._applescript import AppleScript
from .._constants import (
    _MAX_IPTC_KEYWORD_LEN,
    _OSXPHOTOS_NONE_SENTINEL,
    _TEMPLATE_DIR,
    _UNKNOWN_PERSON,
    _XMP_TEMPLATE_NAME,
)
from ..export_db import ExportDBNoOp
from ..exiftool import ExifTool
from ..fileutil import FileUtil
from ..utils import dd_to_dms_str, findfiles

ExportResults = namedtuple(
    "ExportResults",
    ["exported", "new", "updated", "skipped", "exif_updated", "touched"],
)


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
    """ Export photo to dest path using applescript to control Photos
        If photo is a live photo, exports both the photo and associated .mov file
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
        Note: For Live Photos, if edited=True, will export a jpeg but not the movie, even if photo
              has not been edited. This is due to how Photos Applescript interface works.
    """

    # setup the applescript to do the export
    export_scpt = AppleScript(
        """ 
		on export_by_uuid(theUUID, thePath, original, edited, theTimeOut)
			tell application "Photos"
				set thePath to thePath
				set theItem to media item id theUUID
				set theFilename to filename of theItem
				set itemList to {theItem}
				
				if original then
					with timeout of theTimeOut seconds
						export itemList to POSIX file thePath with using originals
					end timeout
				end if
				
				if edited then
					with timeout of theTimeOut seconds
						export itemList to POSIX file thePath
					end timeout
				end if
				
				return theFilename
			end tell

		end export_by_uuid
		"""
    )

    dest = pathlib.Path(dest)
    if not dest.is_dir():
        raise ValueError(f"dest {dest} must be a directory")

    if not original ^ edited:
        raise ValueError(f"edited or original must be True but not both")

    tmpdir = tempfile.TemporaryDirectory(prefix="osxphotos_")

    # export original
    filename = None
    try:
        filename = export_scpt.call(
            "export_by_uuid", uuid, tmpdir.name, original, edited, timeout
        )
    except Exception as e:
        logging.warning(f"Error exporting uuid {uuid}: {e}")
        return None

    if filename is not None:
        # need to find actual filename as sometimes Photos renames JPG to jpeg on export
        # may be more than one file exported (e.g. if Live Photo, Photos exports both .jpeg and .mov)
        # TemporaryDirectory will cleanup on return
        filename_stem = pathlib.Path(filename).stem
        files = glob.glob(os.path.join(tmpdir.name, "*"))
        exported_paths = []
        for fname in files:
            path = pathlib.Path(fname)
            if len(files) > 1 and not live_photo and path.suffix.lower() == ".mov":
                # it's the .mov part of live photo but not requested, so don't export
                logging.debug(f"Skipping live photo file {path}")
                continue
            if len(files) > 1 and burst and path.stem != filename_stem:
                # skip any burst photo that's not the one we asked for
                logging.debug(f"Skipping burst photo file {path}")
                continue
            if filestem:
                # rename the file based on filestem, keeping original extension
                dest_new = dest / f"{filestem}{path.suffix}"
            else:
                # use the name Photos provided
                dest_new = dest / path.name
            logging.debug(f"exporting {path} to dest_new: {dest_new}")
            if not dry_run:
                FileUtil.copy(str(path), str(dest_new))
            exported_paths.append(str(dest_new))
        return exported_paths
    else:
        return None


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
    sidecar_xmp=False,
    use_photos_export=False,
    timeout=120,
    exiftool=False,
    no_xattr=False,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
):
    """ export photo 
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
        sidecar_json: (boolean, default = False); if True will also write a json sidecar with IPTC data in format readable by exiftool
                    sidecar filename will be dest/filename.json 
        sidecar_xmp: (boolean, default = False); if True will also write a XMP sidecar with IPTC data 
                    sidecar filename will be dest/filename.xmp 
        use_photos_export: (boolean, default=False); if True will attempt to export photo via applescript interaction with Photos
        timeout: (int, default=120) timeout in seconds used with use_photos_export
        exiftool: (boolean, default = False); if True, will use exiftool to write metadata to export file
        no_xattr: (boolean, default = False); if True, exports file without preserving extended attributes
        returns list of full paths to the exported files
        use_albums_as_keywords: (boolean, default = False); if True, will include album names in keywords
        when exporting metadata with exiftool or sidecar
        use_persons_as_keywords: (boolean, default = False); if True, will include person names in keywords
        when exporting metadata with exiftool or sidecar
        keyword_template: (list of strings); list of template strings that will be rendered as used as keywords
        description_template: string; optional template string that will be rendered for use as photo description
        returns: list of photos exported
        """

    # Implementation note: calls export2 to actually do the work

    results = self.export2(
        dest,
        *filename,
        edited=edited,
        live_photo=live_photo,
        raw_photo=raw_photo,
        export_as_hardlink=export_as_hardlink,
        overwrite=overwrite,
        increment=increment,
        sidecar_json=sidecar_json,
        sidecar_xmp=sidecar_xmp,
        use_photos_export=use_photos_export,
        timeout=timeout,
        exiftool=exiftool,
        no_xattr=no_xattr,
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
    sidecar_json=False,
    sidecar_xmp=False,
    use_photos_export=False,
    timeout=120,
    exiftool=False,
    no_xattr=False,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
    update=False,
    export_db=None,
    fileutil=FileUtil,
    dry_run=False,
    touch_file=False,
    convert_to_jpeg=False,
    jpeg_quality=1.0,
    ignore_date_modified=False,
):
    """ export photo, like export but with update and dry_run options
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
        live_photo: (boolean, default=False); if True, will also export the associted .mov for live photos
        raw_photo: (boolean, default=False); if True, will also export the associted RAW photo
        export_as_hardlink: (boolean, default=False); if True, will hardlink files instead of copying them
        overwrite: (boolean, default=False); if True will overwrite files if they alreay exist 
        increment: (boolean, default=True); if True, will increment file name until a non-existant name is found 
                    if overwrite=False and increment=False, export will fail if destination file already exists 
        sidecar_json: (boolean, default = False); if True will also write a json sidecar with IPTC data in format readable by exiftool
                    sidecar filename will be dest/filename.json 
        sidecar_xmp: (boolean, default = False); if True will also write a XMP sidecar with IPTC data 
                    sidecar filename will be dest/filename.xmp 
        use_photos_export: (boolean, default=False); if True will attempt to export photo via applescript interaction with Photos
        timeout: (int, default=120) timeout in seconds used with use_photos_export
        exiftool: (boolean, default = False); if True, will use exiftool to write metadata to export file
        no_xattr: (boolean, default = False); if True, exports file without preserving extended attributes
        use_albums_as_keywords: (boolean, default = False); if True, will include album names in keywords
        when exporting metadata with exiftool or sidecar
        use_persons_as_keywords: (boolean, default = False); if True, will include person names in keywords
        when exporting metadata with exiftool or sidecar
        keyword_template: (list of strings); list of template strings that will be rendered as used as keywords
        description_template: string; optional template string that will be rendered for use as photo description
        update: (boolean, default=False); if True export will run in update mode, that is, it will
                not export the photo if the current version already exists in the destination
        export_db: (ExportDB_ABC); instance of a class that conforms to ExportDB_ABC with methods
                for getting/setting data related to exported files to compare update state
        fileutil: (FileUtilABC); class that conforms to FileUtilABC with various file utilities
        dry_run: (boolean, default=False); set to True to run in "dry run" mode
        touch_file: (boolean, default=False); if True, sets file's modification time upon photo date
        convert_to_jpeg: boolean; if True, converts non-jpeg images to jpeg
        jpeg_quality: float in range 0.0 <= jpeg_quality <= 1.0.  A value of 1.0 specifies use best quality, a value of 0.0 specifies use maximum compression.
        ignore_date_modified: for use with sidecar and exiftool; if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set

        Returns: ExportResults namedtuple with fields: exported, new, updated, skipped 
                    where each field is a list of file paths
        
        Note: to use dry run mode, you must set dry_run=True and also pass in memory version of export_db,
              and no-op fileutil (e.g. ExportDBInMemory and FileUtilNoOp)
            """

    # NOTE: This function is very complex and does a lot of things.
    # Don't modify this code if you don't fully understand everything it does.
    # TODO: This is a good candidate for refactoring.

    # when called from export(), won't get an export_db, so use no-op version
    if export_db is None:
        export_db = ExportDBNoOp()

    # suffix to add to edited files
    # e.g. name will be filename_edited.jpg
    edited_identifier = "_edited"

    # list of all files exported during this call to export
    exported_files = []

    # list of new files during update
    update_new_files = []

    # list of files that were updated
    update_updated_files = []

    # list of all files skipped because they do not need to be updated (for use with update=True)
    update_skipped_files = []

    # list of all files with utime touched (touch_file = True)
    touched_files = []

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
            fname = pathlib.Path(self.filename).stem + edited_identifier + edited_suffix
        else:
            fname = self.filename

    uti = self.uti if edited else self.uti_original
    if convert_to_jpeg and self.isphoto and uti != "public.jpeg":
        # not a jpeg but will convert to jpeg upon export so fix file extension
        fname_new = pathlib.Path(fname)
        fname = str(fname_new.parent / f"{fname_new.stem}.jpeg")
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
            if self.ismissing:
                logging.debug(
                    f"Attempting to export photo with ismissing=True: path = {self.path}"
                )

            if self.path is not None:
                src = self.path
            else:
                raise FileNotFoundError("Cannot export photo if path is None")

        if not os.path.isfile(src):
            raise FileNotFoundError(f"{src} does not appear to exist")

        if not _check_export_suffix(src, dest, edited):
            logging.debug(
                f"Invalid destination suffix: {dest.suffix} for {self.path}, "
                + f"edited={edited}, path_edited={self.path_edited}, "
                + f"original_filename={self.original_filename}, filename={self.filename}"
            )

        # found source now try to find right destination
        if update and dest.exists():
            # destination exists, check to see if destination is the right UUID
            dest_uuid = export_db.get_uuid_for_file(dest)
            if dest_uuid is None and fileutil.cmp(src, dest):
                # might be exporting into a pre-ExportDB folder or the DB got deleted
                logging.debug(
                    f"Found matching file with blank uuid: {self.uuid}, {dest}"
                )
                dest_uuid = self.uuid
                export_db.set_data(
                    dest,
                    self.uuid,
                    fileutil.file_sig(dest),
                    (None, None, None),
                    (None, None, None),
                    (None, None, None),
                    self.json(),
                    None,
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
                            dest,
                            self.uuid,
                            fileutil.file_sig(dest),
                            (None, None, None),
                            (None, None, None),
                            (None, None, None),
                            self.json(),
                            None,
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
            no_xattr,
            export_as_hardlink,
            exiftool,
            touch_file,
            convert_to_jpeg,
            fileutil=fileutil,
            edited=edited,
            jpeg_quality=jpeg_quality,
        )
        exported_files = results.exported
        update_new_files = results.new
        update_updated_files = results.updated
        update_skipped_files = results.skipped
        touched_files = results.touched

        # copy live photo associated .mov if requested
        if live_photo and self.live_photo:
            live_name = dest.parent / f"{dest.stem}.mov"
            src_live = self.path_live_photo

            if src_live is not None:
                logging.debug(
                    f"Exporting live photo video of {filename} as {live_name.name}"
                )
                results = self._export_photo(
                    src_live,
                    live_name,
                    update,
                    export_db,
                    overwrite,
                    no_xattr,
                    export_as_hardlink,
                    exiftool,
                    touch_file,
                    False,
                    fileutil=fileutil,
                )
                exported_files.extend(results.exported)
                update_new_files.extend(results.new)
                update_updated_files.extend(results.updated)
                update_skipped_files.extend(results.skipped)
                touched_files.extend(results.touched)
            else:
                logging.debug(f"Skipping missing live movie for {filename}")

        # copy associated RAW image if requested
        if raw_photo and self.has_raw:
            raw_path = pathlib.Path(self.path_raw)
            raw_ext = raw_path.suffix
            raw_name = dest.parent / f"{dest.stem}{raw_ext}"
            if raw_path is not None:
                logging.debug(f"Exporting RAW photo of {filename} as {raw_name.name}")
                results = self._export_photo(
                    raw_path,
                    raw_name,
                    update,
                    export_db,
                    overwrite,
                    no_xattr,
                    export_as_hardlink,
                    exiftool,
                    touch_file,
                    convert_to_jpeg,
                    fileutil=fileutil,
                    jpeg_quality=jpeg_quality,
                )
                exported_files.extend(results.exported)
                update_new_files.extend(results.new)
                update_updated_files.extend(results.updated)
                update_skipped_files.extend(results.skipped)
                touched_files.extend(results.touched)
            else:
                logging.debug(f"Skipping missing RAW photo for {filename}")
    else:
        # use_photo_export
        exported = []
        # export live_photo .mov file?
        live_photo = True if live_photo and self.live_photo else False
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
                dest = dest.parent / f"{filestem}.jpeg"

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
        else:
            # export original version and not edited
            filestem = dest.stem
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
        if exported:
            if touch_file:
                for exported_file in exported:
                    touched_files.append(exported_file)
                    ts = int(self.date.timestamp())
                    fileutil.utime(exported_file, (ts, ts))
            exported_files.extend(exported)
            if update:
                update_new_files.extend(exported)

        else:
            logging.warning(
                f"Error exporting photo {self.uuid} to {dest} with use_photos_export"
            )

    # export metadata
    if sidecar_json:
        logging.debug("writing exiftool_json_sidecar")
        sidecar_filename = dest.parent / pathlib.Path(f"{dest.stem}{dest.suffix}.json")
        sidecar_str = self._exiftool_json_sidecar(
            use_albums_as_keywords=use_albums_as_keywords,
            use_persons_as_keywords=use_persons_as_keywords,
            keyword_template=keyword_template,
            description_template=description_template,
            ignore_date_modified=ignore_date_modified,
        )
        if not dry_run:
            try:
                self._write_sidecar(sidecar_filename, sidecar_str)
            except Exception as e:
                logging.warning(f"Error writing json sidecar to {sidecar_filename}")
                raise e

    if sidecar_xmp:
        logging.debug("writing xmp_sidecar")
        sidecar_filename = dest.parent / pathlib.Path(f"{dest.stem}{dest.suffix}.xmp")
        sidecar_str = self._xmp_sidecar(
            use_albums_as_keywords=use_albums_as_keywords,
            use_persons_as_keywords=use_persons_as_keywords,
            keyword_template=keyword_template,
            description_template=description_template,
            extension=dest.suffix[1:] if dest.suffix else None,
        )
        if not dry_run:
            try:
                self._write_sidecar(sidecar_filename, sidecar_str)
            except Exception as e:
                logging.warning(f"Error writing xmp sidecar to {sidecar_filename}")
                raise e

    # if exiftool, write the metadata
    if update:
        exif_files = update_new_files + update_updated_files + update_skipped_files
    else:
        exif_files = exported_files

    exif_files_updated = []
    if exiftool and update and exif_files:
        for exported_file in exif_files:
            logging.debug(f"checking exif for {exported_file}")
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
                    )
                )[0]
                if old_data != current_data:
                    files_are_different = True

            if old_data is None or files_are_different:
                # didn't have old data, assume we need to write it
                # or files were different
                if not dry_run:
                    self._write_exif_data(
                        exported_file,
                        use_albums_as_keywords=use_albums_as_keywords,
                        use_persons_as_keywords=use_persons_as_keywords,
                        keyword_template=keyword_template,
                        description_template=description_template,
                        ignore_date_modified=ignore_date_modified,
                    )
                export_db.set_exifdata_for_file(
                    exported_file,
                    self._exiftool_json_sidecar(
                        use_albums_as_keywords=use_albums_as_keywords,
                        use_persons_as_keywords=use_persons_as_keywords,
                        keyword_template=keyword_template,
                        description_template=description_template,
                        ignore_date_modified=ignore_date_modified,
                    ),
                )
                export_db.set_stat_exif_for_file(
                    exported_file, fileutil.file_sig(exported_file)
                )
                exif_files_updated.append(exported_file)
    elif exiftool and exif_files:
        for exported_file in exif_files:
            if not dry_run:
                self._write_exif_data(
                    exported_file,
                    use_albums_as_keywords=use_albums_as_keywords,
                    use_persons_as_keywords=use_persons_as_keywords,
                    keyword_template=keyword_template,
                    description_template=description_template,
                    ignore_date_modified=ignore_date_modified,
                )

            export_db.set_exifdata_for_file(
                exported_file,
                self._exiftool_json_sidecar(
                    use_albums_as_keywords=use_albums_as_keywords,
                    use_persons_as_keywords=use_persons_as_keywords,
                    keyword_template=keyword_template,
                    description_template=description_template,
                    ignore_date_modified=ignore_date_modified,
                ),
            )
            export_db.set_stat_exif_for_file(
                exported_file, fileutil.file_sig(exported_file)
            )
            exif_files_updated.append(exported_file)

    if touch_file:
        for exif_file in exif_files_updated:
            touched_files.append(exif_file)
            ts = int(self.date.timestamp())
            fileutil.utime(exif_file, (ts, ts))

    touched_files = list(set(touched_files))

    results = ExportResults(
        exported_files,
        update_new_files,
        update_updated_files,
        update_skipped_files,
        exif_files_updated,
        touched_files,
    )
    return results


def _export_photo(
    self,
    src,
    dest,
    update,
    export_db,
    overwrite,
    no_xattr,
    export_as_hardlink,
    exiftool,
    touch_file,
    convert_to_jpeg,
    fileutil=FileUtil,
    edited=False,
    jpeg_quality=1.0,
):
    """ Helper function for export()
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
        no_xattr: don't copy extended attributes
        export_as_hardlink: bool
        exiftool: bool
        touch_file: bool
        convert_to_jpeg: bool; if True, convert file to jpeg on export
        fileutil: FileUtil class that conforms to fileutil.FileUtilABC
        edited: bool; set to True if exporting edited version of photo
        jpeg_quality: float in range 0.0 <= jpeg_quality <= 1.0.  A value of 1.0 specifies use best quality, a value of 0.0 specifies use maximum compression.

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

    dest_str = str(dest)
    dest_exists = dest.exists()
    op_desc = "export_as_hardlink" if export_as_hardlink else "export_by_copying"

    if update:  # updating
        cmp_touch, cmp_orig = False, False
        if dest_exists:
            # update, destination exists, but we might not need to replace it...
            if exiftool:
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
            logging.debug(f"Update: exporting new file with {op_desc} {src} {dest}")
            update_new_files.append(dest_str)
            if touch_file:
                touched_files.append(dest_str)
    else:
        # not update, export the file
        logging.debug(f"Exporting file with {op_desc} {src} {dest}")
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
            logging.debug(
                f"Update: removing existing file prior to {op_desc} {src} {dest}"
            )
            fileutil.unlink(dest)
        if export_as_hardlink:
            fileutil.hardlink(src, dest)
        elif convert_to_jpeg:
            # use convert_to_jpeg to export the file
            fileutil.convert_to_jpeg(src, dest_str, compression_quality=jpeg_quality)
            converted_stat = fileutil.file_sig(dest_str)
        else:
            fileutil.copy(src, dest_str, norsrc=no_xattr)

        export_db.set_data(
            dest_str,
            self.uuid,
            fileutil.file_sig(dest_str),
            (None, None, None),
            converted_stat,
            edited_stat,
            self.json(),
            None,
        )

    if touched_files:
        ts = int(self.date.timestamp())
        fileutil.utime(dest, (ts, ts))

    return ExportResults(
        exported_files + update_new_files + update_updated_files,
        update_new_files,
        update_updated_files,
        update_skipped_files,
        [],
        touched_files,
    )


def _write_exif_data(
    self,
    filepath,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
    ignore_date_modified=False,
):
    """ write exif data to image file at filepath

    Args:
        filepath: full path to the image file 
        use_albums_as_keywords: treat album names as keywords
        use_persons_as_keywords: treat person names as keywords
        keyword_template: (list of strings); list of template strings to render as keywords
        ignore_date_modified: if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Could not find file {filepath}")
    exif_info = self._exiftool_dict(
        use_albums_as_keywords=use_albums_as_keywords,
        use_persons_as_keywords=use_persons_as_keywords,
        keyword_template=keyword_template,
        description_template=description_template,
        ignore_date_modified=ignore_date_modified,
    )

    with ExifTool(filepath) as exiftool:
        for exiftag, val in exif_info.items():
            if exiftag == "_CreatedBy":
                continue
            elif type(val) == list:
                for v in val:
                    exiftool.setvalue(exiftag, v)
            else:
                exiftool.setvalue(exiftag, val)


def _exiftool_dict(
    self,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
    ignore_date_modified=False,
):
    """ Return dict of EXIF details for building exiftool JSON sidecar or sending commands to ExifTool.
        Does not include all the EXIF fields as those are likely already in the image.

    Args:
        use_albums_as_keywords: treat album names as keywords
        use_persons_as_keywords: treat person names as keywords
        keyword_template: (list of strings); list of template strings to render as keywords
        description_template: (list of strings); list of template strings to render for the description
        ignore_date_modified: if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set

    Returns: dict with exiftool tags / values

    Exports the following:
        EXIF:ImageDescription
        XMP:Description (may include template)
        XMP:Title
        XMP:TagsList
        IPTC:Keywords (may include album name, person name, or template)
        XMP:Subject
        XMP:PersonInImage
        EXIF:GPSLatitude, EXIF:GPSLongitude
        EXIF:GPSPosition
        EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef
        EXIF:DateTimeOriginal
        EXIF:OffsetTimeOriginal
        EXIF:ModifyDate
        IPTC:DateCreated
        IPTC:TimeCreated
    """

    exif = {}
    exif["_CreatedBy"] = "osxphotos, https://github.com/RhetTbull/osxphotos"
    if description_template is not None:
        description = self.render_template(
            description_template, expand_inplace=True, inplace_sep=", "
        )[0]
        exif["EXIF:ImageDescription"] = description
        exif["XMP:Description"] = description
    elif self.description:
        exif["EXIF:ImageDescription"] = self.description
        exif["XMP:Description"] = self.description

    if self.title:
        exif["XMP:Title"] = self.title

    keyword_list = []
    if self.keywords:
        keyword_list.extend(self.keywords)

    person_list = []
    if self.persons:
        # filter out _UNKNOWN_PERSON
        person_list = sorted([p for p in self.persons if p != _UNKNOWN_PERSON])

    if use_persons_as_keywords and person_list:
        keyword_list.extend(sorted(person_list))

    if use_albums_as_keywords and self.albums:
        keyword_list.extend(sorted(self.albums))

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
            logging.warning(
                f"Some keywords exceed max IPTC Keyword length of {_MAX_IPTC_KEYWORD_LEN}: {long_keywords}"
            )

        keyword_list.extend(rendered_keywords)

    if keyword_list:
        exif["XMP:TagsList"] = keyword_list.copy()
        exif["IPTC:Keywords"] = keyword_list.copy()

    if person_list:
        exif["XMP:PersonInImage"] = person_list.copy()

    if self.keywords or person_list:
        # Photos puts both keywords and persons in Subject when using "Export IPTC as XMP"
        # only use Photos' keywords for subject (e.g. don't include template values)
        exif["XMP:Subject"] = self.keywords.copy() + person_list.copy()

    # if self.favorite():
    #     exif["Rating"] = 5

    (lat, lon) = self.location
    if lat is not None and lon is not None:
        exif["EXIF:GPSLatitude"] = lat
        exif["EXIF:GPSLongitude"] = lon
        lat_ref = "N" if lat >= 0 else "S"
        lon_ref = "E" if lon >= 0 else "W"
        exif["EXIF:GPSLatitudeRef"] = lat_ref
        exif["EXIF:GPSLongitudeRef"] = lon_ref

    # process date/time and timezone offset
    # Photos exports the following fields and sets modify date to creation date
    # [EXIF]    Modify Date             : 2020:10:30 00:00:00
    # [EXIF]    Date/Time Original      : 2020:10:30 00:00:00
    # [EXIF]    Create Date             : 2020:10:30 00:00:00
    # [IPTC]    Digital Creation Date   : 2020:10:30
    # [IPTC]    Date Created            : 2020:10:30
    #
    # This code deviates from Photos in one regard:
    # if photo has modification date, use it otherwise use creation date
    date = self.date

    # exiftool expects format to "2015:01:18 12:00:00"
    datetimeoriginal = date.strftime("%Y:%m:%d %H:%M:%S")
    exif["EXIF:DateTimeOriginal"] = datetimeoriginal
    exif["EXIF:CreateDate"] = datetimeoriginal

    offsettime = date.strftime("%z")
    # find timezone offset in format "-04:00"
    offset = re.findall(r"([+-]?)([\d]{2})([\d]{2})", offsettime)
    offset = offset[0]  # findall returns list of tuples
    offsettime = f"{offset[0]}{offset[1]}:{offset[2]}"
    exif["EXIF:OffsetTimeOriginal"] = offsettime

    dateoriginal = date.strftime("%Y:%m:%d")
    exif["IPTC:DateCreated"] = dateoriginal

    timeoriginal = date.strftime(f"%H:%M:%S{offsettime}")
    exif["IPTC:TimeCreated"] = timeoriginal
    print(f"time = {timeoriginal}")

    if self.date_modified is not None and not ignore_date_modified:
        exif["EXIF:ModifyDate"] = self.date_modified.strftime("%Y:%m:%d %H:%M:%S")
    else:
        exif["EXIF:ModifyDate"] = self.date.strftime("%Y:%m:%d %H:%M:%S")

    return exif


def _exiftool_json_sidecar(
    self,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
    ignore_date_modified=False,
):
    """ Return dict of EXIF details for building exiftool JSON sidecar or sending commands to ExifTool.
        Does not include all the EXIF fields as those are likely already in the image.

    Args:
        use_albums_as_keywords: treat album names as keywords
        use_persons_as_keywords: treat person names as keywords
        keyword_template: (list of strings); list of template strings to render as keywords
        description_template: (list of strings); list of template strings to render for the description
        ignore_date_modified: if True, sets EXIF:ModifyDate to EXIF:DateTimeOriginal even if date_modified is set

    Returns: dict with exiftool tags / values

    Exports the following:
        EXIF:ImageDescription
        XMP:Description (may include template)
        XMP:Title
        XMP:TagsList
        IPTC:Keywords (may include album name, person name, or template)
        XMP:Subject
        XMP:PersonInImage
        EXIF:GPSLatitude, EXIF:GPSLongitude
        EXIF:GPSPosition
        EXIF:GPSLatitudeRef, EXIF:GPSLongitudeRef
        EXIF:DateTimeOriginal
        EXIF:OffsetTimeOriginal
        EXIF:ModifyDate
        IPTC:DigitalCreationDate
        IPTC:DateCreated
    """
    exif = self._exiftool_dict(
        use_albums_as_keywords=use_albums_as_keywords,
        use_persons_as_keywords=use_persons_as_keywords,
        keyword_template=keyword_template,
        description_template=description_template,
        ignore_date_modified=ignore_date_modified,
    )
    return json.dumps([exif])


def _xmp_sidecar(
    self,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
    description_template=None,
    extension=None,
):
    """ returns string for XMP sidecar 
        use_albums_as_keywords: treat album names as keywords
        use_persons_as_keywords: treat person names as keywords
        keyword_template: (list of strings); list of template strings to render as keywords 
        description_template: string; optional template string that will be rendered for use as photo description """

    xmp_template = Template(filename=os.path.join(_TEMPLATE_DIR, _XMP_TEMPLATE_NAME))

    if extension is None:
        extension = pathlib.Path(self.original_filename)
        extension = extension.suffix[1:] if extension.suffix else None

    if description_template is not None:
        description = self.render_template(
            description_template, expand_inplace=True, inplace_sep=", "
        )[0]
    else:
        description = self.description if self.description is not None else ""

    keyword_list = []
    if self.keywords:
        keyword_list.extend(self.keywords)

    # TODO: keyword handling in this and _exiftool_json_sidecar is
    # good candidate for pulling out in a function

    person_list = []
    if self.persons:
        # filter out _UNKNOWN_PERSON
        person_list = [p for p in self.persons if p != _UNKNOWN_PERSON]

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

        # check to see if any keywords too long
        long_keywords = [
            long_str
            for long_str in rendered_keywords
            if len(long_str) > _MAX_IPTC_KEYWORD_LEN
        ]
        if long_keywords:
            logging.warning(
                f"Some keywords exceed max IPTC Keyword length of {_MAX_IPTC_KEYWORD_LEN}: {long_keywords}"
            )

        keyword_list.extend(rendered_keywords)

    subject_list = []
    if self.keywords or person_list:
        # Photos puts both keywords and persons in Subject when using "Export IPTC as XMP"
        subject_list = list(self.keywords) + person_list

    xmp_str = xmp_template.render(
        photo=self,
        description=description,
        keywords=keyword_list,
        persons=person_list,
        subjects=subject_list,
        extension=extension,
    )

    # remove extra lines that mako inserts from template
    xmp_str = "\n".join([line for line in xmp_str.split("\n") if line.strip() != ""])
    return xmp_str


def _write_sidecar(self, filename, sidecar_str):
    """ write sidecar_str to filename
        used for exporting sidecar info """
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
