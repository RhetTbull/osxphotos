"""Sort a Photos album by size; run with `osxphotos run sort_album.py [--ascend] ALBUM"""

import sys

import click
import Photos
from Foundation import NSError, NSIndexSet, NSPredicate, NSRange

from osxphotos.cli import echo, echo_error
from osxphotos.photokit_utils import wait_for_photokit_authorization


def find_album_via_path(path: str) -> Photos.PHAssetCollection:
    """
    Resolve 'Folder/SubFolder/Album' → PHAssetCollection.
    Raises ValueError if any component isn’t found.
    """
    parts = [p for p in path.split("/") if p]
    if not parts:
        raise ValueError("Empty album path")

    current: Photos.PHFetchResult = (
        Photos.PHCollectionList.fetchTopLevelUserCollectionsWithOptions_(None)
    )

    for level, name in enumerate(parts):
        match = None
        for idx in range(current.count()):
            coll = current.objectAtIndex_(idx)
            if coll.localizedTitle() == name:
                match = coll
                break

        if match is None:
            raise ValueError(f"Path component “{name}” not found")

        is_last = level == len(parts) - 1
        if is_last:
            if not isinstance(match, Photos.PHAssetCollection):
                raise ValueError(f"“{name}” is a folder, not an album")
            return match
        else:
            if not isinstance(match, Photos.PHCollectionList):
                raise ValueError(f"“{name}” is an album, not a folder")
            current = Photos.PHCollection.fetchCollectionsInCollectionList_options_(
                match, None
            )


def sort_album_by_size(album_path: str, ascend: bool) -> int:
    """
    Re‑order *album_path* so the largest asset appears first.
    Album may be nested inside user folders (e.g. “A/B/C”).

    Args:
        album_path: album name or path to the album in Folder/SubFolder/Album format
        ascend: if True, sort by ascending size; otherwise sort by descending size

    Returns: number of assets sorted
    """
    if not wait_for_photokit_authorization():
        raise RuntimeError("Photos library access not granted")

    album = find_album_via_path(album_path)

    if not album.canPerformEditOperation_(
        Photos.PHCollectionEditOperationRearrangeContent
    ):
        raise RuntimeError("Album cannot be reordered (Smart Album or shared)")

    fetch = Photos.PHAsset.fetchAssetsInAssetCollection_options_(album, None)
    n = fetch.count()
    if n <= 1:
        return n

    assets = [fetch.objectAtIndex_(i) for i in range(n)]

    def asset_size(asset):
        total = 0
        for res in Photos.PHAssetResource.assetResourcesForAsset_(asset):
            s = res.valueForKey_("fileSize")
            if s:
                total += int(s)
        return total

    order = sorted(range(n), key=lambda i: asset_size(assets[i]), reverse=not ascend)
    reordered = [assets[i] for i in order]

    def change_block():
        req = Photos.PHAssetCollectionChangeRequest.changeRequestForAssetCollection_(
            album
        )
        rng = NSRange(0, n)
        idx_set = NSIndexSet.indexSetWithIndexesInRange_(rng)
        req.removeAssetsAtIndexes_(idx_set)
        req.insertAssets_atIndexes_(reordered, idx_set)

    lib = Photos.PHPhotoLibrary.sharedPhotoLibrary()
    ok, err = lib.performChangesAndWait_error_(change_block, None)

    if not ok:
        raise RuntimeError(f"Re‑order failed: {err.localizedDescription()}")
    return len(assets)


@click.command()
@click.option(
    "--ascend",
    "-a",
    is_flag=True,
    help="Sort in ascending size; default is to sort in descending size",
)
@click.argument("album_path", metavar="ALBUM_PATH")
def main(ascend: bool, album_path: str):
    """Sort a specified Photos album by size."""
    try:
        sorted = sort_album_by_size(album_path, ascend)
        echo(
            f"Sorted {sorted} item{'s' if sorted !=1 else ''} in '{album_path}' successfully "
            + f"({'ascending' if ascend else 'descending'})."
        )
    except Exception as e:
        echo_error(f"[error]Error: {e}")
        raise click.Abort()


if __name__ == "__main__":
    main()
