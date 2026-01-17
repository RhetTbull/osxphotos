"""Test debug"""

import importlib
import logging
import sys

import pytest

import osxphotos
from osxphotos.debug import is_debug, relocate_debug_options, set_debug


def test_debug_enable():
    """test set_debug()"""
    set_debug(True)
    assert osxphotos.logger.isEnabledFor(logging.DEBUG)
    assert is_debug()


def test_debug_disable():
    """test set_debug()"""
    set_debug(False)
    assert not osxphotos.logger.isEnabledFor(logging.DEBUG)
    assert not is_debug()


def test_debug_print_true(caplog):
    """test debug()"""
    set_debug(True)
    logger = osxphotos.logger
    logger.debug("test debug")
    assert "test debug" in caplog.text


def test_debug_print_false(caplog):
    set_debug(False)
    logger = osxphotos.logger
    logger.debug("test debug")
    assert caplog.text == ""


def test_import_does_not_affect_root_logger():
    """Test that importing osxphotos does not affect the root logger"""
    # Get root logger state before reimporting
    root_logger = logging.getLogger()
    initial_level = root_logger.level
    initial_handlers_count = len(root_logger.handlers)

    # Reimport osxphotos to simulate fresh import
    if "osxphotos" in sys.modules:
        # Store reference and reload
        importlib.reload(sys.modules["osxphotos"])

    # Check root logger wasn't modified
    assert root_logger.level == initial_level, "Root logger level should not change"
    assert (
        len(root_logger.handlers) == initial_handlers_count
    ), "Root logger handlers should not change"


def test_import_does_not_call_basicConfig():
    """Test that importing osxphotos doesn't call logging.basicConfig"""
    # Get root logger
    root_logger = logging.getLogger()
    initial_handlers = root_logger.handlers[:]

    # Reimport osxphotos
    if "osxphotos" in sys.modules:
        importlib.reload(sys.modules["osxphotos"])

    # If basicConfig was called, it would add a handler to root logger
    # (unless one already exists, but we're checking it didn't add new ones)
    new_handlers = [h for h in root_logger.handlers if h not in initial_handlers]
    assert len(new_handlers) == 0, "No handlers should be added to root logger"


def test_osxphotos_logger_exists():
    """Test that osxphotos logger is properly configured"""
    logger = logging.getLogger("osxphotos")
    assert logger is not None
    assert logger.name == "osxphotos"

    # Should have at least one handler (the one we configured)
    assert len(logger.handlers) > 0, "osxphotos logger should have handlers"


def test_osxphotos_logger_is_not_root():
    """Test that osxphotos.logger is not the root logger"""
    root_logger = logging.getLogger()
    osxphotos_logger = logging.getLogger("osxphotos")

    assert (
        osxphotos_logger is not root_logger
    ), "osxphotos logger should not be root logger"
    assert osxphotos_logger.name != "", "osxphotos logger should have a name"


def test_set_debug_does_not_affect_root_logger():
    """Test that set_debug only affects osxphotos logger, not root"""
    root_logger = logging.getLogger()
    initial_root_level = root_logger.level

    # Enable debug
    set_debug(True)
    assert (
        root_logger.level == initial_root_level
    ), "Root logger level unchanged after set_debug(True)"

    # Disable debug
    set_debug(False)
    assert (
        root_logger.level == initial_root_level
    ), "Root logger level unchanged after set_debug(False)"


def test_set_debug_true_enables_debug_level():
    """Test that set_debug(True) sets osxphotos logger to DEBUG"""
    set_debug(True)
    logger = logging.getLogger("osxphotos")

    assert logger.level == logging.DEBUG, "Logger level should be DEBUG"
    assert logger.isEnabledFor(logging.DEBUG), "Logger should be enabled for DEBUG"


def test_set_debug_false_sets_warning_level():
    """Test that set_debug(False) sets osxphotos logger to WARNING"""
    set_debug(False)
    logger = logging.getLogger("osxphotos")

    assert logger.level == logging.WARNING, "Logger level should be WARNING"
    assert not logger.isEnabledFor(
        logging.DEBUG
    ), "Logger should not be enabled for DEBUG"
    assert logger.isEnabledFor(logging.WARNING), "Logger should be enabled for WARNING"


def test_debug_messages_visible_when_enabled(caplog):
    """Test that debug messages are actually logged when debug is enabled"""
    set_debug(True)
    logger = logging.getLogger("osxphotos")

    with caplog.at_level(logging.DEBUG, logger="osxphotos"):
        logger.debug("test debug message")
        assert "test debug message" in caplog.text


def test_debug_messages_hidden_when_disabled(caplog):
    """Test that debug messages are not logged when debug is disabled"""
    set_debug(False)
    logger = logging.getLogger("osxphotos")

    # Don't use caplog.at_level() - let the logger's own level control what's captured
    logger.debug("test debug message")
    # Debug message should not appear because logger level is WARNING
    assert "test debug message" not in caplog.text


def test_warning_messages_always_visible(caplog):
    """Test that warning messages are logged regardless of debug state"""
    # Test with debug disabled
    set_debug(False)
    logger = logging.getLogger("osxphotos")

    with caplog.at_level(logging.WARNING, logger="osxphotos"):
        logger.warning("test warning message")
        assert "test warning message" in caplog.text

    caplog.clear()

    # Test with debug enabled
    set_debug(True)
    with caplog.at_level(logging.WARNING, logger="osxphotos"):
        logger.warning("test warning message 2")
        assert "test warning message 2" in caplog.text


# Tests for relocate_debug_options


def test_relocate_debug_options_flag_after_subcommand():
    """Test that flags after subcommand are moved to beginning"""
    argv = ["osxphotos", "export", "--profile", "/path"]
    result = relocate_debug_options(
        argv, flags=["--debug", "--profile"], options=["--watch", "--profile-sort"]
    )
    assert result == ["osxphotos", "--profile", "export", "/path"]


def test_relocate_debug_options_multiple_flags():
    """Test that multiple flags are relocated"""
    argv = ["osxphotos", "export", "--debug", "--profile", "/path"]
    result = relocate_debug_options(
        argv, flags=["--debug", "--profile"], options=["--watch", "--profile-sort"]
    )
    assert result == ["osxphotos", "--debug", "--profile", "export", "/path"]


def test_relocate_debug_options_option_with_value():
    """Test that options with values are relocated together"""
    argv = ["osxphotos", "export", "--watch", "module::func", "/path"]
    result = relocate_debug_options(
        argv, flags=["--debug", "--profile"], options=["--watch", "--profile-sort"]
    )
    assert result == ["osxphotos", "--watch", "module::func", "export", "/path"]


def test_relocate_debug_options_option_with_equals():
    """Test that --option=value format is relocated"""
    argv = ["osxphotos", "export", "--profile-sort=cumulative", "/path"]
    result = relocate_debug_options(
        argv, flags=["--debug", "--profile"], options=["--watch", "--profile-sort"]
    )
    assert result == ["osxphotos", "--profile-sort=cumulative", "export", "/path"]


def test_relocate_debug_options_already_at_beginning():
    """Test that options already at beginning stay in place"""
    argv = ["osxphotos", "--profile", "export", "/path"]
    result = relocate_debug_options(
        argv, flags=["--debug", "--profile"], options=["--watch", "--profile-sort"]
    )
    assert result == ["osxphotos", "--profile", "export", "/path"]


def test_relocate_debug_options_mixed_positions():
    """Test with options at beginning and end"""
    argv = ["osxphotos", "--debug", "export", "--profile", "/path"]
    result = relocate_debug_options(
        argv, flags=["--debug", "--profile"], options=["--watch", "--profile-sort"]
    )
    assert result == ["osxphotos", "--debug", "--profile", "export", "/path"]


def test_relocate_debug_options_no_debug_options():
    """Test that argv without debug options is unchanged"""
    argv = ["osxphotos", "export", "/path", "--verbose"]
    result = relocate_debug_options(
        argv, flags=["--debug", "--profile"], options=["--watch", "--profile-sort"]
    )
    assert result == ["osxphotos", "export", "/path", "--verbose"]


def test_relocate_debug_options_empty_argv():
    """Test with only program name"""
    argv = ["osxphotos"]
    result = relocate_debug_options(
        argv, flags=["--debug", "--profile"], options=["--watch", "--profile-sort"]
    )
    assert result == ["osxphotos"]


def test_relocate_debug_options_multiple_option_values():
    """Test with multiple occurrences of option with values"""
    argv = [
        "osxphotos",
        "export",
        "--watch",
        "module1::func1",
        "--watch",
        "module2::func2",
        "/path",
    ]
    result = relocate_debug_options(
        argv, flags=["--debug", "--profile"], options=["--watch", "--profile-sort"]
    )
    assert result == [
        "osxphotos",
        "--watch",
        "module1::func1",
        "--watch",
        "module2::func2",
        "export",
        "/path",
    ]


def test_relocate_debug_options_preserves_order_of_other_args():
    """Test that non-debug options maintain their relative order"""
    argv = [
        "osxphotos",
        "export",
        "--verbose",
        "--profile",
        "/path",
        "--library",
        "lib.photoslibrary",
    ]
    result = relocate_debug_options(
        argv, flags=["--debug", "--profile"], options=["--watch", "--profile-sort"]
    )
    assert result == [
        "osxphotos",
        "--profile",
        "export",
        "--verbose",
        "/path",
        "--library",
        "lib.photoslibrary",
    ]


def test_relocate_debug_options_does_not_modify_original():
    """Test that the original argv is not modified"""
    argv = ["osxphotos", "export", "--profile", "/path"]
    original = argv.copy()
    relocate_debug_options(
        argv, flags=["--debug", "--profile"], options=["--watch", "--profile-sort"]
    )
    assert argv == original
