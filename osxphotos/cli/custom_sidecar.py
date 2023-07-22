"""Generate custom sidecar files for use wit `osxphotos export` command and --sidecar-template option"""

from __future__ import annotations

import pathlib
from typing import Callable

import click
from mako.template import Template

from osxphotos.photoexporter import ExportResults
from osxphotos.photoinfo import PhotoInfo
from osxphotos.phototemplate import PhotoTemplate, RenderOptions


def generate_custom_sidecar(
    photo: PhotoInfo,
    export_results: ExportResults,
    sidecar_template: tuple[tuple[str, str, bool, bool]],
    exiftool_path: str,
    export_dir: str,
    dry_run: bool,
    verbose: Callable[..., None],
) -> list[str]:
    """Generate custom sidecar files for use with `osxphotos export` command and --sidecar-template option

    Args:
        photo: PhotoInfo object for photo
        export_results: ExportResults object
        sidecar_template: tuple of (template_file, filename_template) for sidecar template
        strip_sidecar: bool, strip whitespace and blank lines from sidecar
        exiftool_path: str, path to exiftool
        export_dir: str, path to export directory
        dry_run: bool, if True, do not actually write sidecar files
        verbose: Callable[..., None], verbose logging function

    Returns:
        list of sidecar files written
    """
    sidecar_files = []
    for (
        template_file,
        filename_template,
        strip_whitespace,
        strip_lines,
    ) in sidecar_template:
        for filepath in getattr(export_results, "exported"):
            render_options = RenderOptions(export_dir=export_dir, filepath=filepath)
            photo_template = PhotoTemplate(photo, exiftool_path=exiftool_path)
            template_filename, _ = photo_template.render(
                filename_template, options=render_options
            )
            template_filename = template_filename[0] if template_filename else None
            if not template_filename:
                raise click.BadOptionUsage(
                    f"Invalid SIDECAR_FILENAME_TEMPLATE for --sidecar-template '{filename_template}'"
                )
            verbose(
                f'Writing custom sidecar: "{template_filename} {strip_whitespace} {strip_lines}"'
            )
            sidecar = Template(filename=template_file)
            sidecar_data = sidecar.render(
                photo=photo,
                sidecar_path=pathlib.Path(template_filename),
                photo_path=pathlib.Path(filepath),
            )
            if strip_whitespace:
                # strip whitespace
                sidecar_data = "\n".join(
                    line.strip() for line in sidecar_data.split("\n")
                )
            if strip_lines:
                # strip blank lines
                sidecar_data = "\n".join(
                    line for line in sidecar_data.split("\n") if line.strip()
                )
            print(sidecar_data)
            if not dry_run:
                ...
            sidecar_files.append(template_filename)

    return sidecar_files
