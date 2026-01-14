"""Group files for import so that edited files, burst images, live photos are imported properly"""

import pathlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from itertools import chain
from re import match
from typing import Callable, Iterable, TypeVar

from osxphotos.platform import is_macos

if is_macos:
    from osxphotos.image_file_utils import EDITED_RE, is_edited_version_of_file

# Regex to match increment suffix like " (1)", " (2)", etc. at the end of a string
INCREMENT_SUFFIX_RE = re.compile(r"\s+\(\d+\)$")

# Regex to extract increment suffix for repositioning
EXTRACT_INCREMENT_RE = re.compile(r"^(.+?)(\s+\(\d+\))$")

# Regex to match _edited suffix followed by increment suffix
EDITED_WITH_INCREMENT_RE = re.compile(r"^(.+?)_edited(\s+\(\d+\))$", re.IGNORECASE)

# Regex to match _edited suffix (with optional increment suffix before it)
EDITED_WITH_MIDDLE_INCREMENT_RE = re.compile(
    r"^(.+?)(\s+\(\d+\))?_edited$", re.IGNORECASE
)


def strip_increment_suffix(stem: str) -> str:
    """Strip the increment suffix like ' (1)' from the end of a file stem.

    When osxphotos exports files with duplicate names, it appends ' (1)', ' (2)', etc.
    This function removes that suffix if present.

    Args:
        stem: The file stem (filename without extension)

    Returns:
        The stem with any increment suffix removed
    """
    return INCREMENT_SUFFIX_RE.sub("", stem)


def normalize_edited_stem(stem: str) -> str:
    """Normalize an edited file stem for comparison.

    This handles cases where the increment suffix can be in different positions:
    - 'img_0102 (1)_edited' (increment before _edited)
    - 'img_0102_edited (1)' (increment after _edited)

    Both forms are normalized to 'img_0102_edited' for comparison.

    Args:
        stem: The file stem (lowercase)

    Returns:
        Normalized stem with increment suffix removed regardless of position.
    """
    # First, try matching _edited at the end (possibly with increment before it)
    # e.g., 'img_0102 (1)_edited' -> 'img_0102_edited'
    if m := EDITED_WITH_MIDDLE_INCREMENT_RE.match(stem):
        return m.group(1) + "_edited"

    # Try matching _edited followed by increment
    # e.g., 'img_0102_edited (1)' -> 'img_0102_edited'
    if m := EDITED_WITH_INCREMENT_RE.match(stem):
        return m.group(1) + "_edited"

    # No increment suffix found, return as-is
    return stem


def get_original_stems_for_edited_with_increment(stem: str) -> list[str]:
    """Get potential original stems for an edited file with increment suffix.

    For files like 'img_0102_edited (1)', the original would be 'img_0102 (1)'.
    For files like 'img_e1234_edited (1)', possible originals are:
    - 'img_e1234 (1)' (direct original)
    - 'img_1234 (1)' (if _e was stripped during grouping)

    Args:
        stem: The file stem to analyze (lowercase)

    Returns:
        List of potential original stems. Empty list if pattern doesn't match.
        For 'img_0102_edited (1)', returns ['img_0102 (1)'].
        For 'img_e1234_edited (1)', returns ['img_e1234 (1)', 'img_1234 (1)'].
    """
    if m := EDITED_WITH_INCREMENT_RE.match(stem):
        # m.group(1) is the base (e.g., 'img_0102' or 'img_e1234')
        # m.group(2) is the increment suffix (e.g., ' (1)')
        base = m.group(1)
        increment = m.group(2)
        result = [base + increment]

        # If the base looks like it has _e pattern (abc_e followed by digits),
        # also try the stem without _e since _e files get grouped with their originals
        if re.match(r"^[a-z]{3}_e\d+", base):
            # Remove the 'e' after the underscore to get potential grouped location
            # e.g., 'img_e1235' -> 'img_1235'
            # base[:4] = 'img_', base[5:] = '1235' -> 'img_1235'
            base_without_e = base[:4] + base[5:]
            result.append(base_without_e + increment)

        return result
    return []


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
            # Also check if stems match when normalized for increment suffix position.
            # This handles the case where edited files have the increment suffix in a different position,
            # e.g., "IMG_0102 (1).HEIC" has edited stem "img_0102 (1)_edited" but the actual
            # edited file might be named "IMG_0102_edited (1).heic" with stem "img_0102_edited (1)".
            # Both normalize to "img_0102_edited" which matches.
            elif normalize_edited_stem(
                self.files[0].edited_stem
            ) == normalize_edited_stem(item.stem):
                self.files.append(item)
                return None
            elif match(EDITED_RE, str(item.path)):
                # If the file we are handling is also an edited file (with _E), we need to match it
                # to a potential _E file in the group. This does not place files in the group if
                # there isn't an existing _E file.
                for file in self.files:
                    if match(EDITED_RE, str(file.path)) and (
                        file.edited_stem == item.stem
                        or normalize_edited_stem(file.edited_stem)
                        == normalize_edited_stem(item.stem)
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

        # Handle _O pattern for original adjustment AAE files (e.g., IMG_O1234.AAE or Filename_O.AAE)
        # These are adjustments to the original file used for Portrait images, etc.
        if (
            key == "_"
            and len(remaining) > 1
            and remaining[1] == "o"
            and item.path.suffix.lower() == ".aae"
        ):
            # Only skip _o if:
            # 1. At the end (remaining == "_o"), e.g., Filename_O.AAE
            # 2. After IMG_ and before digits (e.g., IMG_O1234.AAE)
            if len(remaining) == 2 or remaining[2:].isdigit():
                if len(remaining) == 2:
                    # Filename_O.AAE pattern - add to current node if there are existing files
                    if self.files:
                        self.files.append(item)
                        return None
                    # If no existing files, fall through to normal tree traversal (standalone file)
                else:
                    # IMG_O1234.AAE pattern - skip _o and traverse the digits
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

    def find_files_at_path(self, path: str) -> list[Groupable] | None:
        """Find files stored at a specific path in the tree.

        Args:
            path: The stem path to look up (lowercase)

        Returns:
            List of Groupable files at that path, or None if path doesn't exist or has no files.
        """
        if len(path) == 0:
            return self.files if self.files else None

        key = path[0]
        child = self.children.get(key)
        if not child:
            return None
        return child.find_files_at_path(path[1:])


@dataclass
class GroupingRoot:
    tree: "GroupingNode" = field(default_factory=GroupingNode)

    def add(self, item: Groupable):
        # Check if this is an edited file with increment suffix that should be matched
        # to an original with the increment suffix in a different position.
        # E.g., 'img_0102_edited (1)' should match original 'img_0102 (1)'.
        for original_stem in get_original_stems_for_edited_with_increment(item.stem):
            if files_at_original := self.tree.find_files_at_path(original_stem):
                # Verify that any file at the original path could be the original
                # by checking that its edited_stem matches our stem (when normalized)
                # This handles cases like:
                # - edited_stem: 'img_0102 (1)_edited'
                # - item.stem: 'img_0102_edited (1)'
                # Both normalize to 'img_0102_edited'
                # We check all files in the group because IMG_E files may be grouped
                # with their originals, so IMG_E1235_edited needs to match IMG_E1235's edited_stem.
                normalized_item_stem = normalize_edited_stem(item.stem)
                for file in files_at_original:
                    if normalize_edited_stem(file.edited_stem) == normalized_item_stem:
                        files_at_original.append(item)
                        return

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
