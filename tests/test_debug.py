"""Test debug"""

import logging

import osxphotos
from osxphotos.debug import is_debug, set_debug


def test_debug_enable():
    set_debug(True)
    logger = osxphotos._get_logger()
    assert logger.isEnabledFor(logging.DEBUG)
    assert is_debug()


def test_debug_disable():
    set_debug(False)
    logger = osxphotos._get_logger()
    assert not logger.isEnabledFor(logging.DEBUG)
    assert not is_debug()
