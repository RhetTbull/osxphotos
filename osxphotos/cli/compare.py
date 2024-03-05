"""Compare two libraries"""

from __future__ import annotations

import sys

import click

from osxphotos.compare_libraries import compare_photos_libraries
from osxphotos.photosdb import PhotosDB

from .cli_params import VERBOSE_OPTION
from .param_types import TemplateString
from .verbose import verbose_print


@click.command()
@click.option(
    "--check",
    "-k",
    is_flag=True,
    help="Check if libraries are different and print out total number of differences. "
    "If libraries are different, exits with error code 1, otherwise 0 if they are the same.",
)
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
@click.option(
    "--signature",
    "-s",
    type=TemplateString(),
    help="Custom template for signature. "
    "The signature is used to match photos from one library to another. "
    "The default is '{photo.original_filename|lower}:{photo.fingerprint}' "
    "which should work well in most cases.",
)
@VERBOSE_OPTION
@click.argument("library_a", type=click.Path(exists=True))
@click.argument("library_b", type=click.Path(exists=True))
@click.pass_context
def compare(
    ctx,
    check,
    csv_flag,
    tsv_flag,
    json_flag,
    output,
    signature,
    verbose_flag,
    library_a,
    library_b,
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

    _signature = None
    if signature:

        def _signature(photo):
            sig, _ = photo.render_template(signature)
            return sig[0]

    diff = compare_photos_libraries(
        db_a, db_b, verbose=verbose, signature_function=_signature
    )

    if check:
        if diff:
            print(len(diff))
            sys.exit(1)
        else:
            print(0)
            sys.exit(0)

    if not any([csv_flag, tsv_flag, json_flag]):
        print_output(diff, output)
        sys.exit(0)

    if csv_flag:
        print_output(diff.csv(), output)
    elif tsv_flag:
        print_output(diff.csv(delimiter="\t"), output)
    elif json_flag:
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
                ctx.params.get("check"),
                ctx.params.get("csv_flag"),
                ctx.params.get("tsv_flag"),
                ctx.params.get("json_flag"),
            ]
        )
        > 1
    ):
        raise click.BadParameter(
            "Only one of --check, --csv, --tsv, or --json may be specified"
        )
