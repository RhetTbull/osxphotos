import io
import os
import sys
import tempfile
import unittest
import unittest.mock

import osxphotos.gitignorefile


class TestMatch(unittest.TestCase):
    def test_simple(self):
        matches = self.__parse_gitignore_string(
            ["__pycache__/", "*.py[cod]"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/main.py", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/main.pyc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/dir/main.pyc", is_dir=is_dir))
        self.assertFalse(matches("/home/michael/__pycache__", is_dir=False))
        self.assertTrue(matches("/home/michael/__pycache__", is_dir=True))

    def test_simple_without_trailing_slash(self):
        matches = self.__parse_gitignore_string(
            ["__pycache__", "*.py[cod]"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/main.py", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/main.pyc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/dir/main.pyc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/__pycache__", is_dir=is_dir))

    def test_wildcard(self):
        matches = self.__parse_gitignore_string(
            ["hello.*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/hello.txt", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/hello.foobar", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/dir/hello.txt", is_dir=is_dir))
                if (
                    os.name != "nt"
                ):  # Invalid paths on Windows will be normalized in `os.path.abspath`.
                    self.assertTrue(matches("/home/michael/hello.", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/hello", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/helloX", is_dir=is_dir))

    def test_anchored_wildcard(self):
        matches = self.__parse_gitignore_string(
            ["/hello.*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/hello.txt", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/hello.c", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/a/hello.java", is_dir=is_dir))

    def test_outside_of_base_path(self):
        matches = self.__parse_gitignore_string(
            ["/hello.*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/heather/hello.txt", is_dir=is_dir))
                self.assertFalse(matches("/home/heather/hello.c", is_dir=is_dir))

    def test_trailingspaces(self):
        matches = self.__parse_gitignore_string(
            [
                "ignoretrailingspace ",
                "notignoredspace\\ ",
                "partiallyignoredspace\\  ",
                "partiallyignoredspace2 \\  ",
                "notignoredmultiplespace\\ \\ \\ ",
            ],
            mock_base_path="/home/michael",
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(
                    matches("/home/michael/ignoretrailingspace", is_dir=is_dir)
                )
                if (
                    os.name != "nt"
                ):  # Invalid paths on Windows will be normalized in `os.path.abspath`.
                    self.assertFalse(
                        matches("/home/michael/ignoretrailingspace ", is_dir=is_dir)
                    )
                    self.assertTrue(
                        matches("/home/michael/partiallyignoredspace ", is_dir=is_dir)
                    )
                    self.assertFalse(
                        matches("/home/michael/partiallyignoredspace  ", is_dir=is_dir)
                    )
                    self.assertTrue(
                        matches("/home/michael/partiallyignoredspace2  ", is_dir=is_dir)
                    )
                    self.assertFalse(
                        matches(
                            "/home/michael/partiallyignoredspace2   ", is_dir=is_dir
                        )
                    )
                    self.assertFalse(
                        matches("/home/michael/partiallyignoredspace2 ", is_dir=is_dir)
                    )
                    self.assertTrue(
                        matches("/home/michael/notignoredspace ", is_dir=is_dir)
                    )
                    self.assertTrue(
                        matches(
                            "/home/michael/notignoredmultiplespace   ", is_dir=is_dir
                        )
                    )
                self.assertFalse(
                    matches("/home/michael/partiallyignoredspace", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/michael/partiallyignoredspace2", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/michael/notignoredspace", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/michael/notignoredmultiplespace", is_dir=is_dir)
                )

    def test_comment(self):
        matches = self.__parse_gitignore_string(
            ["somematch", "#realcomment", "othermatch", "\\#imnocomment"],
            mock_base_path="/home/michael",
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/somematch", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/#realcomment", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/othermatch", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/#imnocomment", is_dir=is_dir))

    def test_second_level_directories(self):
        """
        For example, a pattern `doc/frotz/` matches `doc/frotz` directory, but not `a/doc/frotz` directory;
        however `frotz/` matches `frotz` and `a/frotz` that is a directory (all paths are relative from the
        `.gitignore` file). See https://git-scm.com/docs/gitignore .
        """
        matches = self.__parse_gitignore_string(
            ["doc/frotz/"], mock_base_path="/home/michael"
        )
        self.assertFalse(matches("/home/michael/doc/frotz", is_dir=False))
        self.assertTrue(matches("/home/michael/doc/frotz", is_dir=True))
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/a/doc/frotz", is_dir=is_dir))

    def test_second_level_directories_unchained(self):
        matches = self.__parse_gitignore_string(
            ["**/doc/frotz/"], mock_base_path="/home/michael"
        )
        self.assertFalse(matches("/home/michael/doc/frotz", is_dir=False))
        self.assertTrue(matches("/home/michael/doc/frotz", is_dir=True))
        self.assertFalse(matches("/home/michael/a/doc/frotz", is_dir=False))
        self.assertTrue(matches("/home/michael/a/doc/frotz", is_dir=True))
        self.assertFalse(matches("/home/michael/a/b/doc/frotz", is_dir=False))
        self.assertTrue(matches("/home/michael/a/b/doc/frotz", is_dir=True))
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/doc/frotz/file", is_dir=False))
                self.assertTrue(matches("/home/michael/doc/frotz/file", is_dir=True))
                self.assertTrue(matches("/home/michael/a/doc/frotz/file", is_dir=False))
                self.assertTrue(matches("/home/michael/a/doc/frotz/file", is_dir=True))
                self.assertTrue(
                    matches("/home/michael/a/b/doc/frotz/file", is_dir=False)
                )
                self.assertTrue(
                    matches("/home/michael/a/b/doc/frotz/file", is_dir=True)
                )

    def test_second_level_files(self):
        matches = self.__parse_gitignore_string(
            ["doc/frotz"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/doc/frotz", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/a/doc/frotz", is_dir=is_dir))

    def test_ignore_file(self):
        matches = self.__parse_gitignore_string(
            [".venv"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/.venv", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/.venv/folder", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/.venv/file.txt", is_dir=is_dir))

    def test_ignore_core_file(self):
        matches = self.__parse_gitignore_string(
            ["core", "!core/"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/core/a", is_dir=is_dir))
        self.assertTrue(matches("/home/michael/core", is_dir=False))
        self.assertFalse(matches("/home/michael/core", is_dir=True))
        self.assertTrue(matches("/home/michael/a/core", is_dir=False))
        self.assertFalse(matches("/home/michael/a/core", is_dir=True))

    def test_ignore_directory(self):
        matches = self.__parse_gitignore_string(
            [".venv/"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/.venv/folder", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/.venv/file.txt", is_dir=is_dir))
        self.assertFalse(matches("/home/michael/.venv", is_dir=False))
        self.assertTrue(matches("/home/michael/.venv", is_dir=True))

    def test_ignore_directory_greedy(self):
        matches = self.__parse_gitignore_string(
            [".venv"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/.venvlol", is_dir=is_dir))

    def test_ignore_file_greedy(self):
        matches = self.__parse_gitignore_string(
            [".venv/"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/.venvlol", is_dir=is_dir))

    def test_ignore_directory_asterisk(self):
        matches = self.__parse_gitignore_string(
            [".venv/*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/.venv", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/.venv/folder", is_dir=is_dir))

    def test_negation(self):
        matches = self.__parse_gitignore_string(
            ["*.ignore", "!keep.ignore"],
            mock_base_path="/home/michael",
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/trash.ignore", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/keep.ignore", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/waste.ignore", is_dir=is_dir))

    def test_double_asterisks(self):
        matches = self.__parse_gitignore_string(
            ["foo/**/Bar"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/foo/hello/Bar", is_dir=is_dir))
                self.assertTrue(
                    matches("/home/michael/foo/hello/world/Bar", is_dir=is_dir)
                )
                self.assertTrue(matches("/home/michael/foo/world/Bar", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/foo/Bar", is_dir=is_dir))

    def test_single_asterisk(self):
        matches = self.__parse_gitignore_string(["*"], mock_base_path="/home/michael")
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/file.txt", is_dir=is_dir))
                self.assertTrue(
                    matches("/home/michael/directory/file.txt", is_dir=is_dir)
                )

    def test_spurious_matches(self):
        matches = self.__parse_gitignore_string(["abc"], mock_base_path="/home/michael")
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/abc.txt", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/file-abc.txt", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/fileabc", is_dir=is_dir))
                self.assertFalse(
                    matches("/home/michael/directoryabc-trailing", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/michael/abc-suffixed/file.txt", is_dir=is_dir)
                )
                self.assertFalse(matches("/home/michael/subdir/abc.txt", is_dir=is_dir))
                self.assertFalse(
                    matches("/home/michael/subdir/directoryabc", is_dir=is_dir)
                )
                self.assertFalse(
                    matches(
                        "/home/michael/subdir/directory-abc-trailing", is_dir=is_dir
                    )
                )
                self.assertFalse(
                    matches(
                        "/home/michael/subdir/directory-abc-trailing/file.txt",
                        is_dir=is_dir,
                    )
                )

    def test_spurious_matches_with_asterisks(self):
        matches = self.__parse_gitignore_string(
            ["xyz/**/abc"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/xyz/uvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyz/uvwabc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvwabc", is_dir=is_dir))

    def test_double_asterisks_start(self):
        matches = self.__parse_gitignore_string(
            ["**/abc"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/xyz/uvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyz/uvwabc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/xyzuvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvwabc", is_dir=is_dir))

    def test_double_asterisks_end(self):
        matches = self.__parse_gitignore_string(
            ["xyz/**"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/xyz/uvw/abc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/xyz/uvwabc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvwabc", is_dir=is_dir))

    def test_single_asterisk_start(self):
        matches = self.__parse_gitignore_string(
            ["*/abc"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/xyz/uvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyz/uvwabc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/xyzuvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvwabc", is_dir=is_dir))

    def test_single_asterisk_end(self):
        matches = self.__parse_gitignore_string(
            ["xyz/*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/xyz/uvw/abc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/xyz/uvwabc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvwabc", is_dir=is_dir))

    def test_does_not_fail_with_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            matches = self.__parse_gitignore_string(["*.venv"], mock_base_path=d)
            os.makedirs(f"{d}/.venv/bin")
            os.symlink(sys.executable, f"{d}/.venv/bin/python")
            self.assertTrue(matches(f"{d}/.venv/bin/python"))

    def test_single_letter(self):
        matches = self.__parse_gitignore_string(["a"], mock_base_path="/home/michael")
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/a", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/b", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/b/a", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/a/b", is_dir=is_dir))

    def test_exclude_directories(self):
        matches = self.__parse_gitignore_string(
            ["*.yaml", "!*.yaml/"], mock_base_path="/home/michael"
        )
        self.assertTrue(matches("/home/michael/file.yaml", is_dir=False))
        self.assertFalse(matches("/home/michael/file.yaml", is_dir=True))
        self.assertFalse(matches("/home/michael/dir.yaml/file.sql", is_dir=False))

    def test_excludes_nested(self):
        matches = self.__parse_gitignore_string(
            ["/*", "!/foo", "/foo/*", "!/foo/bar"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/oo", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/foo", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/foo/ar", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/foo/bar", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/foo/bar/hey", is_dir=is_dir))

    def test_excludes_direct(self):
        matches = self.__parse_gitignore_string(
            ["/*", "!/foo/bar"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/oo", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/foo", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/foo/ar", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/foo/bar", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/foo/bar/hey", is_dir=is_dir))

    def test_exclude_from_subdirectory(self):
        matches = self.__parse_gitignore_string(
            ["*.log", "!important/*.log", "trace.*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/a.log", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/b.txt", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/important", is_dir=is_dir))
                self.assertFalse(
                    matches("/home/michael/important/d.log", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/michael/important/e.txt", is_dir=is_dir)
                )
                self.assertTrue(matches("/home/michael/trace.c", is_dir=is_dir))

    def test_ignore_all_subdirectories(self):
        matches = self.__parse_gitignore_string(["**/"], mock_base_path="/home/michael")
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/directory/file", is_dir=is_dir))
        self.assertFalse(matches("/home/michael/file.txt", is_dir=False))
        self.assertTrue(matches("/home/michael/directory", is_dir=True))

    def test_robert_simple_rules(self):
        matches = self.__parse_gitignore_string(
            ["__pycache__", "*.py[cod]", ".venv/"], mock_base_path="/home/robert"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/robert/main.py", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/dir/main.pyc", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/__pycache__", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/.venv/folder", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/.venv/file.txt", is_dir=is_dir))
                self.assertTrue(
                    matches("/home/robert/.venv/folder/file.txt", is_dir=is_dir)
                )
                self.assertTrue(
                    matches("/home/robert/.venv/folder/folder", is_dir=is_dir)
                )
        self.assertTrue(matches("/home/robert/.venv", is_dir=True))
        self.assertFalse(matches("/home/robert/.venv", is_dir=False))

    def test_robert_comments(self):
        matches = self.__parse_gitignore_string(
            ["somematch", "#realcomment", "othermatch", "\\#imnocomment"],
            mock_base_path="/home/robert",
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/robert/somematch", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/#realcomment", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/othermatch", is_dir=is_dir))
                self.assertFalse(matches("/home/robert", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/\\", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/#imnocomment", is_dir=is_dir))

    def test_robert_wildcard(self):
        matches = self.__parse_gitignore_string(
            ["hello.*"], mock_base_path="/home/robert"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/robert/hello.txt", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/dir/hello.txt", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/dir/shello.txt", is_dir=is_dir))
                if (
                    os.name != "nt"
                ):  # Invalid paths on Windows will be normalized in `os.path.abspath`.
                    self.assertTrue(matches("/home/robert/dir/hello.", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/dir/hello", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/dir/helloX", is_dir=is_dir))

    def test_robert_anchored_wildcard(self):
        matches = self.__parse_gitignore_string(
            ["/hello.*"], mock_base_path="/home/robert"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/robert/hello.txt", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/hello.c", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/a/hello.java", is_dir=is_dir))

    def test_robert_negation_rules(self):
        matches = self.__parse_gitignore_string(
            ["*.ignore", "!keep.ignore"], mock_base_path="/home/robert"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/robert/trash.ignore", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/whatever.ignore", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/keep.ignore", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/!keep.ignore", is_dir=is_dir))

    def test_robert_match_does_not_resolve_symlinks(self):
        """Test match on files under symlinked directories
        This mimics how virtual environment sets up the .venv directory by
        symlinking to an interpreter. This test is to ensure that the symlink is
        being ignored (matched) correctly.
        """
        with tempfile.TemporaryDirectory() as d:
            matches = self.__parse_gitignore_string(["*.venv"], mock_base_path=d)
            os.makedirs(f"{d}/.venv/bin")
            os.symlink(sys.executable, f"{d}/.venv/bin/python")
            for is_dir in (False, True):
                with self.subTest(i=is_dir):
                    self.assertTrue(matches(f"{d}/.venv", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/.venv/", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/.venv/bin", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/.venv/bin/", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/.venv/bin/python", is_dir=is_dir))
                    self.assertFalse(matches(f"{d}/.venv2", is_dir=is_dir))
                    self.assertFalse(matches(f"{d}/.venv2/", is_dir=is_dir))
                    self.assertFalse(matches(f"{d}/.venv2/bin", is_dir=is_dir))
                    self.assertFalse(matches(f"{d}/.venv2/bin/", is_dir=is_dir))
                    self.assertFalse(matches(f"{d}/.venv2/bin/python", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/a.venv", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/a.venv/", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/a.venv/bin", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/a.venv/bin/", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/a.venv/bin/python", is_dir=is_dir))

    def test_robert_match_files_under_symlink(self):
        # FIXME What's going on?
        """
        see: https://git-scm.com/docs/gitignore#_pattern_format
        The pattern foo/ will match a directory foo and paths underneath it,
        but will not match a regular file or a symbolic link foo
        (this is consistent with the way how pathspec works in general in Git)
        """
        pass

    def test_robert_handle_base_directories_with_a_symlink_in_their_components(self):
        """
        See https://github.com/bitranox/igittigitt/issues/28 .
        """
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(f"{d}/igittigitt01")
            os.symlink(
                f"{d}/igittigitt01",
                f"{d}/symlink_to_igittigitt01",
                target_is_directory=True,
            )

            matches = self.__parse_gitignore_string(
                ["*.txt"], mock_base_path=f"{d}/symlink_to_igittigitt01"
            )

            for is_dir in (False, True):
                with self.subTest(i=is_dir):
                    self.assertTrue(
                        matches(f"{d}/symlink_to_igittigitt01/file.txt", is_dir=is_dir)
                    )
                    self.assertFalse(
                        matches(f"{d}/symlink_to_igittigitt01/file.png", is_dir=is_dir)
                    )

            for path in (
                f"{d}/symlink_to_igittigitt01/file.txt",
                f"{d}/symlink_to_igittigitt01/file.png",
            ):
                with open(path, "w"):
                    pass

            self.assertTrue(matches(f"{d}/symlink_to_igittigitt01/file.txt"))
            self.assertFalse(matches(f"{d}/symlink_to_igittigitt01/file.png"))

    def test_robert_parse_rule_files(self):
        matches = self.__parse_gitignore_string(
            [
                "test__pycache__",
                "*.py[cod]",
                ".test_venv/",
                ".test_venv/**",
                ".test_venv/*",
                "!test_inverse",
                "!hello.pyc",
            ],
            mock_base_path="/home/robert",
        )

        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/robert/test__pycache__", is_dir=is_dir))
                self.assertTrue(
                    matches(
                        "/home/robert/test__pycache__/.test_gitignore", is_dir=is_dir
                    )
                )
                self.assertTrue(
                    matches("/home/robert/test__pycache__/excluded", is_dir=is_dir)
                )
                self.assertTrue(
                    matches(
                        "/home/robert/test__pycache__/excluded/excluded", is_dir=is_dir
                    )
                )
                self.assertTrue(
                    matches(
                        "/home/robert/test__pycache__/excluded/excluded/excluded.txt",
                        is_dir=is_dir,
                    )
                )
                # This file will actually be ignored by Git because it won't go into ignored directory
                # `test__pycache__` while globbing. If you are globbing through the directory tree, check that parent
                # directory is not ignored (`!/foo`, `/foo/*`, `!/foo/bar`) and if it is, don't call `matches` on
                # nested file.
                self.assertFalse(
                    matches(
                        "/home/robert/test__pycache__/excluded/excluded/test_inverse"
                    )
                )
                self.assertFalse(matches("/home/robert/hello.pyc"))
                self.assertTrue(
                    matches("/home/robert/test__pycache__/some_file.txt", is_dir=is_dir)
                )
                self.assertTrue(
                    matches("/home/robert/test__pycache__/test", is_dir=is_dir)
                )
                self.assertFalse(matches("/home/robert/.test_gitignore", is_dir=is_dir))
                self.assertTrue(
                    matches("/home/robert/.test_venv/some_file.txt", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded.txt", is_dir=is_dir)
                )
                self.assertFalse(matches("/home/robert/not_excluded", is_dir=is_dir))
                self.assertTrue(
                    matches("/home/robert/not_excluded/test__pycache__", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded/.test_gitignore", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded/excluded_not", is_dir=is_dir)
                )
                self.assertFalse(
                    matches(
                        "/home/robert/not_excluded/excluded_not/sub_excluded.txt",
                        is_dir=is_dir,
                    )
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded/excluded", is_dir=is_dir)
                )
                self.assertFalse(
                    matches(
                        "/home/robert/not_excluded/excluded/excluded.txt", is_dir=is_dir
                    )
                )
                self.assertFalse(
                    matches(
                        "/home/robert/not_excluded/not_excluded2.txt", is_dir=is_dir
                    )
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded/not_excluded2", is_dir=is_dir)
                )
                self.assertFalse(
                    matches(
                        "/home/robert/not_excluded/not_excluded2/sub_excluded.txt",
                        is_dir=is_dir,
                    )
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded/excluded_not.txt", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/robert/.test_gitignore_empty", is_dir=is_dir)
                )
        self.assertFalse(matches("/home/robert/.test_venv", is_dir=False))
        self.assertTrue(matches("/home/robert/.test_venv", is_dir=True))

    def __parse_gitignore_string(self, data, mock_base_path):
        with unittest.mock.patch(
            "builtins.open", lambda _: io.StringIO("\n".join(data))
        ):
            return osxphotos.gitignorefile.parse(
                f"{mock_base_path}/.gitignore", base_path=mock_base_path
            )


class TestMatchList(unittest.TestCase):
    """Test pattern_from_list"""

    def test_simple(self):
        matches = self.__parse_gitignore_string(
            ["__pycache__/", "*.py[cod]"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/main.py", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/main.pyc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/dir/main.pyc", is_dir=is_dir))
        self.assertFalse(matches("/home/michael/__pycache__", is_dir=False))
        self.assertTrue(matches("/home/michael/__pycache__", is_dir=True))

    def test_simple_without_trailing_slash(self):
        matches = self.__parse_gitignore_string(
            ["__pycache__", "*.py[cod]"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/main.py", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/main.pyc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/dir/main.pyc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/__pycache__", is_dir=is_dir))

    def test_wildcard(self):
        matches = self.__parse_gitignore_string(
            ["hello.*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/hello.txt", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/hello.foobar", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/dir/hello.txt", is_dir=is_dir))
                if (
                    os.name != "nt"
                ):  # Invalid paths on Windows will be normalized in `os.path.abspath`.
                    self.assertTrue(matches("/home/michael/hello.", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/hello", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/helloX", is_dir=is_dir))

    def test_anchored_wildcard(self):
        matches = self.__parse_gitignore_string(
            ["/hello.*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/hello.txt", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/hello.c", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/a/hello.java", is_dir=is_dir))

    def test_outside_of_base_path(self):
        matches = self.__parse_gitignore_string(
            ["/hello.*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/heather/hello.txt", is_dir=is_dir))
                self.assertFalse(matches("/home/heather/hello.c", is_dir=is_dir))

    def test_trailingspaces(self):
        matches = self.__parse_gitignore_string(
            [
                "ignoretrailingspace ",
                "notignoredspace\\ ",
                "partiallyignoredspace\\  ",
                "partiallyignoredspace2 \\  ",
                "notignoredmultiplespace\\ \\ \\ ",
            ],
            mock_base_path="/home/michael",
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(
                    matches("/home/michael/ignoretrailingspace", is_dir=is_dir)
                )
                if (
                    os.name != "nt"
                ):  # Invalid paths on Windows will be normalized in `os.path.abspath`.
                    self.assertFalse(
                        matches("/home/michael/ignoretrailingspace ", is_dir=is_dir)
                    )
                    self.assertTrue(
                        matches("/home/michael/partiallyignoredspace ", is_dir=is_dir)
                    )
                    self.assertFalse(
                        matches("/home/michael/partiallyignoredspace  ", is_dir=is_dir)
                    )
                    self.assertTrue(
                        matches("/home/michael/partiallyignoredspace2  ", is_dir=is_dir)
                    )
                    self.assertFalse(
                        matches(
                            "/home/michael/partiallyignoredspace2   ", is_dir=is_dir
                        )
                    )
                    self.assertFalse(
                        matches("/home/michael/partiallyignoredspace2 ", is_dir=is_dir)
                    )
                    self.assertTrue(
                        matches("/home/michael/notignoredspace ", is_dir=is_dir)
                    )
                    self.assertTrue(
                        matches(
                            "/home/michael/notignoredmultiplespace   ", is_dir=is_dir
                        )
                    )
                self.assertFalse(
                    matches("/home/michael/partiallyignoredspace", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/michael/partiallyignoredspace2", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/michael/notignoredspace", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/michael/notignoredmultiplespace", is_dir=is_dir)
                )

    def test_comment(self):
        matches = self.__parse_gitignore_string(
            ["somematch", "#realcomment", "othermatch", "\\#imnocomment"],
            mock_base_path="/home/michael",
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/somematch", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/#realcomment", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/othermatch", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/#imnocomment", is_dir=is_dir))

    def test_second_level_directories(self):
        """
        For example, a pattern `doc/frotz/` matches `doc/frotz` directory, but not `a/doc/frotz` directory;
        however `frotz/` matches `frotz` and `a/frotz` that is a directory (all paths are relative from the
        `.gitignore` file). See https://git-scm.com/docs/gitignore .
        """
        matches = self.__parse_gitignore_string(
            ["doc/frotz/"], mock_base_path="/home/michael"
        )
        self.assertFalse(matches("/home/michael/doc/frotz", is_dir=False))
        self.assertTrue(matches("/home/michael/doc/frotz", is_dir=True))
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/a/doc/frotz", is_dir=is_dir))

    def test_second_level_directories_unchained(self):
        matches = self.__parse_gitignore_string(
            ["**/doc/frotz/"], mock_base_path="/home/michael"
        )
        self.assertFalse(matches("/home/michael/doc/frotz", is_dir=False))
        self.assertTrue(matches("/home/michael/doc/frotz", is_dir=True))
        self.assertFalse(matches("/home/michael/a/doc/frotz", is_dir=False))
        self.assertTrue(matches("/home/michael/a/doc/frotz", is_dir=True))
        self.assertFalse(matches("/home/michael/a/b/doc/frotz", is_dir=False))
        self.assertTrue(matches("/home/michael/a/b/doc/frotz", is_dir=True))
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/doc/frotz/file", is_dir=False))
                self.assertTrue(matches("/home/michael/doc/frotz/file", is_dir=True))
                self.assertTrue(matches("/home/michael/a/doc/frotz/file", is_dir=False))
                self.assertTrue(matches("/home/michael/a/doc/frotz/file", is_dir=True))
                self.assertTrue(
                    matches("/home/michael/a/b/doc/frotz/file", is_dir=False)
                )
                self.assertTrue(
                    matches("/home/michael/a/b/doc/frotz/file", is_dir=True)
                )

    def test_second_level_files(self):
        matches = self.__parse_gitignore_string(
            ["doc/frotz"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/doc/frotz", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/a/doc/frotz", is_dir=is_dir))

    def test_ignore_file(self):
        matches = self.__parse_gitignore_string(
            [".venv"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/.venv", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/.venv/folder", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/.venv/file.txt", is_dir=is_dir))

    def test_ignore_core_file(self):
        matches = self.__parse_gitignore_string(
            ["core", "!core/"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/core/a", is_dir=is_dir))
        self.assertTrue(matches("/home/michael/core", is_dir=False))
        self.assertFalse(matches("/home/michael/core", is_dir=True))
        self.assertTrue(matches("/home/michael/a/core", is_dir=False))
        self.assertFalse(matches("/home/michael/a/core", is_dir=True))

    def test_ignore_directory(self):
        matches = self.__parse_gitignore_string(
            [".venv/"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/.venv/folder", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/.venv/file.txt", is_dir=is_dir))
        self.assertFalse(matches("/home/michael/.venv", is_dir=False))
        self.assertTrue(matches("/home/michael/.venv", is_dir=True))

    def test_ignore_directory_greedy(self):
        matches = self.__parse_gitignore_string(
            [".venv"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/.venvlol", is_dir=is_dir))

    def test_ignore_file_greedy(self):
        matches = self.__parse_gitignore_string(
            [".venv/"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/.venvlol", is_dir=is_dir))

    def test_ignore_directory_asterisk(self):
        matches = self.__parse_gitignore_string(
            [".venv/*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/.venv", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/.venv/folder", is_dir=is_dir))

    def test_negation(self):
        matches = self.__parse_gitignore_string(
            ["*.ignore", "!keep.ignore"],
            mock_base_path="/home/michael",
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/trash.ignore", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/keep.ignore", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/waste.ignore", is_dir=is_dir))

    def test_double_asterisks(self):
        matches = self.__parse_gitignore_string(
            ["foo/**/Bar"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/foo/hello/Bar", is_dir=is_dir))
                self.assertTrue(
                    matches("/home/michael/foo/hello/world/Bar", is_dir=is_dir)
                )
                self.assertTrue(matches("/home/michael/foo/world/Bar", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/foo/Bar", is_dir=is_dir))

    def test_single_asterisk(self):
        matches = self.__parse_gitignore_string(["*"], mock_base_path="/home/michael")
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/file.txt", is_dir=is_dir))
                self.assertTrue(
                    matches("/home/michael/directory/file.txt", is_dir=is_dir)
                )

    def test_spurious_matches(self):
        matches = self.__parse_gitignore_string(["abc"], mock_base_path="/home/michael")
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/abc.txt", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/file-abc.txt", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/fileabc", is_dir=is_dir))
                self.assertFalse(
                    matches("/home/michael/directoryabc-trailing", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/michael/abc-suffixed/file.txt", is_dir=is_dir)
                )
                self.assertFalse(matches("/home/michael/subdir/abc.txt", is_dir=is_dir))
                self.assertFalse(
                    matches("/home/michael/subdir/directoryabc", is_dir=is_dir)
                )
                self.assertFalse(
                    matches(
                        "/home/michael/subdir/directory-abc-trailing", is_dir=is_dir
                    )
                )
                self.assertFalse(
                    matches(
                        "/home/michael/subdir/directory-abc-trailing/file.txt",
                        is_dir=is_dir,
                    )
                )

    def test_spurious_matches_with_asterisks(self):
        matches = self.__parse_gitignore_string(
            ["xyz/**/abc"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/xyz/uvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyz/uvwabc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvwabc", is_dir=is_dir))

    def test_double_asterisks_start(self):
        matches = self.__parse_gitignore_string(
            ["**/abc"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/xyz/uvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyz/uvwabc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/xyzuvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvwabc", is_dir=is_dir))

    def test_double_asterisks_end(self):
        matches = self.__parse_gitignore_string(
            ["xyz/**"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/xyz/uvw/abc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/xyz/uvwabc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvwabc", is_dir=is_dir))

    def test_single_asterisk_start(self):
        matches = self.__parse_gitignore_string(
            ["*/abc"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/michael/xyz/uvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyz/uvwabc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/xyzuvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvwabc", is_dir=is_dir))

    def test_single_asterisk_end(self):
        matches = self.__parse_gitignore_string(
            ["xyz/*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/xyz/uvw/abc", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/xyz/uvwabc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvw/abc", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/xyzuvwabc", is_dir=is_dir))

    def test_does_not_fail_with_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            matches = self.__parse_gitignore_string(["*.venv"], mock_base_path=d)
            os.makedirs(f"{d}/.venv/bin")
            os.symlink(sys.executable, f"{d}/.venv/bin/python")
            self.assertTrue(matches(f"{d}/.venv/bin/python"))

    def test_single_letter(self):
        matches = self.__parse_gitignore_string(["a"], mock_base_path="/home/michael")
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/a", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/b", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/b/a", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/a/b", is_dir=is_dir))

    def test_exclude_directories(self):
        matches = self.__parse_gitignore_string(
            ["*.yaml", "!*.yaml/"], mock_base_path="/home/michael"
        )
        self.assertTrue(matches("/home/michael/file.yaml", is_dir=False))
        self.assertFalse(matches("/home/michael/file.yaml", is_dir=True))
        self.assertFalse(matches("/home/michael/dir.yaml/file.sql", is_dir=False))

    def test_excludes_nested(self):
        matches = self.__parse_gitignore_string(
            ["/*", "!/foo", "/foo/*", "!/foo/bar"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/oo", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/foo", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/foo/ar", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/foo/bar", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/foo/bar/hey", is_dir=is_dir))

    def test_excludes_direct(self):
        matches = self.__parse_gitignore_string(
            ["/*", "!/foo/bar"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/oo", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/foo", is_dir=is_dir))
                self.assertTrue(matches("/home/michael/foo/ar", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/foo/bar", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/foo/bar/hey", is_dir=is_dir))

    def test_exclude_from_subdirectory(self):
        matches = self.__parse_gitignore_string(
            ["*.log", "!important/*.log", "trace.*"], mock_base_path="/home/michael"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/a.log", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/b.txt", is_dir=is_dir))
                self.assertFalse(matches("/home/michael/important", is_dir=is_dir))
                self.assertFalse(
                    matches("/home/michael/important/d.log", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/michael/important/e.txt", is_dir=is_dir)
                )
                self.assertTrue(matches("/home/michael/trace.c", is_dir=is_dir))

    def test_ignore_all_subdirectories(self):
        matches = self.__parse_gitignore_string(["**/"], mock_base_path="/home/michael")
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/michael/directory/file", is_dir=is_dir))
        self.assertFalse(matches("/home/michael/file.txt", is_dir=False))
        self.assertTrue(matches("/home/michael/directory", is_dir=True))

    def test_robert_simple_rules(self):
        matches = self.__parse_gitignore_string(
            ["__pycache__", "*.py[cod]", ".venv/"], mock_base_path="/home/robert"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(matches("/home/robert/main.py", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/dir/main.pyc", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/__pycache__", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/.venv/folder", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/.venv/file.txt", is_dir=is_dir))
                self.assertTrue(
                    matches("/home/robert/.venv/folder/file.txt", is_dir=is_dir)
                )
                self.assertTrue(
                    matches("/home/robert/.venv/folder/folder", is_dir=is_dir)
                )
        self.assertTrue(matches("/home/robert/.venv", is_dir=True))
        self.assertFalse(matches("/home/robert/.venv", is_dir=False))

    def test_robert_comments(self):
        matches = self.__parse_gitignore_string(
            ["somematch", "#realcomment", "othermatch", "\\#imnocomment"],
            mock_base_path="/home/robert",
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/robert/somematch", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/#realcomment", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/othermatch", is_dir=is_dir))
                self.assertFalse(matches("/home/robert", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/\\", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/#imnocomment", is_dir=is_dir))

    def test_robert_wildcard(self):
        matches = self.__parse_gitignore_string(
            ["hello.*"], mock_base_path="/home/robert"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/robert/hello.txt", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/dir/hello.txt", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/dir/shello.txt", is_dir=is_dir))
                if (
                    os.name != "nt"
                ):  # Invalid paths on Windows will be normalized in `os.path.abspath`.
                    self.assertTrue(matches("/home/robert/dir/hello.", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/dir/hello", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/dir/helloX", is_dir=is_dir))

    def test_robert_anchored_wildcard(self):
        matches = self.__parse_gitignore_string(
            ["/hello.*"], mock_base_path="/home/robert"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/robert/hello.txt", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/hello.c", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/a/hello.java", is_dir=is_dir))

    def test_robert_negation_rules(self):
        matches = self.__parse_gitignore_string(
            ["*.ignore", "!keep.ignore"], mock_base_path="/home/robert"
        )
        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/robert/trash.ignore", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/whatever.ignore", is_dir=is_dir))
                self.assertFalse(matches("/home/robert/keep.ignore", is_dir=is_dir))
                self.assertTrue(matches("/home/robert/!keep.ignore", is_dir=is_dir))

    def test_robert_match_does_not_resolve_symlinks(self):
        """Test match on files under symlinked directories
        This mimics how virtual environment sets up the .venv directory by
        symlinking to an interpreter. This test is to ensure that the symlink is
        being ignored (matched) correctly.
        """
        with tempfile.TemporaryDirectory() as d:
            matches = self.__parse_gitignore_string(["*.venv"], mock_base_path=d)
            os.makedirs(f"{d}/.venv/bin")
            os.symlink(sys.executable, f"{d}/.venv/bin/python")
            for is_dir in (False, True):
                with self.subTest(i=is_dir):
                    self.assertTrue(matches(f"{d}/.venv", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/.venv/", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/.venv/bin", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/.venv/bin/", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/.venv/bin/python", is_dir=is_dir))
                    self.assertFalse(matches(f"{d}/.venv2", is_dir=is_dir))
                    self.assertFalse(matches(f"{d}/.venv2/", is_dir=is_dir))
                    self.assertFalse(matches(f"{d}/.venv2/bin", is_dir=is_dir))
                    self.assertFalse(matches(f"{d}/.venv2/bin/", is_dir=is_dir))
                    self.assertFalse(matches(f"{d}/.venv2/bin/python", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/a.venv", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/a.venv/", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/a.venv/bin", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/a.venv/bin/", is_dir=is_dir))
                    self.assertTrue(matches(f"{d}/a.venv/bin/python", is_dir=is_dir))

    def test_robert_match_files_under_symlink(self):
        # FIXME What's going on?
        """
        see: https://git-scm.com/docs/gitignore#_pattern_format
        The pattern foo/ will match a directory foo and paths underneath it,
        but will not match a regular file or a symbolic link foo
        (this is consistent with the way how pathspec works in general in Git)
        """
        pass

    def test_robert_handle_base_directories_with_a_symlink_in_their_components(self):
        """
        See https://github.com/bitranox/igittigitt/issues/28 .
        """
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(f"{d}/igittigitt01")
            os.symlink(
                f"{d}/igittigitt01",
                f"{d}/symlink_to_igittigitt01",
                target_is_directory=True,
            )

            matches = self.__parse_gitignore_string(
                ["*.txt"], mock_base_path=f"{d}/symlink_to_igittigitt01"
            )

            for is_dir in (False, True):
                with self.subTest(i=is_dir):
                    self.assertTrue(
                        matches(f"{d}/symlink_to_igittigitt01/file.txt", is_dir=is_dir)
                    )
                    self.assertFalse(
                        matches(f"{d}/symlink_to_igittigitt01/file.png", is_dir=is_dir)
                    )

            for path in (
                f"{d}/symlink_to_igittigitt01/file.txt",
                f"{d}/symlink_to_igittigitt01/file.png",
            ):
                with open(path, "w"):
                    pass

            self.assertTrue(matches(f"{d}/symlink_to_igittigitt01/file.txt"))
            self.assertFalse(matches(f"{d}/symlink_to_igittigitt01/file.png"))

    def test_robert_parse_rule_files(self):
        matches = self.__parse_gitignore_string(
            [
                "test__pycache__",
                "*.py[cod]",
                ".test_venv/",
                ".test_venv/**",
                ".test_venv/*",
                "!test_inverse",
                "!hello.pyc",
            ],
            mock_base_path="/home/robert",
        )

        for is_dir in (False, True):
            with self.subTest(i=is_dir):
                self.assertTrue(matches("/home/robert/test__pycache__", is_dir=is_dir))
                self.assertTrue(
                    matches(
                        "/home/robert/test__pycache__/.test_gitignore", is_dir=is_dir
                    )
                )
                self.assertTrue(
                    matches("/home/robert/test__pycache__/excluded", is_dir=is_dir)
                )
                self.assertTrue(
                    matches(
                        "/home/robert/test__pycache__/excluded/excluded", is_dir=is_dir
                    )
                )
                self.assertTrue(
                    matches(
                        "/home/robert/test__pycache__/excluded/excluded/excluded.txt",
                        is_dir=is_dir,
                    )
                )
                # This file will actually be ignored by Git because it won't go into ignored directory
                # `test__pycache__` while globbing. If you are globbing through the directory tree, check that parent
                # directory is not ignored (`!/foo`, `/foo/*`, `!/foo/bar`) and if it is, don't call `matches` on
                # nested file.
                self.assertFalse(
                    matches(
                        "/home/robert/test__pycache__/excluded/excluded/test_inverse"
                    )
                )
                self.assertFalse(matches("/home/robert/hello.pyc"))
                self.assertTrue(
                    matches("/home/robert/test__pycache__/some_file.txt", is_dir=is_dir)
                )
                self.assertTrue(
                    matches("/home/robert/test__pycache__/test", is_dir=is_dir)
                )
                self.assertFalse(matches("/home/robert/.test_gitignore", is_dir=is_dir))
                self.assertTrue(
                    matches("/home/robert/.test_venv/some_file.txt", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded.txt", is_dir=is_dir)
                )
                self.assertFalse(matches("/home/robert/not_excluded", is_dir=is_dir))
                self.assertTrue(
                    matches("/home/robert/not_excluded/test__pycache__", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded/.test_gitignore", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded/excluded_not", is_dir=is_dir)
                )
                self.assertFalse(
                    matches(
                        "/home/robert/not_excluded/excluded_not/sub_excluded.txt",
                        is_dir=is_dir,
                    )
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded/excluded", is_dir=is_dir)
                )
                self.assertFalse(
                    matches(
                        "/home/robert/not_excluded/excluded/excluded.txt", is_dir=is_dir
                    )
                )
                self.assertFalse(
                    matches(
                        "/home/robert/not_excluded/not_excluded2.txt", is_dir=is_dir
                    )
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded/not_excluded2", is_dir=is_dir)
                )
                self.assertFalse(
                    matches(
                        "/home/robert/not_excluded/not_excluded2/sub_excluded.txt",
                        is_dir=is_dir,
                    )
                )
                self.assertFalse(
                    matches("/home/robert/not_excluded/excluded_not.txt", is_dir=is_dir)
                )
                self.assertFalse(
                    matches("/home/robert/.test_gitignore_empty", is_dir=is_dir)
                )
        self.assertFalse(matches("/home/robert/.test_venv", is_dir=False))
        self.assertTrue(matches("/home/robert/.test_venv", is_dir=True))

    def __parse_gitignore_string(self, data, mock_base_path):
        return osxphotos.gitignorefile.parse_pattern_list(data, mock_base_path)
