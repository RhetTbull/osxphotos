"""Manage rich themes"""


import pathlib
from typing import Callable, List, Optional
from os.path import exists

from rich.color import Color
from rich.console import Console
from rich.style import Style
from rich.table import Table, box
from rich.text import Text

from .theme import Theme

SAMPLE_TEXT = "The quick brown fox..."


class ThemeManager:
    """Manage rich themes"""

    def __init__(
        self,
        theme_dir: Optional[str] = None,
        themes: Optional[List[Theme]] = None,
        default: Optional[Callable] = None,
    ):
        self._theme_dir = pathlib.Path(theme_dir) if theme_dir else None
        self._themes = {theme.name: theme for theme in themes} if themes else {}
        self._default = default

        if self._theme_dir is not None:
            for theme in self.themes:
                theme.path = str(self._theme_dir / f"{theme.name}.theme")
            self.load_themes()
            self.write_themes()

    @property
    def themes(self) -> List[Theme]:
        """Themes"""
        return list(self._themes.values())

    def add(self, theme: Theme):
        """Add theme"""
        self._themes[theme.name] = theme

    def remove(self, theme: Theme):
        """Remove theme"""
        del self._themes[theme.name]

    def get(self, theme_name: Optional[str] = None) -> Theme:
        """Get theme by name"""
        for theme in self.themes:
            if theme.name == theme_name:
                return theme
        raise ValueError(f"Theme {theme_name} not found")

    def load_themes(self) -> None:
        """Load themes"""
        for path in self._theme_dir.glob("*.theme"):
            theme = Theme.read(str(path))
            self._themes[theme.name] = theme

    def write_themes(self, overwrite=False) -> None:
        """Write themes"""
        for theme in self.themes:
            if not exists(theme.path) or overwrite:
                theme.save()

    def preview_theme(
        self, theme: Theme, sample_text: Optional[str] = None, show_path: bool = True
    ) -> None:
        """Preview a theme to the console"""
        title = f"Theme: {theme.name}"
        if show_path:
            title += f" - {theme.path}"
        table = Table(
            title=title,
            title_justify="center",
            show_header=True,
            show_lines=True,
            header_style="bold",
            box=box.SQUARE,
        )

        sample_text = sample_text or SAMPLE_TEXT

        for column in [
            "style",
            "color",
            "color",
            "bgcolor",
            "bgcolor",
            "attributes",
            "example",
        ]:
            table.add_column(column)

        for style_name in theme.style_names:
            style = theme.styles.get(style_name)
            if not style:
                continue
            color = (style.color.name or style.color.rgb) if style.color else "None"
            bgcolor = (
                (style.bgcolor.name or style.bgcolor.rgb) if style.bgcolor else "None"
            )

            attributes = attribute_str(style)

            table.add_row(
                style_name,
                str(color),
                color_bar(5, style.color) if style.color else " " * 5,
                str(bgcolor),
                color_bar(5, style.bgcolor) if style.bgcolor else " " * 5,
                attributes,
                f"[{style_name}]{sample_text}",
            )

        console = Console(theme=theme)
        console.print(table)

        legend = Table(
            title="Attributes Legend",
            title_justify="left",
            show_header=False,
            show_lines=False,
            box=box.SQUARE,
        )
        legend.add_row(
            (
                f"{_bold('b')}: bold, "
                f"{_bold('d')}: dim, "
                f"{_bold('i')}: italic, "
                f"{_bold('u')}: underline, "
                f"{_bold('U')}: double underline, "
                f"{_bold('B')}: blink, "
                f"{_bold('2')}: blink2"
            )
        )
        legend.add_row(
            (
                f"{_bold('r')}: reverse, "
                f"{_bold('c')}: conceal, "
                f"{_bold('s')}: strike, "
                f"{_bold('f')}: frame, "
                f"{_bold('e')}: encircle, "
                f"{_bold('o')}: overline, "
                f"{_bold('L')}: Link"
            )
        )
        console.print(legend)

    def list_themes(
        self, show_path: bool = True, theme_names: Optional[List[str]] = None
    ) -> List[Theme]:
        """List themes"""
        table = Table(show_header=True, show_lines=False, box=None)
        table.add_column("Theme")
        table.add_column("Description")
        table.add_column("Tags")
        if show_path:
            table.add_column("Path")
        for theme in self.themes:
            if theme_names and theme.name not in theme_names:
                continue
            row = [
                theme.name,
                theme.description,
                str(", ".join(theme.tags)),
            ]
            if show_path:
                row.append(theme.path or "")
            table.add_row(*row)
        console = Console()
        console.print(table)


def _bold(text: str) -> str:
    return f"[bold]{text}[/]"


def attribute_str(style: Style) -> str:
    """Return a string representing all attributes of a style"""
    attributes = "" + (_bold("b") if style.bold else "-")
    attributes += _bold("d") if style.dim else "-"
    attributes += _bold("i") if style.italic else "-"
    attributes += _bold("u") if style.underline else "-"
    attributes += _bold("U") if style.underline2 else "-"
    attributes += _bold("B") if style.blink else "-"
    attributes += _bold("2") if style.blink2 else "-"
    attributes += _bold("r") if style.reverse else "-"
    attributes += _bold("c") if style.conceal else "-"
    attributes += _bold("s") if style.strike else "-"
    attributes += _bold("f") if style.frame else "-"
    attributes += _bold("e") if style.encircle else "-"
    attributes += _bold("o") if style.overline else "-"
    attributes += _bold("L") if style.link else "-"
    return attributes


def color_bar(length: int, color: Color) -> str:
    """Create a color bar."""
    bar = "█" * length
    return Text(bar, style=Style(color=color))
