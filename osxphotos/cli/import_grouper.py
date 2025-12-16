"""Group files for import so that edited files, burst images, live photos are imported properly"""

import pathlib
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from itertools import chain
from re import match
from typing import Callable, Iterable, TypeVar
from osxphotos.platform import is_macos

if is_macos:
    from osxphotos.image_file_utils import EDITED_RE, is_edited_version_of_file

@dataclass
class Groupable:
    path: pathlib.Path
    stem: str
    _edited_stem_func: Callable[[pathlib.Path], str]
    _burst_uuid_func: Callable[[pathlib.Path], str | None]

    def __init__(
        self,
        path: pathlib.Path,
        edited_stem_func: Callable[[pathlib.Path], str],
        burst_uuid_func: Callable[[pathlib.Path], str | None],
    ):
        self.path = path
        self.stem = path.stem.lower()
        self._edited_stem_func = edited_stem_func
        self._burst_uuid_func = burst_uuid_func

    @cached_property
    def edited_stem(self) -> str:
        return self._edited_stem_func(self.path)

    @cached_property
    def burst_uuid(self) -> str | None:
        return self._burst_uuid_func(self.path)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Groupable):
            return self.path == other.path

        return False

    def __hash__(self) -> int:
        return hash(self.path)


@dataclass
class GroupingNode:
    children: dict[str, "GroupingNode"] = field(default_factory=dict)
    files: list[Groupable] = field(default_factory=list)

    def add(
        self, item: Groupable, remaining: str, maybe_e: bool = False
    ) -> Groupable | None:
        """Add an item (Groupable) to the tree.

        Args:
            item (Groupable): The Groupable to add.
            remaining (str): The remaining part of the lowercase stem.
            maybe_e (bool): Whether to try matching a potentially edited version of a file to an original.

        Returns:
            Optional[Groupable]: None if the item was added, or the original item if a match was not found
            (only possible if maybe_e is True).
        """
        if len(remaining) == 0:
            # Tried to find a matching original for a maybe edited file (=candidate). The matching original should
            # already be handled as the edited files have longer file names and are later in the sorting order.
            # If there isn't an already matching file for the candidate, treat it as a separate file and send back up
            # the tree to be placed in the correct spot.
            if maybe_e:
                if not self.files:
                    return item
                if not is_edited_version_of_file(self.files[0].path, item.path):
                    return item
            else:
                self.files.append(item)

            return None
        elif self.files:
            # We have already found files with the current stem, so it is possible that this is actually
            # an edited file with a configurable suffix.
            if self.files[0].edited_stem == item.stem:
                self.files.append(item)
                return None
            elif match(EDITED_RE, str(item.path)):
                # If the file we are handling is also an edited file (with _E), we need to match it
                # to a potential _E file in the group. This does not place files in the group if
                # there isn't an existing _E file.
                for file in self.files:
                    if (
                        match(EDITED_RE, str(file.path))
                        and file.edited_stem == item.stem
                    ):
                        self.files.append(item)
                        return None

        key = remaining[0]
        child = self.children.get(key)
        if not child:
            child = GroupingNode()
            self.children[key] = child

        # Files with '_E' in the name ('_e' in the stem) might be edited, skip the e and try to match to an existing file.
        if key == "_" and len(remaining) > 1 and remaining[1] == "e":
            result = child.add(item, remaining[2:], maybe_e)
            if not result:
                return None

        return child.add(item, remaining[1:], maybe_e)

    def collect(self) -> list[list[Groupable]]:
        groups = []
        if self.files:
            groups.append(self.files)
        for key in sorted(self.children.keys()):
            groups.extend(self.children[key].collect())

        return groups


@dataclass
class GroupingRoot:
    tree: "GroupingNode" = field(default_factory=GroupingNode)

    def add(self, item: Groupable):
        self.tree.add(item, item.stem)

    def collect(self) -> list[list[Groupable]]:
        return self.tree.collect()


def group_files_for_import(
    files: list[pathlib.Path],
    edited_stem_func: Callable[[pathlib.Path], str] = None,
    burst_uuid_func: Callable[[pathlib.Path], str | None] = None,
    advance_progress=None,
) -> list[tuple[pathlib.Path, ...]]:
    """Group related files for import.

    Groups files that should be imported together: originals with their edited versions,
    live photos with their video components, and burst sequences.

    Algorithm:
    1. Build a prefix tree from file stems (lowercase) to group files with common prefixes
       - Each character in the stem becomes a node in the tree
       - Files with identical stems are grouped at the same leaf node

    2. Handle edited versions during tree building:
       - Files matching edited_stem pattern (e.g., IMG_1234_edited.JPG) group with their original
       - iOS edited files (IMG_E1234.JPG) try to match by skipping '_e' in the stem
       - Unmatched edited files become standalone groups

    3. Merge burst sequences after tree grouping:
       - Files with the same burst_uuid are merged into a single group
       - Overrides stem-based grouping for burst photos

    Returns groups sorted with the primary file first.
    """

    # Building the tree is most likely quite a bit faster unless there are a lot of files with suffixes,
    # so do not advance the progress too much per added file to not give a false impression.
    tree_advance_multiplier = 0.1

    sorted_files = sort_paths(files, lambda p: p)
    root_node = GroupingRoot()
    expected_parent = files[0].parent
    for file in sorted_files:
        # avoid foot-gun by verifying that all paths have the same parent
        if file.parent != expected_parent:
            raise ValueError("All files must have the same parent path")
        root_node.add(Groupable(file, edited_stem_func, burst_uuid_func))
        if advance_progress:
            advance_progress(tree_advance_multiplier)

    grouped = root_node.collect()
    burst_groups = defaultdict(list)

    # Divide the remaining advance for the remaining burst checks
    burst_advance_multiplier = (
        len(sorted_files) * (1 - tree_advance_multiplier) / len(grouped)
    )

    non_bursts = []
    for group in grouped:
        if group[0].burst_uuid:
            burst_groups[group[0].burst_uuid].extend(group)
        else:
            non_bursts.append(group)
        if advance_progress:
            advance_progress(burst_advance_multiplier)

    result = [
        tuple([p.path for p in g]) for g in chain(burst_groups.values(), non_bursts)
    ]

    return sort_paths(result, lambda g: g[0])


P = TypeVar("P")


def sort_paths(paths: Iterable[P], path_func: Callable[[P], pathlib.Path]) -> list[P]:
    """Sort paths into desired order for import so the key file is first

      Sort order is:
      - alphabetically up to the first '_' of the stem
      - length of the stem (shorter first)
      - non-video files before MOV and MP4 files
      - non-AAE files before AAE files
      - alphabetically based on the full file name

    For example:

    ABC_1234.jpg, ABC_1234.mov, ABC_1234.aae, ABC_1234_edited.mov, IMG_1234.jpg

    """

    def path_key(sortable: P) -> tuple[str, int, bool, bool, str]:
        path = path_func(sortable)
        extension = path.suffix.lower()
        is_aae = extension == ".aae"
        is_mov = extension in (".mov", ".mp4")
        base_name = path.stem.split("_")[0]  # Extract the base name without suffixes
        return base_name, len(path.stem), is_aae, is_mov, str(path.name)

    return sorted(paths, key=path_key)
