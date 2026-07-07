"""Test crash_reporter decorator and one-shot crash callback behavior."""

from __future__ import annotations

import pytest

import osxphotos.crash_reporter as crash_reporter_module
from osxphotos.crash_reporter import (
    crash_reporter,
    register_crash_callback,
    unregister_crash_callback,
)


@pytest.fixture(autouse=True)
def clear_callbacks():
    """Ensure the global callback registry is clean around each test."""
    crash_reporter_module._global_callbacks.clear()
    yield
    crash_reporter_module._global_callbacks.clear()


def _wrapped_crasher(crash_log):
    """Return a crash_reporter-wrapped function that always raises."""

    @crash_reporter(str(crash_log), "crash message", "crash title", "postamble")
    def boom():
        raise RuntimeError("boom")

    return boom


def test_crash_reporter_writes_log(tmp_path):
    """crash_reporter writes a crash log and exits with code 1 on error."""
    crash_log = tmp_path / "crash.log"
    with pytest.raises(SystemExit) as exc_info:
        _wrapped_crasher(crash_log)()
    assert exc_info.value.code == 1
    assert "boom" in crash_log.read_text()


def test_crash_callback_runs_on_crash(tmp_path):
    """A registered crash callback runs when a crash is handled."""
    crash_log = tmp_path / "crash.log"
    ran = []
    register_crash_callback(lambda: ran.append(True), "running callback")

    with pytest.raises(SystemExit):
        _wrapped_crasher(crash_log)()

    assert ran == [True]


def test_crash_callback_is_one_shot(tmp_path):
    """A crash callback is unregistered after it runs so it does not leak.

    Regression test: an interrupted `export --ramdb` registered a crash
    callback that was only unregistered on the success path. A crashed export
    leaked it into the global registry, where it fired again (with stale state)
    on the next unrelated crash in the same process.
    """
    crash_log = tmp_path / "crash.log"
    calls = []
    register_crash_callback(lambda: calls.append(True))

    # first crash: callback runs and is then removed from the registry
    with pytest.raises(SystemExit):
        _wrapped_crasher(crash_log)()
    assert calls == [True]
    assert crash_reporter_module._global_callbacks == {}

    # second, unrelated crash: the callback must NOT run again
    with pytest.raises(SystemExit):
        _wrapped_crasher(crash_log)()
    assert calls == [True]


def test_failing_crash_callback_does_not_prevent_log(tmp_path):
    """A callback that raises must not prevent the crash log from being written."""
    crash_log = tmp_path / "crash.log"

    def bad_callback():
        raise ValueError("callback exploded")

    register_crash_callback(bad_callback)

    with pytest.raises(SystemExit):
        _wrapped_crasher(crash_log)()

    # crash log was still written despite the failing callback
    assert "boom" in crash_log.read_text()
    # and the failing callback was still removed from the registry
    assert crash_reporter_module._global_callbacks == {}


def test_unregister_crash_callback():
    """unregister_crash_callback removes a callback; invalid id raises ValueError."""
    callback_id = register_crash_callback(lambda: None)
    assert callback_id in crash_reporter_module._global_callbacks
    unregister_crash_callback(callback_id)
    assert callback_id not in crash_reporter_module._global_callbacks
    with pytest.raises(ValueError):
        unregister_crash_callback(callback_id)
