import click
import osxphotos
from loguru import logger
import json
import yaml
import csv
import sys


class CLI_Obj:
    def __init__(self, db=None, json=False):
        self.photosdb = osxphotos.PhotosDB(dbfile=db)
        self.json = json


@click.group()
@click.option(
    "--db",
    required=False,
    metavar="<Photos database path>",
    default=None,
    help="Specify database file",
)
@click.option(
    "--json",
    required=False,
    is_flag=True,
    default=False,
    help="Print output in JSON format",
)
@click.pass_context
def cli(ctx, db, json):
    ctx.obj = CLI_Obj(db=db, json=json)


@cli.command()
@click.pass_obj
def keywords(cli_obj):
    """ print out keywords found in the Photos library"""
    keywords = {"keywords": cli_obj.photosdb.keywords_as_dict()}
    if cli_obj.json:
        print(json.dumps(keywords))
    else:
        print(yaml.dump(keywords, sort_keys=False))


@cli.command()
@click.pass_obj
def albums(cli_obj):
    """ print out albums found in the Photos library """
    albums = {"albums": cli_obj.photosdb.albums_as_dict()}
    if cli_obj.json:
        print(json.dumps(albums))
    else:
        print(yaml.dump(albums, sort_keys=False))


@cli.command()
@click.pass_obj
def persons(cli_obj):
    """ print out persons (faces) found in the Photos library """
    persons = {"persons": cli_obj.photosdb.persons_as_dict()}
    if cli_obj.json:
        print(json.dumps(persons))
    else:
        print(yaml.dump(persons, sort_keys=False))


@cli.command()
@click.pass_obj
def info(cli_obj):
    """ print out descriptive info of the Photos library database """
    pdb = cli_obj.photosdb
    info = {}
    info["database_path"] = pdb.get_db_path()
    info["database_version"] = pdb.get_db_version()

    photos = pdb.photos()
    info["photo_count"] = len(photos)

    keywords = pdb.keywords_as_dict()
    info["keywords_count"] = len(keywords)
    info["keywords"] = keywords

    albums = pdb.albums_as_dict()
    info["albums_count"] = len(albums)
    info["albums"] = albums

    persons = pdb.persons_as_dict()
    info["persons_count"] = len(persons)
    info["persons"] = persons

    if cli_obj.json:
        print(json.dumps(info))
    else:
        print(yaml.dump(info, sort_keys=False))


@cli.command()
# @click.option('--delim',default=",",help="")
@click.pass_obj
def dump(cli_obj):
    """ print list of all photos & associated info from the Photos library """
    pdb = cli_obj.photosdb
    photos = pdb.photos()

    csv_writer = csv.writer(
        sys.stdout, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
    )
    if cli_obj.json:
        dump = []
        for p in photos:
            dump.append(
                {
                    "uuid": p.uuid(),
                    "filename": p.filename(),
                    "date": str(p.date()),
                    "description": p.description(),
                    "name": p.name(),
                    "keywords": p.keywords(),
                    "albums": p.albums(),
                    "persons": p.persons(),
                    "path": p.path(),
                    "ismissing": p.ismissing(),
                    "hasadjustments": p.hasadjustments(),
                }
            )
        print(json.dumps(dump))
    else:
        dump = []
        # add headers
        dump.append(
            [
                "uuid",
                "filename",
                "date",
                "description",
                "name",
                "keywords",
                "albums",
                "persons",
                "path",
                "ismissing",
                "hasadjustments",
            ]
        )
        for p in photos:
            dump.append(
                [
                    p.uuid(),
                    p.filename(),
                    str(p.date()),
                    p.description(),
                    p.name(),
                    ", ".join(p.keywords()),
                    ", ".join(p.albums()),
                    ", ".join(p.persons()),
                    p.path(),
                    p.ismissing(),
                    p.hasadjustments(),
                ]
            )
        for row in dump:
            csv_writer.writerow(row)


if __name__ == "__main__":
    cli()
