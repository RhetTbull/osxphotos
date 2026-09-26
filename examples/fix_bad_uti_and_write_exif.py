"""Post-function for ``osxphotos export --post-function`` to repair extension and write metadata.

This function is intended for assets whose exported filename extension does not match the
actual file type (for example, a HEIC file labeled as JPEG in Photos).

It performs three tasks:
1. Detect actual file type with exiftool and rename the exported file if the extension is wrong.
2. Write the same metadata osxphotos would write with ``--exiftool`` (default ExifOptions).
3. Write additional camera metadata from ``PhotoInfo.exif_info`` that osxphotos does not
   normally export.
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable
from typing import Any

from osxphotos import ExportResults, PhotoInfo
from osxphotos.exiftool import ExifTool, exiftool_can_write
from osxphotos.exifwriter import ExifOptions, ExifWriter, exif_options_from_options
from osxphotos.image_file_utils import is_video_file


def _append_unique(values: list[Any], value: Any) -> None:
    if value not in values:
        values.append(value)


def _equivalent_extensions(expected: str, actual: str) -> bool:
    expected = expected.lower().lstrip(".")
    actual = actual.lower().lstrip(".")
    if expected == actual:
        return True
    return {expected, actual} <= {"jpg", "jpeg"}


def _detect_actual_extension(filepath: pathlib.Path) -> str | None:
    exiftool = ExifTool(filepath)
    exifdict = exiftool.asdict()
    actual_ext = exifdict.get("File:FileTypeExtension")
    return actual_ext.lower() if actual_ext else None


def _rename_with_correct_extension(
    filepath: pathlib.Path, verbose: Callable[[Any], None]
) -> tuple[pathlib.Path, bool]:
    actual_ext = _detect_actual_extension(filepath)
    if not actual_ext:
        verbose(
            f"[warning]Could not detect actual file type extension for [filepath]{filepath}[/]"
        )
        return filepath, False

    current_ext = filepath.suffix.lower().lstrip(".")
    if not current_ext or not _equivalent_extensions(current_ext, actual_ext):
        new_filepath = filepath.with_suffix(f".{actual_ext}")
        if new_filepath == filepath:
            return filepath, False
        if new_filepath.exists():
            raise FileExistsError(
                f"Cannot rename {filepath} to {new_filepath}: destination already exists"
            )
        verbose(
            f"[change]Renaming [filepath]{filepath}[/] to [filepath]{new_filepath}[/] "
            f"(actual type: [filename]{actual_ext}[/])"
        )
        filepath.rename(new_filepath)
        return new_filepath, True

    verbose(f"[no_change]Extension OK for [filepath]{filepath}[/]")
    return filepath, False


def _exif_options_from_kwargs(kwargs: dict[str, Any]) -> ExifOptions:
    # Current osxphotos export post-function API does not pass export options.
    # If a future version adds them, use them so this mirrors --exiftool behavior.
    export_options = kwargs.get("export_options") or kwargs.get("options")
    if export_options is not None:
        try:
            return exif_options_from_options(export_options)
        except Exception:
            pass
    return ExifOptions()


def _camera_exif_tags(photo: PhotoInfo) -> dict[str, Any]:
    exif_info = photo.exif_info
    if not exif_info:
        return {}

    tags: dict[str, Any] = {}
    if exif_info.camera_make:
        tags["EXIF:Make"] = exif_info.camera_make
    if exif_info.camera_model:
        tags["EXIF:Model"] = exif_info.camera_model
    if exif_info.lens_model:
        tags["EXIF:LensModel"] = exif_info.lens_model
    if exif_info.iso is not None:
        tags["EXIF:ISO"] = exif_info.iso
    if exif_info.aperture is not None:
        tags["EXIF:FNumber"] = exif_info.aperture
    if exif_info.focal_length is not None:
        tags["EXIF:FocalLength"] = exif_info.focal_length
    if exif_info.shutter_speed is not None:
        tags["EXIF:ExposureTime"] = exif_info.shutter_speed
    if exif_info.exposure_bias is not None:
        tags["EXIF:ExposureCompensation"] = exif_info.exposure_bias
    if exif_info.metering_mode is not None:
        tags["EXIF:MeteringMode"] = exif_info.metering_mode
    if exif_info.white_balance is not None:
        tags["EXIF:WhiteBalance"] = exif_info.white_balance
    if exif_info.flash_fired is not None:
        # EXIF:Flash is a bit field; 0/1 preserves the information available from Photos.
        tags["EXIF:Flash"] = 1 if exif_info.flash_fired else 0
    return tags


def _write_extra_camera_metadata(
    photo: PhotoInfo,
    filepath: pathlib.Path,
    exif_options: ExifOptions,
    verbose: Callable[[Any], None],
) -> tuple[str, str]:
    if is_video_file(filepath):
        verbose(
            f"[no_change]Skipping extra camera EXIF for video component [filepath]{filepath}[/]"
        )
        return "", ""

    tags = _camera_exif_tags(photo)
    if not tags:
        verbose(f"[no_change]No extra camera EXIF metadata for [uuid]{photo.uuid}[/]")
        return "", ""

    verbose(
        f"Writing [count]{len(tags)}[/] extra camera EXIF tag(s) to [filepath]{filepath}[/]"
    )
    with ExifTool(
        filepath,
        exiftool=getattr(photo, "_exiftool_path", None),
        flags=exif_options.exiftool_flags,
    ) as exiftool:
        for tag, value in tags.items():
            exiftool.setvalue(tag, value)

    return exiftool.warning or "", exiftool.error or ""


def fix_bad_uti_and_write_exif(
    photo: PhotoInfo,
    results: ExportResults,
    verbose: Callable[[Any], None],
    **kwargs,
) -> ExportResults | None:
    """Call with:
    ``osxphotos export /path/to/export --post-function examples/fix_bad_uti_and_write_exif.py::fix_bad_uti_and_write_exif``

    Notes:
        This writes default ``--exiftool`` metadata because current post-function callbacks do
        not receive export options. If future osxphotos versions pass export options in
        ``kwargs``, the function will use them automatically.
    """

    post_results = ExportResults()
    exif_options = _exif_options_from_kwargs(kwargs)
    writer = ExifWriter(photo)

    files_to_process = []
    for filename in list(results.exported) + list(results.updated):
        path = pathlib.Path(filename)
        if path not in files_to_process:
            files_to_process.append(path)

    for filepath in files_to_process:
        try:
            if not filepath.exists():
                error = f"Exported file does not exist: {filepath}"
                verbose(f"[error]{error}[/]")
                post_results.user_error.append((str(filepath), error))
                continue

            video_component = is_video_file(filepath)
            if video_component:
                # For Live Photos, keep the companion video filename/extension unchanged.
                # The user issue is the image component having the wrong extension/UTI.
                verbose(
                    f"[no_change]Skipping extension repair for video component [filepath]{filepath}[/]"
                )
                renamed = False
            else:
                filepath, renamed = _rename_with_correct_extension(filepath, verbose)
            if renamed:
                _append_unique(post_results.user_written, str(filepath))

            if not exiftool_can_write(filepath.suffix):
                verbose(
                    f"[warning]ExifTool cannot write file type [filename]{filepath.suffix}[/] "
                    f"for [filepath]{filepath}[/]; skipping metadata write"
                )
                if not renamed:
                    _append_unique(post_results.user_skipped, str(filepath))
                continue

            verbose(
                f"Writing standard export metadata (same as [bold]--exiftool[/]) to "
                f"[filepath]{filepath}[/]"
            )
            warning, error = writer.write_exif_data(filepath, exif_options)
            if warning:
                verbose(
                    f"[warning]ExifTool warning for [filepath]{filepath}[/]: {warning}[/]"
                )
            if error:
                verbose(
                    f"[error]ExifTool error for [filepath]{filepath}[/]: {error}[/]"
                )
                post_results.user_error.append((str(filepath), str(error)))
                continue

            warning, error = _write_extra_camera_metadata(
                photo, filepath, exif_options, verbose
            )
            if warning:
                verbose(
                    f"[warning]ExifTool warning for extra camera metadata on "
                    f"[filepath]{filepath}[/]: {warning}[/]"
                )
            if error:
                verbose(
                    f"[error]ExifTool error writing extra camera metadata on "
                    f"[filepath]{filepath}[/]: {error}[/]"
                )
                post_results.user_error.append((str(filepath), str(error)))
                continue

            _append_unique(post_results.user_written, str(filepath))

        except Exception as e:
            verbose(
                f"[error]Error processing [filepath]{filepath}[/] for [uuid]{photo.uuid}[/]: {e}[/]"
            )
            post_results.user_error.append((str(filepath), str(e)))

    return post_results
