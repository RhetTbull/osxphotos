import os
import unittest

import osxphotos.gitignorefile


class TestIgnored(unittest.TestCase):
    def test_simple(self):
        # if there is no __pycahce__ directory, this test will fail
        # so create a dummy __pycache__ directory if not present
        if not os.path.isdir(f"{os.path.dirname(__file__)}/__pycache__"):
            os.mkdir(f"{os.path.dirname(__file__)}/__pycache__")
        for is_dir in (None, False, True):
            with self.subTest(i=is_dir):
                self.assertFalse(
                    osxphotos.gitignorefile.ignored(__file__, is_dir=is_dir)
                )
                if is_dir is not True:
                    self.assertTrue(
                        osxphotos.gitignorefile.ignored(
                            f"{os.path.dirname(__file__)}/__pycache__/some.pyc",
                            is_dir=is_dir,
                        )
                    )
                self.assertFalse(
                    osxphotos.gitignorefile.ignored(
                        os.path.dirname(__file__), is_dir=is_dir
                    )
                )
                if is_dir is not False:
                    self.assertTrue(
                        osxphotos.gitignorefile.ignored(
                            f"{os.path.dirname(__file__)}/__pycache__", is_dir=is_dir
                        )
                    )
                else:
                    # Note: this test will fail if your .gitignore file does not contain __pycache__/
                    self.assertFalse(
                        osxphotos.gitignorefile.ignored(
                            f"{os.path.dirname(__file__)}/__pycache__", is_dir=is_dir
                        )
                    )
