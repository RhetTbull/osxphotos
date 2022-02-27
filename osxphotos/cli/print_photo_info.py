"""print_photo_info function to print PhotoInfo objects"""

import csv
import sys
from typing import Callable, List

from osxphotos.photoinfo import PhotoInfo


def print_photo_info(
    photos: List[PhotoInfo], json: bool = False, print_func: Callable = print
):
    dump = []
    if json:
        dump.extend(p.json() for p in photos)
        print_func(f"[{', '.join(dump)}]")
    else:
        # dump as CSV
        csv_writer = csv.writer(
            sys.stdout, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        # add headers
        dump.append(
            [
                "uuid",
                "filename",
                "original_filename",
                "date",
                "description",
                "title",
                "keywords",
                "albums",
                "persons",
                "path",
                "ismissing",
                "hasadjustments",
                "external_edit",
                "favorite",
                "hidden",
                "shared",
                "latitude",
                "longitude",
                "path_edited",
                "isphoto",
                "ismovie",
                "uti",
                "burst",
                "live_photo",
                "path_live_photo",
                "iscloudasset",
                "incloud",
                "date_modified",
                "portrait",
                "screenshot",
                "slow_mo",
                "time_lapse",
                "hdr",
                "selfie",
                "panorama",
                "has_raw",
                "uti_raw",
                "path_raw",
                "intrash",
            ]
        )
        for p in photos:
            date_modified_iso = p.date_modified.isoformat() if p.date_modified else None
            dump.append(
                [
                    p.uuid,
                    p.filename,
                    p.original_filename,
                    p.date.isoformat(),
                    p.description,
                    p.title,
                    ", ".join(p.keywords),
                    ", ".join(p.albums),
                    ", ".join(p.persons),
                    p.path,
                    p.ismissing,
                    p.hasadjustments,
                    p.external_edit,
                    p.favorite,
                    p.hidden,
                    p.shared,
                    p._latitude,
                    p._longitude,
                    p.path_edited,
                    p.isphoto,
                    p.ismovie,
                    p.uti,
                    p.burst,
                    p.live_photo,
                    p.path_live_photo,
                    p.iscloudasset,
                    p.incloud,
                    date_modified_iso,
                    p.portrait,
                    p.screenshot,
                    p.slow_mo,
                    p.time_lapse,
                    p.hdr,
                    p.selfie,
                    p.panorama,
                    p.has_raw,
                    p.uti_raw,
                    p.path_raw,
                    p.intrash,
                ]
            )
        for row in dump:
            csv_writer.writerow(row)
