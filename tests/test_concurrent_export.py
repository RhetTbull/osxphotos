""""Test that PhotoInfo.export can export concurrently"""

import concurrent.futures
import pathlib
import sqlite3
import tempfile

import pytest

import osxphotos

PHOTOS_DB = "tests/Test-10.15.7.photoslibrary"


@pytest.mark.skipif(sqlite3.threadsafety != 3, reason="sqlite3 not threadsafe")
@pytest.mark.parametrize(
    "count", range(10)
)  # repeat multiple times to try to catch any concurrency errors
def test_concurrent_export(count):
    """Test that PhotoInfo.export can export concurrently"""
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = [p for p in photosdb.photos() if not p.ismissing]

    with tempfile.TemporaryDirectory() as tmpdir:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(p.export, tmpdir, f"{p.uuid}_{p.original_filename}")
                for p in photos
            ]
            exported = []
            for future in concurrent.futures.as_completed(futures):
                exported.extend(future.result())
    assert len(exported) == len(photos)


@pytest.mark.skipif(sqlite3.threadsafety != 3, reason="sqlite3 not threadsafe")
@pytest.mark.parametrize(
    "count", range(10)
)  # repeat multiple times to try to catch any concurrency errors
def test_concurrent_export_with_exportdb(count):
    """Test that PhotoInfo.export can export concurrently"""
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = [p for p in photosdb.photos() if not p.ismissing]

    with tempfile.TemporaryDirectory() as tmpdir:
        exportdb = osxphotos.ExportDB(pathlib.Path(tmpdir) / "export.db", tmpdir)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for p in photos:
                options = osxphotos.ExportOptions()
                options.export_db = exportdb
                exporter = osxphotos.PhotoExporter(p)
                futures.append(
                    executor.submit(
                        exporter.export,
                        tmpdir,
                        f"{p.uuid}_{p.original_filename}",
                        options=options,
                    )
                )
            export_results = osxphotos.photoexporter.ExportResults()
            for future in concurrent.futures.as_completed(futures):
                export_results += future.result()

    assert len(export_results.exported) == len(photos)
    assert len(list(exportdb.get_exported_files())) == len(photos)
