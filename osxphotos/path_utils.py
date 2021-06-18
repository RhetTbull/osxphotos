""" utility functions for validating/sanitizing path components """

import pathvalidate

from ._constants import MAX_DIRNAME_LEN, MAX_FILENAME_LEN


def sanitize_filepath(filepath):
    """sanitize a filepath"""
    return pathvalidate.sanitize_filepath(filepath, platform="macos")


def is_valid_filepath(filepath):
    """returns True if a filepath is valid otherwise False"""
    return pathvalidate.is_valid_filepath(filepath, platform="macos")


def sanitize_filename(filename, replacement=":"):
    """replace any illegal characters in a filename and truncate filename if needed

    Args:
        filename: str, filename to sanitze
        replacement: str, value to replace any illegal characters with; default = ":"

    Returns:
        filename with any illegal characters replaced by replacement and truncated if necessary
    """

    if filename:
        filename = filename.replace("/", replacement)
        if len(filename) > MAX_FILENAME_LEN:
            parts = filename.split(".")
            drop = len(filename) - MAX_FILENAME_LEN
            if len(parts) > 1:
                # has an extension
                ext = parts.pop(-1)
                stem = ".".join(parts)
                if drop > len(stem):
                    ext = ext[:-drop]
                else:
                    stem = stem[:-drop]
                filename = f"{stem}.{ext}"
            else:
                filename = filename[:-drop]
    return filename


def sanitize_dirname(dirname, replacement=":"):
    """replace any illegal characters in a directory name and truncate directory name if needed

    Args:
        dirname: str, directory name to sanitize
        replacement: str, value to replace any illegal characters with; default = ":"; if None, no replacement occurs

    Returns:
        dirname with any illegal characters replaced by replacement and truncated if necessary
    """
    if dirname:
        dirname = sanitize_pathpart(dirname, replacement=replacement)
    return dirname


def sanitize_pathpart(pathpart, replacement=":"):
    """replace any illegal characters in a path part (either directory or filename without extension) and truncate name if needed

    Args:
        pathpart: str, path part to sanitize
        replacement: str, value to replace any illegal characters with; default = ":"; if None, no replacement occurs

    Returns:
        pathpart with any illegal characters replaced by replacement and truncated if necessary
    """
    if pathpart:
        pathpart = (
            pathpart.replace("/", replacement) if replacement is not None else pathpart
        )
        if len(pathpart) > MAX_DIRNAME_LEN:
            drop = len(pathpart) - MAX_DIRNAME_LEN
            pathpart = pathpart[:-drop]
    return pathpart
