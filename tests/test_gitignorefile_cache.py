import io
import itertools
import os
import stat
import tempfile
import unittest
import unittest.mock

import osxphotos.gitignorefile


class TestCache(unittest.TestCase):
    def test_simple(self):
        def normalize_path(path):
            return os.path.abspath(path).replace(os.sep, "/")

        class StatResult:
            def __init__(self, is_file=False):
                self.st_ino = id(self)
                self.st_dev = 0
                self.st_mode = stat.S_IFREG if is_file else stat.S_IFDIR

            def isdir(self):
                return self.st_mode == stat.S_IFDIR

            def isfile(self):
                return self.st_mode == stat.S_IFREG

        class Stat:
            def __init__(self, directories, files):
                self.__filesystem = {}
                for path in directories:
                    self.__filesystem[normalize_path(path)] = StatResult()
                for path in files:
                    self.__filesystem[normalize_path(path)] = StatResult(True)

            def __call__(self, path):
                try:
                    return self.__filesystem[normalize_path(path)]

                except KeyError:
                    raise FileNotFoundError()

        for ignore_file_name in (".gitignore", ".mylovelytoolignore"):
            with self.subTest(ignore_file_name=ignore_file_name):
                my_stat = Stat(
                    [
                        "/home/vladimir/project/directory/subdirectory",
                        "/home/vladimir/project/directory",
                        "/home/vladimir/project",
                        "/home/vladimir",
                        "/home",
                        "/",
                    ],
                    [
                        "/home/vladimir/project/directory/subdirectory/subdirectory/file.txt",
                        "/home/vladimir/project/directory/subdirectory/subdirectory/file2.txt",
                        "/home/vladimir/project/directory/subdirectory/subdirectory/file3.txt",
                        "/home/vladimir/project/directory/subdirectory/file.txt",
                        "/home/vladimir/project/directory/subdirectory/file2.txt",
                        "/home/vladimir/project/directory/%s" % ignore_file_name,
                        "/home/vladimir/project/directory/file.txt",
                        "/home/vladimir/project/directory/file2.txt",
                        "/home/vladimir/project/file.txt",
                        "/home/vladimir/project/%s" % ignore_file_name,
                        "/home/vladimir/file.txt",
                    ],
                )

                def mock_open(path):
                    data = {
                        normalize_path(
                            "/home/vladimir/project/directory/%s" % ignore_file_name
                        ): ["file.txt"],
                        normalize_path(
                            "/home/vladimir/project/%s" % ignore_file_name
                        ): ["file2.txt"],
                    }

                    statistics["open"] += 1
                    try:
                        return io.StringIO("\n".join(data[normalize_path(path)]))

                    except KeyError:
                        raise FileNotFoundError()

                def mock_isdir(path):
                    statistics["isdir"] += 1
                    try:
                        return my_stat(path).isdir()
                    except FileNotFoundError:
                        return False

                def mock_isfile(path):
                    statistics["isfile"] += 1
                    try:
                        return my_stat(path).isfile()
                    except FileNotFoundError:
                        return False

                data = {
                    "/home/vladimir/project/directory/subdirectory/file.txt": True,
                    "/home/vladimir/project/directory/subdirectory/file2.txt": True,
                    "/home/vladimir/project/directory/subdirectory/subdirectory/file.txt": True,
                    "/home/vladimir/project/directory/subdirectory/subdirectory/file2.txt": True,
                    "/home/vladimir/project/directory/subdirectory/subdirectory/file3.txt": False,
                    "/home/vladimir/project/directory/file.txt": True,
                    "/home/vladimir/project/directory/file2.txt": True,
                    "/home/vladimir/project/file.txt": False,
                    "/home/vladimir/file.txt": False,  # No rules and no `isdir` calls for this file.
                }

                # 9! == 362880 combinations.
                for permutation in itertools.islice(
                    itertools.permutations(data.items()), 0, None, 6 * 8
                ):
                    statistics = {"open": 0, "isdir": 0, "isfile": 0}

                    with unittest.mock.patch("builtins.open", mock_open):
                        with unittest.mock.patch("os.path.isdir", mock_isdir):
                            with unittest.mock.patch("os.path.isfile", mock_isfile):
                                matches = osxphotos.gitignorefile.Cache(
                                    ignore_names=[ignore_file_name]
                                )
                                for path, expected in permutation:
                                    self.assertEqual(matches(path), expected)

                    self.assertEqual(statistics["open"], 2)
                    self.assertEqual(statistics["isdir"], len(data) - 1)
                    self.assertEqual(statistics["isfile"], 7)  # Unique path fragments.

    def test_wrong_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            matches = osxphotos.gitignorefile.Cache()
            os.makedirs(f"{d}/.venv/bin")
            os.symlink(f"/nonexistent-path-{id(self)}", f"{d}/.venv/bin/python")
            self.assertFalse(matches(f"{d}/.venv/bin/python"))
