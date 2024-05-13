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


class PhotoInfoFromDict(PhotoInfoMixin):
    """Create a PhotoInfo compatible object from a PhotoInfo dictionary created with PhotoInfo.asdict() or deserialized from JSON"""

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
