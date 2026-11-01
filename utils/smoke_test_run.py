"""Smoke test for the "osxphotos run" command in the PyInstaller executable.

make_cli_exe.sh runs this with the built executable:

    dist/osxphotos run utils/smoke_test_run.py --package-dir osxphotos

Scripts run with "osxphotos run" can import any osxphotos module or bundled
dependency, but only the modules imported at startup are exercised by
"osxphotos --version". A module PyInstaller failed to bundle (for example, one
loaded with importlib, see #2283) would only fail when a script imports it.
This script imports every osxphotos submodule plus the third-party packages that
run scripts commonly use, and exits with an error listing any that fail.

The list of osxphotos submodules is read from the source tree (--package-dir),
not from the executable, so modules missing from the bundle are still checked.
"""

from __future__ import annotations

import argparse
import importlib
import pathlib
import sys
import traceback

__all__ = ["main"]

# Modules that are not expected to be importable in the executable
SKIP_MODULES = {
    # entry point for "python -m osxphotos"; the executable uses cli.py instead
    "osxphotos.__main__",
    # not imported anywhere in osxphotos, so PyInstaller does not bundle it
    "osxphotos.frozen_photoinfo",
}

# Third-party packages that osxphotos run scripts commonly import directly
THIRD_PARTY_MODULES = [
    "click",
    "Foundation",
    "objc",
    "osxmetadata",
    "pathvalidate",
    "Photos",
    "photoscript",
    "Quartz",
    "rich",
    "rich.console",
    "rich.progress",
    "sqlite3",
    "strpdatetime",
    "utitools",
    "xattr",
    "yaml",
]


def osxphotos_submodules(package_dir: str) -> list[str]:
    """Return the names of all osxphotos submodules found in package_dir.

    This walks the files rather than using pkgutil.walk_packages, which imports
    each subpackage and would then list that subpackage's modules from the
    executable instead of from the source tree.
    """
    root = pathlib.Path(package_dir)
    modules = set()
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        # only include files in packages, i.e. every directory has an __init__.py
        if not all(
            (root / parent / "__init__.py").exists() for parent in relative.parents
        ):
            continue
        parts = relative.with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            modules.add(".".join(("osxphotos", *parts)))
    return sorted(modules - SKIP_MODULES)


def main() -> int:
    """Import the modules and report any that fail; returns the exit code"""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--package-dir",
        required=True,
        help="path to the osxphotos package in the source tree",
    )
    args = parser.parse_args()

    modules = osxphotos_submodules(args.package_dir)
    if not modules:
        print(f"No osxphotos modules found in {args.package_dir}", file=sys.stderr)
        return 1
    modules = ["osxphotos", *modules, *THIRD_PARTY_MODULES]

    failed: list[str] = []
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception:
            failed.append(name)
            print(f"Failed to import {name}:", file=sys.stderr)
            traceback.print_exc()

    if failed:
        print(
            f"{len(failed)} of {len(modules)} modules failed to import: "
            + ", ".join(failed),
            file=sys.stderr,
        )
        return 1
    print(f"Imported {len(modules)} modules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
