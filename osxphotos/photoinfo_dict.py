"""Create a PhotoInfo compatible object from a PhotoInfo dictionary created with PhotoInfo.asdict()"""

from __future__ import annotations

import json
from typing import Any

from .exiftool import ExifToolCaching, get_exiftool_path
from .rehydrate import rehydrate_class

try:
    EXIFTOOL_PATH = get_exiftool_path()
except FileNotFoundError:
    EXIFTOOL_PATH = None

__all__ = ["PhotoInfoFromDict", "photoinfo_from_dict"]


class PhotoInfoFromDict:
    """Create a PhotoInfo compatible object from a PhotoInfo dictionary created with PhotoInfo.asdict() or deserialized from JSON"""

    def asdict(self) -> dict[str, Any]:
        """Return the PhotoInfo dictionary"""
        return self._data

    def json(self) -> str:
        """Return the PhotoInfo dictionary as a JSON string"""
        return json.dumps(self._data)


def photoinfo_from_dict(
    data: dict[str, Any], exiftool: str | None = None
) -> PhotoInfoFromDict:
    """Create a PhotoInfoFromDict object from a dictionary"""
    photoinfo = rehydrate_class(data, PhotoInfoFromDict)
    photoinfo._exiftool_path = exiftool or EXIFTOOL_PATH
    photoinfo._data = data
    return photoinfo
