"""Test PhotoExporter._kill_photos_process functionality"""

import getpass
import os
import shutil
import subprocess
import time

import pytest

import osxphotos.cli.kill_photos as kill_photos_module
import osxphotos.photoexporter as photoexporter_module
from osxphotos.photoexporter import PhotoExporter
from osxphotos.platform import is_macos


def is_photos_running():
    """Check if Photos.app is running for the current user.

    Matches only the main Photos executable owned by the current user. A plain
    `pgrep -f Photos.app` is too broad in two ways that make these tests fail on
    a machine where the current user is not the only one using Photos:

    - it matches every user's processes, so another logged-in user running
      Photos looks like "Photos is still running" even though
      `_kill_photos_process` quit the current user's copy (pkill cannot signal
      another user's processes without root);
    - it matches any path containing "Photos.app", including helper processes
      such as Contents/PlugIns/PhotosReliveWidget.appex.

    `pgrep -u <uid> -x Photos` matches the process name exactly and only for
    this user, so helpers and other users' processes are ignored.
    """
    try:
        result = subprocess.run(
            ["pgrep", "-u", str(os.getuid()), "-x", "Photos"],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except OSError:
        # pgrep missing or not executable; treat as "not running"
        return False


def start_photos():
    """Start Photos.app and wait for it to launch"""
    try:
        subprocess.run(["open", "-a", "Photos"], check=True)
        # Wait a moment for Photos to start
        for _ in range(10):  # Wait up to 10 seconds
            time.sleep(1)
            if is_photos_running():
                return True
        return False
    except (OSError, subprocess.CalledProcessError):
        # `open` missing, or it failed to launch Photos
        return False


@pytest.mark.skipif(not is_macos, reason="Only runs on macOS")
@pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") == "true", reason="Skip on GitHub Actions"
)
def test_kill_photos_process():
    """Test that _kill_photos_process successfully kills Photos.app"""

    # Record initial state
    initial_running = is_photos_running()

    # If Photos is not running, start it
    if not initial_running:
        success = start_photos()
        assert success, "Failed to start Photos.app"

    # Verify Photos is running
    assert is_photos_running(), "Photos.app should be running"

    # Kill Photos using the method we're testing
    PhotoExporter._kill_photos_process()

    # Wait a moment for the process to be killed
    time.sleep(2)

    # Verify Photos is no longer running
    assert not is_photos_running(), "Photos.app should have been killed"

    # Clean up: if Photos was originally running, start it again
    if initial_running:
        start_photos()


@pytest.mark.skipif(not is_macos, reason="Only runs on macOS")
@pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") == "true", reason="Skip on GitHub Actions"
)
def test_kill_photos_process_when_not_running():
    """Test that _kill_photos_process handles case where Photos is not running"""

    # Make sure Photos is not running first
    if is_photos_running():
        PhotoExporter._kill_photos_process()
        time.sleep(2)

    # Verify Photos is not running
    assert not is_photos_running(), "Photos.app should not be running"

    # This should not raise an exception even if Photos is not running
    PhotoExporter._kill_photos_process()

    # Photos should still not be running
    assert not is_photos_running(), "Photos.app should still not be running"


class _RunRecorder:
    """Stand-in for subprocess.run that records the command it was given"""

    def __init__(self, returncode=0, stderr=""):
        self.calls = []
        self.returncode = returncode
        self.stderr = stderr

    def __call__(self, args, **kwargs):
        self.calls.append(list(args))
        return subprocess.CompletedProcess(args, self.returncode, "", self.stderr)


def test_kill_photos_process_matches_only_this_users_photos(monkeypatch):
    """_kill_photos_process signals only the current user's main Photos process"""
    recorder = _RunRecorder()
    monkeypatch.setattr(photoexporter_module.subprocess, "run", recorder)

    PhotoExporter._kill_photos_process()

    assert recorder.calls == [["pkill", "-u", str(os.getuid()), "-x", "Photos"]]


def test_kill_photos_matches_only_this_users_photos(monkeypatch):
    """kill_photos signals only the current user's Photos"""
    recorder = _RunRecorder()
    monkeypatch.setattr(kill_photos_module.subprocess, "run", recorder)
    monkeypatch.setattr(kill_photos_module, "echo_error", lambda *args: None)

    assert kill_photos_module.kill_photos()

    assert recorder.calls == [["killall", "-u", getpass.getuser(), "Photos"]]


@pytest.mark.skipif(shutil.which("pkill") is None, reason="needs pkill")
@pytest.mark.skipif(is_photos_running(), reason="Photos is running and would be killed")
def test_kill_photos_process_spares_other_apps(tmp_path):
    """A process with "Photos.app" in its path but another name survives"""
    sleep = shutil.which("sleep")
    macos_dir = tmp_path / "Zouti Photos.app" / "Contents" / "MacOS"
    macos_dir.mkdir(parents=True)
    decoy_path = macos_dir / "Zouti Photos"
    decoy_path.symlink_to(sleep)

    decoy = subprocess.Popen([str(decoy_path), "30"])
    try:
        # wait for the decoy to exec so pkill sees its final command line
        for _ in range(50):
            result = subprocess.run(
                ["pgrep", "-f", "Zouti Photos.app"], capture_output=True, check=False
            )
            if str(decoy.pid) in result.stdout.decode().split():
                break
            time.sleep(0.1)

        PhotoExporter._kill_photos_process()
        time.sleep(0.5)

        assert decoy.poll() is None, "_kill_photos_process killed an unrelated app"
    finally:
        decoy.kill()
        decoy.wait()
