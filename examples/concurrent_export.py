"""Example for concurrent export of photos using osxphotos.PhotoExporter.export()

Note: concurrent export can only be used on Python 3.11 and later due to the way
python's sqlite3 module is implemented. See https://docs.python.org/3/library/sqlite3.html#sqlite3.threadsafety
for more information.
"""

import concurrent.futures
import os
import time

import click

import osxphotos
from osxphotos.cli import echo, query_command, verbose


@query_command()
@click.option(
    "--workers",
    metavar="WORKERS",
    help="Maximum number of worker threads to use for export. "
    "If not specified, it will default to the number of processors on the machine, multiplied by 5.",
    type=int,
)
@click.argument(
    "export_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True),
)
def export(workers, export_dir, photos: list[osxphotos.PhotoInfo], **kwargs):
    """Export photos to EXPORT_DIR using concurrent export.
    Use --workers to specify the number of worker threads to use.
    """
    workers = workers or os.cpu_count() * 5
    echo(f"Exporting {len(photos)} photos to {export_dir} using {workers} workers")
    start_t = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(p.export, export_dir, f"{p.uuid}_{p.original_filename}")
            for p in photos
        ]
        exported = []
        for future in concurrent.futures.as_completed(futures):
            exported.extend(future.result())
    end_t = time.perf_counter()
    echo(
        f"Exported {len(exported)} photos to {export_dir} in {end_t-start_t:.4f} seconds"
    )


if __name__ == "__main__":
    export()
