"""Test PhotoInfoFromFile"""

from __future__ import annotations

import json
import pathlib
import shutil

import pytest

from osxphotos.photoinfo_file import (
    PhotoInfoFromFile,
    render_photo_template_from_filepath,
)

TEST_IMAGE = "tests/test-images/IMG_4179.jpeg"


@pytest.fixture
def image_with_unknown_sidecar(
    tmp_path: pathlib.Path,
) -> tuple[pathlib.Path, pathlib.Path]:
    """Copy test image to tmp_path with a JSON sidecar of unrecognized format"""
    image = tmp_path / pathlib.Path(TEST_IMAGE).name
    shutil.copy(TEST_IMAGE, image)
    sidecar = tmp_path / f"{image.name}.json"
    sidecar.write_text(json.dumps({"foo": "bar"}))
    return image, sidecar


def test_photoinfo_file_unknown_sidecar(image_with_unknown_sidecar, caplog):
    """Unrecognized sidecar should log a warning, not raise (#2228)"""
    image, sidecar = image_with_unknown_sidecar
    photo = PhotoInfoFromFile(image, sidecar=str(sidecar))
    assert photo.filename == image.name
    assert "Unknown sidecar type" in caplog.text


def test_render_template_unknown_sidecar(image_with_unknown_sidecar):
    """Rendering an import template with unrecognized sidecar should not raise (#2228)"""
    image, sidecar = image_with_unknown_sidecar
    rendered = render_photo_template_from_filepath(
        image, None, "{filepath.parent.name}", None, sidecar
    )
    assert rendered == [image.parent.name]
