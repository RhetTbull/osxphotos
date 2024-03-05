"""Test compare command."""

import json

import pytest
from click.testing import CliRunner

from osxphotos.cli.compare import compare

from .test_compare import LIBRARY_A, LIBRARY_B


def test_compare_a_b():
    """Basic test of osxphotos compare"""

    runner = CliRunner()
    result = runner.invoke(compare, [LIBRARY_A, LIBRARY_B])
    assert result.exit_code == 0
    assert "in_a_and_b_different = 1 asset" in result.output


def test_compare_a_b_json():
    """Test osxphotos compare --json"""

    runner = CliRunner()
    result = runner.invoke(compare, [LIBRARY_A, LIBRARY_B, "--json"])
    assert result.exit_code == 0
    got = json.loads(result.output)
    assert len(got["in_a_and_b_different"]) == 1
    assert len(got["in_a_and_b_same"]) == 2
    assert len(got["in_a_not_b"]) == 1
    assert len(got["in_b_not_a"]) == 2


def test_compare_check():
    """Test osxphotos compare --check"""

    runner = CliRunner()
    result = runner.invoke(compare, [LIBRARY_A, LIBRARY_B, "--check"])
    assert result.exit_code == 1
    assert result.output.strip() == "4"


def test_compare_check_same():
    """Test osxphotos compare --check with same library"""

    runner = CliRunner()
    result = runner.invoke(compare, [LIBRARY_A, LIBRARY_A, "--check"])
    assert result.exit_code == 0
    assert result.output.strip() == "0"
