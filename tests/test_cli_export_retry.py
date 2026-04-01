"""Tests for export retry handling."""

from __future__ import annotations

from osxphotos.cli.export import _is_retryable_export_exception


def test_is_retryable_export_exception_false_for_existing_destination():
    """File-exists export failures should not be retried."""
    exception = Exception(
        'Error Domain=NSCocoaErrorDomain Code=516 "file couldn’t be copied" '
        'because an item with the same name already exists. '
        "NSUnderlyingError=Error Domain=NSPOSIXErrorDomain Code=17 \"File exists\""
    )

    assert not _is_retryable_export_exception(exception)


def test_is_retryable_export_exception_true_for_transient_failure():
    """Transient failures should still be retried."""
    exception = Exception("timed out waiting for Photos export")

    assert _is_retryable_export_exception(exception)
