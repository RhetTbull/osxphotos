"""Create a PhotoInfo compatible object from a PhotoInfo dictionary created with PhotoInfo.asdict()"""

from __future__ import annotations

import json
from typing import Any

from .exiftool import ExifToolCaching, get_exiftool_path
from .photoinfo_protocol import PhotoInfoMixin
from .phototemplate import PhotoTemplate, RenderOptions
from .rehydrate import rehydrate_class

try:
    EXIFTOOL_PATH = get_exiftool_path()
except FileNotFoundError:
    EXIFTOOL_PATH = None

__all__ = ["PhotoInfoFromDict", "photoinfo_from_dict"]


class AlbumInfoFromDict:
    """A minimal AlbumInfo object reconstructed from PhotoInfo.asdict()["folders"]"""

    def __init__(self, title: str, folders: list[str]):
        self._title = title
        self._folder_names = folders

    @property
    def title(self) -> str:
        return self._title

    @property
    def folder_names(self) -> list[str]:
        return self._folder_names

    def __getattr__(self, name):
        if name in {
            "uuid",
            "creation_date",
            "start_date",
            "end_date",
            "owner",
            "sort_order",
            "parent",
        }:
            return None
        elif name == "folder_list":
            return []
        else:
            raise AttributeError(f"Invalid attribute: {name}")


class PhotoInfoFromDict(PhotoInfoMixin):
    """Create a PhotoInfo compatible object from a PhotoInfo dictionary created with PhotoInfo.asdict() or deserialized from JSON"""

    @property
    def album_info(self) -> AlbumInfoFromDict:
        """Return AlbumInfo objects for photo"""
        # this is a little hacky but it works for `osxphotos import` use case
        if not getattr(self, "folders"):
            return []
        # self.folders is a rehydrated object so need access it's __dict__ to get the actual data
        return [
            AlbumInfoFromDict(title, folders)
            for title, folders in self.folders.__dict__.items()
        ]

    def asdict(self) -> dict[str, Any]:
        """Return the PhotoInfo dictionary"""
        return self._data

    def json(self) -> str:
        """Return the PhotoInfo dictionary as a JSON string"""
        return json.dumps(self._data)

    def render_template(self, template_str: str, options: RenderOptions | None = None):
        """Renders a template string for PhotoInfo instance using PhotoTemplate

        Args:
            template_str: a template string with fields to render
            options: a RenderOptions instance

        Returns:
            ([rendered_strings], [unmatched]): tuple of list of rendered strings and list of unmatched template values
        """
        options = options or RenderOptions()
        template = PhotoTemplate(self, exiftool_path=self._exiftool_path)
        return template.render(template_str, options)


def photoinfo_from_dict(
    data: dict[str, Any], exiftool: str | None = None
) -> PhotoInfoFromDict:
    """Create a PhotoInfoFromDict object from a dictionary"""
    photoinfo = rehydrate_class(data, PhotoInfoFromDict)
    photoinfo._exiftool_path = exiftool or EXIFTOOL_PATH
    photoinfo._data = data
    return photoinfo
