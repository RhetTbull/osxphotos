"""Test osxphotos export with cloud filters #800"""

import os

import pytest
from click.testing import CliRunner

UUID_INCLOUD = "F73D96B2-24A6-40B2-B37C-5F82CF3F79E1"  # IMG_0008.MOV
UUID_NOT_INCLOUD = "C64A019E-7BB6-4A20-8540-686B5DF7BC1A"  # 6E81F4CA-B7D9-4121-96E3-7667EFB7B310.JPG  # shared images show as not in cloud
UUID_CLOUDASSET = (
    "E214E862-9289-4769-B12B-BB5CC97929B3"  # 7885e3f8-392e-44ea-b3b6-07ee97f0fea2.jpg
)
UUID_NOT_CLOUDASSET = "DC99FBDD-7A52-4100-A5BB-344131646C30"  # St James Park.jpg

PHOTOS_DB_CLOUD = "tests/Test-Cloud-13.1.photoslibrary"
PHOTOS_DB_NOT_CLOUD = "tests/Test-13.0.0.photoslibrary"

from osxphotos.cli import export


def test_export_cloud_asset():
    """test basic export with --cloudasset"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_CLOUD), ".", "-V", "--cloudasset"]
        )
        assert result.exit_code == 0
        assert UUID_CLOUDASSET in result.output


def test_export_not_cloud_asset():
    """test basic export with --not-cloudasset"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_CLOUD), ".", "-V", "--not-cloudasset"]
        )
        assert result.exit_code == 0
        assert "Did not find any photos to export" in result.output


def test_export_not_cloud_asset_2():
    """test basic export with --not-cloudasset"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_NOT_CLOUD), ".", "-V", "--not-cloudasset"],
        )
        assert result.exit_code == 0
        assert UUID_NOT_CLOUDASSET in result.output


def test_export_in_cloud():
    """test basic export with --incloud"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_CLOUD), ".", "-V", "--incloud"]
        )
        assert result.exit_code == 0
        assert UUID_INCLOUD in result.output
        assert UUID_NOT_INCLOUD not in result.output


def test_export_not_in_cloud():
    """test basic export with --not-incloud"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_CLOUD), ".", "-V", "--not-incloud"]
        )
        assert result.exit_code == 0
        assert UUID_INCLOUD not in result.output
        assert UUID_NOT_INCLOUD in result.output
