""" FileUtil class with methods for copy, hardlink, unlink, etc. """

import logging
import os
import pathlib
import stat
import subprocess
import sys
from abc import ABC, abstractmethod


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
    def cmp_sig(cls, file1, file2):
        pass

    @classmethod
    @abstractmethod
    def file_sig(cls, file1):
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
            logging.critical(f"os.link returned error: {e}")
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

        if not os.path.isfile(src):
            raise FileNotFoundError("src file does not appear to exist", src)

        if norsrc:
            command = ["/usr/bin/ditto", "--norsrc", src, dest]
        else:
            command = ["/usr/bin/ditto", src, dest]

        # if error on copy, subprocess will raise CalledProcessError
        try:
            result = subprocess.run(command, check=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            logging.critical(
                f"ditto returned error: {e.returncode} {e.stderr.decode(sys.getfilesystemencoding()).rstrip()}"
            )
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
    def cmp_sig(cls, f1, s2):
        """Compare file f1 to signature s2.
        Arguments:
        f1 --  File name
        s2 -- stats as returned by sig

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

    @staticmethod
    def _sig(st):
        return (stat.S_IFMT(st.st_mode), st.st_size, st.st_mtime)


class FileUtil(FileUtilMacOS):
    """ Various file utilities """

    pass


class FileUtilNoOp(FileUtil):
    """ No-Op implementation of FileUtil for testing / dry-run mode
        all methods with exception of cmp_sig and file_cmp are no-op
        cmp_sig functions as FileUtil.cmp_sig does
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
    def file_sig(cls, file1):
        cls.verbose(f"file_sig: {file1}")
        return (42, 42, 42)
