import os
import asyncio
from mcp.server.fastmcp import Context
from .schemas import PhotoInfoExportOptions
from typing import List, Dict, Any
from osxphotos import PhotosDB, ExifTool
import photoscript
import pathlib

def write_enabled() -> bool:
    """Checks if write operations are enabled via an environment variable."""
    return os.environ.get("OSXPHOTOS_MCP_ALLOW_WRITE") == "1"

async def export_photos(uuids: List[str], options: PhotoInfoExportOptions, ctx: Context) -> Dict[str, Any]:
    """
    Exports photos to a specified destination.

    :param uuids: A list of photo UUIDs to export.
    :param options: An PhotoInfoExportOptions object with export settings.
    :return: A dictionary with lists of exported files and errors.
    """
    if not write_enabled():
        return {"error": "write operations not enabled"}
    
    db = PhotosDB()
    exported_files = []
    errors = []
    total = len(uuids)

    export_args = options.model_dump()
    dest = export_args.pop("dest")
    
    try:
        dest_path = pathlib.Path(dest).resolve()
    except Exception as e:
        return {"error": f"Invalid destination path: {e}"}

    for i, uuid in enumerate(uuids, 1):
        if await ctx.is_cancelled():
            return {"status": "cancelled", "exported": exported_files, "errors": errors}

        photo = db.get_photo(uuid)
        if not photo:
            errors.append({"uuid": uuid, "error": "photo not found"})
            continue

        try:
            # Run the blocking export call in a separate thread
            exported = await asyncio.to_thread(photo.export, str(dest_path), **export_args)
            exported_files.extend(exported)
        except Exception as e:
            errors.append({"uuid": uuid, "error": "An unexpected error occurred during export."})
        
        await ctx.report_progress(progress=i/total, message=f"Exported {i} of {total} photos.")

    return {"exported": exported_files, "errors": errors}

def add_keywords(uuids: List[str], keywords: List[str], ctx: Context) -> Dict[str, Any]:
    """
    Adds keywords to a list of photos.

    :param uuids: A list of photo UUIDs.
    :param keywords: A list of keywords to add.
    :return: A dictionary with success count and a list of errors.
    """
    if not write_enabled():
        return {"error": "write operations not enabled"}

    success_count = 0
    errors = []

    for uuid in uuids:
        try:
            photo = photoscript.Photo(uuid)
            existing_keywords = set(photo.keywords)
            new_keywords = existing_keywords.union(set(keywords))
            photo.keywords = list(new_keywords)
            success_count += 1
        except Exception as e:
            errors.append({"uuid": uuid, "error": "Failed to add keywords."})

    return {"success": success_count, "errors": errors}

def create_album(title: str, ctx: Context) -> Dict[str, Any]:
    """
    Creates a new album in Photos.

    :param title: The title of the new album.
    :return: A dictionary with the new album's UUID and title, or an error.
    """
    if not write_enabled():
        return {"error": "write operations not enabled"}

    try:
        library = photoscript.PhotosLibrary()
        album = library.create_album(title)
        return {"uuid": album.uuid, "title": album.title}
    except Exception as e:
        return {"error": "Failed to create album."}

def add_to_album(album_uuid: str, uuids: List[str], ctx: Context) -> Dict[str, Any]:
    """
    Adds photos to an existing album.

    :param album_uuid: The UUID of the album to add photos to.
    :param uuids: A list of photo UUIDs to add to the album.
    :return: A dictionary indicating success or an error.
    """
    if not write_enabled():
        return {"error": "write operations not enabled"}

    try:
        album = photoscript.Album(album_uuid)
        photos = [photoscript.Photo(uuid) for uuid in uuids]
        album.add(photos)
        return {"success": True}
    except Exception as e:
        return {"error": "Failed to add photos to album."}

def write_exif(uuids: List[str], fields: Dict, ctx: Context) -> Dict[str, Any]:
    """
    Writes EXIF data to a list of photos.

    :param uuids: A list of photo UUIDs to write EXIF data to.
    :param fields: A dictionary of EXIF tags and values to write.
    :return: A dictionary with success count and a list of errors.
    """
    if not write_enabled():
        return {"error": "write operations not enabled"}

    db = PhotosDB()
    success_count = 0
    errors = []

    for uuid in uuids:
        photo = db.get_photo(uuid)
        if not photo or not photo.path:
            errors.append({"uuid": uuid, "error": "photo not found or path is missing"})
            continue

        try:
            with ExifTool(photo.path) as exif:
                for tag, value in fields.items():
                    exif.set_value(tag, value)
            success_count += 1
        except Exception as e:
            errors.append({"uuid": uuid, "error": "Failed to write EXIF data."})

    return {"success": success_count, "errors": errors}