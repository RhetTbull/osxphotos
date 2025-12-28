"""test ConfigOptions class"""

import datetime
import pathlib
from io import StringIO

import pytest
import toml

from osxphotos.configoptions import (
    ConfigOptions,
    ConfigOptionsInvalidError,
    ConfigOptionsLoadError,
)

VARS = {"foo": "bar", "bar": False, "test1": (), "test2": None, "test2_setting": False}


def test_init():
    cfg = ConfigOptions("test", VARS)
    assert isinstance(cfg, ConfigOptions)
    assert cfg.foo == "bar"
    assert not cfg.bar
    assert type(cfg.test1) == tuple


def test_init_with_ignore():
    cfg = ConfigOptions("test", VARS, ignore=["test2"])
    assert isinstance(cfg, ConfigOptions)
    assert hasattr(cfg, "test1")
    assert not hasattr(cfg, "test2")


def test_write_to_file_load_from_file(tmpdir):
    cfg = ConfigOptions("test", VARS)
    cfg.bar = True
    cfg_file = pathlib.Path(str(tmpdir)) / "test.toml"
    cfg.write_to_file(str(cfg_file))
    assert cfg_file.is_file()

    cfg_dict = toml.load(str(cfg_file))
    assert cfg_dict["test"]["foo"] == "bar"

    cfg2 = ConfigOptions("test", VARS).load_from_file(str(cfg_file))
    assert cfg2.foo == "bar"
    assert cfg2.bar


def test_load_from_str(tmpdir):
    cfg = ConfigOptions("test", VARS)
    cfg.bar = True
    cfg_str = cfg.write_to_str()
    cfg2 = ConfigOptions("test", VARS).load_from_str(cfg_str)
    assert cfg2.foo == "bar"
    assert cfg2.bar


def test_load_from_file_error(tmpdir):
    cfg_file = pathlib.Path(str(tmpdir)) / "test.toml"
    cfg = ConfigOptions("test", VARS)
    cfg.write_to_file(str(cfg_file))
    # try to load with a section that doesn't exist in the TOML file
    with pytest.raises(ConfigOptionsLoadError):
        cfg2 = ConfigOptions("FOO", VARS).load_from_file(str(cfg_file))


def test_asdict():
    cfg = ConfigOptions("test", VARS)
    cfg_dict = cfg.asdict()
    assert cfg_dict["foo"] == "bar"
    assert not cfg_dict["bar"]
    assert cfg_dict["test1"] == ()


def test_validate():
    cfg = ConfigOptions("test", VARS)

    # test exclusive
    assert cfg.validate(exclusive=[("foo", "bar")])
    cfg.bar = True
    with pytest.raises(ConfigOptionsInvalidError):
        assert cfg.validate(exclusive=[("foo", "bar")])

    # test dependent
    cfg.test2 = True
    cfg.test2_setting = 1.0
    assert cfg.validate(dependent=[("test2_setting", ("test2"))])
    cfg.test2 = False
    with pytest.raises(ConfigOptionsInvalidError):
        assert cfg.validate(dependent=[("test2_setting", ("test2"))])

    # test inclusive
    cfg.foo = "foo"
    cfg.bar = True
    assert cfg.validate(inclusive=[("foo", "bar")])
    cfg.foo = None
    with pytest.raises(ConfigOptionsInvalidError):
        assert cfg.validate(inclusive=[("foo", "bar")])


def test_load_datetime_from_toml(tmpdir):
    """Test that datetime.date objects from TOML are converted to datetime.datetime, #1925"""
    # Create a TOML file with date values (TOML parser converts these to datetime.date)
    cfg_file = pathlib.Path(str(tmpdir)) / "test_date.toml"
    toml_content = """
[test]
added_after = 2025-01-01
added_before = 2025-12-31
"""
    cfg_file.write_text(toml_content)

    # Load the TOML file
    vars_with_dates = {"added_after": None, "added_before": None}
    cfg = ConfigOptions("test", vars_with_dates).load_from_file(str(cfg_file))

    # Verify that the date values are converted to datetime.datetime objects
    assert isinstance(cfg.added_after, datetime.datetime)
    assert isinstance(cfg.added_before, datetime.datetime)
    assert cfg.added_after == datetime.datetime(2025, 1, 1, 0, 0, 0)
    assert cfg.added_before == datetime.datetime(2025, 12, 31, 0, 0, 0)
