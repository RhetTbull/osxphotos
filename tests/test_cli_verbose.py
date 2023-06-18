"""Test verbose functions"""

import re
from io import StringIO

from osxphotos.cli.verbose import (
    _reset_verbose_globals,
    get_verbose_level,
    set_verbose_level,
    verbose,
    verbose_print,
)


def test_set_get_verbose_level(capsys):
    """Test verbose_print"""
    set_verbose_level(2)
    assert get_verbose_level() == 2


def test_verbose_print_no_rich(capsys):
    """Test verbose_print"""
    set_verbose_level(1)
    verbose = verbose_print(1, False, False)
    verbose("test")
    captured = capsys.readouterr()
    assert captured.out.strip() == "test"

    verbose("test2", level=1)
    captured = capsys.readouterr()
    assert captured.out.strip() == "test2"

    verbose("test3", level=2)
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_verbose_print_rich(capsys):
    """Test verbose with rich"""
    set_verbose_level(1)
    verbose = verbose_print(1, False, True)
    verbose("test")
    captured = capsys.readouterr()
    assert captured.out.strip() == "test"

    verbose("test2", level=1)
    captured = capsys.readouterr()
    assert captured.out.strip() == "test2"

    verbose("test3", level=2)
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_verbose_print_timestamp(capsys):
    """Test verbose with timestamp"""
    set_verbose_level(1)
    verbose = verbose_print(1, True, False)
    verbose("test")
    captured = capsys.readouterr()

    # regex to match timestamp in this format: 2023-01-25 06:40:18.216297
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}", captured.out.strip())
    assert captured.out.strip().endswith("test")

    verbose("test2", level=1)
    captured = capsys.readouterr()
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}", captured.out.strip())
    assert captured.out.strip().endswith("test2")

    verbose("test3", level=2)
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_verbose_print_file():
    """Test verbose with file"""
    set_verbose_level(1)
    stream = StringIO()
    verbose = verbose_print(1, False, False, file=stream)
    verbose("test")
    assert stream.getvalue().strip() == "test"


def test_verbose_print_noop(capsys):
    """Test verbose with noop"""
    set_verbose_level(1)
    verbose = verbose_print(0, False, False)
    verbose("test")
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_verbose(capsys):
    """ "Test verbose()"""
    # reset verbose module globals for testing
    _reset_verbose_globals()
    set_verbose_level(0)
    verbose("test")
    captured = capsys.readouterr()
    assert captured.out.strip() == ""

    set_verbose_level(1)
    verbose("test")
    captured = capsys.readouterr()
    assert captured.out.strip() == "test"

    verbose("test2", level=2)
    captured = capsys.readouterr()
    assert captured.out.strip() == ""

    set_verbose_level(2)
    verbose("test2", level=2)
    captured = capsys.readouterr()
    assert captured.out.strip() == "test2"
