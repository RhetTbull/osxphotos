import os
import shutil
import tempfile
import unittest
import unittest.mock

import osxphotos.gitignorefile


class TestIgnore(unittest.TestCase):
    def test_robert_shutil_ignore_function(self):
        with tempfile.TemporaryDirectory() as d:
            for directory in [
                "test__pycache__/excluded/excluded",
                ".test_venv",
                "not_excluded/test__pycache__",
                "not_excluded/excluded_not",
                "not_excluded/excluded",
                "not_excluded/not_excluded2",
            ]:
                os.makedirs(f"{d}/example/{directory}")

            for name in [
                "test__pycache__/.test_gitignore",
                "test__pycache__/excluded/excluded/excluded.txt",
                "test__pycache__/excluded/excluded/test_inverse",
                "test__pycache__/some_file.txt",
                "test__pycache__/test",
                ".test_gitignore",
                ".test_venv/some_file.txt",
                "not_excluded.txt",
                "not_excluded/.test_gitignore",
                "not_excluded/excluded_not/sub_excluded.txt",
                "not_excluded/excluded/excluded.txt",
                "not_excluded/not_excluded2.txt",
                "not_excluded/not_excluded2/sub_excluded.txt",
                "not_excluded/excluded_not.txt",
                ".test_gitignore_empty",
            ]:
                with open(f"{d}/example/{name}", "w"):
                    pass

            with open(f"{d}/example/.gitignore", "w") as f:
                print("test__pycache__", file=f)
                print("*.py[cod]", file=f)
                print(".test_venv/", file=f)
                print(".test_venv/**", file=f)
                print(".test_venv/*", file=f)
                print("!test_inverse", file=f)

            result = []
            shutil.copytree(
                f"{d}/example", f"{d}/target", ignore=osxphotos.gitignorefile.ignore()
            )
            for root, directories, files in os.walk(f"{d}/target"):
                for directory in directories:
                    result.append(os.path.join(root, directory))
                for name in files:
                    result.append(os.path.join(root, name))

            result = sorted(
                (os.path.relpath(x, f"{d}/target").replace(os.sep, "/") for x in result)
            )

            self.assertEqual(
                result,
                [
                    ".gitignore",
                    ".test_gitignore",
                    ".test_gitignore_empty",
                    "not_excluded",
                    "not_excluded.txt",
                    "not_excluded/.test_gitignore",
                    "not_excluded/excluded",
                    "not_excluded/excluded/excluded.txt",
                    "not_excluded/excluded_not",
                    "not_excluded/excluded_not.txt",
                    "not_excluded/excluded_not/sub_excluded.txt",
                    "not_excluded/not_excluded2",
                    "not_excluded/not_excluded2.txt",
                    "not_excluded/not_excluded2/sub_excluded.txt",
                ],
            )
