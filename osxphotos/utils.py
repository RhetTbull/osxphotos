import glob
import logging
import os.path
import platform
import sqlite3
import subprocess
import tempfile
import urllib.parse
import pathlib
from plistlib import load as plistload

import CoreFoundation
import objc
from Foundation import *

from osxphotos._applescript import AppleScript

_DEBUG = False


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s",
)

if not _DEBUG:
    logging.disable(logging.DEBUG)


def _get_logger():
    """Used only for testing
    
    Returns:
        logging.Logger object -- logging.Logger object for osxphotos
    """
    return logging.Logger(__name__)


def _set_debug(debug):
    """ Enable or disable debug logging """
    global _DEBUG
    _DEBUG = debug
    if debug:
        logging.disable(logging.NOTSET)
    else:
        logging.disable(logging.DEBUG)


def _debug():
    """ returns True if debugging turned on (via _set_debug), otherwise, false """
    return _DEBUG


def _get_os_version():
    # returns tuple containing OS version
    # e.g. 10.13.6 = (10, 13, 6)
    version = platform.mac_ver()[0].split(".")
    if len(version) == 2:
        (ver, major) = version
        minor = "0"
    elif len(version) == 3:
        (ver, major, minor) = version
    else:
        raise (
            ValueError(
                f"Could not parse version string: {platform.mac_ver()} {version}"
            )
        )
    return (ver, major, minor)


def _check_file_exists(filename):
    """ returns true if file exists and is not a directory
        otherwise returns false """
    filename = os.path.abspath(filename)
    return os.path.exists(filename) and not os.path.isdir(filename)


def _get_resource_loc(model_id):
    """ returns folder_id and file_id needed to find location of edited photo """
    """ and live photos for version <= Photos 4.0 """
    # determine folder where Photos stores edited version
    # edited images are stored in:
    # Photos Library.photoslibrary/resources/media/version/XX/00/fullsizeoutput_Y.jpeg
    # where XX and Y are computed based on RKModelResources.modelId

    # file_id (Y in above example) is hex representation of model_id without leading 0x
    file_id = hex_id = hex(model_id)[2:]

    # folder_id (XX) in above example if first two chars of model_id converted to hex
    # and left padded with zeros if < 4 digits
    folder_id = hex_id.zfill(4)[0:2]

    return folder_id, file_id


def _dd_to_dms(dd):
    """ convert lat or lon in decimal degrees (dd) to degrees, minutes, seconds """
    """ return tuple of int(deg), int(min), float(sec) """
    dd = float(dd)
    negative = dd < 0
    dd = abs(dd)
    min_, sec_ = divmod(dd * 3600, 60)
    deg_, min_ = divmod(min_, 60)
    if negative:
        if deg_ > 0:
            deg_ = deg_ * -1
        elif min_ > 0:
            min_ = min_ * -1
        else:
            sec_ = sec_ * -1

    return int(deg_), int(min_), sec_


def _copy_file(src, dest):
    """ Copies a file from src path to dest path 
        src: source path as string 
        dest: destination path as string
        Uses ditto to perform copy; will silently overwrite dest if it exists
        Raises exception if copy fails or either path is None """

    if src is None or dest is None:
        raise ValueError("src and dest must not be None", src, dest)

    if not os.path.isfile(src):
        raise ValueError("src file does not appear to exist", src)

    # if error on copy, subprocess will raise CalledProcessError
    try:
        subprocess.run(
            ["/usr/bin/ditto", src, dest], check=True, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        logging.critical(
            f"ditto returned error: {e.returncode} {e.stderr.decode(sys.getfilesystemencoding()).rstrip()}"
        )
        raise e


def dd_to_dms_str(lat, lon):
    """ convert latitude, longitude in degrees to degrees, minutes, seconds as string """
    """ lat: latitude in degrees  """
    """ lon: longitude in degrees """
    """ returns: string tuple in format ("51 deg 30' 12.86\" N", "0 deg 7' 54.50\" W") """
    """ this is the same format used by exiftool's json format """
    # TODO: add this to readme

    lat_deg, lat_min, lat_sec = _dd_to_dms(lat)
    lon_deg, lon_min, lon_sec = _dd_to_dms(lon)

    lat_hemisphere = "N"
    if any([lat_deg < 0, lat_min < 0, lat_sec < 0]):
        lat_hemisphere = "S"

    lon_hemisphere = "E"
    if any([lon_deg < 0, lon_min < 0, lon_sec < 0]):
        lon_hemisphere = "W"

    lat_str = (
        f"{abs(lat_deg)} deg {abs(lat_min)}' {abs(lat_sec):.2f}\" {lat_hemisphere}"
    )
    lon_str = (
        f"{abs(lon_deg)} deg {abs(lon_min)}' {abs(lon_sec):.2f}\" {lon_hemisphere}"
    )

    return lat_str, lon_str


def get_system_library_path():
    """ return the path to the system Photos library as string """
    """ only works on MacOS 10.15+ """
    """ on earlier versions, returns None """
    _, major, _ = _get_os_version()
    if int(major) < 15:
        logging.debug(
            f"get_system_library_path not implemented for MacOS < 10.15: you have {major}"
        )
        return None

    plist_file = pathlib.Path(
        str(pathlib.Path.home())
        + "/Library/Containers/com.apple.photolibraryd/Data/Library/Preferences/com.apple.photolibraryd.plist"
    )
    if plist_file.is_file():
        with open(plist_file, "rb") as fp:
            pl = plistload(fp)
    else:
        logging.warning(f"could not find plist file: {str(plist_file)}")
        return None

    photospath = pl["SystemLibraryPath"]

    if photospath is not None:
        return photospath
    else:
        logging.warning("Could not get path to Photos database")
        return None


def get_last_library_path():
    """ returns the path to the last opened Photos library 
        If a library has never been opened, returns None """
    plist_file = pathlib.Path(
        str(pathlib.Path.home())
        + "/Library/Containers/com.apple.Photos/Data/Library/Preferences/com.apple.Photos.plist"
    )
    if plist_file.is_file():
        with open(plist_file, "rb") as fp:
            pl = plistload(fp)
    else:
        logging.debug(f"could not find plist file: {str(plist_file)}")
        return None

    # get the IPXDefaultLibraryURLBookmark from com.apple.Photos.plist
    # this is a serialized CFData object
    photosurlref = pl["IPXDefaultLibraryURLBookmark"]

    if photosurlref is not None:
        # use CFURLCreateByResolvingBookmarkData to de-serialize bookmark data into a CFURLRef
        # pylint: disable=no-member
        # pylint: disable=undefined-variable
        photosurl = CoreFoundation.CFURLCreateByResolvingBookmarkData(
            kCFAllocatorDefault, photosurlref, 0, None, None, None, None
        )

        # the CFURLRef we got is a sruct that python treats as an array
        # I'd like to pass this to CFURLGetFileSystemRepresentation to get the path but
        # CFURLGetFileSystemRepresentation barfs when it gets an array from python instead of expected struct
        # first element is the path string in form:
        # file:///Users/username/Pictures/Photos%20Library.photoslibrary/
        photosurlstr = photosurl[0].absoluteString() if photosurl[0] else None

        # now coerce the file URI back into an OS path
        # surely there must be a better way
        if photosurlstr is not None:
            photospath = os.path.normpath(
                urllib.parse.unquote(urllib.parse.urlparse(photosurlstr).path)
            )
        else:
            logging.warning(
                "Could not extract photos URL String from IPXDefaultLibraryURLBookmark"
            )
            return None

        return photospath
    else:
        logging.debug("Could not get path to Photos database")
        return None


def list_photo_libraries():
    """ returns list of Photos libraries found on the system """
    """ on MacOS < 10.15, this may omit some libraries """

    # On 10.15, mdfind appears to find all libraries
    # On older MacOS versions, mdfind appears to ignore some libraries
    # glob to find libraries in ~/Pictures then mdfind to find all the others
    # TODO: make this more robust
    lib_list = glob.glob(f"{str(pathlib.Path.home())}/Pictures/*.photoslibrary")

    # On older OS, may not get all libraries so make sure we get the last one
    last_lib = get_last_library_path()
    if last_lib:
        lib_list.append(last_lib)

    output = subprocess.check_output(
        ["/usr/bin/mdfind", "-onlyin", "/", "-name", ".photoslibrary"]
    ).splitlines()
    for lib in output:
        lib_list.append(lib.decode("utf-8"))
    lib_list = list(set(lib_list))
    lib_list.sort()
    return lib_list


def create_path_by_date(dest, dt):
    """ Creates a path in dest folder in form dest/YYYY/MM/DD/
        dest: valid path as str
        dt: datetime.timetuple() object
        Checks to see if path exists, if it does, do nothing and return path
        If path does not exist, creates it and returns path"""
    if not os.path.isdir(dest):
        raise FileNotFoundError(f"dest {dest} must be valid path")
    yyyy, mm, dd = dt[0:3]
    yyyy = str(yyyy).zfill(4)
    mm = str(mm).zfill(2)
    dd = str(dd).zfill(2)
    new_dest = os.path.join(dest, yyyy, mm, dd)
    if not os.path.isdir(new_dest):
        os.makedirs(new_dest)
    return new_dest


# TODO: this doesn't always work, still looking for a way to
# force Photos to open the library being operated on
# def _open_photos_library_applescript(library_path):
#     """ Force Photos to open a specific library
#         library_path: path to the Photos library """
#     open_scpt = AppleScript(
#         f"""
#         on openLibrary
#             tell application "Photos"
# 	          open POSIX file "{library_path}"
#             end tell
#         end openLibrary
#         """
#     )
#     open_scpt.run()


def _export_photo_uuid_applescript(
    uuid,
    dest,
    filestem=None,
    original=True,
    edited=False,
    live_photo=False,
    timeout=120,
    burst=False,
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
        logging.warning("Error exporting uuid %s: %s" % (uuid, str(e)))
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
            _copy_file(str(path), str(dest_new))
            exported_paths.append(str(dest_new))
        return exported_paths
    else:
        return None


def _open_sql_file(dbname):
    """ opens sqlite file dbname in read-only mode
        returns tuple of (connection, cursor) """
    try:
        dbpath = pathlib.Path(dbname).resolve()
        conn = sqlite3.connect(f"{dbpath.as_uri()}?mode=ro", timeout=1, uri=True)
        c = conn.cursor()
    except sqlite3.Error as e:
        sys.exit(f"An error occurred opening sqlite file: {e.args[0]} {dbname}")
    return (conn, c)


def _db_is_locked(dbname):
    """ check to see if a sqlite3 db is locked
        returns True if database is locked, otherwise False
        dbname: name of database to test """

    # first, check to see if lock file exists, if so, assume the file is locked
    lock_name = f"{dbname}.lock"
    if os.path.exists(lock_name):
        logging.debug(f"{dbname} is locked")
        return True

    # no lock file so try to read from the database to see if it's locked
    locked = None
    try:
        (conn, c) = _open_sql_file(dbname)
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        conn.close()
        logging.debug(f"{dbname} is not locked")
        locked = False
    except:
        logging.debug(f"{dbname} is locked")
        locked = True

    return locked
