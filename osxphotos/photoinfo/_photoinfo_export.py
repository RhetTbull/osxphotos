""" Export methods for PhotoInfo 
    The following methods are defined and must be imported into PhotoInfo as instance methods:
    export
    export2
    _export_photo
    _write_exif_data
    _exiftool_json_sidecar
    _xmp_sidecar
    _write_sidecar
    """

# TODO: should this be its own PhotoExporter class?

import filecmp
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
from .._export_db import ExportDBNoOp
from ..exiftool import ExifTool
from ..fileutil import FileUtil
from ..utils import dd_to_dms_str

ExportResults = namedtuple(
    "ExportResults", ["exported", "new", "updated", "skipped", "exif_updated"]
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
    if not dest.is_dir:
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
    update=False,
    export_db=None,
    fileutil=FileUtil,
    dry_run=False,
):
    """ export photo, like export but with update and dry_run options
        dest: must be valid destination path or exception raised 
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
        update: (boolean, default=False); if True export will run in update mode, that is, it will
                not export the photo if the current version already exists in the destination
        export_db: (ExportDB_ABC); instance of a class that conforms to ExportDB_ABC with methods
                for getting/setting data related to exported files to compare update state
        fileutil: (FileUtilABC); class that conforms to FileUtilABC with various file utilities
        dry_run: (boolean, default=False); set to True to run in "dry run" mode

        Returns: ExportResults namedtuple with fields: exported, new, updated, skipped 
                    where each field is a list of file paths
        
        Note: to use dry run mode, you must set dry_run=True and also pass in memory version of export_db,
              and no-op fileutil (e.g. ExportDBInMemory and FileUtilNoOp)
            """

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
    else:
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
                    pathlib.Path(self.filename).stem + edited_identifier + edited_suffix
                )
            else:
                fname = self.filename

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
        glob_str = str(dest.parent / f"{dest.stem}*")
        dest_files = glob.glob(glob_str)
        dest_files = [pathlib.Path(f).stem for f in dest_files]
        dest_new = dest.stem
        while dest_new in dest_files:
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
            logging.warning(
                f"Invalid destination suffix: {dest.suffix} for {self.path}, "
                + f"edited={edited}, path_edited={self.path_edited}, "
                + f"original_filename={self.original_filename}, filename={self.filename}"
            )

        logging.debug(
            f"exporting {src} to {dest}, overwrite={overwrite}, increment={increment}, dest exists: {dest.exists()}"
        )

        # found source now try to find right destination
        if update and dest.exists():
            # destination exists, check to see if destination is the right UUID
            dest_uuid = export_db.get_uuid_for_file(dest)
            if dest_uuid is None and filecmp.cmp(src, dest):
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
                    self.json(),
                    None,
                )
            if dest_uuid != self.uuid:
                # not the right file, find the right one
                logging.debug(
                    f"Need to find right photo: uuid={self.uuid}, dest={dest_uuid}, dest={dest}, path={self.path}"
                )
                count = 1
                glob_str = str(dest.parent / f"{dest.stem} (*{dest.suffix}")
                dest_files = glob.glob(glob_str)
                found_match = False
                for file_ in dest_files:
                    dest_uuid = export_db.get_uuid_for_file(file_)
                    if dest_uuid == self.uuid:
                        logging.debug(
                            f"Found matching file for uuid: {dest_uuid}, {file_}"
                        )
                        dest = pathlib.Path(file_)
                        found_match = True
                        break
                    elif dest_uuid is None and filecmp.cmp(src, file_):
                        # files match, update the UUID
                        logging.debug(
                            f"Found matching file with blank uuid: {self.uuid}, {file_}"
                        )
                        dest = pathlib.Path(file_)
                        found_match = True
                        export_db.set_data(
                            dest,
                            self.uuid,
                            fileutil.file_sig(dest),
                            (None, None, None),
                            self.json(),
                            None,
                        )
                        break

                if not found_match:
                    logging.debug(
                        f"Didn't find destination match for uuid {self.uuid} {dest}"
                    )

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
                    logging.debug(f"New destination = {dest}, uuid = {self.uuid}")

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
            fileutil,
        )
        exported_files = results.exported
        update_new_files = results.new
        update_updated_files = results.updated
        update_skipped_files = results.skipped

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
                    fileutil,
                )
                exported_files.extend(results.exported)
                update_new_files.extend(results.new)
                update_updated_files.extend(results.updated)
                update_skipped_files.extend(results.skipped)
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
                    fileutil,
                )
                exported_files.extend(results.exported)
                update_new_files.extend(results.new)
                update_updated_files.extend(results.updated)
                update_skipped_files.extend(results.skipped)
            else:
                logging.debug(f"Skipping missing RAW photo for {filename}")
    else:
        # use_photo_export
        exported = None
        # export live_photo .mov file?
        live_photo = True if live_photo and self.live_photo else False
        if edited:
            # exported edited version and not original
            if filename:
                # use filename stem provided
                filestem = dest.stem
            else:
                # didn't get passed a filename, add _edited
                filestem = f"{dest.stem}_edited"
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

        if exported is not None:
            exported_files.extend(exported)
        else:
            logging.warning(
                f"Error exporting photo {self.uuid} to {dest} with use_photos_export"
            )

    # export metadata
    info = export_db.get_info_for_uuid(self.uuid)

    if sidecar_json:
        logging.debug("writing exiftool_json_sidecar")
        sidecar_filename = dest.parent / pathlib.Path(f"{dest.stem}.json")
        sidecar_str = self._exiftool_json_sidecar(
            use_albums_as_keywords=use_albums_as_keywords,
            use_persons_as_keywords=use_persons_as_keywords,
            keyword_template=keyword_template,
        )
        if not dry_run:
            try:
                self._write_sidecar(sidecar_filename, sidecar_str)
            except Exception as e:
                logging.warning(f"Error writing json sidecar to {sidecar_filename}")
                raise e

    if sidecar_xmp:
        logging.debug("writing xmp_sidecar")
        sidecar_filename = dest.parent / pathlib.Path(f"{dest.stem}.xmp")
        sidecar_str = self._xmp_sidecar(
            use_albums_as_keywords=use_albums_as_keywords,
            use_persons_as_keywords=use_persons_as_keywords,
            keyword_template=keyword_template,
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
                    )
                )[0]
                if old_data != current_data:
                    files_are_different = True

            if old_data is None or files_are_different:
                # didn't have old data, assume we need to write it
                # or files were different
                logging.debug(f"No exifdata for {exported_file}, writing it")
                if not dry_run:
                    self._write_exif_data(
                        exported_file,
                        use_albums_as_keywords=use_albums_as_keywords,
                        use_persons_as_keywords=use_persons_as_keywords,
                        keyword_template=keyword_template,
                    )
                export_db.set_exifdata_for_file(
                    exported_file,
                    self._exiftool_json_sidecar(
                        use_albums_as_keywords=use_albums_as_keywords,
                        use_persons_as_keywords=use_persons_as_keywords,
                        keyword_template=keyword_template,
                    ),
                )
                export_db.set_stat_exif_for_file(
                    exported_file, fileutil.file_sig(exported_file)
                )
                exif_files_updated.append(exported_file)
    elif exiftool and exif_files:
        for exported_file in exif_files:
            logging.debug(f"Writing exif data to {exported_file}")
            if not dry_run:
                self._write_exif_data(
                    exported_file,
                    use_albums_as_keywords=use_albums_as_keywords,
                    use_persons_as_keywords=use_persons_as_keywords,
                    keyword_template=keyword_template,
                )
            export_db.set_exifdata_for_file(
                exported_file,
                self._exiftool_json_sidecar(
                    use_albums_as_keywords=use_albums_as_keywords,
                    use_persons_as_keywords=use_persons_as_keywords,
                    keyword_template=keyword_template,
                ),
            )
            export_db.set_stat_exif_for_file(
                exported_file, fileutil.file_sig(exported_file)
            )
            exif_files_updated.append(exported_file)

    return ExportResults(
        exported_files,
        update_new_files,
        update_updated_files,
        update_skipped_files,
        exif_files_updated,
    )


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
    fileutil=FileUtil,
):
    """ Helper function for export()
        Does the actual copy or hardlink taking the appropriate 
        action depending on update, overwrite
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
        fileutil: FileUtil class that conforms to fileutil.FileUtilABC

    Returns:
        ExportResults
    """

    exported_files = []
    update_updated_files = []
    update_new_files = []
    update_skipped_files = []

    dest_str = str(dest)
    dest_exists = dest.exists()
    if export_as_hardlink:
        # use hardlink instead of copy
        if not update:
            # not update, do the the hardlink
            if overwrite and dest.exists():
                # need to remove the destination first
                # dest.unlink()
                fileutil.unlink(dest)
            logging.debug(f"Not update: export_as_hardlink linking file {src} {dest}")
            fileutil.hardlink(src, dest)
            export_db.set_data(
                dest_str,
                self.uuid,
                fileutil.file_sig(dest_str),
                (None, None, None),
                self.json(),
                None,
            )
            exported_files.append(dest_str)
        elif dest_exists and dest.samefile(src):
            # update, hardlink and it already points to the right file, do nothing
            logging.debug(
                f"Update: skipping samefile with export_as_hardlink {src} {dest}"
            )
            update_skipped_files.append(dest_str)
        elif dest_exists:
            # update, not the same file (e.g. user may not have used export_as_hardlink last time it was run
            logging.debug(
                f"Update: removing existing file prior to export_as_hardlink {src} {dest}"
            )
            # dest.unlink()
            fileutil.unlink(dest)
            fileutil.hardlink(src, dest)
            export_db.set_data(
                dest_str,
                self.uuid,
                fileutil.file_sig(dest_str),
                (None, None, None),
                self.json(),
                None,
            )
            update_updated_files.append(dest_str)
            exported_files.append(dest_str)
        else:
            # update, hardlink, destination doesn't exist (new file)
            logging.debug(
                f"Update: exporting new file with export_as_hardlink {src} {dest}"
            )
            fileutil.hardlink(src, dest)
            export_db.set_data(
                dest_str,
                self.uuid,
                fileutil.file_sig(dest_str),
                (None, None, None),
                self.json(),
                None,
            )
            exported_files.append(dest_str)
            update_new_files.append(dest_str)
    else:
        if not update:
            # not update, do the the copy
            if overwrite and dest.exists():
                # need to remove the destination first
                # dest.unlink()
                fileutil.unlink(dest)
            logging.debug(f"Not update: copying file {src} {dest}")
            fileutil.copy(src, dest_str, norsrc=no_xattr)
            exported_files.append(dest_str)
            export_db.set_data(
                dest_str,
                self.uuid,
                fileutil.file_sig(dest_str),
                (None, None, None),
                self.json(),
                None,
            )
        # elif dest_exists and not exiftool and cmp_file(dest_str, export_db.get_stat_orig_for_file(dest_str)):
        elif (
            dest_exists
            and not exiftool
            and filecmp.cmp(src, dest)
            and not dest.samefile(src)
        ):
            # destination exists but is identical
            logging.debug(f"Update: skipping identifical original files {src} {dest}")
            # call set_stat because code can reach this spot if no export DB but exporting a RAW or live photo
            # potentially re-writes the data in the database but ensures database is complete
            export_db.set_stat_orig_for_file(dest_str, fileutil.file_sig(dest_str))
            update_skipped_files.append(dest_str)
        elif (
            dest_exists
            and exiftool
            and fileutil.cmp_sig(dest_str, export_db.get_stat_exif_for_file(dest_str))
            and not dest.samefile(src)
        ):
            # destination exists but is identical
            logging.debug(f"Update: skipping identifical exiftool files {src} {dest}")
            update_skipped_files.append(dest_str)
        elif dest_exists:
            # destination exists but is different or is a hardlink
            logging.debug(f"Update: removing existing file prior to copy {src} {dest}")
            stat_src = os.stat(src)
            stat_dest = os.stat(dest)
            # dest.unlink()
            fileutil.unlink(dest)
            fileutil.copy(src, dest_str, norsrc=no_xattr)
            export_db.set_data(
                dest_str,
                self.uuid,
                fileutil.file_sig(dest_str),
                (None, None, None),
                self.json(),
                None,
            )
            exported_files.append(dest_str)
            update_updated_files.append(dest_str)
        else:
            # destination doesn't exist, copy the file
            logging.debug(f"Update: copying new file {src} {dest}")
            fileutil.copy(src, dest_str, norsrc=no_xattr)
            export_db.set_data(
                dest_str,
                self.uuid,
                fileutil.file_sig(dest_str),
                (None, None, None),
                self.json(),
                None,
            )
            exported_files.append(dest_str)
            update_new_files.append(dest_str)

    return ExportResults(
        exported_files, update_new_files, update_updated_files, update_skipped_files, []
    )


def _write_exif_data(
    self,
    filepath,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
):
    """ write exif data to image file at filepath
    filepath: full path to the image file """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Could not find file {filepath}")
    exiftool = ExifTool(filepath)
    exif_info = json.loads(
        self._exiftool_json_sidecar(
            use_albums_as_keywords=use_albums_as_keywords,
            use_persons_as_keywords=use_persons_as_keywords,
            keyword_template=keyword_template,
        )
    )[0]
    for exiftag, val in exif_info.items():
        if type(val) == list:
            # more than one, set first value the add additional values
            exiftool.setvalue(exiftag, val.pop(0))
            if val:
                # add any remaining items
                exiftool.addvalues(exiftag, *val)
        else:
            exiftool.setvalue(exiftag, val)


def _exiftool_json_sidecar(
    self,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
):
    """ return json string of EXIF details in exiftool sidecar format
        Does not include all the EXIF fields as those are likely already in the image
        use_albums_as_keywords: treat album names as keywords
        use_persons_as_keywords: treat person names as keywords
        keyword_template: (list of strings); list of template strings to render as keywords
        Exports the following:
            FileName
            ImageDescription
            Description
            Title
            TagsList
            Keywords (may include album name, person name, or template)
            Subject
            PersonInImage
            GPSLatitude, GPSLongitude
            GPSPosition
            GPSLatitudeRef, GPSLongitudeRef
            DateTimeOriginal
            OffsetTimeOriginal
            ModifyDate """

    exif = {}
    exif["_CreatedBy"] = "osxphotos, https://github.com/RhetTbull/osxphotos"

    if self.description:
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
        exif["XMP:TagsList"] = exif["IPTC:Keywords"] = keyword_list

    if person_list:
        exif["XMP:PersonInImage"] = person_list

    if self.keywords or person_list:
        # Photos puts both keywords and persons in Subject when using "Export IPTC as XMP"
        # only use Photos' keywords for subject
        exif["XMP:Subject"] = list(self.keywords) + person_list

    # if self.favorite():
    #     exif["Rating"] = 5

    (lat, lon) = self.location
    if lat is not None and lon is not None:
        lat_str, lon_str = dd_to_dms_str(lat, lon)
        exif["EXIF:GPSLatitude"] = lat_str
        exif["EXIF:GPSLongitude"] = lon_str
        exif["Composite:GPSPosition"] = f"{lat_str}, {lon_str}"
        lat_ref = "North" if lat >= 0 else "South"
        lon_ref = "East" if lon >= 0 else "West"
        exif["EXIF:GPSLatitudeRef"] = lat_ref
        exif["EXIF:GPSLongitudeRef"] = lon_ref

    # process date/time and timezone offset
    date = self.date
    # exiftool expects format to "2015:01:18 12:00:00"
    datetimeoriginal = date.strftime("%Y:%m:%d %H:%M:%S")
    offsettime = date.strftime("%z")
    # find timezone offset in format "-04:00"
    offset = re.findall(r"([+-]?)([\d]{2})([\d]{2})", offsettime)
    offset = offset[0]  # findall returns list of tuples
    offsettime = f"{offset[0]}{offset[1]}:{offset[2]}"
    exif["EXIF:DateTimeOriginal"] = datetimeoriginal
    exif["EXIF:OffsetTimeOriginal"] = offsettime

    if self.date_modified is not None:
        exif["EXIF:ModifyDate"] = self.date_modified.strftime("%Y:%m:%d %H:%M:%S")

    json_str = json.dumps([exif])
    return json_str


def _xmp_sidecar(
    self,
    use_albums_as_keywords=False,
    use_persons_as_keywords=False,
    keyword_template=None,
):
    """ returns string for XMP sidecar 
        use_albums_as_keywords: treat album names as keywords
        use_persons_as_keywords: treat person names as keywords
        keyword_template: (list of strings); list of template strings to render as keywords """

    # TODO: add additional fields to XMP file?

    xmp_template = Template(filename=os.path.join(_TEMPLATE_DIR, _XMP_TEMPLATE_NAME))

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
        photo=self, keywords=keyword_list, persons=person_list, subjects=subject_list
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
