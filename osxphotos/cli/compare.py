"""Compare two libraries"""

from __future__ import annotations

import sys

import click

from osxphotos.compare_libraries import compare_photos_libraries
from osxphotos.photosdb import PhotosDB

from .cli_params import VERBOSE_OPTION
from .verbose import verbose_print


@click.command()
@click.option(
    "--csv",
    "-c",
    "csv_flag",
    is_flag=True,
    help="Output results in CSV (comma delimited) format",
)
@click.option(
    "--tsv",
    "-t",
    "tsv_flag",
    is_flag=True,
    help="Output results in TSV (tab delimited) format",
)
@click.option(
    "--json", "-j", "json_flag", is_flag=True, help="Output results in JSON format"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False),
)
@VERBOSE_OPTION
@click.argument("library_a", type=click.Path(exists=True))
@click.argument("library_b", type=click.Path(exists=True))
@click.pass_context
def compare(
    ctx, csv_flag, tsv_flag, json_flag, output, verbose_flag, library_a, library_b
):
    """Compare two Photos libraries to find differences"""

    _validate_compare_options(ctx)

    # send verbose output to stderr so that the following pattern works:
    # osxphotos compare --verbose library_a library_b --csv > output.csv
    verbose = verbose_print(verbose=verbose_flag, file=sys.stderr)
    verbose("Comparing libraries")
    verbose(f"Library A: {library_a}")
    verbose(f"Library B: {library_b}")

    verbose("Opening library A")
    db_a = PhotosDB(dbfile=library_a, verbose=verbose)
    verbose("Opening library B")
    db_b = PhotosDB(dbfile=library_b, verbose=verbose)

    diff = compare_photos_libraries(db_a, db_b, verbose=verbose)

    # handle normal output
    if not any([csv_flag, tsv_flag, json_flag]):
        print_output(diff, output)
        sys.exit(0)

    if csv_flag:
        print_output(diff.csv(), output)
    if tsv_flag:
        print_output(diff.csv(delimiter="\t"), output)
    if json_flag:
        print_output(diff.json(), output)


def print_output(message: str, file: str | None):
    if file:
        with open(file, "w") as f:
            f.write(message)
    else:
        print(message, end="")


def _validate_compare_options(ctx):
    if (
        sum(
            [
                ctx.params.get("csv_flag"),
                ctx.params.get("tsv_flag"),
                ctx.params.get("json_flag"),
            ]
        )
        > 1
    ):
        raise click.BadParameter("Only one of --csv, --tsv, or --json may be specified")
