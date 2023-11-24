"""Test tempdir module."""

from osxphotos.tempdir import cleanup, tempdir


def test_tempdir():
    """Test tempdir() and cleanup()"""
    tmp = tempdir()
    assert tmp.exists()

    tmp2 = tempdir()
    assert tmp2.exists()

    assert tmp == tmp2

    cleanup()
    assert not tmp.exists()


def test_tempdir():
    """Test tempdir() and cleanup() with subdir"""
    tmp = tempdir("foo")
    assert tmp.exists()

    tmp2 = tempdir("foo")
    assert tmp2.exists()

    assert tmp == tmp2

    cleanup()
    assert not tmp.exists()
