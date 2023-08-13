"""Search through a sqlite database file for a given string"""

import re
import sqlite3
from typing import Generator, List

__all__ = ["sqlgrep"]


def sqlgrep(
    filename: str,
    pattern: str,
    ignore_case: bool = False,
    print_filename: bool = True,
    rich_markup: bool = False,
) -> Generator[List[str], None, None]:
    """grep through a sqlite database file for a given string

    Args:
        filename (str): The filename of the sqlite database file
        pattern (str): The pattern to search for
        ignore_case (bool, optional): Ignore case when searching. Defaults to False.
        print_filename (bool, optional): include the filename of the file with table name. Defaults to True.
        rich_markup (bool, optional): Add rich markup to mark found text in bold. Defaults to False.

    Returns:
        Generator which yields list of [table, column, row_id, value]
    """
    flags = re.IGNORECASE if ignore_case else 0
    try:
        with sqlite3.connect(f"file:{filename}?mode=ro", uri=True) as conn:
            regex = re.compile(f"({pattern})", flags=flags)
            filename_header = f"{filename}: " if print_filename else ""
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for tablerow in cursor.fetchall():
                table = tablerow[0]
                cursor.execute("SELECT * FROM {t}".format(t=table))
                for row_num, row in enumerate(cursor):
                    for field in row.keys():
                        field_value = row[field]
                        if not field_value or isinstance(field_value, bytes):
                            # don't search binary blobs
                            next
                        field_value = str(field_value)
                        if re.search(pattern, field_value, flags=flags):
                            if rich_markup:
                                field_value = regex.sub(r"[bold]\1[/bold]", field_value)
                            yield [
                                f"{filename_header}{table}",
                                field,
                                str(row_num),
                                field_value,
                            ]
    except sqlite3.DatabaseError as e:
        raise sqlite3.DatabaseError(f"{filename}: {e}") from e
