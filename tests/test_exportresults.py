""" test ExportResults class """

import pytest
from osxphotos.photoexporter import ExportResults

EXPORT_RESULT_ATTRIBUTES = [
    "exported",
    "new",
    "updated",
    "skipped",
    "exif_updated",
    "touched",
    "converted_to_jpeg",
    "sidecar_json_written",
    "sidecar_json_skipped",
    "sidecar_exiftool_written",
    "sidecar_exiftool_skipped",
    "sidecar_xmp_written",
    "sidecar_xmp_skipped",
    "missing",
    "error",
    "exiftool_warning",
    "exiftool_error",
    "deleted_files",
    "deleted_directories",
]


def test_exportresults_init():
    results = ExportResults()
    assert results.exported == []
    assert results.new == []
    assert results.updated == []
    assert results.skipped == []
    assert results.exif_updated == []
    assert results.touched == []
    assert results.converted_to_jpeg == []
    assert results.sidecar_json_written == []
    assert results.sidecar_json_skipped == []
    assert results.sidecar_exiftool_written == []
    assert results.sidecar_exiftool_skipped == []
    assert results.sidecar_xmp_written == []
    assert results.sidecar_xmp_skipped == []
    assert results.missing == []
    assert results.error == []
    assert results.exiftool_warning == []
    assert results.exiftool_error == []
    assert results.deleted_files == []
    assert results.deleted_directories == []
    assert results.exported_album == []
    assert results.skipped_album == []
    assert results.missing_album == []


def test_exportresults_iadd():
    results1 = ExportResults()
    results2 = ExportResults()
    for x in EXPORT_RESULT_ATTRIBUTES:
        setattr(results1, x, [f"{x}1"])
        setattr(results2, x, [f"{x}2"])

    results1 += results2
    for x in EXPORT_RESULT_ATTRIBUTES:
        assert getattr(results1, x) == [f"{x}1", f"{x}2"]

    # exiftool_warning and exiftool_error are lists of tuples
    results1 = ExportResults()
    results2 = ExportResults()
    results1.exiftool_warning = [("exiftool_warning1", "foo")]
    results2.exiftool_warning = [("exiftool_warning2", "bar")]
    results1.exiftool_error = [("exiftool_error1", "foo")]
    results2.exiftool_error = [("exiftool_error2", "bar")]

    results1.deleted_files = [("foo1")]
    results2.deleted_files = [("foo2")]

    results1.deleted_directories = [("bar1")]
    results2.deleted_directories = [("bar2")]

    results1 += results2

    assert results1.exiftool_warning == [
        ("exiftool_warning1", "foo"),
        ("exiftool_warning2", "bar"),
    ]
    assert results1.exiftool_error == [
        ("exiftool_error1", "foo"),
        ("exiftool_error2", "bar"),
    ]

    assert results1.deleted_files == ["foo1", "foo2"]
    assert results1.deleted_directories == ["bar1", "bar2"]


def test_all_files():
    """test ExportResults.all_files()"""
    results = ExportResults()
    for x in EXPORT_RESULT_ATTRIBUTES:
        setattr(results, x, [f"{x}1"])
    results.exiftool_warning = [("exiftool_warning1", "foo")]
    results.exiftool_error = [("exiftool_error1", "foo")]
    results.error = [("error1", "foo")]
    results.deleted_files = ["deleted_files1"]
    results.deleted_directories = ["deleted_directories1"]

    assert sorted(
        results.all_files() + results.deleted_files + results.deleted_directories
    ) == sorted([f"{x}1" for x in EXPORT_RESULT_ATTRIBUTES])
