"""Profile PhotosDB processing

To use this you'll need to install line_profiler:
pip install line_profiler
or
osxphotos install line_profiler

Run with:
    osxphotos run profile_db_load.py [--library <path_to_library>]
"""

import datetime
import time

import click
from line_profiler import LineProfiler

from osxphotos import PhotosDB

LAST_VERBOSE = None


def verbose(*args, **kwargs):
    """Print a message with timestamp and time elapsed since last call"""
    global LAST_VERBOSE
    if LAST_VERBOSE is not None:
        elapsed = time.time() - LAST_VERBOSE
        print(f"Elapsed: {elapsed:.2f} seconds")
    LAST_VERBOSE = time.time()
    print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ", *args)


@click.command()
@click.option("--library", type=click.Path(exists=True), help="Path to Photos library")
def main(library):
    """Main function"""
    lp = LineProfiler()
    # Get a reference to the original unbound method
    original_process_database5 = PhotosDB._process_database5

    # Define a wrapper that profiles the original method
    def profiled_process_database5(self, *args, **kwargs):
        # Wrap the original method with the profiler
        profiled_func = lp(original_process_database5)
        return profiled_func(self, *args, **kwargs)

    # Monkey-patch the PhotosDB class method before instantiation
    PhotosDB._process_database5 = profiled_process_database5
    start_t = time.time()
    photosdb = PhotosDB(dbfile=library, verbose=verbose)
    verbose(f"Loaded {len(photosdb)} photos in {time.time() - start_t:.2f} seconds")
    lp.print_stats()


if __name__ == "__main__":
    main()
