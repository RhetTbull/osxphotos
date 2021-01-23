import fnmatch
import glob
import inspect
import logging
import os
import os.path
import pathlib
import platform
import re
import sqlite3
import subprocess
import sys
import unicodedata
import urllib.parse
from plistlib import load as plistload

import CoreFoundation
import CoreServices
import objc

from ._constants import UNICODE_FORMAT

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


def noop(*args, **kwargs):
    """ do nothing (no operation) """
    pass


def lineno(filename):
    """ Returns string with filename and current line number in caller as '(filename): line_num'
    Will trim filename to just the name, dropping path, if any. """
    line = inspect.currentframe().f_back.f_lineno
    filename = pathlib.Path(filename).name
    return f"{filename}: {line}"


def _get_os_version():
    # returns tuple of str containing OS version
    # e.g. 10.13.6 = ("10", "13", "6")
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
    """ only works on MacOS 10.15 """
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
        logging.debug(f"could not find plist file: {str(plist_file)}")
        return None

    return pl.get("SystemLibraryPath")


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
    photosurlref = pl.get("IPXDefaultLibraryURLBookmark")

    if photosurlref is not None:
        # use CFURLCreateByResolvingBookmarkData to de-serialize bookmark data into a CFURLRef
        # pylint: disable=no-member
        # pylint: disable=undefined-variable
        photosurl = CoreFoundation.CFURLCreateByResolvingBookmarkData(
            CoreFoundation.kCFAllocatorDefault, photosurlref, 0, None, None, None, None
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


def get_preferred_uti_extension(uti):
    """ get preferred extension for a UTI type
        uti: UTI str, e.g. 'public.jpeg'
        returns: preferred extension as str """

    # reference: https://developer.apple.com/documentation/coreservices/1442744-uttypecopypreferredtagwithclass?language=objc
    with objc.autorelease_pool():
        return CoreServices.UTTypeCopyPreferredTagWithClass(
            uti, CoreServices.kUTTagClassFilenameExtension
        )


def findfiles(pattern, path_):
    """Returns list of filenames from path_ matched by pattern
       shell pattern. Matching is case-insensitive.
       If 'path_' is invalid/doesn't exist, returns []."""
    if not os.path.isdir(path_):
        return []
    # See: https://gist.github.com/techtonik/5694830

    rule = re.compile(fnmatch.translate(pattern), re.IGNORECASE)
    return [name for name in os.listdir(path_) if rule.match(name)]


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


# OSXPHOTOS_XATTR_UUID = "com.osxphotos.uuid"

# def get_uuid_for_file(filepath):
#     """ returns UUID associated with an exported file
#         filepath: path to exported photo
#     """
#     attr = xattr.xattr(filepath)
#     try:
#         uuid_bytes = attr[OSXPHOTOS_XATTR_UUID]
#         uuid_str = uuid_bytes.decode('utf-8')
#     except KeyError:
#         uuid_str = None
#     return uuid_str

# def set_uuid_for_file(filepath, uuid):
#     """ sets the UUID associated with an exported file
#         filepath: path to exported photo
#         uuid: uuid string for photo
#     """
#     if not os.path.exists(filepath):
#         raise FileNotFoundError(f"Missing file: {filepath}")

#     attr = xattr.xattr(filepath)
#     uuid_bytes = bytes(uuid, 'utf-8')
#     attr.set(OSXPHOTOS_XATTR_UUID, uuid_bytes)


def normalize_unicode(value):
    """ normalize unicode data """
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError("value must be str")
    return unicodedata.normalize(UNICODE_FORMAT, value)


def increment_filename(filepath):
    """ Return filename (1).ext, etc if filename.ext exists

        If file exists in filename's parent folder with same stem as filename, 
        add (1), (2), etc. until a non-existing filename is found.

    Args:
        filepath: str; full path, including file name

    Returns:
        new filepath (or same if not incremented)

    Note: This obviously is subject to race condition so using with caution.
    """
    dest = pathlib.Path(str(filepath))
    count = 1
    dest_files = findfiles(f"{dest.stem}*", str(dest.parent))
    dest_files = [pathlib.Path(f).stem.lower() for f in dest_files]
    dest_new = dest.stem
    while dest_new.lower() in dest_files:
        dest_new = f"{dest.stem} ({count})"
        count += 1
    dest = dest.parent / f"{dest_new}{dest.suffix}"
    return str(dest)
