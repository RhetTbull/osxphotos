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
    html = markdown2.markdown(markdown_text)
    soup = BeautifulSoup(html, "html.parser")

    lines = []
    for elem in soup.recursiveChildGenerator():
        if elem.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            lines.append(elem.get_text(strip=True))
            lines.append("")  # blank line after headers
        elif elem.name == "li":
            lines.append(f"- {elem.get_text(strip=True)}")
        elif elem.name == "p":
            text = elem.get_text(strip=True)
            if text:
                lines.append(text)
                lines.append("")  # preserve spacing after paragraphs

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
