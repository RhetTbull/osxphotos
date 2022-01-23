import re
import sys

from os import walk
from collections import Counter


FILE_PATTERN = "^(?!_).*\.py$"
SOUCE_CODE_ROOT = "osxphotos"

def create_module_name(dirpath: str, filename: str) -> str:
    prefix = dirpath[dirpath.rfind(SOUCE_CODE_ROOT):].replace('/', '.')
    return f"{prefix}.{filename}".replace(".py", "")


def test_check_duplicate():
    for dirpath, dirnames, filenames in walk(SOUCE_CODE_ROOT):
        print("\n", sys.modules)
        for filename in filenames:
            if re.search(FILE_PATTERN, filename):
                module = create_module_name(dirpath, filename)
                if module in sys.modules:
                    all_list = sys.modules[module].__all__
                    all_set = set(all_list)
                    assert Counter(all_list) == Counter(all_set)