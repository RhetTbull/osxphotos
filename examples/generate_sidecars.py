"""Generate sidecar files for photos previously exported from Photos.

This can be run with:
    osxphotos run https://raw.githubusercontent.com/RhetTbull/osxphotos/refs/heads/main/examples/generate_sidecars.py

    or

    osxphotos run generate_sidecars.py
if you've downloaded the script to your Mac.

Use --help to see help.

This is hacked together using code from `osxphotos import` to allow generation of sidecar files for photos
exported from Photos without the use of `osxphotos export`. If you exported photos using `osxphotos export`,
add options `--update --sidecar xmp` to your export command and re-run it to generate the sidecar files.
"""

import os.path
import pathlib

import click

from osxphotos import PhotosDB
from osxphotos._constants import SIDECAR_EXIFTOOL, SIDECAR_JSON, SIDECAR_XMP
from osxphotos.cli.click_rich_echo import rich_echo as echo
from osxphotos.cli.click_rich_echo import rich_echo_error
from osxphotos.cli.rich_progress import rich_progress
from osxphotos.cli.verbose import get_verbose_console, verbose_print
from osxphotos.exportoptions import ExportOptions
from osxphotos.fingerprintquery import FingerprintQuery
from osxphotos.image_file_utils import is_image_file, is_video_file
from osxphotos.sidecars import SidecarWriter
from osxphotos.utils import get_last_library_path, pluralize


def verbose(*args, **kwargs):
    """Dummy placeholder for verbose"""
    return


@click.command
@click.option("--xmp", "--XMP", "-x", is_flag=True, help="Generate XMP sidecars")
@click.option(
    "--json", "--JSON", "-j", "json_flag", is_flag=True, help="Generate JSON sidecars"
)
@click.option("--exiftool", "-e", is_flag=True, help="Generate exiftool sidecars")
@click.option(
    "--sidecar-drop-ext",
    "--drop-ext",
    "-d",
    is_flag=True,
    help="Drop image extension when adding sidecar extension. "
    "For example, sidecar file would be 'IMG_1234.xmp' instead of 'IMG_1234.jpg.xmp'.",
)
@click.option(
    "--walk", "-w", is_flag=True, help="Walk directories looking for photo/video files."
)
@click.option(
    "--verbose",
    "-V",
    "verbose_option",
    count=True,
    help="Show verbose output. Repeat to increase verbose level.",
)
@click.option(
    "--dry-run", "-D", is_flag=True, help="Dry run only, do not write sidecar files."
)
@click.argument("files", metavar="FILES", type=click.Path(exists=True), nargs=-1)
def generate_sidecars(
    xmp: bool,
    json_flag: bool,
    exiftool: bool,
    sidecar_drop_ext: bool,
    walk: bool,
    dry_run: bool,
    verbose_option: int,
    files: tuple[str, ...],
):
    """Generate sidecar files for photos previously exported from Photos.

    Any file paths passed will be matched to photos in Photos. If a matching photo is found,
    a sidecar file is generated and saved.

    At least one of --xmp, --json, --exiftool must be used to generate the appropriate sidecar format.

    Use --dry-run to test without actually generating sidecar files.
    """
    if not any([xmp, json_flag, exiftool]):
        raise click.UsageError(
            "At least one of --xmp, --json, or --exiftool must be selected."
        )
    if json_flag and exiftool:
        raise click.UsageError("--json and --exiftool  are mutually exclusive.")

    sidecar_flags = 0
    if json_flag:
        sidecar_flags |= SIDECAR_JSON
    if xmp:
        sidecar_flags |= SIDECAR_XMP
    if exiftool:
        sidecar_flags |= SIDECAR_EXIFTOOL

    global verbose
    verbose = verbose_print(verbose_option)

    files_to_process = collect_files_to_import(files, walk, (), False)
    matches = find_matching_files_in_photos(files_to_process, None)
    if not matches:
        echo("Did not find any matching files in Photos")
        return
    echo(f"Found [num]{len(matches)}[/] matching file(s) in Photos")

    echo("Loading Photos database...")
    photosdb = PhotosDB()
    options = ExportOptions(
        sidecar=sidecar_flags, sidecar_drop_ext=sidecar_drop_ext, dry_run=dry_run
    )
    for filepath, uuid in matches:
        echo(f"Writing sidecar for [filepath]{filepath}[/]: [uuid]{uuid}[/]")
        photo = photosdb.get_photo(uuid)
        writer = SidecarWriter(photo)
        files = writer.write_sidecar_files(filepath, options)
        sidecar_files = (
            files.sidecar_xmp_written
            + files.sidecar_json_written
            + files.sidecar_exiftool_written
        )
        if sidecar_files:
            echo("Wrote sidecar file(s): ")
            for f in sidecar_files:
                echo(f"\t[filepath]{f}[/]")
        else:
            rich_echo_error("No sidecar files written")


def find_matching_files_in_photos(
    files: list[tuple[pathlib.Path, ...]],
    library: str | None,
) -> list[str]:
    """Check if files have been previously imported and print results"""

    if not library:
        library = get_last_library_path()

    if not files:
        rich_echo_error("No files to check")
        return

    matches = []
    filecount = len(files)
    file_word = pluralize(filecount, "file", "files")
    verbose(f"Checking [num]{filecount}[/] {file_word} to match imported files.")

    fq = FingerprintQuery(library)
    for filepath in files:
        verbose(f"Checking [filepath]{filepath}[/]")
        if duplicates := fq.possible_duplicates(filepath):
            uuid = duplicates[0][0]
            matches.append((filepath, uuid))
            verbose(f"Found match for [filepath]{filepath}[/]: [uuid]{uuid}[/]")

    return matches


def collect_files_to_import(
    files: tuple[str, ...],
    walk: bool,
    glob: tuple[str, ...],
    no_progress: bool,
) -> list[pathlib.Path]:
    """Collect files to import, recursively if necessary

    Args:
        files: list of initial files or directories to import
        walk: whether to walk directories
        glob: glob patterns to match files or empty tuple if none
        no_progress: if True, do not print progress bars

    Note: ignores any files that appear to be image sidecar files
    """
    files_to_import = []
    with rich_progress(console=get_verbose_console(), mock=no_progress) as progress:
        task = progress.add_task("Collecting files to check...", total=None)
        for file in files:
            if os.path.isfile(file):
                files_to_import.append(file)
                progress.advance(task)
            elif os.path.isdir(file):
                if not walk:
                    # don't recurse but do collect all files in the directory
                    dir_files = [
                        os.path.join(file, f)
                        for f in os.listdir(file)
                        if os.path.isfile(os.path.join(file, f))
                    ]
                    files_to_import.extend(dir_files)
                    progress.advance(task)
                else:
                    for root, dirs, filenames in os.walk(file):
                        for file in filenames:
                            files_to_import.append(os.path.join(root, file))
                            progress.advance(task)
            else:
                progress.advance(task)
                continue

    # if glob:
    #     verbose("Filtering files with glob...")
    #     files_to_import = [
    #         f
    #         for f in files_to_import
    #         if filename_matches_patterns(os.path.basename(f), glob)
    #     ]

    files_to_import = [pathlib.Path(f).absolute() for f in files_to_import]

    # keep only image files, video files
    filtered_file_list = []
    with rich_progress(console=get_verbose_console(), mock=no_progress) as progress:
        task = progress.add_task(
            "Filtering files for image & video files...",
            total=len(files_to_import),
        )
        for f in files_to_import:
            if is_image_file(f) or is_video_file(f):
                filtered_file_list.append(f)
            progress.advance(task)

    # there may be duplicates if user passed both a directory and files in that directory
    # e.g. /Volumes/import /Volumes/import/IMG_1234.*
    # so strip duplicates before returning the list
    return list(set(filtered_file_list))


if __name__ == "__main__":
    generate_sidecars()
