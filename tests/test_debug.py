"""Test debug"""

import logging

import osxphotos
from osxphotos.debug import debug, is_debug, set_debug


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
    debug("test debug")
    assert "test debug" in caplog.text


def test_debug_print_false(caplog):
    set_debug(False)
    debug("test debug")
    assert caplog.text == ""
