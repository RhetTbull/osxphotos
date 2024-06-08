"""Query any photos since the last run and extract text from them."""

import datetime
import json

import osxphotos
from osxphotos.cli import echo, kvstore, query_command


@query_command()
def new_text(photos: list[osxphotos.PhotoInfo], **kwargs):
    """Query any photos since the last run and extract text from them."""
    kv = kvstore("osxphotos_new_text")
    results = []
    for photo in photos:
        if photo.uuid in kv:
            continue
        if text := photo.search_info.detected_text:
            data = {
                "photo": photo.original_filename,
                "path": photo.path,
                "uuid": photo.uuid,
                "date_added": (
                    photo.date_added.isoformat() if photo.date_added else None
                ),
                "text": text,
            }
            results.append(data)
        kv[photo.uuid] = datetime.datetime.now().isoformat()
    kv.close()
    echo(json.dumps(results, indent=4))


if __name__ == "__main__":
    new_text()
