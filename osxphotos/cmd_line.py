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


CTX_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CTX_SETTINGS)
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
@click.pass_obj
def dump(cli_obj):
    """ print list of all photos & associated info from the Photos library """
    pdb = cli_obj.photosdb
    photos = pdb.photos()

    if cli_obj.json:
        dump = []
        for p in photos:
            dump.append(p.to_json())
        print(f"[{', '.join(dump)}]")
    else:
        # dump as CSV
        csv_writer = csv.writer(
            sys.stdout, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
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


@cli.command()
@click.option("--keyword", default=None, multiple=True, help="search for keyword(s)")
@click.option("--person", default=None, multiple=True, help="search for person(s)")
@click.option("--album", default=None, multiple=True, help="search for album(s)")
@click.option("--uuid", default=None, multiple=True, help="search for UUID(s)")
@click.pass_obj
@click.pass_context
def query(ctx, cli_obj, keyword, person, album, uuid):
    """ query the Photos database using 1 or more search options """
    photos = cli_obj.photosdb.photos(
        keywords=keyword, persons=person, albums=album, uuid=uuid
    )
    print(photos)
    pass


@cli.command()
@click.argument("topic", default=None, required=False, nargs=1)
@click.pass_context
def help(ctx, topic, **kw):
    """ print help; for help on commands: help <command> """
    if topic is None:
        print(ctx.parent.get_help())
    else:
        print(cli.commands[topic].get_help(ctx))


if __name__ == "__main__":
    cli()
