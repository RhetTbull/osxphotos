"""Tests for PhotoAsset._request_resource_data error handling (#2253).

PhotoKit calls the completion handler of requestDataForAssetResource on its own dispatch
queue. An exception raised there becomes an uncaught NSException and aborts the process,
so the handler must only record the error and the calling thread must raise it. These
tests use a fake PHAssetResourceManager that calls back from a background thread and need
no Photos library or network.
"""

from __future__ import annotations

import threading
import time

import pytest

from osxphotos.platform import is_macos

if is_macos:
    import Foundation

    from osxphotos import photokit
    from osxphotos.photokit import PhotoAsset, PhotoKitExportError
else:
    pytest.skip(allow_module_level=True, reason="Tests only run on macOS")


class FakePHAsset:
    """Stand-in for PHAsset; _request_resource_data only needs localIdentifier()"""

    def localIdentifier(self) -> str:
        return "TEST-ASSET-ID/L0/001"


class FakeResourceManager:
    """Stand-in for PHAssetResourceManager that calls back from a background thread,
    as PhotoKit does from its com.apple.photos.assetResources.fileIO queue"""

    def __init__(self, chunks: list[bytes], error: Foundation.NSError | None):
        self.chunks = chunks
        self.error = error
        self.thread: threading.Thread | None = None
        self.callback_exception: BaseException | None = None

    def requestDataForAssetResource_options_dataReceivedHandler_completionHandler_(
        self, resource, options, data_handler, completion_handler
    ):
        def run():
            try:
                for chunk in self.chunks:
                    data_handler(chunk)
                completion_handler(self.error)
            except BaseException as e:  # in PhotoKit this would abort the process
                self.callback_exception = e

        self.thread = threading.Thread(target=run)
        self.thread.start()
        return 1


def _request_with_fake_manager(
    monkeypatch, chunks: list[bytes], error: Foundation.NSError | None
) -> tuple[FakeResourceManager, bytes | None, BaseException | None]:
    """Run _request_resource_data against a FakeResourceManager and return the manager,
    the returned data (if any), and the exception raised on the calling thread (if any)"""
    manager = FakeResourceManager(chunks, error)
    monkeypatch.setattr(
        photokit.Photos,
        "PHAssetResourceManager",
        type("PHAssetResourceManager", (), {"defaultManager": lambda: manager}),
    )
    monkeypatch.setattr(photokit, "PHOTOKIT_REQUEST_TIMEOUT", 5.0)
    asset = PhotoAsset(None, FakePHAsset())
    data = raised = None
    try:
        data = asset._request_resource_data(resource=None)
    except Exception as e:
        raised = e
    manager.thread.join()
    return manager, data, raised


def test_request_resource_data_returns_data(monkeypatch):
    """Successful request -> concatenated data chunks are returned"""
    manager, data, raised = _request_with_fake_manager(
        monkeypatch, [b"abc", b"def"], None
    )
    assert raised is None
    assert manager.callback_exception is None
    assert data == b"abcdef"


def test_request_resource_data_error_raises_on_calling_thread(monkeypatch):
    """Failed request -> PhotoKitExportError raised on the calling thread, promptly and
    with PhotoKit's error message, not from inside the completion handler"""
    error = Foundation.NSError.errorWithDomain_code_userInfo_(
        "PHPhotosErrorDomain",
        3164,
        {Foundation.NSLocalizedDescriptionKey: "Network access is required"},
    )
    start = time.monotonic()
    manager, data, raised = _request_with_fake_manager(monkeypatch, [], error)
    elapsed = time.monotonic() - start

    # nothing escaped the completion handler (in PhotoKit that is a SIGABRT)
    assert manager.callback_exception is None
    assert isinstance(raised, PhotoKitExportError)
    assert "Network access is required" in str(raised)
    assert "TEST-ASSET-ID" in str(raised)
    assert data is None
    # the handler still signalled completion, so there was no wait for the timeout
    assert elapsed < 2.0
