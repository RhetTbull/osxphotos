"""Freeze a PhotoInfo object to allow it to be used in concurrent.futures."""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
from types import SimpleNamespace
from typing import Any

from osxmetadata import OSXMetaData

import osxphotos

from ._constants import TEXT_DETECTION_CONFIDENCE_THRESHOLD
from .exiftool import ExifToolCaching, get_exiftool_path
from .phototemplate import PhotoTemplate, RenderOptions
from .text_detection import detect_text


def frozen_photoinfo_factory(photo: "osxphotos.photoinfo.PhotoInfo") -> SimpleNamespace:
    """Return a frozen SimpleNamespace object for a PhotoInfo object"""
    photo_json = photo.json()

    def _object_hook(d: dict[Any, Any]):
        if not d:
            return d

        # if d key matches a ISO 8601 datetime ('2023-03-24T06:46:57.690786', '2019-07-04T16:24:01-07:00', '2019-07-04T16:24:01+07:00'), convert to datetime
        # fromisoformat will also handle dates with timezone offset in form +0700, etc.
        for k, v in d.items():
            if isinstance(v, str) and re.match(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[.]?\d*[+-]?\d{2}[:]?\d{2}?", v
            ):
                d[k] = datetime.datetime.fromisoformat(v)
        return SimpleNamespace(**d)

    frozen = json.loads(photo_json, object_hook=lambda d: _object_hook(d))

    # add on json() method to frozen object
    def _json(*args):
        return photo_json

    frozen.json = _json

    # add hexdigest property to frozen object
    frozen.hexdigest = photo.hexdigest

    # add on detected_text method to frozen object
    frozen = _add_detected_text(frozen)

    # add on exiftool property to frozen object
    frozen = _add_exiftool(frozen, photo)

    # add on render_template method to frozen object
    frozen = _add_render_template(frozen)

    # add on the _db property to frozen object
    # frozen objects don't really have a _db class but some things expect it (e.g. _db._beta)
    frozen._db = SimpleNamespace(_beta=photo._db._beta)

    return frozen


def _add_detected_text(frozen: SimpleNamespace) -> SimpleNamespace:
    """Add detected_text method to frozen PhotoInfo object"""

    def detected_text(confidence_threshold=TEXT_DETECTION_CONFIDENCE_THRESHOLD):
        """Detects text in photo and returns lists of results as (detected text, confidence)

        confidence_threshold: float between 0.0 and 1.0. If text detection confidence is below this threshold,
        text will not be returned. Default is TEXT_DETECTION_CONFIDENCE_THRESHOLD

        If photo is edited, uses the edited photo, otherwise the original; falls back to the preview image if neither edited or original is available

        Returns: list of (detected text, confidence) tuples
        """

        try:
            return frozen._detected_text_cache[confidence_threshold]
        except (AttributeError, KeyError) as e:
            if isinstance(e, AttributeError):
                frozen._detected_text_cache = {}

            try:
                detected_text = frozen._detected_text()
            except Exception as e:
                logging.warning(f"Error detecting text in photo {frozen.uuid}: {e}")
                detected_text = []

            frozen._detected_text_cache[confidence_threshold] = [
                (text, confidence)
                for text, confidence in detected_text
                if confidence >= confidence_threshold
            ]
            return frozen._detected_text_cache[confidence_threshold]

    def _detected_text():
        """detect text in photo, either from cached extended attribute or by attempting text detection"""
        path = (
            frozen.path_edited
            if frozen.hasadjustments and frozen.path_edited
            else frozen.path
        )
        path = path or frozen.path_derivatives[0] if frozen.path_derivatives else None
        if not path:
            return []

        md = OSXMetaData(path)
        try:

            def decoder(val):
                """Decode value from JSON"""
                return json.loads(val.decode("utf-8"))

            detected_text = md.get_xattr(
                "osxphotos.metadata:detected_text", decode=decoder
            )
        except KeyError:
            detected_text = None
        if detected_text is None:
            orientation = frozen.orientation or None
            detected_text = detect_text(path, orientation)

            def encoder(obj):
                """Encode value as JSON"""
                val = json.dumps(obj)
                return val.encode("utf-8")

            md.set_xattr(
                "osxphotos.metadata:detected_text", detected_text, encode=encoder
            )
        return detected_text

    frozen.detected_text = detected_text
    frozen._detected_text = _detected_text

    return frozen


def _add_exiftool(
    frozen: SimpleNamespace, photo: "osxphotos.photoinfo.PhotoInfo"
) -> SimpleNamespace:
    """Add exiftool property to frozen PhotoInfo object"""
    frozen._exiftool_path = photo._db._exiftool_path or None
    return frozen


def _add_render_template(frozen: SimpleNamespace) -> SimpleNamespace:
    """Add render_template method to frozen PhotoInfo object"""

    def render_template(template_str: str, options: RenderOptions | None = None):
        """Renders a template string for PhotoInfo instance using PhotoTemplate

        Args:
            template_str: a template string with fields to render
            options: a RenderOptions instance

        Returns:
            ([rendered_strings], [unmatched]): tuple of list of rendered strings and list of unmatched template values
        """
        options = options or RenderOptions()
        template = PhotoTemplate(frozen, exiftool_path=frozen._exiftool_path)
        return template.render(template_str, options)

    frozen.render_template = render_template
    return frozen
