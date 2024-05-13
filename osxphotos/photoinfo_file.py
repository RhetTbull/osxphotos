"""A mock PhotoInfo class for a file instead of an asset in the Photos library"""

from __future__ import annotations

import datetime
import logging
import os
import pathlib
import uuid
from typing import Optional, Union

from ._constants import _OSXPHOTOS_NONE_SENTINEL
from .datetime_utils import datetime_naive_to_local
from .exiftool import ExifToolCaching, get_exiftool_path
from .metadata_reader import MetaData, metadata_from_exiftool, metadata_from_sidecar
from .phototemplate import PhotoTemplate, RenderOptions
from .platform import is_macos

if is_macos:
    from .fingerprint import fingerprint
    from .image_file_utils import is_image_file, is_video_file

try:
    EXIFTOOL_PATH = get_exiftool_path()
except FileNotFoundError:
    EXIFTOOL_PATH = None

logger = logging.getLogger("osxphotos")

__all__ = ["PhotoInfoFromFile"]


class PhotoInfoFromFile:
    """Mock PhotoInfo class for a file

    Returns None for most attributes but allows some templates like exiftool and created to work correctly
    """

    def __init__(
        self,
        filepath: Union[str, pathlib.Path],
        exiftool: str | None = None,
        sidecar: str | None = None,
    ):
        self._path = str(filepath)
        self._exiftool_path = exiftool or EXIFTOOL_PATH
        self._uuid = str(uuid.uuid1()).upper()
        self._sidecar = sidecar
        self._metadata = MetaData()
        if self._exiftool_path:
            self._metadata |= metadata_from_exiftool(
                pathlib.Path(filepath), self._exiftool_path
            )
        if sidecar:
            self._metadata |= metadata_from_sidecar(pathlib.Path(sidecar), exiftool)

    @property
    def uuid(self):
        return self._uuid

    @property
    def original_filename(self) -> str:
        return pathlib.Path(self._path).name

    @property
    def filename(self):
        return pathlib.Path(self._path).name

    @property
    def original_filesize(self) -> int:
        return os.stat(pathlib.Path(self._path)).st_size

    @property
    def isphoto(self) -> bool | None:
        """Return True if file is an image file otherwise False; if not on macOS, returns None"""
        if not is_macos:
            return None
        return is_image_file(self._path)

    @property
    def ismovie(self) -> bool | None:
        """Return True if file is a video file otherwise False; if not on macOS, returns None"""
        if not is_macos:
            return None
        return is_video_file(self._path)

    @property
    def date(self):
        """Use file creation date and local time zone if not exiftool or sidecar"""
        if self._metadata.date:
            if dt := self._metadata.date:
                return datetime_naive_to_local(dt)

        ctime = os.path.getctime(self._path)
        dt = datetime.datetime.fromtimestamp(ctime)
        return datetime_naive_to_local(dt)

    @property
    def path(self):
        """Path to photo file"""
        return self._path

    @property
    def keywords(self) -> list[str]:
        """list of keywords for picture"""
        return self._metadata.keywords

    @property
    def persons(self) -> list[str]:
        """list of persons in picture"""
        return self._metadata.persons

    @property
    def title(self) -> str | None:
        """name / title of picture"""
        return self._metadata.title

    @property
    def description(self) -> str | None:
        """description of picture"""
        return self._metadata.description

    @property
    def rating(self) -> int:
        """rating of picture; reads XMP:Rating from the photo or sidecar file if available, else returns 0"""
        return self._metadata.rating

    @property
    def fingerprint(self) -> str | None:
        """Returns fingerprint of original photo as a string or None if not on macOS"""
        if is_macos:
            return fingerprint(self._path)
        return None

    @property
    def height(self) -> int:
        """height of photo in pixels"""
        return self._metadata.height

    @property
    def width(self) -> int:
        """width of photo in pixels"""
        return self._metadata.width

    @property
    def exiftool(self):
        """Returns a ExifToolCaching (read-only instance of ExifTool) object for the photo.
        Requires that exiftool (https://exiftool.org/) be installed
        If exiftool not installed, logs warning and returns None
        If photo path is missing, returns None
        """
        try:
            # return the memoized instance if it exists
            return self._exiftool
        except AttributeError:
            try:
                exiftool_path = self._exiftool_path or get_exiftool_path()
                if self._path is not None and os.path.isfile(self._path):
                    exiftool = ExifToolCaching(self._path, exiftool=exiftool_path)
                else:
                    exiftool = None
            except FileNotFoundError:
                # get_exiftool_path raises FileNotFoundError if exiftool not found
                exiftool = None
                logger.warning(
                    "exiftool not in path; download and install from https://exiftool.org/"
                )

            self._exiftool = exiftool
            return self._exiftool

    def render_template(
        self, template_str: str, options: Optional[RenderOptions] = None
    ):
        """Renders a template string for PhotoInfo instance using PhotoTemplate

        Args:
            template_str: a template string with fields to render
            options: a RenderOptions instance

        Returns:
            ([rendered_strings], [unmatched]): tuple of list of rendered strings and list of unmatched template values
        """
        options = options or RenderOptions(caller="import", filepath=self.path)
        template = PhotoTemplate(self, exiftool_path=self._exiftool_path)
        return template.render(template_str, options)

    def __getattr__(self, name):
        """Return None for any other non-private attribute"""
        if not name.startswith("_"):
            return None
        raise AttributeError()


def render_photo_template_from_filepath(
    filepath: pathlib.Path,
    relative_filepath: pathlib.Path | None,
    template: str,
    exiftool_path: str | None,
    sidecar: pathlib.Path | None,
):
    """Render template string for a photo from a file instead of a PhotoInfo object

    Args:
        filepath: path to the photo being rendered
        relative_filepath: path to the photo relative to the library or import root; if None, uses filepath
        template: template string to render
        exiftool_path: path to exiftool to retrieve metadata
        sidecar: path to sidecar file if it exists for retrieving metadata

    Returns: list of rendered strings
    """
    photoinfo = PhotoInfoFromFile(
        filepath, exiftool=exiftool_path, sidecar=str(sidecar) if sidecar else None
    )
    render_filepath = relative_filepath or filepath
    options = RenderOptions(
        none_str=_OSXPHOTOS_NONE_SENTINEL,
        # filepath=str(relative_filepath),
        filepath=str(render_filepath),
        caller="import",
    )
    template_values, _ = photoinfo.render_template(template, options=options)
    # filter out empty strings
    template_values = [v.replace(_OSXPHOTOS_NONE_SENTINEL, "") for v in template_values]
    template_values = [v for v in template_values if v]
    return template_values


def strip_edited_suffix(
    filepath: pathlib.Path,
    edited_suffix: str | None,
    exiftool_path: str | None,
) -> pathlib.Path:
    """Strip edited suffix from filename if present

    Args:
        filepath: path to photo file
        edited_suffix: str: suffix template to strip from filename
        exiftool_path: path to exiftool

    Returns: pathlib.Path with edited suffix stripped
    """
    photoinfo = PhotoInfoFromFile(filepath, exiftool=exiftool_path, sidecar=None)
    if not edited_suffix:
        return filepath

    options = RenderOptions()
    template_values, _ = photoinfo.render_template(edited_suffix, options=options)
    if len(template_values) != 1:
        raise ValueError(
            f"edited_suffix template {edited_suffix} must return exactly one value"
        )
    suffix = template_values[0]
    return filepath.with_name(filepath.stem[: -len(suffix)] + filepath.suffix)
