"""Support for colorized output for photos_time_warp"""

from typing import Optional

from rich.style import Style
from rich.themes import Theme

from .common import noop
from .darkmode import is_dark_mode

__all__ = ["get_theme"]


COLOR_THEMES = {
    "dark": Theme(
        {
            # color pallette from https://github.com/dracula/dracula-theme
            "color": Style(color="rgb(248,248,242)"),
            "count": Style(color="rgb(139,233,253)"),
            "error": Style(color="rgb(255,85,85)", bold=True),
            "filename": Style(color="rgb(189,147,249)", bold=True),
            "filepath": Style(color="rgb(80,250,123)", bold=True),
            "highlight": Style(color="#000000", bgcolor="#d73a49", bold=True),
            "num": Style(color="rgb(139,233,253)", bold=True),
            "time": Style(color="rgb(139,233,253)", bold=True),
            "uuid": Style(color="rgb(255,184,108)"),
            "warning": Style(color="rgb(241,250,140)", bold=True),
            "bar.back": Style(color="rgb(68,71,90)"),
            "bar.complete": Style(color="rgb(249,38,114)"),
            "bar.finished": Style(color="rgb(80,250,123)"),
            "bar.pulse": Style(color="rgb(98,114,164)"),
            "progress.elapsed": Style(color="rgb(139,233,253)"),
            "progress.percentage": Style(color="rgb(255,121,198)"),
            "progress.remaining": Style(color="rgb(139,233,253)"),
        }
    ),
    "light": Theme(
        {
            "color": Style(color="#000000"),
            "count": Style(color="#005cc5", bold=True),
            "error": Style(color="#b31d28", bold=True, underline=True, italic=True),
            "filename": Style(color="#6f42c1", bold=True),
            "filepath": Style(color="#22863a", bold=True),
            "highlight": Style(color="#ffffff", bgcolor="#d73a49", bold=True),
            "num": Style(color="#005cc5", bold=True),
            "time": Style(color="#032f62", bold=True),
            "uuid": Style(color="#d73a49", bold=True),
            "warning": Style(color="#e36209", bold=True, underline=True, italic=True),
            "bar.back": Style(color="grey23"),
            "bar.complete": Style(color="rgb(249,38,114)"),
            "bar.finished": Style(color="rgb(114,156,31)"),
            "bar.pulse": Style(color="rgb(249,38,114)"),
            "progress.elapsed": Style(color="#032f62", bold=True),
            "progress.percentage": Style(color="#6f42c1", bold=True),
            "progress.remaining": Style(color="#032f62", bold=True),
        }
    ),
    "mono": Theme(
        {
            "count": "bold",
            "error": "reverse italic",
            "filename": "bold",
            "filepath": "bold underline",
            "highlight": "reverse italic",
            "num": "bold",
            "time": "bold",
            "uuid": "bold",
            "warning": "bold italic",
            "bar.back": "",
            "bar.complete": "reverse",
            "bar.finished": "bold",
            "bar.pulse": "bold",
            "progress.elapsed": "",
            "progress.percentage": "bold",
            "progress.remaining": "bold",
        }
    ),
    "plain": Theme(
        {
            "color": "",
            "count": "",
            "error": "",
            "filename": "",
            "filepath": "",
            "highlight": "",
            "num": "",
            "time": "",
            "uuid": "",
            "warning": "",
            "bar.back": "",
            "bar.complete": "",
            "bar.finished": "",
            "bar.pulse": "",
            "progress.elapsed": "",
            "progress.percentage": "",
            "progress.remaining": "",
        }
    ),
}


def get_theme(
    theme_name: Optional[str] = None,
    theme_file: Optional[str] = None,
    verbose=None,
):
    """Get the color theme based on the color flags or load from config file"""
    if not verbose:
        verbose = noop
    # figure out which color theme to use
    theme_name = theme_name or "default"
    if theme_name == "default" and theme_file and theme_file.is_file():
        # load theme from file
        verbose(f"Loading color theme from {theme_file}")
        try:
            theme = Theme.read(theme_file)
        except Exception as e:
            raise ValueError(f"Error reading theme file {theme_file}: {e}")
    elif theme_name == "default":
        # try to auto-detect dark/light mode
        theme = COLOR_THEMES["dark"] if is_dark_mode() else COLOR_THEMES["light"]
    else:
        theme = COLOR_THEMES[theme_name]
    return theme
