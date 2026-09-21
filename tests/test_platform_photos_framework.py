"""Test that osxphotos.platform claims the com.apple.Photos bundle identifier for
Photos.framework before photoscript registers Photos.app under it; see #2212."""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from osxphotos.platform import is_macos

if not is_macos:
    pytest.skip("skipping Photos framework tests, macOS only", allow_module_level=True)


def _bundle_path_for_photos_identifier(*modules: str) -> str:
    """Import modules in a fresh interpreter, return path of the bundle registered
    for com.apple.Photos; the CFBundle registry is per-process so this must not
    run in the pytest interpreter."""
    imports = "\n".join(f"import {module}" for module in modules)
    script = imports + textwrap.dedent("""
        from Foundation import NSBundle

        bundle = NSBundle.bundleWithIdentifier_("com.apple.Photos")
        print(bundle.bundlePath() if bundle else "")
        """)
    proc = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def test_photoscript_registers_photos_app():
    """photoscript compiles a `tell application "Photos"` script on import which
    registers Photos.app under com.apple.Photos; this is what osxphotos.platform
    must pre-empt."""
    assert _bundle_path_for_photos_identifier("photoscript").endswith("Photos.app")


def test_platform_claims_photos_framework():
    """Importing osxphotos.platform before photoscript leaves the identifier
    pointing at Photos.framework so pyobjc does not try to load Photos.app."""
    assert _bundle_path_for_photos_identifier(
        "osxphotos.platform", "photoscript"
    ).endswith("Photos.framework")


@pytest.mark.parametrize(
    "module",
    [
        "osxphotos",
        "osxphotos.cli",
        "osxphotos.photoexporter",
        "osxphotos.photoquery",
        "osxphotos.photosalbum",
    ],
)
def test_photos_identifier_resolves_to_framework(module: str):
    """Every entry point that pulls in photoscript must still resolve
    com.apple.Photos to Photos.framework."""
    assert _bundle_path_for_photos_identifier(module).endswith("Photos.framework")
