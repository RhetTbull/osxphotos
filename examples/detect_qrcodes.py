"""Detect QR Codes in photos in Apple Photos and add qrcode tag/keyword to photos contain a QR Code

    Run with `osxphotos run detect_qrcodes.py`

    Run with `osxphotos run detect_qrcodes.py --help` for help
    
    You'll need to install opencv into your osxphotos environment.  This can be done with:
    `osxphotos install opencv-python`

    All the other dependencies should be already installed with osxphotos (e.g. rich, click)
"""

import datetime
import json
import os
import os.path
from typing import Optional

import click
import cv2
from photoscript import Photo, PhotosLibrary
from rich import print
from rich.progress import Progress

from osxphotos import PhotosDB
from osxphotos.cli.common import get_data_dir
from osxphotos.sqlitekvstore import SQLiteKVStore

QRCODE_KEYWORD = "qrcode"


def detect_qrcode_in_image_cv2(filename: str) -> Optional[str]:
    """Detect QR Code in image file"""
    image = cv2.imread(filename)
    qr_detect = cv2.QRCodeDetector()
    decoded_text, points, qrcode = qr_detect.detectAndDecode(image)
    return decoded_text or None


@click.command()
@click.option(
    "--keyword",
    "-k",
    default=QRCODE_KEYWORD,
    help=f"Keyword to add to photos with QR Code; default = '{QRCODE_KEYWORD}'.",
)
@click.option(
    "--description",
    "-d",
    is_flag=True,
    help="Set the description of the photo to the decoded QR Code text.",
)
@click.option(
    "--verbose",
    "-V",
    "verbose_mode",
    is_flag=True,
    help="Print verbose output.",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Dry run mode: don't actually update keywords in Photos library.",
)
@click.option(
    "--selected",
    "-s",
    is_flag=True,
    help="Only process selected photos.",
)
@click.option(
    "--reset",
    "-R",
    help="Reset the database of previously processed photos.",
    is_flag=True,
)
def detect_qrcodes(keyword, description, verbose_mode, dry_run, selected, reset):
    """Detect QR Codes in your photos and add a tag/keyword to photos containing a QR Code."""
    # osxphotos includes a simple sqlite-based key-value store for storing data
    # Use this to store photos that have already been processed so if the script is re-run
    # it doesn't re-process photos that have already been processed

    # get_data_dir() returns the path to the user's XDG data directory, usually ~/.local/share/osxphotos
    # reference: https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html

    def verbose(msg):
        if not verbose_mode:
            return
        print(msg)

    db_path = os.path.join(get_data_dir(), "qrcodes.db")
    if reset:
        verbose(f"Resetting database: {db_path}")
        if os.path.exists(db_path):
            os.remove(db_path)
    verbose(f"Using database {db_path}")
    # enable write-ahead logging for performance, serialize/deserialize data as JSON
    kvstore = SQLiteKVStore(
        db_path, wal=True, serialize=json.dumps, deserialize=json.loads
    )

    # get list of photos to process
    verbose("Getting list of photos to process...")
    # Capture selection before loading the Photos database it can take a while to process the database
    # and the selection may change while the database is being processed
    selection = PhotosLibrary().selection if selected else []
    # the QR detection doesn't work on movies so exclude movies
    photos = PhotosDB().photos(movies=False)
    if selected:
        selected_uuid = [p.uuid for p in selection]
        photos = [p for p in photos if p.uuid in selected_uuid]

    # track number of photos processed for reporting at the end
    num_photos = len(photos)
    num_processed = 0
    num_previously_processed = 0
    num_skipped = 0
    num_qrcodes = 0

    # process all the photos
    with Progress() as progress:
        task = progress.add_task(f"Processing {num_photos} photos", total=num_photos)
        for photo in photos:
            # check if photo has already been processed
            if kvstore.get(photo.uuid):
                verbose(
                    f"Skipping previously processed photo {photo.original_filename} ({photo.uuid})"
                )
                num_previously_processed += 1
                continue

            # cv2.imread() doesn't work on some file types like HEIC but every photo has a
            # JPEG preview image ("derivative" in Photos) so use that. The preview image is
            # smaller and lower-resolution, but in my testing, good enough for QR detection
            if not photo.path_derivatives:
                verbose(
                    f"Skipping {photo.original_filename} ({photo.uuid}), could not find photo path"
                )
                num_skipped += 1
                continue
            photo_path = photo.path_derivatives[0]

            # record that will be stored in the kvstore database
            record = {
                "datetime": datetime.datetime.now().isoformat(),
                "uuid": photo.uuid,
                "original_filename": photo.original_filename,
                "qrcode": None,
            }
            verbose(f"Processing {photo.original_filename} ({photo.uuid})")
            num_processed += 1
            if qrcode_text := detect_qrcode_in_image_cv2(photo_path):
                # add qrcode tag/keyword to photo
                # osxphotos PhotoInfo objects are read-only but you can get a photoscript Photo object
                # that allows you to modify certain data about the Photo via the Photos app AppleScript interface
                photo_ = Photo(photo.uuid)
                if not dry_run:
                    photo_.keywords = list(set(photo_.keywords + [keyword]))
                    if description:
                        photo_.description = qrcode_text
                record["qrcode"] = qrcode_text
                verbose(
                    f"Added {keyword} to {photo.original_filename} ({photo.uuid}), detected QR Code: {qrcode_text}"
                )
                num_qrcodes += 1

            # store photo in kvstore to indicate it's been processed
            if not dry_run:
                kvstore.set(photo.uuid, record)

            progress.advance(task)

    print(f"Processed {num_photos} photos")
    print(f"Previously processed {num_previously_processed} photos")
    print(f"Skipped {num_skipped} missing photos")
    print(f"Processed {num_processed} photos this time")
    print(f"Detected {num_qrcodes} QR Codes")


if __name__ == "__main__":
    detect_qrcodes()
