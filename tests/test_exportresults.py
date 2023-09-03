""" test ExportResults class """

import pytest

from osxphotos.exportoptions import ExportResults

EXPORT_RESULT_ATTRIBUTES = ExportResults().attributes


def test_exportresults_init():
    results = ExportResults()
    for x in EXPORT_RESULT_ATTRIBUTES:
        assert getattr(results, x) == []


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
    all_file_attributes = [
        "converted_to_jpeg",
        "exif_updated",
        "exported",
        "missing",
        "new",
        "sidecar_exiftool_skipped",
        "sidecar_exiftool_written",
        "sidecar_json_skipped",
        "sidecar_json_written",
        "sidecar_xmp_skipped",
        "sidecar_xmp_written",
        "skipped",
        "touched",
        "updated",
    ]
    for x in all_file_attributes:
        setattr(results, x, [f"{x}1"])
    results.exiftool_warning = [("exiftool_warning1", "foo")]
    results.exiftool_error = [("exiftool_error1", "foo")]
    results.error = [("error1", "foo")]

    assert sorted(results.all_files()) == sorted(
        [
            f"{x}1"
            for x in all_file_attributes
            + ["error", "exiftool_warning", "exiftool_error"]
        ]
    )
