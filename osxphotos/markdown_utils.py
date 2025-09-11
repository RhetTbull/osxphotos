"""Utilities for markdown formatting"""

import markdown2
from bs4 import BeautifulSoup
from rich.console import Console
from rich.markdown import Markdown


def markdown_to_plaintext(markdown_text: str) -> str:
    """Convert Markdown to plain text, preserving bullet points but stripping formatting.

    Args:
        markdown_text (str): The Markdown text to convert.

    Returns:
        str: The plain text representation of the Markdown.
    """
    # Convert Markdown to HTML
    html = markdown2.markdown(markdown_text, extras=["fenced-code-blocks"])
    soup = BeautifulSoup(html, "html.parser")

    lines = []

    def add_line(text="", indent=0):
        if text is not None:
            indented = (" " * indent) + text.strip()
            lines.append(indented)

    for elem in soup.recursiveChildGenerator():
        if elem.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            add_line(elem.get_text())
            lines.append("")  # blank line after headers

        elif elem.name == "p":
            add_line(elem.get_text())
            lines.append("")  # blank line after paragraphs

        elif elem.name == "li":
            add_line(f"- {elem.get_text()}")

        elif elem.name == "blockquote":
            for sub in elem.stripped_strings:
                add_line(sub, indent=4)
            lines.append("")  # blank line after blockquote

        elif elem.name == "pre":
            code = elem.get_text().rstrip().splitlines()
            for line in code:
                add_line(line, indent=4)
            lines.append("")  # blank line after code block

    return "\n".join(lines).strip()


def format_markdown_for_console(markdown_text: str, width: int = 80) -> str:
    """Format Markdown for console output.

    Args:
        markdown_text (str): The Markdown text to format.
        width (int, optional): The maximum width of the formatted text. Defaults to 80.

    Returns:
        str: The formatted Markdown text.
    """
    console = Console()
    with console.capture() as capture:
        console.print(Markdown(markdown_text), width=min(width, console.width))
    return capture.get()
