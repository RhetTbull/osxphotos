"""
Batch edit currently selected photo metadata using osxphotos.

Run this with `osxphotos run batch_edit.py` or `osxphotos run batch_edit.py --help` for more information.
"""

from __future__ import annotations

import sys

import click
import photoscript

import osxphotos
from osxphotos.cli import echo, echo_error, selection_command, verbose
from osxphotos.cli.param_types import TemplateString
from osxphotos.phototemplate import RenderOptions


@selection_command
@click.option(
    "--title",
    metavar="TITLE_TEMPLATE",
    type=TemplateString(),
    help="Set title of photo.",
)
@click.option(
    "--description",
    metavar="DESCRIPTION_TEMPLATE",
    type=TemplateString(),
    help="Set description of photo.",
)
@click.option(
    "--keyword",
    metavar="KEYWORD_TEMPLATE",
    type=TemplateString(),
    multiple=True,
    help="Set keywords of photo. May be specified multiple times.",
)
@click.option("--dry-run", is_flag=True, help="Don't actually change anything.")
def batch_edit(
    photos: list[osxphotos.PhotoInfo], title, description, keyword, dry_run, **kwargs
):
    """
    Batch edit photo metadata such as title, description, keywords, etc.
    Operates on currently selected photos.

    Select one or more photos in Photos then run this command to edit the metadata.

    For example:

    \b
        osxphotos run batch_edit.py \\
        --verbose \\
        --title "California vacation 2023 {created.year}-{created.dd}-{created.mm} {counter:03d}" \\
        --description "{place.name}" \\ 
        --keyword "Family" --keyword "Travel" --keyword "{keyword}"

    This will set the title to "California vacation 2023 2023-02-20 001", and so on,
    the description to the reverse geolocation place name, 
    and the keywords to "Family", "Travel", and any existing keywords of the photo.

    --title, --description, and --keyword may be any valid template string.
    See https://rhettbull.github.io/osxphotos/template_help.html for more information
    on the osxphotos template system.
    """

    if not title and not description and not keyword:
        echo_error(
            "[error] Must specify at least one of --title, --description, or --keyword"
        )
        sys.exit(1)

    if not photos:
        echo_error("[error] No photos selected")
        sys.exit(1)

    echo(f"Processing [num]{len(photos)}[/] photos...")
    for photo in photos:
        ps_photo = photoscript.Photo(photo.uuid)
        # don't render None values
        render_options = RenderOptions(none_str="")
        verbose(
            f"Processing [filename]{photo.original_filename}[/] ([uuid]{photo.uuid}[/])"
        )
        if title:
            title_string, _ = photo.render_template(title, render_options)
            if len(title_string) > 1:
                echo_error(
                    f"[error] Title template must return a single string: {title_string}"
                )
                sys.exit(1)
            if title_string:
                verbose(f"Setting title to [bold]{title_string[0]}")
                if not dry_run:
                    ps_photo.title = title_string[0]
        if description:
            description_string, _ = photo.render_template(description, render_options)
            if len(description_string) > 1:
                echo_error(
                    f"[error] Description template must return a single string: {description_string}"
                )
                sys.exit(1)
            if description_string:
                verbose(f"Setting description to [bold]{description_string[0]}")
                if not dry_run:
                    ps_photo.description = description_string[0]
        if keyword:
            keywords = set()
            for kw in keyword:
                kw_string, _ = photo.render_template(kw, render_options)
                if kw_string:
                    # filter out empty strings
                    keywords.update([k for k in kw_string if k])
            verbose(
                f"Setting keywords to {', '.join(f'[bold]{kw}[/]' for kw in keywords)}"
            )
            if not dry_run:
                ps_photo.keywords = keywords


if __name__ == "__main__":
    batch_edit()
