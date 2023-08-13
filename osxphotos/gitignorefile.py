"""A spec-compliant `.gitignore` parser for Python.

Versioned from: https://github.com/excitoon/gitignorefile to add parse_pattern_list() function
to apply .gitignore rules to a list of patterns that aren't actually a .gitignore file.

The original code was licensed under the MIT license, Copyright (c) 2022 Vladimir Chebotarev
"""

from __future__ import annotations

import os
import re
from typing import Callable

DEFAULT_IGNORE_NAMES = [".gitignore", ".git/info/exclude"]


def parse_pattern_list(
    patterns: list[str], base_path: str = None
) -> Callable[[str], bool]:
    """Parse a list of patterns and return a callable to match against a path.

    Args:
        patterns (list[str]): List of patterns to match against.
        base_path (str): Base path for applying ignore rules.

    Returns:
        Callable[[str], bool]: Callable which returns `True` if specified path is ignored.
            You can also pass `is_dir: bool` optional parameter if you know whether the specified path is a directory.
    """
    rules = []
    for pattern in patterns:
        pattern = pattern.rstrip("\r\n")
        if rule := _rule_from_pattern(pattern):
            rules.append(rule)

    return _IgnoreRules(rules, base_path).match


def parse(path, base_path=None):
    """Parses single `.gitignore` file.

    Args:
        path (str): Path to `.gitignore` file.
        base_path (str): Base path for applying ignore rules.

    Returns:
        Callable[[str], bool]: Callable which returns `True` if specified path is ignored.
            You can also pass `is_dir: bool` optional parameter if you know whether the specified path is a directory.
    """

    if base_path is None:
        base_path = os.path.dirname(path) or os.path.dirname(os.path.abspath(path))

    rules = []
    with open(path) as ignore_file:
        for line in ignore_file:
            line = line.rstrip("\r\n")
            if rule := _rule_from_pattern(line):
                rules.append(rule)

    return _IgnoreRules(rules, base_path).match


def ignore(ignore_names=DEFAULT_IGNORE_NAMES):
    """Returns `shutil.copytree()`-compatible ignore function for skipping ignored files.

    It will check if file is ignored by any `.gitignore` in the directory tree.

    Args:
        ignore_names (list[str], optional): List of names of ignore files.

    Returns:
        Callable[[str, list[str]], list[str]]: Callable compatible with `shutil.copytree()`.
    """

    matches = Cache(ignore_names=ignore_names)
    return lambda root, names: {
        name for name in names if matches(os.path.join(root, name))
    }


def ignored(path, is_dir=None, ignore_names=DEFAULT_IGNORE_NAMES):
    """Checks if file is ignored by any `.gitignore` in the directory tree.

    Args:
        path (str): Path to check against ignore rules.
        is_dir (bool, optional): Set if you know whether the specified path is a directory.
        ignore_names (list[str], optional): List of names of ignore files.

    Returns:
        bool: `True` if the path is ignored.
    """

    return Cache(ignore_names=ignore_names)(path, is_dir=is_dir)


class Cache:
    """Caches information about different `.gitignore` files in the directory tree.

    Allows to reduce number of queries to filesystem to mininum.
    """

    def __init__(self, ignore_names=DEFAULT_IGNORE_NAMES):
        """Constructs `Cache` objects.

        Args:
            ignore_names (list[str], optional): List of names of ignore files.
        """

        self.__ignore_names = ignore_names
        self.__gitignores = {}

    def __call__(self, path, is_dir=None):
        """Checks whether the specified path is ignored.

        Args:
            path (str): Path to check against ignore rules.
            is_dir (bool, optional): Set if you know whether the specified path is a directory.
        """

        path = _Path(path)
        add_to_children = {}
        plain_paths = []
        for parent in path.parents():
            if parent.parts in self.__gitignores:
                break

            ignore_paths = []
            for ignore_name in self.__ignore_names:
                ignore_path = parent.join(ignore_name)
                if ignore_path.isfile():
                    ignore_paths.append(str(ignore_path))

            if ignore_paths:
                matches = [
                    parse(ignore_path, base_path=parent) for ignore_path in ignore_paths
                ]
                add_to_children[parent] = (matches, plain_paths)
                plain_paths = []

            else:
                plain_paths.append(parent)

        else:
            parent = _Path(tuple())  # Null path.
            self.__gitignores[parent.parts] = []

        for plain_path in plain_paths:
            # assert plain_path.parts not in self.__gitignores
            self.__gitignores[plain_path.parts] = self.__gitignores[parent.parts]

        for parent, (_, parent_plain_paths) in reversed(list(add_to_children.items())):
            # assert parent.parts not in self.__gitignores
            self.__gitignores[parent.parts] = self.__gitignores[
                parent.parts[:-1]
            ].copy()
            for parent_to_add, (gitignores_to_add, _) in reversed(
                list(add_to_children.items())
            ):
                self.__gitignores[parent.parts].extend(gitignores_to_add)
                if parent_to_add == parent:
                    break

            self.__gitignores[parent.parts].reverse()

            for plain_path in parent_plain_paths:
                # assert plain_path.parts not in self.__gitignores
                self.__gitignores[plain_path.parts] = self.__gitignores[parent.parts]

        # This parent comes either from first or second loop.
        return any((m(path, is_dir=is_dir) for m in self.__gitignores[parent.parts]))


class _Path:
    def __init__(self, path):
        if isinstance(path, (str, bytes, os.PathLike)):
            abs_path = os.path.abspath(path)
            self.__parts = tuple(_path_split(abs_path))
            self.__joined = abs_path
            self.__is_dir = None

        else:
            self.__parts = path
            self.__joined = None
            self.__is_dir = None

    @property
    def parts(self):
        return self.__parts

    def join(self, name):
        return _Path(self.__parts + (name,))

    def relpath(self, base_path):
        if self.__parts[: len(base_path.__parts)] == base_path.__parts:
            return "/".join(self.__parts[len(base_path.__parts) :])

        else:
            return None

    def parents(self):
        for i in range(len(self.__parts) - 1, 0, -1):
            yield _Path(self.__parts[:i])

    def isfile(self):
        return os.path.isfile(str(self))

    def isdir(self):
        if self.__is_dir is not None:
            return self.__is_dir
        self.__is_dir = os.path.isdir(str(self))
        return self.__is_dir

    def __str__(self):
        if self.__joined is None:
            self.__joined = (
                os.sep.join(self.__parts) if self.__parts != ("",) else os.sep
            )
        return self.__joined


def _rule_from_pattern(pattern):
    # Takes a `.gitignore` match pattern, such as "*.py[cod]" or "**/*.bak",
    # and returns an `_IgnoreRule` suitable for matching against files and
    # directories. Patterns which do not match files, such as comments
    # and blank lines, will return `None`.

    # Early returns follow
    # Discard comments and separators
    if not pattern.lstrip() or pattern.lstrip().startswith("#"):
        return

    # Discard anything with more than two consecutive asterisks
    if "***" in pattern:
        return

    # Strip leading bang before examining double asterisks
    if pattern.startswith("!"):
        negation = True
        pattern = pattern[1:]
    else:
        negation = False

    # Discard anything with invalid double-asterisks -- they can appear
    # at the start or the end, or be surrounded by slashes
    for m in re.finditer("\\*\\*", pattern):
        start_index = m.start()
        if (
            start_index != 0
            and start_index != len(pattern) - 2
            and (pattern[start_index - 1] != "/" or pattern[start_index + 2] != "/")
        ):
            return

    # Special-casing '/', which doesn't match any files or directories
    if pattern.rstrip() == "/":
        return

    directory_only = pattern.endswith("/")

    # A slash is a sign that we're tied to the `base_path` of our rule
    # set.
    anchored = "/" in pattern[:-1]

    if pattern.startswith("/"):
        pattern = pattern[1:]
    if pattern.startswith("**"):
        pattern = pattern[2:]
        anchored = False
    if pattern.startswith("/"):
        pattern = pattern[1:]
    if pattern.endswith("/"):
        pattern = pattern[:-1]

    # patterns with leading hashes are escaped with a backslash in front, unescape it
    if pattern.startswith("\\#"):
        pattern = pattern[1:]

    # trailing spaces are ignored unless they are escaped with a backslash
    i = len(pattern) - 1
    striptrailingspaces = True
    while i > 1 and pattern[i] == " ":
        if pattern[i - 1] == "\\":
            pattern = pattern[: i - 1] + pattern[i:]
            i -= 1
            striptrailingspaces = False
        else:
            if striptrailingspaces:
                pattern = pattern[:i]
        i -= 1

    regexp = _fnmatch_pathname_to_regexp(pattern, anchored, directory_only)
    return _IgnoreRule(regexp, negation, directory_only)


class _IgnoreRules:
    def __init__(self, rules, base_path):
        self.__rules = rules
        self.__can_return_immediately = not any((r.negation for r in rules))
        self.__base_path = (
            _Path(base_path) if not isinstance(base_path, _Path) else base_path
        )

    def match(self, path, is_dir=None):
        if not isinstance(path, _Path):
            path = _Path(path)

        rel_path = path.relpath(self.__base_path)

        if rel_path is not None:
            if is_dir is None:
                is_dir = path.isdir()  # TODO Pass callable here.

            if self.__can_return_immediately:
                return any((r.match(rel_path, is_dir) for r in self.__rules))

            else:
                matched = False
                for rule in self.__rules:
                    if rule.match(rel_path, is_dir):
                        matched = not rule.negation

                else:
                    return matched

        else:
            return False


class _IgnoreRule:
    def __init__(self, regexp, negation, directory_only):
        self.__regexp = re.compile(regexp)
        self.__negation = negation
        self.__directory_only = directory_only
        self.__match = self.__regexp.match

    @property
    def regexp(self):
        return self.__regexp

    @property
    def negation(self):
        return self.__negation

    def match(self, rel_path, is_dir):
        m = self.__match(rel_path)

        # If we need a directory, check there is something after slash and if there is not, target must be a directory.
        # If there is something after slash then it's a directory irrelevant to type of target.
        # `self.directory_only` implies we have group number 1.
        # N.B. Question mark inside a group without a name can shift indices. :(
        return m and (not self.__directory_only or m.group(1) is not None or is_dir)


if os.altsep is not None:
    _all_seps_expr = f"[{re.escape(os.sep)}{re.escape(os.altsep)}]"
    _path_split = lambda path: re.split(_all_seps_expr, path)  # noqa: E731

else:
    _path_split = lambda path: path.split(os.sep)  # noqa: E731


def _fnmatch_pathname_to_regexp(pattern, anchored, directory_only):
    # Implements `fnmatch` style-behavior, as though with `FNM_PATHNAME` flagged;
    # the path separator will not match shell-style `*` and `.` wildcards.

    # Frustratingly, python's fnmatch doesn't provide the FNM_PATHNAME
    # option that `.gitignore`'s behavior depends on.

    if not pattern:
        if directory_only:
            return "[^/]+(/.+)?$"  # Empty name means no path fragment.

        else:
            return ".*"

    i, n = 0, len(pattern)

    res = ["(?:^|.+/)" if not anchored else ""]
    while i < n:
        c = pattern[i]
        i += 1
        if c == "*":
            if i < n and pattern[i] == "*":
                i += 1
                if i < n and pattern[i] == "/":
                    i += 1
                    res.append("(.+/)?")  # `/**/` matches `/`.

                else:
                    res.append(".*")

            else:
                res.append("[^/]*")

        elif c == "?":
            res.append("[^/]")

        elif c == "[":
            j = i
            if j < n and pattern[j] == "!":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 1

            if j >= n:
                res.append("\\[")
            else:
                stuff = pattern[i:j].replace("\\", "\\\\")
                i = j + 1
                if stuff[0] == "!":
                    stuff = f"^{stuff[1:]}"
                elif stuff[0] == "^":
                    stuff = f"\\{stuff}"
                res.append(f"[{stuff}]")

        else:
            res.append(re.escape(c))

    if (
        directory_only
    ):  # In this case we are interested if there is something after slash.
        res.append("(/.+)?$")

    else:
        res.append("(?:/.+)?$")

    return "".join(res)
