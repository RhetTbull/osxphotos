from mcp.server.fastmcp import Context, Image
from osxphotos import PhotosDB
import os

def _db() -> PhotosDB:
    """Returns a PhotosDB instance.
    Note: This might need to be adapted to handle different library paths
    based on configuration or user input in a real implementation."""
    return PhotosDB()

def library_default() -> dict:
    """Returns metadata about the default Photos library."""
    db = _db()
    return {
        "library_path": db.library_path,
        "db_path": db.db_path,
        "db_version": db.db_version,
        "counts": {"photos": len(db.photos()), "albums": len(list(db.albums))},
    }

def album_json(uuid: str) -> dict:
    """Returns metadata for a specific album."""
    db = _db()
    album = db.get_album(uuid)
    if not album:
        return {"error": "album not found", "uuid": uuid}
    
    return {
        "uuid": album.uuid,
        "title": album.title,
        "photo_uuids": [p.uuid for p in album.photos],
    }

def photo_json(uuid: str) -> dict:
    """Returns the full metadata for a photo as a dictionary."""
    p = _db().get_photo(uuid)
    return p.asdict() if p else {"error": "not found", "uuid": uuid}

def photo_thumb(uuid: str) -> Image | dict:
    """Returns a thumbnail for a photo."""
    p = _db().get_photo(uuid)
    if not p:
        return {"error": "not found", "uuid": uuid}

    # Use the smallest derivative as the thumbnail
    derivatives = p.path_derivatives
    if not derivatives:
        return {"error": "no thumbnail available", "uuid": uuid}

    thumb_path = derivatives[-1] # Smallest is last

    if not os.path.exists(thumb_path):
        return {"error": "thumbnail file not found", "uuid": uuid, "path": thumb_path}

    with open(thumb_path, "rb") as f:
        content = f.read()
    
    # Determine mimetype from extension
    ext = os.path.splitext(thumb_path)[1].lower()
    mimetype = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }.get(ext, "application/octet-stream")

    return Image(data=content)
