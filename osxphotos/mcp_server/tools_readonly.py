from mcp.server.fastmcp import Context
from .schemas import QueryOptionsLike
from osxphotos import PhotosDB
from typing import Optional, List, Dict, Any

def _db() -> PhotosDB:
    """Returns a PhotosDB instance."""
    return PhotosDB()

def list_albums(pattern: str | None = None, ctx: Context = None) -> list[dict]:
    """
    Lists albums, optionally filtering by a pattern.

    :param pattern: A string to filter album titles by (case-insensitive).
    :return: A list of dictionaries, each representing an album.
    """
    db = PhotosDB()
    albums = [a for a in db.album_info if (not pattern or pattern.lower() in a.title.lower())]
    return [{"uuid": a.uuid, "title": a.title} for a in albums]

def search_photos(q: QueryOptionsLike, ctx: Context) -> list[str]:
    """
    Searches for photos based on a set of query options.

    :param q: A QueryOptionsLike object with search criteria.
    :return: A list of UUIDs for the photos that match the query.
    """
    db = PhotosDB()
    query_args = q.model_dump(exclude_none=True)
    results = db.query(QueryOptions(**query_args))
    return [p.uuid for p in results]

def photo_info(uuid: str, ctx: Context) -> dict:
    """
    Gets the information for a specific photo.

    :param uuid: The UUID of the photo to get information for.
    :return: A dictionary containing the photo's information.
    """
    db = PhotosDB()
    photo = db.get_photo(uuid)
    return photo.asdict() if photo else {"error": "not found", "uuid": uuid}

def estimate_export(uuids: list[str], options: ExportOptionsLike, ctx: Context) -> dict:
    """
    (Not Implemented) Estimates the result of an export operation.
    """
    raise NotImplementedError("estimate_export is not yet implemented.")

def estimate_export(plan: Dict) -> Dict[str, Any]:
    """(Placeholder) Estimates the results of an export operation."""
    # This is a placeholder. A real implementation would need an `ExportPlan` schema
    # and would call the exporter in dry_run mode.
    return {"status": "not_implemented", "message": "estimate_export requires a defined ExportPlan schema."}
