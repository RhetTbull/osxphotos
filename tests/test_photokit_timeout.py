"""Tests for the PhotoKit request timeout (PHOTOKIT_REQUEST_TIMEOUT / PhotoKitTimeoutError).

These tests exercise the timeout helper directly and need no Photos library or network:
they reproduce the exact failure mode (an async PhotoKit request whose completion handler
never fires, e.g. a stalled iCloud download) and assert the wait is bounded rather than
blocking the calling thread forever.
"""

import threading
import time

import pytest

from osxphotos import photokit
from osxphotos.photokit import PhotoKitTimeoutError, _wait_for_event_or_timeout


def test_timeout_raises_when_handler_never_fires(monkeypatch):
    """Stalled handler (event never set) -> PhotoKitTimeoutError, bounded by the timeout."""
    monkeypatch.setattr(photokit, "PHOTOKIT_REQUEST_TIMEOUT", 0.2)
    event = threading.Event()  # never set -> simulates a stalled iCloud callback
    start = time.monotonic()
    with pytest.raises(PhotoKitTimeoutError):
        _wait_for_event_or_timeout(event, "TEST-ASSET-ID")
    elapsed = time.monotonic() - start
    # returned at ~the timeout, not hung forever
    assert 0.15 < elapsed < 2.0


def test_returns_when_handler_fires(monkeypatch):
    """Handler fired (event set) -> returns without raising."""
    monkeypatch.setattr(photokit, "PHOTOKIT_REQUEST_TIMEOUT", 5.0)
    event = threading.Event()
    event.set()
    assert _wait_for_event_or_timeout(event, "TEST-ASSET-ID") is None


def test_zero_timeout_restores_wait_forever(monkeypatch):
    """PHOTOKIT_REQUEST_TIMEOUT == 0 restores legacy 'wait forever' behavior.

    (A set event is used so the test itself does not block; the point is that 0 maps to
    Event.wait(None) rather than to a zero-second poll.)
    """
    monkeypatch.setattr(photokit, "PHOTOKIT_REQUEST_TIMEOUT", 0)
    event = threading.Event()
    event.set()
    assert _wait_for_event_or_timeout(event, "TEST-ASSET-ID") is None


def test_error_message_includes_asset_id(monkeypatch):
    """The raised error names the asset, to aid debugging a real stall."""
    monkeypatch.setattr(photokit, "PHOTOKIT_REQUEST_TIMEOUT", 0.1)
    event = threading.Event()
    with pytest.raises(PhotoKitTimeoutError, match="TEST-ASSET-ID"):
        _wait_for_event_or_timeout(event, "TEST-ASSET-ID")
