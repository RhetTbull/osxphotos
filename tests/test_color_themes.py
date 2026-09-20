"""Test osxphotos.cli.color_themes"""

from __future__ import annotations

import pathlib
import threading

import pytest
from rich.style import Style
from rich_theme_manager import Theme

from osxphotos.cli.color_themes import COLOR_THEMES, get_theme_manager


@pytest.fixture
def theme_dir(tmp_path: pathlib.Path, monkeypatch) -> pathlib.Path:
    """Point the osxphotos config dir at a temporary directory"""
    monkeypatch.setattr(
        "osxphotos.cli.common.xdg_base_dirs.xdg_config_home", lambda: tmp_path
    )
    return tmp_path / "osxphotos" / "themes"


def test_sync_theme_files_creates_themes(theme_dir: pathlib.Path):
    get_theme_manager()
    for name in COLOR_THEMES:
        assert (theme_dir / f"{name}.theme").exists()


def test_sync_theme_files_is_idempotent(theme_dir: pathlib.Path):
    """Theme files must not be rewritten once they're up to date (#2201)"""
    get_theme_manager()
    mtimes = {p: p.stat().st_mtime_ns for p in theme_dir.glob("*.theme")}
    get_theme_manager()
    assert {p: p.stat().st_mtime_ns for p in theme_dir.glob("*.theme")} == mtimes


def test_sync_theme_files_repairs_truncated_theme(theme_dir: pathlib.Path):
    """A theme file truncated by an interrupted write is rewritten, not fatal"""
    get_theme_manager()
    truncated = theme_dir / "dark.theme"
    truncated.write_text("")
    assert get_theme_manager().get("dark").styles["error"]
    assert Theme.read(str(truncated)).name == "dark"


def test_sync_theme_files_adds_missing_styles(theme_dir: pathlib.Path):
    """Missing styles are added without clobbering user customizations"""
    get_theme_manager()
    path = theme_dir / "dark.theme"
    custom = Theme.read(str(path))
    custom.styles["error"] = Style(color="magenta")
    del custom.styles["warning"]
    custom._rtm_styles.remove("warning")
    path.write_text(custom.config)

    theme = get_theme_manager().get("dark")
    assert theme.styles["error"] == Style(color="magenta")
    assert theme.styles["warning"] == COLOR_THEMES["dark"].styles["warning"]


def test_get_theme_manager_concurrent(theme_dir: pathlib.Path):
    """Concurrent osxphotos runs must not crash reading theme files (#2201)"""
    errors = []

    def load_themes():
        try:
            for _ in range(25):
                get_theme_manager()
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")

    threads = [threading.Thread(target=load_themes) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
