"""Test sqlitekvstore"""

import gzip
import json
import pickle
import sqlite3
from typing import Any

import pytest

from osxphotos.sqlitekvstore import SQLiteKVStore


def pickle_and_zip(data: Any) -> bytes:
    """
    Pickle and gzip data.

    Args:
        data: data to pickle and gzip (must be pickle-able)

    Returns:
        bytes of gzipped pickled data
    """
    pickled = pickle.dumps(data)
    return gzip.compress(pickled)


def unzip_and_unpickle(data: bytes) -> Any:
    """
    Unzip and unpickle data.

    Args:
        data: data to unzip and unpickle

    Returns:
        unpickled data
    """
    return pickle.loads(gzip.decompress(data))


def test_basic_get_set(tmpdir):
    """Test basic functionality"""
    dbpath = tmpdir / "kvtest.db"
    kvstore = SQLiteKVStore(dbpath)
    kvstore.set("foo", "bar")
    assert kvstore.get("foo") == "bar"
    assert kvstore.get("FOOBAR") is None
    kvstore.delete("foo")
    assert kvstore.get("foo") is None
    kvstore.set("baz", None)
    assert kvstore.get("baz") is None

    kvstore.close()

    # verify that the connection is closed
    conn = kvstore.connection()
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("PRAGMA user_version;")


def test_basic_get_set_wal(tmpdir):
    """Test basic functionality with WAL mode"""
    dbpath = tmpdir / "kvtest.db"
    kvstore = SQLiteKVStore(dbpath, wal=True)
    kvstore.set("foo", "bar")
    assert kvstore.get("foo") == "bar"
    assert kvstore.get("FOOBAR") is None
    kvstore.delete("foo")
    assert kvstore.get("foo") is None
    kvstore.set("baz", None)
    assert kvstore.get("baz") is None

    kvstore.vacuum()

    kvstore.close()

    # verify that the connection is closed
    conn = kvstore.connection()
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("PRAGMA user_version;")


def test_set_many(tmpdir):
    """Test set_many()"""
    dbpath = tmpdir / "kvtest.db"

    kvstore = SQLiteKVStore(dbpath)
    kvstore.set_many([("foo", "bar"), ("baz", "qux")])
    assert kvstore.get("foo") == "bar"
    assert kvstore.get("baz") == "qux"
    kvstore.close()

    # make sure values got committed
    kvstore = SQLiteKVStore(dbpath)
    assert kvstore.get("foo") == "bar"
    assert kvstore.get("baz") == "qux"
    kvstore.close()


def test_set_many_dict(tmpdir):
    """Test set_many() with dict of values"""
    dbpath = tmpdir / "kvtest.db"

    kvstore = SQLiteKVStore(dbpath)
    kvstore.set_many({"foo": "bar", "baz": "qux"})
    assert kvstore.get("foo") == "bar"
    assert kvstore.get("baz") == "qux"
    kvstore.close()

    # make sure values got committed
    kvstore = SQLiteKVStore(dbpath)
    assert kvstore.get("foo") == "bar"
    assert kvstore.get("baz") == "qux"
    kvstore.close()


def test_basic_context_handler(tmpdir):
    """Test basic functionality with context handler"""

    dbpath = tmpdir / "kvtest.db"
    with SQLiteKVStore(dbpath) as kvstore:
        kvstore.set("foo", "bar")
        assert kvstore.get("foo") == "bar"
        assert kvstore.get("FOOBAR") is None
        kvstore.delete("foo")
        assert kvstore.get("foo") is None

    # verify that the connection is closed
    conn = kvstore.connection()
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("PRAGMA user_version;")


def test_about(tmpdir):
    """Test about property"""
    dbpath = tmpdir / "kvtest.db"
    with SQLiteKVStore(dbpath) as kvstore:
        kvstore.about = "My description"
        assert kvstore.about == "My description"
        kvstore.about = "My new description"
        assert kvstore.about == "My new description"


def test_existing_db(tmpdir):
    """Test that opening an existing database works as expected"""
    dbpath = tmpdir / "kvtest.db"
    with SQLiteKVStore(dbpath) as kvstore:
        kvstore.set("foo", "bar")

    with SQLiteKVStore(dbpath) as kvstore:
        assert kvstore.get("foo") == "bar"


def test_dict_interface(tmpdir):
    """ "Test dict interface"""
    dbpath = tmpdir / "kvtest.db"
    with SQLiteKVStore(dbpath) as kvstore:
        kvstore["foo"] = "bar"
        assert kvstore["foo"] == "bar"
        assert len(kvstore) == 1
        assert kvstore.get("foo") == "bar"

        assert "foo" in kvstore
        assert "FOOBAR" not in kvstore

        assert kvstore.pop("foo") == "bar"
        assert kvstore.get("foo") is None

        kvstore["❤️"] = "💖"
        assert kvstore["❤️"] == "💖"
        assert kvstore.get("❤️") == "💖"

        del kvstore["❤️"]
        assert kvstore.get("❤️") is None

        with pytest.raises(KeyError):
            kvstore["baz"]

        with pytest.raises(KeyError):
            del kvstore["notakey"]

        with pytest.raises(KeyError):
            kvstore.pop("foo")


def test_serialize_deserialize(tmpdir):
    """Test serialize/deserialize"""
    dbpath = tmpdir / "kvtest.db"
    kvstore = SQLiteKVStore(dbpath, serialize=json.dumps, deserialize=json.loads)
    kvstore.set("foo", {"bar": "baz"})
    assert kvstore.get("foo") == {"bar": "baz"}
    assert kvstore.get("FOOBAR") is None


def test_serialize_deserialize_binary_data(tmpdir):
    """Test serialize/deserialize with binary data"""
    dbpath = tmpdir / "kvtest.db"
    kvstore = SQLiteKVStore(
        dbpath, serialize=pickle_and_zip, deserialize=unzip_and_unpickle
    )
    kvstore.set("foo", {"bar": "baz"})
    assert kvstore.get("foo") == {"bar": "baz"}
    assert kvstore.get("FOOBAR") is None


def test_serialize_deserialize_bad_callable(tmpdir):
    """Test serialize/deserialize with bad values"""
    dbpath = tmpdir / "kvtest.db"
    with pytest.raises(TypeError):
        SQLiteKVStore(dbpath, serialize=1, deserialize=None)

    with pytest.raises(TypeError):
        SQLiteKVStore(dbpath, serialize=None, deserialize=1)


def test_iter(tmpdir):
    """Test generator behavior"""
    dbpath = tmpdir / "kvtest.db"
    kvstore = SQLiteKVStore(dbpath)
    kvstore.set("foo", "bar")
    kvstore.set("baz", "qux")
    kvstore.set("quux", "corge")
    kvstore.set("grault", "garply")
    assert len(kvstore) == 4
    assert sorted(iter(kvstore)) == ["baz", "foo", "grault", "quux"]


def test_keys_values_items(tmpdir):
    """Test keys, values, items"""
    dbpath = tmpdir / "kvtest.db"
    kvstore = SQLiteKVStore(dbpath)
    kvstore.set("foo", "bar")
    kvstore.set("baz", "qux")
    kvstore.set("quux", "corge")
    kvstore.set("grault", "garply")
    assert sorted(kvstore.keys()) == ["baz", "foo", "grault", "quux"]
    assert sorted(kvstore.values()) == ["bar", "corge", "garply", "qux"]
    assert sorted(kvstore.items()) == [
        ("baz", "qux"),
        ("foo", "bar"),
        ("grault", "garply"),
        ("quux", "corge"),
    ]


def test_path(tmpdir):
    """Test path property"""
    dbpath = tmpdir / "kvtest.db"
    kvstore = SQLiteKVStore(dbpath)
    assert kvstore.path == dbpath


def test_wipe(tmpdir):
    """Test wipe"""
    dbpath = tmpdir / "kvtest.db"
    kvstore = SQLiteKVStore(dbpath)
    kvstore.set("foo", "bar")
    kvstore.set("baz", "qux")
    kvstore.set("quux", "corge")
    kvstore.set("grault", "garply")
    assert len(kvstore) == 4
    kvstore.wipe()
    assert len(kvstore) == 0
    assert "foo"
    kvstore.set("foo", "bar")
    assert kvstore.get("foo") == "bar"
