"""FileUtil class with methods for copy, hardlink, unlink, etc."""

import fcntl
import logging
import os
import pathlib
import shutil
import stat
import tempfile
import typing as t
from abc import ABC, abstractmethod
from tempfile import TemporaryDirectory

from tenacity import (
    RetryCallState,
    retry,
    stop_after_attempt,
    retry_if_exception,
    wait_fixed,
    before_log,
    after_log,
)


from .imageconverter import ImageConverter
from .platform import is_macos
from .unicode import normalize_fs_path

# logger
logger = logging.getLogger(__name__)


# Global configuration — PhotosLibrary can change these
RETRY_FILEUTIL_CONFIG = {
    "retry_enabled": True,
    "retries": 5,  # TODO
    "wait_seconds": 30,  # TODO
    "ALIAS_PATH": "/Users/msp/Library/Application Support/MyApp/TEST.alias"
}


def configure_fileutil_run(retry_enabled=None, retries=None, wait_seconds=None):
    """Change global retry behavior for FileUtil."""
    if retry_enabled is not None:
        RETRY_FILEUTIL_CONFIG["retry_enabled"] = retry_enabled
    if retries is not None:
        RETRY_FILEUTIL_CONFIG["retries"] = retries
    if wait_seconds is not None:
        RETRY_FILEUTIL_CONFIG["wait_seconds"] = wait_seconds


# Check for errot "AppleScript timed out" to allow retry
def is_fileutil_error(exception) -> bool:
    """Check if exception is an AppleScript timed out"""
    logger.warning("\n--------- IN is_fileutil_error")
    # TODO
    # return "Permission denied" in str(exception)
    return True

def retry_all_methods(**retry_kwargs):
    """Apply tenacity.retry to all callable methods of a class."""
    def decorator(cls):
        logger.warning("\n--------- IN retry_all_methods")
        for name, attr in cls.__dict__.items():
            if callable(attr) and not name.startswith("__"):
                wrapped = retry(**retry_kwargs)(attr)
                setattr(cls, name, wrapped)
        return cls
    return decorator


import subprocess

def open_alias_script(retry_state: RetryCallState) -> None:
    script = f'''
    tell application "Finder"
        open (POSIX file "{RETRY_FILEUTIL_CONFIG["ALIAS_PATH"]}") -- Finder resolves aliases automatically
    end tell
    '''

    return subprocess.call(
        ["osascript", "-e", script]
    )


if is_macos:
    import Foundation

__all__ = ["FileUtilABC", "FileUtilMacOS", "FileUtilShUtil", "FileUtil", "FileUtilNoOp"]


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
    def cmp(cls, f1, f2, mtime1=None):
        pass

    @classmethod
    @abstractmethod
    def cmp_file_sig(cls, f1, s2):
        pass

    @classmethod
    @abstractmethod
    def file_sig(cls, f1):
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

@retry_all_methods(
    stop=stop_after_attempt(RETRY_FILEUTIL_CONFIG["retries"]),
    wait=wait_fixed(RETRY_FILEUTIL_CONFIG["wait_seconds"]),
    retry=retry_if_exception(is_fileutil_error),
    before_sleep=open_alias_script,
    before=before_log(logger, logging.WARNING),
    after=after_log(logger, logging.WARNING),
    reraise=True,
)
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
    @retry(
        stop=stop_after_attempt(RETRY_FILEUTIL_CONFIG["retries"]),
        wait=wait_fixed(RETRY_FILEUTIL_CONFIG["wait_seconds"]),
        retry=retry_if_exception(is_fileutil_error),
        before_sleep=open_alias_script,
        before=before_log(logger, logging.WARNING),
        after=after_log(logger, logging.WARNING),
        reraise=True,
    )
    def makedirs(cls, name, mode: int = 511, exist_ok: bool = False) -> None:
        """create directory path; creates parent directories if needed"""
        logger.warning(f"\n--------- IN makedirs: {name=}")
        dirpath = normalize_fs_path(name)
        if isinstance(dirpath, pathlib.Path):
            logger.warning(f"\n--------- IN makedirs.mkdir")
            dirpath.mkdir(parents=True, mode=mode, exist_ok=exist_ok)
        else:
            logger.warning(f"\n--------- IN makedirs.os.makedirs")
            os.makedirs(dirpath, mode=mode, exist_ok=exist_ok)

    @classmethod
    def utime(cls, path, times):
        """Set the access and modified time of path."""
        path = normalize_fs_path(path)

        fd = None
        try:
            # Open file and set F_NOCACHE to prevent filesystem cache interference
            fd = os.open(path, os.O_RDONLY)
            fcntl.fcntl(fd, fcntl.F_NOCACHE, 1)

            os.utime(path, times)
            return True
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

    @classmethod
    def cmp(cls, f1, f2, mtime1=None):
        """Does shallow compare (file signatures) of f1 to file f2.
        Arguments:
        f1 --  File name
        f2 -- File name
        mtime1 -- optional, pass alternate file modification timestamp for f1; will be converted to int

        Return value:
        True if the file signatures as returned by stat are the same, False otherwise.
        Does not do a byte-by-byte comparison.
        """

        f1 = normalize_fs_path(f1)
        f2 = normalize_fs_path(f2)

        s1 = cls._sig(os.stat(f1))
        if mtime1 is not None:
            s1 = (s1[0], s1[1], int(mtime1))
        s2 = cls._sig(os.stat(f2))
        if s1[0] != stat.S_IFREG or s2[0] != stat.S_IFREG:
            return False
        return s1 == s2

    @classmethod
    def cmp_file_sig(cls, f1, s2):
        """Compare file f1 to signature s2.
        Arguments:
        f1 --  File name
        s2 -- stats as returned by _sig

        Return value:
        True if the files are the same, False otherwise.
        """

        if not s2:
            return False

        f1 = normalize_fs_path(f1)
        s1 = cls._sig(os.stat(f1))
        if s1[0] != stat.S_IFREG or s2[0] != stat.S_IFREG:
            return False
        return s1 == s2

    @classmethod
    def file_sig(cls, f1):
        """return os.stat signature for file f1 as tuple of (mode, size, mtime)"""
        f1 = normalize_fs_path(f1)
        return cls._sig(os.stat(f1))

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
            raise OSError(f"Error copying {src} to {dest}: {e}") from e

        return True

    @classmethod
    def utime(cls, path, times):
        """Set the access and modified time of path."""
        path = normalize_fs_path(path)
        os.utime(path, times)


class FileUtil(FileUtilShUtil):
    """Various file utilities"""


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
    def file_sig(cls, f1):
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
