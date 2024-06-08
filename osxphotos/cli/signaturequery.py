"""Check a signature template against Photos library to determine if a photo is a match"""

import datetime
import os
import pathlib

from osxphotos.cli.sidecar import get_sidecar_file_with_template
from osxphotos.photoinfo_file import PhotoInfoFromFile
from osxphotos.photosdb import PhotosDB


class SignatureQuery:
    """Class to query Photos library for photos matching signature; works like FingerprintQuery but uses signature instead of fingerprint"""

    def __init__(
        self,
        library: str | os.PathLike | None,
        signature: str,
        sidecar: bool = False,
        sidecar_template: str | None = None,
        edited_suffix: str | None = None,
        exiftool_path: str | None = None,
    ):
        """Create a new SignatureQuery object

        Args:
            library: path to Photos library
        """
        self.photosdb = PhotosDB(dbfile=str(library) if library else None)
        self.signature = signature
        self.sidecar = sidecar
        self.sidecar_template = sidecar_template
        self.exiftool_path = exiftool_path
        self.edited_suffix = edited_suffix
        self._mapping = self._map_signatures()

    def possible_duplicates(
        self, filepath: str | os.PathLike
    ) -> list[tuple[str, datetime.datetime, str]]:
        """Return a list of tuples of (uuid, date_added, filename) for all photos matching signature"""
        sidecar_file = get_sidecar_file_with_template(
            filepath=filepath,
            sidecar=self.sidecar,
            sidecar_filename_template=self.sidecar_template,
            edited_suffix=self.edited_suffix,
            exiftool_path=self.exiftool_path,
        )
        photo = PhotoInfoFromFile(
            filepath, exiftool=self.exiftool_path, sidecar=sidecar_file
        )
        rendered, _ = photo.render_template(self.signature)
        signature = rendered[0] if rendered else None
        if not signature:
            return []
        print(f"Signature: {signature}")
        if signature in self._mapping:
            return [
                (
                    photo.uuid,
                    photo.date_added,
                    photo.original_filename,
                )
                for photo in self._mapping[signature]
            ]
        return []

    def _map_signatures(self):
        """Map signature to photos in Photos library"""
        photos = self.photosdb.photos()
        signature_map = {}
        for photo in photos:
            renderd, _ = photo.render_template(self.signature)
            sig = renderd[0] if renderd else None
            if not sig:
                continue
            if sig in signature_map:
                signature_map[sig].append(photo)
            else:
                signature_map[sig] = [photo]
            print(f"Signature: {sig}")
        return signature_map
