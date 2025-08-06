from pydantic import BaseModel
from typing import Optional, List

class QueryOptionsLike(BaseModel):
    keywords: Optional[List[str]] = None
    persons: Optional[List[str]] = None
    albums: Optional[List[str]] = None
    from_date: Optional[str] = None  # ISO8601
    to_date: Optional[str] = None
    images: bool = True
    movies: bool = True

class PhotoInfoExportOptions(BaseModel):
    dest: str
    filename: Optional[str] = None
    edited: bool = False
    live_photo: bool = False
    export_as_hardlink: bool = False
    overwrite: bool = False
    increment: bool = True
    sidecar_json: bool = False
    sidecar_exiftool: bool = False
    sidecar_xmp: bool = False
    use_photos_export: bool = False
    use_photokit: bool = True
    timeout: int = 120
    exiftool: bool = False
    use_albums_as_keywords: bool = False
    use_persons_as_keywords: bool = False
