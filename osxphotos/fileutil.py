"""FileUtil class with methods for copy, hardlink, unlink, etc."""

import datetime
import enum
import errno
import fcntl
import functools
import logging
import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import types
import typing as t
from abc import ABC, abstractmethod
from tempfile import TemporaryDirectory

from tenacity import (
    RetryCallState,
    after_log,
    before_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_fixed,
)

from .imageconverter import ImageConverter
from .platform import is_macos
from .unicode import normalize_fs_path

# logger
logger = logging.getLogger(__name__)


# module-level dict RETRY_FILEUTIL_CONFIG that controls retry behavior. See cfg_fileutil_retry
RETRY_FILEUTIL_CONFIG = {
    "retry_enabled": False,
    "retries": 3,
    "wait_seconds": 15,
    "nas_export_alias": "",
}


def cfg_fileutil_retry(
    retry_enabled: bool | None = None,
    retries: int | None = None,
    wait_seconds: int | None = None,
    nas_export_alias: str | None = None,
):
    """Change global retry behavior for FileUtil.

    Retry configuration for fileutil operations.
    The configuration is kept on the module-level dict RETRY_FILEUTIL_CONFIG.

    Useful when operating over NAS SMB drive, in the event of connection failure.
    The retry passes to Finder, an alias file to the NAS SMB drive, which causes
      macOS to re-mount the drive.

    Applicable when retry_enabled is True. If nas_export_alias is not defined, the
      re-mount is bypassed. wait-seconds coonfiguration is the delay in between attempts.

    Only methods on classes decorated with @retry_all_methods() are wrapped with tenacity
    retry logic — changing the config affects in real-time those wrapped methods.

    Key config keys and effects

    - retry_enabled (bool)
      - If False (default) is_fileutil_error() immediately returns False =>
      retry_if_exception(is_fileutil_error) will not trigger retries. Wrapped
      methods still run but will not retry on errors.
      - If True, recoverable exceptions will cause retries.
    - retries (int)
      - Controls stop_after_attempt(RETRY_FILEUTIL_CONFIG["retries"]) — maximum retry attempts.
    - wait_seconds (int)
      - Controls wait_fixed(RETRY_FILEUTIL_CONFIG["wait_seconds"]) — delay between attempts.
    - nas_export_alias (str)
      - Path used by open_alias_script() (called before sleeping between retries) to attempt
      re-mounting an SMB alias via osascript on macOS.

    Behavioral flow on exception (when retry_enabled=True)

    1. A wrapped method raises an exception.
    2. is_fileutil_error(exception) is called:
      - Logs a warning.
      - Returns True if PermissionError or "Permission denied" in message,
      or if OSError with errno in RECOVERABLE_ERRNOS.
    3. If True, tenacity will:
      - Call open_alias_script(...) before each retry sleep (which will attempt
      to open the Finder alias if set and on macOS).
      - Wait wait_seconds between attempts.
      - Stop after retries attempts.
      - Reraise final exception if still failing.
    4. after_log logs retry events.

    Notes and caveats

    - cfg_fileutil_retry modifies a global dict — changes take effect immediately for
    subsequent calls but are not thread-safe.
    - Only exceptions that satisfy is_fileutil_error trigger retries; other exceptions
    propagate immediately.
    - The retry wrapper is applied at class decoration time, but the wrapper reads current
    RETRY_FILEUTIL_CONFIG values when invoked, so updating config later changes runtime behavior.
    - open_alias_script only runs on macOS and only if nas_export_alias is non-empty.

    Args:
    - retry_enabled (bool | None): Enable or disable retry logic. If None,
    leaves current setting unchanged.
    - retries (int | None): Number of retry attempts. If None, leaves current setting unchanged.
    - wait_seconds (int | None): Seconds to wait between retries. If None or non-positive,
    leaves current setting unchanged.
    - nas_export_alias (str | None): Path to Finder alias used to re-mount NAS on SMB errors.
    If None, leaves current setting unchanged.

    Returns:
    - None: Modifies the module-level RETRY_FILEUTIL_CONFIG in place.
    """
    if retry_enabled is not None:
        RETRY_FILEUTIL_CONFIG["retry_enabled"] = retry_enabled
    if retries is not None:
        RETRY_FILEUTIL_CONFIG["retries"] = retries
    if wait_seconds is not None and wait_seconds > 0:
        RETRY_FILEUTIL_CONFIG["wait_seconds"] = wait_seconds
    if nas_export_alias is not None:
        RETRY_FILEUTIL_CONFIG["nas_export_alias"] = nas_export_alias


# Set of recoverable errno values for SMB/network failures
RECOVERABLE_ERRNOS = {
    errno.EIO,  # Input/output error
    errno.ETIMEDOUT,  # Operation timed out
    errno.ENOTCONN,  # Socket is not connected
    errno.EHOSTUNREACH,  # No route to host
    errno.ECONNRESET,  # Connection reset by peer
    errno.ECONNREFUSED,  # Connection refused
    errno.ENETDOWN,  # Network is down
    errno.ENETUNREACH,  # Network is unreachable
}


# Check for errot PermissionError or OSError in RECOVERABLE_ERRNOS to allow retry
def is_fileutil_error(exception) -> bool:
    """Determine whether an exception should be treated as a recoverable fileutil error.

    If retry is enabled via RETRY_FILEUTIL_CONFIG["retry_enabled"], exception is logged (warning)
    and if it represents a recoverable file-system condition that warrants another attempt.

    Recovery conditions:
    - The exception is an instance of PermissionError, or its string representation
        contains the substring "Permission denied".
    - The exception is an instance of OSError and its errno attribute is present in the
        RECOVERABLE_ERRNOS collection.

    Args:
        exception: BaseException. The exception object to inspect.

    Returns:
        bool: True if the exception should be considered recoverable (eligible for a retry).

    Notes
    -----
    - It relies on global configuration mapping RETRY_FILEUTIL_CONFIG with a boolean
        "retry_enabled" key, and on the global RECOVERABLE_ERRNOS collection of errno integers.
    """

    if not RETRY_FILEUTIL_CONFIG["retry_enabled"]:
        return False

    logger.warning("⚠️  fileutil: exception: %s ", str(exception))

    if isinstance(exception, PermissionError) or "Permission denied" in str(exception):
        return True

    if isinstance(exception, OSError) and exception.errno in RECOVERABLE_ERRNOS:
        return True

    return False


def retry_all_methods():
    """Apply tenacity.retry to all callable methods of a class."""

    def decorator(cls):
        for name, value in cls.__dict__.items():

            # Skip dunder methods (e.g. __init__, __str__, etc.)
            if name.startswith("__"):
                continue

            def make_retry(func):
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    retryer = retry(
                        stop=stop_after_attempt(RETRY_FILEUTIL_CONFIG["retries"]),
                        wait=wait_fixed(RETRY_FILEUTIL_CONFIG["wait_seconds"]),
                        retry=retry_if_exception(is_fileutil_error),
                        before_sleep=open_alias_script,
                        # before=before_log(logger, logging.WARNING),
                        after=after_log(logger, logging.WARNING),
                        reraise=True,
                    )
                    return retryer(func)(*args, **kwargs)

                return wrapper

            # functions -> instance methods
            if isinstance(value, types.FunctionType):
                setattr(cls, name, make_retry(value))

            # classmethod
            elif isinstance(value, classmethod):
                setattr(cls, name, classmethod(make_retry(value.__func__)))

            # staticmethod
            elif isinstance(value, staticmethod):
                setattr(cls, name, staticmethod(make_retry(value.__func__)))

        return cls

    return decorator


def open_alias_script(retry_state: RetryCallState) -> int | None:
    """Attempt to (re)open a Finder alias pointing to an SMB export so macOS will
    resolve and mount the associated network share.

    Args:
        retry_state: RetryCallState
            Context/state object provided by the caller's retry mechanism. This function
            accepts the value for compatibility with retry wrappers but does not use it
            directly.

    Returns:
        int: The exit code returned by the 'osascript' subprocess when attempting
            to run the AppleScript (0 indicates success, non-zero indicates failure).
        None: Returned when no attempt is made because either the host is not
            macOS or the configured alias path is empty.

    Side effects:
    - Reads the global RETRY_FILEUTIL_CONFIG["nas_export_alias"] to obtain the POSIX
      path of the alias to open.
    - Logs informational/warning messages about the attempt and outcome via the
      global logger.
    - If applicable, constructs and executes a small AppleScript that tells Finder
      to open the POSIX file; Finder will resolve the alias and trigger mounting of
      the SMB share if needed.

    """

    alias = RETRY_FILEUTIL_CONFIG.get("nas_export_alias", "")
    logger.warning(
        "⚠️  fileutil: SMB error: %s%s",
        (
            "retrying mount SMB alias"
            if is_macos
            else "not retrying mount SMB alias (not macOS)"
        ),
        (
            f': nas_export_alias="{alias}"...'
            if alias
            else ": bypassing nas_export_alias not defined)."
        ),
    )

    if not is_macos or RETRY_FILEUTIL_CONFIG["nas_export_alias"] == "":
        return None

    script = f"""
    tell application "Finder"
        open (POSIX file "{RETRY_FILEUTIL_CONFIG["nas_export_alias"]}") -- Finder resolves aliases automatically
    end tell
    """

    if rc := subprocess.call(["osascript", "-e", script]) == 0:
        logger.warning("✅ fileutil: re-mounted SMB alias succssefully.")
    else:
        logger.warning(
            "❌  fileutil: re-mounted SMB alias failed with return code: %s", rc
        )

    return rc


if is_macos:
    import Foundation


class FileDateType(enum.IntFlag):
    """Bitfield flags for file date types"""

    CREATION = 1
    MODIFICATION = 2
    ACCESS = 4


__all__ = [
    "FileUtilABC",
    "FileUtilMacOS",
    "FileUtilShUtil",
    "FileUtil",
    "FileUtilNoOp",
    "FileDateType",
    "set_file_dates",
]

logger = logging.getLogger("osxphotos")


def utime_no_cache(path: os.PathLike, times: tuple[int, int]) -> bool:
    """Set file modification and access times with filesystem caching disabled

    Args:
        path: The file system path to the file
        times: A tuple of two integers representing the access and modification times in seconds since the epoch

    Returns:
        bool: True if successful, False if an error occurred

    Note:
        The file access, modification will all be set to the modification time passed in.
        This method is required for some network-attached storage which does not preserve utime results
        if caching is not disabled.
    """
    fd = None
    try:
        # Open file and set F_NOCACHE to prevent filesystem cache interference
        fd = os.open(path, os.O_RDONLY)
        fcntl.fcntl(fd, fcntl.F_NOCACHE, 1)
        os.utime(path, times)
        return True
    except Exception as e:
        logger.warning(f"Could not set utime for file {path}: {e}")
        return False
    finally:
        if fd is not None:
            try:
                # Clear F_NOCACHE flag before closing
                fcntl.fcntl(fd, fcntl.F_NOCACHE, 0)
                os.close(fd)
            except:
                try:
                    os.close(fd)
                except:
                    pass


def utime_macos(path: os.PathLike, times: tuple[int, int]) -> bool:
    """Adjust file access, modified time, and creation time on macOS

    Args:
        path: The file system path to the file
        times: A tuple of two integers representing the access and modification times in seconds since the epoch

    Returns:
        bool: True if successful, False if an error occurred

    Note:
        The file access, modification, and creation date/time will all be set to the modification time passed inZ
    """
    dt = datetime.datetime.fromtimestamp(times[1])
    # set access/modification via utime for NAS devices
    if not utime_no_cache(path, times):
        return False
    # set creation date with native macOS calls
    return set_file_dates(path, dt, FileDateType.CREATION)


def set_file_dates(
    file_path: pathlib.Path | os.PathLike,
    date: datetime.datetime,
    date_type: FileDateType = FileDateType.CREATION
    | FileDateType.MODIFICATION
    | FileDateType.ACCESS,
):
    """
    Sets the specified date(s) of a file to the given datetime

    Args:
        file_path: The file system path to the file
        date: The datetime to set for the specified date type(s) (default is to set all file date types)
        date_type: Bitfield flag(s) specifying which date(s) to set
                   (FileDateType.CREATION, FileDateType.MODIFICATION, FileDateType.ACCESS)
                   Can be combined using bitwise OR: FileDateType.CREATION | FileDateType.MODIFICATION

    Returns:
        bool: True if successful, False if an error occurred

    Raises:
        ValueError: if invalid arguments
        FileNotFoundError: if path is not found
    """
    if not is_macos:
        logger.warning("Only valid on macOS")
        return False

    if not file_path or not date:
        raise ValueError(
            "Error: Invalid parameters - file_path and date cannot be None"
        )

    if not isinstance(date_type, FileDateType):
        raise ValueError(
            f"Error: Invalid date_type - must be FileDateType, got {type(date_type)}"
        )

    file_url = Foundation.NSURL.fileURLWithPath_(str(file_path))
    exists, error = file_url.checkResourceIsReachableAndReturnError_(None)
    if not exists:
        raise FileNotFoundError(
            f"Error: File does not exist at path: {file_path}: {error}"
        )

    ns_date = Foundation.NSDate.dateWithTimeIntervalSince1970_(date.timestamp())

    # Map date type flags to Foundation keys
    date_key_map = {
        FileDateType.CREATION: Foundation.NSURLCreationDateKey,
        FileDateType.MODIFICATION: Foundation.NSURLContentModificationDateKey,
        FileDateType.ACCESS: Foundation.NSURLContentAccessDateKey,
    }

    # Set each requested date type
    all_success = True
    for flag, key in date_key_map.items():
        if date_type & flag:
            success, error = file_url.setResourceValue_forKey_error_(ns_date, key, None)
            if not success:
                error_msg = error.localizedDescription() if error else "Unknown error"
                logger.warning(f"Error setting {flag.name.lower()} date: {error_msg}")
                all_success = False

    return all_success


class FileUtilABC(ABC):
    """Abstract base class for FileUtil"""

    @classmethod
    @abstractmethod
    def hardlink(cls, src, dest):
        pass

    @classmethod
    @abstractmethod
    def copy(cls, src, dest):
        pass

    @classmethod
    @abstractmethod
    def unlink(cls, filepath):
        pass

    @classmethod
    @abstractmethod
    def rmdir(cls, dirpath):
        pass

    @classmethod
    @abstractmethod
    def makedirs(cls, name, mode: int = 511, exist_ok: bool = False) -> None:
        pass

    @classmethod
    @abstractmethod
    def utime(cls, path, times):
        pass

    @classmethod
    @abstractmethod
    def cmp(cls, file1, file2, mtime1=None):
        pass

    @classmethod
    @abstractmethod
    def cmp_file_sig(cls, file1, sig2):
        pass

    @classmethod
    @abstractmethod
    def file_sig(cls, file1):
        pass

    @classmethod
    @abstractmethod
    def convert_to_jpeg(cls, src_file, dest_file, compression_quality=1.0):
        pass

    @classmethod
    @abstractmethod
    def rename(cls, src, dest):
        pass

    @classmethod
    @abstractmethod
    def tmpdir(
        cls, prefix: t.Optional[str] = None, dirpath: t.Optional[str] = None
    ) -> tempfile.TemporaryDirectory:
        pass


@retry_all_methods()
class FileUtilMacOS(FileUtilABC):
    """Various file utilities"""

    @classmethod
    def hardlink(cls, src, dest):
        """Hardlinks a file from src path to dest path
        src: source path as string
        dest: destination path as string
        Raises exception if linking fails or either path is None"""

        if src is None or dest is None:
            raise ValueError("src and dest must not be None", src, dest)

        src = normalize_fs_path(src)
        dest = normalize_fs_path(dest)

        if not os.path.isfile(src):
            raise FileNotFoundError("src file does not appear to exist", src)

        try:
            os.link(src, dest)
        except Exception as e:
            raise e from e

    @classmethod
    def copy(cls, src, dest):
        """Copies a file from src path to dest path

        Args:
            src: source path as string; must be a valid file path
            dest: destination path as string
                  dest may be either directory or file; in either case, src file must not exist in dest
            Note: src and dest may be either a string or a pathlib.Path object

        Returns:
            True if copy succeeded

        Raises:
            OSError if copy fails
            TypeError if either path is None
        """
        src = normalize_fs_path(src)
        dest = normalize_fs_path(dest)

        if not isinstance(src, pathlib.Path):
            src = pathlib.Path(src)

        if not isinstance(dest, pathlib.Path):
            dest = pathlib.Path(dest)

        if dest.is_dir():
            dest /= src.name

        filemgr = Foundation.NSFileManager.defaultManager()
        error = filemgr.copyItemAtPath_toPath_error_(str(src), str(dest), None)
        # error is a tuple of (bool, error_string)
        # error[0] is True if copy succeeded
        if not error[0]:
            raise OSError(error[1])
        return True

    @classmethod
    def unlink(cls, filepath):
        """unlink filepath; if it's pathlib.Path, use Path.unlink, otherwise use os.unlink"""
        filepath = normalize_fs_path(filepath)
        if isinstance(filepath, pathlib.Path):
            filepath.unlink()
        else:
            os.unlink(filepath)

    @classmethod
    def rmdir(cls, dirpath):
        """remove directory filepath; dirpath must be empty"""
        dirpath = normalize_fs_path(dirpath)
        if isinstance(dirpath, pathlib.Path):
            dirpath.rmdir()
        else:
            os.rmdir(dirpath)

    @classmethod
    def makedirs(cls, name, mode: int = 511, exist_ok: bool = False) -> None:
        """create directory path; creates parent directories if needed"""
        dirpath = normalize_fs_path(name)
        if isinstance(dirpath, pathlib.Path):
            dirpath.mkdir(parents=True, mode=mode, exist_ok=exist_ok)
        else:
            os.makedirs(dirpath, mode=mode, exist_ok=exist_ok)

    @classmethod
    def utime(cls, path, times):
        """Set the access and modified time of path."""
        path = normalize_fs_path(path)
        utime_macos(path, times)

    @classmethod
    def cmp(cls, file1, file2, mtime1=None):
        """Does shallow compare (file signatures) of file1 to file file2.

        Args:
            file1 -- File name
            file2 -- File name
            mtime1 -- optional, pass alternate file modification timestamp for file1; will be converted to int

        Returns:
            True if the file signatures as returned by stat are the same, False otherwise.
            Does not do a byte-by-byte comparison.
        """

        file1 = normalize_fs_path(file1)
        file2 = normalize_fs_path(file2)

        sig1 = cls._sig(os.stat(file1))
        if mtime1 is not None:
            sig1 = (sig1[0], sig1[1], int(mtime1))
        sig2 = cls._sig(os.stat(file2))
        if sig1[0] != stat.S_IFREG or sig2[0] != stat.S_IFREG:
            return False
        return sig1 == sig2

    @classmethod
    def cmp_file_sig(cls, file1, sig2):
        """Compare file file1 to signature sig2.

        Args:
           file1 -- File name
           sig2  -- stats as returned by _sig

        Returns:
           True if the files are the same, False otherwise.
        """

        if not sig2:
            return False

        file1 = normalize_fs_path(file1)
        sig1 = cls._sig(os.stat(file1))
        if sig1[0] != stat.S_IFREG or sig2[0] != stat.S_IFREG:
            return False
        return sig1 == sig2

    @classmethod
    def file_sig(cls, file1):
        """return os.stat signature for file file1 as tuple of (mode, size, mtime)"""
        file1 = normalize_fs_path(file1)
        return cls._sig(os.stat(file1))

    @classmethod
    def convert_to_jpeg(cls, src_file, dest_file, compression_quality=1.0):
        """converts image file src_file to jpeg format as dest_file

        Args:
            src_file: image file to convert
            dest_file: destination path to write converted file to
            compression quality: JPEG compression quality in range 0.0 <= compression_quality <= 1.0; default 1.0 (best quality)

        Returns:
            True if success, otherwise False
        """
        src_file = normalize_fs_path(src_file)
        dest_file = normalize_fs_path(dest_file)
        converter = ImageConverter()
        return converter.write_jpeg(
            src_file, dest_file, compression_quality=compression_quality
        )

    @classmethod
    def rename(cls, src, dest):
        """Copy src to dest

        Args:
            src: path to source file
            dest: path to destination file

        Returns:
            Name of renamed file (dest)

        """
        src = normalize_fs_path(src)
        dest = normalize_fs_path(dest)
        os.rename(str(src), str(dest))
        return dest

    @classmethod
    def tmpdir(
        cls, prefix: t.Optional[str] = None, dirpath: t.Optional[str] = None
    ) -> tempfile.TemporaryDirectory:
        """Securely creates a temporary directory using the same rules as mkdtemp().
        The resulting object can be used as a context manager.
        On completion of the context or destruction of the temporary directory object,
        the newly created temporary directory and all its contents are removed from the filesystem.
        """
        return TemporaryDirectory(prefix=prefix, dir=dirpath)

    @staticmethod
    def _sig(st):
        """return tuple of (mode, size, mtime) of file based on os.stat
        Args:
            st: os.stat signature
        """
        # use int(st.st_mtime) because ditto does not copy fractional portion of mtime
        return (stat.S_IFMT(st.st_mode), st.st_size, int(st.st_mtime))


@retry_all_methods()
class FileUtilShUtil(FileUtilMacOS):
    """Various file utilities, uses shutil.copy to copy files instead of NSFileManager (#807)"""

    @classmethod
    def copy(cls, src, dest):
        """Copies a file from src path to dest path using shutil.copy

        Args:
            src: source path as string; must be a valid file path
            dest: destination path as string
                  dest may be either directory or file; in either case, src file must not exist in dest
            Note: src and dest may be either a string or a pathlib.Path object

        Returns:
            True if copy succeeded

        Raises:
            OSError if copy fails
            TypeError if either path is None
        """
        src = normalize_fs_path(src)
        dest = normalize_fs_path(dest)

        if not isinstance(src, pathlib.Path):
            src = pathlib.Path(src)

        if not isinstance(dest, pathlib.Path):
            dest = pathlib.Path(dest)

        if dest.is_dir():
            dest /= src.name

        try:
            shutil.copy(str(src), str(dest))
        except Exception as e:
            # TODO: Code masks all exceptions as OSError and drops errno on raise.
            # The retry wrapper, if active, will not execute. To be reviewed.
            raise OSError(f"Error copying {src} to {dest}: {e}") from e

        return True

    @classmethod
    def utime(cls, path, times):
        """Set the access and modified time of path."""
        path = normalize_fs_path(path)
        if is_macos:
            utime_macos(path, times)
        else:
            os.utime(str(path), times)


class FileUtil(FileUtilShUtil):
    """Various file utilities"""


@retry_all_methods()
class FileUtilNoOp(FileUtil):
    """No-Op implementation of FileUtil for testing / dry-run mode
    all methods with exception of tmpdir, cmp, cmp_file_sig and file_cmp are no-op
    cmp and cmp_file_sig functions as FileUtil methods do
    file_cmp returns mock data
    """

    @staticmethod
    def noop(*args):
        pass

    def __new__(cls, verbose=None):
        if verbose:
            if callable(verbose):
                cls.verbose = verbose
            else:
                raise ValueError(f"verbose {verbose} not callable")
        return super(FileUtilNoOp, cls).__new__(cls)

    @classmethod
    def hardlink(cls, src, dest):
        pass

    @classmethod
    def copy(cls, src, dest):
        pass

    @classmethod
    def unlink(cls, filepath):
        pass

    @classmethod
    def rmdir(cls, dirpath):
        pass

    @classmethod
    def makedirs(cls, name, mode: int = 511, exist_ok: bool = False) -> None:
        pass

    @classmethod
    def utime(cls, path, times):
        pass

    @classmethod
    def file_sig(cls, file1):
        return (42, 42, 42)

    @classmethod
    def convert_to_jpeg(cls, src_file, dest_file, compression_quality=1.0):
        pass

    @classmethod
    def rename(cls, src, dest):
        pass

    @classmethod
    def tmpdir(
        cls, prefix: t.Optional[str] = None, dirpath: t.Optional[str] = None
    ) -> tempfile.TemporaryDirectory:
        """Securely creates a temporary directory using the same rules as mkdtemp().
        The resulting object can be used as a context manager.
        On completion of the context or destruction of the temporary directory object,
        the newly created temporary directory and all its contents are removed from the filesystem.
        """
        return TemporaryDirectory(prefix=prefix, dir=dirpath)
