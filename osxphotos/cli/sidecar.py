"""Generate custom sidecar files for use with `osxphotos export` command and --sidecar-template option"""

from __future__ import annotations

import pathlib
from functools import cache
from typing import Callable

import click
from mako.template import Template

from osxphotos.cli.click_rich_echo import rich_echo_error
from osxphotos.exportoptions import ExportResults
from osxphotos.photoinfo import PhotoInfo
from osxphotos.phototemplate import PhotoTemplate, RenderOptions


@cache
def get_template(template: str) -> Template:
    """Get template from cache or load from file"""
    return Template(filename=template)


def generate_user_sidecar(
    photo: PhotoInfo,
    export_results: ExportResults,
    sidecar_template: tuple[tuple[str, str, tuple[str, ...]], ...],
    exiftool_path: str,
    export_dir: str,
    dry_run: bool,
    verbose: Callable[..., None],
) -> ExportResults:
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
        ExportResults object with sidecar_user_written and sidecar_user_skipped set
    """
    sidecar_results = ExportResults()
    for (
        template_file,
        filename_template,
        options,
    ) in sidecar_template:
        strip_whitespace = "strip_whitespace" in options
        strip_lines = "strip_lines" in options
        write_skipped = "write_skipped" in options
        skip_zero = "skip_zero" in options
        catch_errors = "catch_errors" in options

        if not write_skipped:
            # skip writing sidecar if photo not exported
            # but if run with --update and --cleanup, a sidecar file may have been written
            # in the past, so check if it exists and if so keep it
            for filepath in export_results.skipped:
                template_filename = _render_sidecar_filename(
                    photo=photo,
                    filepath=filepath,
                    filename_template=filename_template,
                    export_dir=export_dir,
                    exiftool_path=exiftool_path,
                )
                if template_filename and pathlib.Path(template_filename).exists():
                    verbose(
                        f"Skipping existing sidecar file [filepath]{template_filename}[/]"
                    )
                    sidecar_results.sidecar_user_skipped.append(template_filename)

        # write sidecar files for exported and missing files (and skipped if write_skipped)
        files_to_process = export_results.exported + export_results.missing
        if write_skipped:
            files_to_process += export_results.skipped
        for filepath in files_to_process:
            template_filename = _render_sidecar_filename(
                photo=photo,
                filepath=filepath,
                filename_template=filename_template,
                export_dir=export_dir,
                exiftool_path=exiftool_path,
            )
            if not template_filename:
                raise click.BadOptionUsage(
                    f"Invalid SIDECAR_FILENAME_TEMPLATE for --sidecar-template '{filename_template}'"
                )

            verbose(f"Writing sidecar file [filepath]{template_filename}[/]")
            if error := _render_sidecar_and_write_data(
                template_file=template_file,
                photo=photo,
                template_filename=template_filename,
                filepath=filepath,
                strip_whitespace=strip_whitespace,
                strip_lines=strip_lines,
                skip_zero=skip_zero,
                catch_errors=catch_errors,
                verbose=verbose,
                dry_run=dry_run,
            ):
                sidecar_results.sidecar_user_error.append((template_filename, error))
            else:
                sidecar_results.sidecar_user_written.append(template_filename)

    print(sidecar_results)
    return sidecar_results


def _render_sidecar_filename(
    photo: PhotoInfo,
    filepath: str,
    filename_template: str,
    export_dir: str,
    exiftool_path: str,
):
    """Render sidecar filename template"""
    render_options = RenderOptions(export_dir=export_dir, filepath=filepath)
    photo_template = PhotoTemplate(photo, exiftool_path=exiftool_path)
    template_filename, _ = photo_template.render(
        filename_template, options=render_options
    )
    template_filename = template_filename[0] if template_filename else None

    return template_filename


def _render_sidecar_and_write_data(
    template_file: str,
    photo: PhotoInfo,
    template_filename: str,
    filepath: str,
    strip_whitespace: bool,
    strip_lines: bool,
    skip_zero: bool,
    catch_errors: bool,
    verbose: Callable[..., None],
    dry_run: bool,
) -> Exception | None:
    """Render sidecar template and write data to file

    Returns:
        None if no errors, otherwise Exception if catch_errors is True
        If catch_errors is False, raises exception if error
    """
    sidecar = get_template(template_file)
    try:
        sidecar_data = sidecar.render(
            photo=photo,
            sidecar_path=pathlib.Path(template_filename),
            photo_path=pathlib.Path(filepath),
        )
    except Exception as e:
        if catch_errors:
            rich_echo_error(f"[error]Error rendering sidecar template: {e}[/]")
            return e
        raise e

    if strip_whitespace:
        # strip whitespace
        sidecar_data = "\n".join(line.strip() for line in sidecar_data.split("\n"))
    if strip_lines:
        # strip blank lines
        sidecar_data = "\n".join(
            line for line in sidecar_data.split("\n") if line.strip()
        )
    if not dry_run:
        # write sidecar file
        if skip_zero and not sidecar_data:
            verbose(f"Skipping empty sidecar file [filepath]{template_filename}[/]")
            return
        with open(template_filename, "w") as f:
            f.write(sidecar_data)

    return None
