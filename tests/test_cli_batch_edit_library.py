"""Tests for --library support in osxphotos batch-edit."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from osxphotos.platform import is_macos

if is_macos:
    import importlib

    batch_edit_module = importlib.import_module("osxphotos.cli.batch_edit")
    batch_edit = batch_edit_module.batch_edit
else:
    pytest.skip(allow_module_level=True)


def test_batch_edit_accepts_library_option_and_passes_it_to_processing(monkeypatch, tmp_path):
    """batch-edit should accept --library like query/export and pass it through."""

    library = tmp_path / "Photos Library.photoslibrary"
    library.mkdir()
    seen_kwargs = {}

    class FakePhoto:
        uuid = "FAKE-UUID"
        date = None
        original_filename = "fake.jpg"
        keywords = []

        def json(self):
            return "{}"

        def render_template(self, template, options=None):
            return [template], None

    def fake_get_photos_for_processing(**kwargs):
        seen_kwargs.update(kwargs)
        return [FakePhoto()]

    monkeypatch.setattr(batch_edit_module, "get_photos_for_processing", fake_get_photos_for_processing)
    monkeypatch.setattr(batch_edit_module, "save_photo_undo_info", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(batch_edit_module, "set_photo_keywords_from_template", lambda *_args, **_kwargs: None)

    result = CliRunner().invoke(
        batch_edit,
        [
            "--library",
            str(library),
            "--uuid",
            "FAKE-UUID",
            "--keyword",
            "Sailing",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert seen_kwargs["db"] == str(library)
