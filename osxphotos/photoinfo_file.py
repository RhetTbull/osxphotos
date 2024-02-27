"""A mock PhotoInfo class for a file or a dict instead of an asset in the Photos library"""

from __future__ import annotations

import datetime
import logging
import os
import pathlib
import uuid
from typing import Optional, Union

from .datetime_utils import datetime_naive_to_local
from .exiftool import ExifToolCaching, get_exiftool_path
from .metadata_reader import MetaData, metadata_from_file, metadata_from_sidecar
from .phototemplate import PhotoTemplate, RenderOptions
from .platform import is_macos

if is_macos:
    from .fingerprint import fingerprint

try:
    EXIFTOOL_PATH = get_exiftool_path()
except FileNotFoundError:
    EXIFTOOL_PATH = None

logger = logging.getLogger("osxphotos")

__all__ = ["PhotoInfoFromDict", "PhotoInfoFromFile"]


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
        if sidecar:
            self._metadata = metadata_from_sidecar(pathlib.Path(sidecar), exiftool)
        elif self._exiftool_path:
            self._metadata = metadata_from_file(
                pathlib.Path(filepath), self._exiftool_path
            )
        else:
            self._metadata = MetaData(
                title="", description="", keywords=[], location=(None, None)
            )

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
    def fingerprint(self) -> str | None:
        """Returns fingerprint of original photo as a string or None if not on macOS"""
        if is_macos:
            return fingerprint(self._path)
        return None

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
        options = options or RenderOptions(caller="import")
        template = PhotoTemplate(self, exiftool_path=self._exiftool_path)
        return template.render(template_str, options)

    def __getattr__(self, name):
        """Return None for any other non-private attribute"""
        if not name.startswith("_"):
            return None
        raise AttributeError()


class PhotoInfoFromDict:
    """Rehydrate a PhotoInfo class from a dict"""

    def __init__(
        self,
        data: dict,
        exiftool: str | None = None,
    ):
        self._data = data
        self._exiftool_path = exiftool or EXIFTOOL_PATH

    def __getattr__(self, name):
        """Return dict value or None for non-private attribute"""
        if not name.startswith("_"):
            return self._data.get(name)
        raise AttributeError()
