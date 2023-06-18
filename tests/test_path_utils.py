""" Test path_utils.py """

from osxphotos._constants import _OSXPHOTOS_LOCK_EXTENSION, MAX_FILENAME_LEN
from osxphotos.path_utils import sanitize_filename


def test_sanitize_filename():
    # basic sanitize
    filenames = {
        "Foobar.txt": "Foobar.txt",
        "Foo:bar.txt": "Foo:bar.txt",
        "Foo/bar.txt": "Foo:bar.txt",
        "Foo//.txt": "Foo::.txt",
    }
    for filename, sanitized in filenames.items():
        filename = sanitize_filename(filename)
        assert filename == sanitized

    # sanitize with replacement
    filenames = {
        "Foobar.txt": "Foobar.txt",
        "Foo:bar.txt": "Foo:bar.txt",
        "Foo/bar.txt": "Foo_bar.txt",
        "Foo//.txt": "Foo__.txt",
    }
    for filename, sanitized in filenames.items():
        filename = sanitize_filename(filename, replacement="_")
        assert filename == sanitized

    # filename too long
    filename = "foo" + "x" * 512
    new_filename = sanitize_filename(filename)
    assert len(new_filename) == MAX_FILENAME_LEN
    assert new_filename == "foo" + "x" * (252 - len(_OSXPHOTOS_LOCK_EXTENSION))

    # filename too long with extension
    filename = "x" * 512 + ".jpeg"
    new_filename = sanitize_filename(filename)
    assert len(new_filename) == MAX_FILENAME_LEN
    assert new_filename == "x" * (250 - len(_OSXPHOTOS_LOCK_EXTENSION)) + ".jpeg"

    # more than one extension
    filename = "foo.bar" + "x" * 255 + ".foo.bar.jpeg"
    new_filename = sanitize_filename(filename)
    assert len(new_filename) == MAX_FILENAME_LEN
    assert (
        new_filename
        == "foo.bar" + "x" * (243 - len(_OSXPHOTOS_LOCK_EXTENSION)) + ".jpeg"
    )

    # shorter than drop count
    filename = "foo." + "x" * 256
    new_filename = sanitize_filename(filename)
    assert len(new_filename) == MAX_FILENAME_LEN
    assert new_filename == "foo." + "x" * (251 - len(_OSXPHOTOS_LOCK_EXTENSION))


def test_sanitize_dirname():
    from osxphotos._constants import MAX_DIRNAME_LEN
    from osxphotos.path_utils import sanitize_dirname

    # basic sanitize
    dirnames = {
        "Foobar": "Foobar",
        "Foo:bar": "Foo:bar",
        "Foo/bar": "Foo:bar",
        "Foo//": "Foo::",
    }
    for dirname, sanitized in dirnames.items():
        dirname = sanitize_dirname(dirname)
        assert dirname == sanitized

    # sanitize with replacement
    dirnames = {
        "Foobar": "Foobar",
        "Foo:bar": "Foo:bar",
        "Foo/bar": "Foo_bar",
        "Foo//": "Foo__",
    }
    for dirname, sanitized in dirnames.items():
        dirname = sanitize_dirname(dirname, replacement="_")
        assert dirname == sanitized

    # dirname too long
    dirname = "foo" + "x" * 512 + "bar"
    new_dirname = sanitize_dirname(dirname)
    assert len(new_dirname) == MAX_DIRNAME_LEN
    assert new_dirname == "foo" + "x" * 252


def test_sanitize_pathpart():
    from osxphotos._constants import MAX_DIRNAME_LEN
    from osxphotos.path_utils import sanitize_pathpart

    # basic sanitize
    dirnames = {
        "Foobar": "Foobar",
        "Foo:bar": "Foo:bar",
        "Foo/bar": "Foo:bar",
        "Foo//": "Foo::",
    }
    for dirname, sanitized in dirnames.items():
        dirname = sanitize_pathpart(dirname)
        assert dirname == sanitized

    # sanitize with replacement
    dirnames = {
        "Foobar": "Foobar",
        "Foo:bar": "Foo:bar",
        "Foo/bar": "Foo_bar",
        "Foo//": "Foo__",
    }
    for dirname, sanitized in dirnames.items():
        dirname = sanitize_pathpart(dirname, replacement="_")
        assert dirname == sanitized

    # dirname too long
    dirname = "foo" + "x" * 512 + "bar"
    new_dirname = sanitize_pathpart(dirname)
    assert len(new_dirname) == MAX_DIRNAME_LEN
    assert new_dirname == "foo" + "x" * 252
