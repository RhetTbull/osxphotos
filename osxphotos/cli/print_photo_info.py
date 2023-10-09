"""print_photo_info function to print PhotoInfo objects"""

import csv
import json
import sys
from typing import Callable, List, Tuple

from osxphotos.photoinfo import PhotoInfo


def print_photo_info(
    photos: List[PhotoInfo], json: bool = False, print_func: Callable = print
):
    dump = []
    if json:
        dump.extend(p.json(shallow=False) for p in photos)
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


def print_photo_fields(
    photos: List[PhotoInfo], fields: Tuple[Tuple[str]], json_format: bool
):
    """Output custom field templates from PhotoInfo objects

    Args:
        photos: List of PhotoInfo objects
        fields: Tuple of Tuple of field names/field templates to output"""
    keys = [f[0] for f in fields]
    data = []
    for p in photos:
        record = {}
        for field in fields:
            rendered_value, unmatched = p.render_template(field[1])
            if unmatched:
                raise ValueError(
                    f"Unmatched template variables in field {field[0]}: {field[1]}"
                )
            field_value = (
                rendered_value[0]
                if len(rendered_value) == 1
                else ",".join(rendered_value)
                if not json_format
                else rendered_value
            )
            record[field[0]] = field_value
        data.append(record)

    if json_format:
        print(json.dumps(data, indent=4))
    else:
        # dump as CSV
        csv_writer = csv.writer(
            sys.stdout, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        # add headers
        csv_writer.writerow(keys)
        for record in data:
            csv_writer.writerow(record.values())
