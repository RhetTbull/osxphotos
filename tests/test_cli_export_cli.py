"""Test direct calling of export.py::export_cli"""

import os

import osxphotos
from osxphotos.cli.export import export_cli

TEST_LIBRARY = "tests/Test-15.4.1.photoslibrary"


def test_export_cli_basic(tmp_path):
    """test basic export_cli"""
    cwd = os.getcwd()
    export_dir = str(tmp_path)
    assert export_cli(dest=export_dir, db=TEST_LIBRARY) == 0
    files = os.listdir(export_dir)
    assert len(files) == 18 + 1  # 18 photos + export db


def test_export_cli_photosdb(tmp_path):
    """test export_cli with a pre-instantiated PhotosDB"""
    cwd = os.getcwd()
    export_dir = str(tmp_path)
    photosdb = osxphotos.PhotosDB(TEST_LIBRARY)
    assert export_cli(dest=export_dir, db=photosdb) == 0
    files = os.listdir(export_dir)
    assert len(files) == 18 + 1  # 18 photos + export db
