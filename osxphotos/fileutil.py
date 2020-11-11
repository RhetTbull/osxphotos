""" FileUtil class with methods for copy, hardlink, unlink, etc. """

import os
import pathlib
import stat
import subprocess
import sys
from abc import ABC, abstractmethod

from .imageconverter import ImageConverter

class FileUtilABC(ABC):
    """ Abstract base class for FileUtil """

    @classmethod
    @abstractmethod
    def hardlink(cls, src, dest):
        pass

    @classmethod
    @abstractmethod
    def copy(cls, src, dest, norsrc=False):
        pass

    @classmethod
    @abstractmethod
    def unlink(cls, dest):
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
    def cmp_file_sig(cls, file1, file2):
        pass

    @classmethod
    @abstractmethod
    def file_sig(cls, file1):
        pass

    @classmethod
    @abstractmethod
    def convert_to_jpeg(cls, src_file, dest_file, compression_quality=1.0):
        pass


class FileUtilMacOS(FileUtilABC):
    """ Various file utilities """

    @classmethod
    def hardlink(cls, src, dest):
        """ Hardlinks a file from src path to dest path 
            src: source path as string 
            dest: destination path as string
            Raises exception if linking fails or either path is None """

        if src is None or dest is None:
            raise ValueError("src and dest must not be None", src, dest)

        if not os.path.isfile(src):
            raise FileNotFoundError("src file does not appear to exist", src)

        # if error on copy, subprocess will raise CalledProcessError
        try:
            os.link(src, dest)
        except Exception as e:
            raise e

    @classmethod
    def copy(cls, src, dest, norsrc=False):
        """ Copies a file from src path to dest path 
            src: source path as string 
            dest: destination path as string
            norsrc: (bool) if True, uses --norsrc flag with ditto so it will not copy
                    resource fork or extended attributes.  May be useful on volumes that
                    don't work with extended attributes (likely only certain SMB mounts)
                    default is False
            Uses ditto to perform copy; will silently overwrite dest if it exists
            Raises exception if copy fails or either path is None """

        if src is None or dest is None:
            raise ValueError("src and dest must not be None", src, dest)

        if not os.path.exists(src):
            raise FileNotFoundError("src file does not appear to exist", src)

        if norsrc:
            command = ["/usr/bin/ditto", "--norsrc", src, dest]
        else:
            command = ["/usr/bin/ditto", src, dest]

        # if error on copy, subprocess will raise CalledProcessError
        try:
            result = subprocess.run(command, check=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise e

        return result.returncode

    @classmethod
    def unlink(cls, filepath):
        """ unlink filepath; if it's pathlib.Path, use Path.unlink, otherwise use os.unlink """
        if isinstance(filepath, pathlib.Path):
            filepath.unlink()
        else:
            os.unlink(filepath)

    @classmethod
    def utime(cls, path, times):
        """ Set the access and modified time of path. """
        os.utime(path, times)

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

        s1 = cls._sig(os.stat(f1))

        if s1[0] != stat.S_IFREG or s2[0] != stat.S_IFREG:
            return False
        return s1 == s2

    @classmethod
    def file_sig(cls, f1):
        """ return os.stat signature for file f1 """
        return cls._sig(os.stat(f1))
    
    @classmethod
    def convert_to_jpeg(cls, src_file, dest_file, compression_quality=1.0):
        """ converts image file src_file to jpeg format as dest_file

            Args:
                src_file: image file to convert
                dest_file: destination path to write converted file to
                compression quality: JPEG compression quality in range 0.0 <= compression_quality <= 1.0; default 1.0 (best quality)
                
            Returns:
                True if success, otherwise False 
        """
        converter = ImageConverter()
        return converter.write_jpeg(src_file, dest_file, compression_quality=compression_quality)

    @staticmethod
    def _sig(st):
        """ return tuple of (mode, size, mtime) of file based on os.stat
            Args:
                st: os.stat signature
        """
        # use int(st.st_mtime) because ditto does not copy fractional portion of mtime
        return (stat.S_IFMT(st.st_mode), st.st_size, int(st.st_mtime))

class FileUtil(FileUtilMacOS):
    """ Various file utilities """

    pass


class FileUtilNoOp(FileUtil):
    """ No-Op implementation of FileUtil for testing / dry-run mode
        all methods with exception of cmp, cmp_file_sig and file_cmp are no-op
        cmp and cmp_file_sig functions as FileUtil methods do
        file_cmp returns mock data
    """

    @staticmethod
    def noop(*args):
        pass

    verbose = noop

    def __new__(cls, verbose=None):
        if verbose:
            if callable(verbose):
                cls.verbose = verbose
            else:
                raise ValueError(f"verbose {verbose} not callable")
        return super(FileUtilNoOp, cls).__new__(cls)

    @classmethod
    def hardlink(cls, src, dest):
        cls.verbose(f"hardlink: {src} {dest}")

    @classmethod
    def copy(cls, src, dest, norsrc=False):
        cls.verbose(f"copy: {src} {dest}")

    @classmethod
    def unlink(cls, dest):
        cls.verbose(f"unlink: {dest}")

    @classmethod
    def utime(cls, path, times):
        cls.verbose(f"utime: {path}, {times}")

    @classmethod
    def file_sig(cls, file1):
        cls.verbose(f"file_sig: {file1}")
        return (42, 42, 42)

    @classmethod
    def convert_to_jpeg(cls, src_file, dest_file, compression_quality=1.0):
        cls.verbose(f"convert_to_jpeg: {src_file}, {dest_file}, {compression_quality}")
