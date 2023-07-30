""" Test match with non-string arguments. """

import io
import pathlib
import unittest
import unittest.mock

import osxphotos.gitignorefile


class TestMatchNonStr(unittest.TestCase):
    """Test match with non-string arguments."""

    def test_simple_base_path(self):
        """Test non-str pathlike arguments for base_path"""
        matches = self.__parse_gitignore_string(
            ["__pycache__/", "*.py[cod]"], mock_base_path=pathlib.Path("/home/michael")
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/main.py", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/main.pyc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/dir/main.pyc", is_dir=is_dir))
        self.assertFalse(matches("/home/michael/__pycache__", is_dir=False))
        self.assertTrue(matches("/home/michael/__pycache__", is_dir=True))

    def test_simple_matches(self):
        """Test non-str pathlike arguments for match"""
        matches = self.__parse_gitignore_string(
            ["__pycache__/", "*.py[cod]"], mock_base_path=pathlib.Path("/home/michael")
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(
                    matches(pathlib.Path("/home/michael/main.py"), is_dir=is_dir)
                )
                self.assertTrue(
                    matches(pathlib.Path("/home/michael/main.pyc"), is_dir=is_dir)
                )
                self.assertTrue(
                    matches(pathlib.Path("/home/michael/dir/main.pyc"), is_dir=is_dir)
                )
        self.assertFalse(
            matches(pathlib.Path("/home/michael/__pycache__"), is_dir=False)
        )
        self.assertTrue(matches(pathlib.Path("/home/michael/__pycache__"), is_dir=True))

    def __parse_gitignore_string(self, data, mock_base_path):
        with unittest.mock.patch(
            "builtins.open", lambda _: io.StringIO("\n".join(data))
        ):
            return osxphotos.gitignorefile.parse(
                f"{mock_base_path}/.gitignore", base_path=mock_base_path
            )
