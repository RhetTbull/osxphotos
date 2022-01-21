"""Build sql queries from template to retrieve info from the database"""

import os.path
import pathlib
from functools import lru_cache

from mako.template import Template

from ._constants import _DB_TABLE_NAMES

__all__ = ["get_query"]

QUERY_DIR = os.path.join(os.path.dirname(__file__), "queries")


def get_query(query_name, photos_ver, **kwargs):
    """Return sqlite query string for an attribute and a given database version"""

    # there can be a single query for multiple database versions or separate queries for each version
    # try generic version first (most common case), if that fails, look for version specific query
    query_string = _get_query_string(query_name, photos_ver)
    asset_table = _DB_TABLE_NAMES[photos_ver]["ASSET"]
    query_template = Template(query_string)
    return query_template.render(asset_table=asset_table, **kwargs)


@lru_cache(maxsize=None)
def _get_query_string(query_name, photos_ver):
    """Return sqlite query string for an attribute and a given database version"""
    query_file = pathlib.Path(QUERY_DIR) / f"{query_name}.sql.mako"
    if not query_file.is_file():
        query_file = pathlib.Path(QUERY_DIR) / f"{query_name}_{photos_ver}.sql.mako"
        if not query_file.is_file():
            raise FileNotFoundError(f"Query file '{query_file}' not found")

    with open(query_file, "r") as f:
        query_string = f.read()
    return query_string
