"""
Export Photos folder and album hierarchy to a text file with tab indentation.

Modified from code by John Gordon: https://tech.kateva.org/2025/10/certified-vibe-coding-success-python.html

If saved locally, run with osxphotos run folder_tree.py
Otherwise, use the following command to run the script directly from GitHub:
osxphotos run https://raw.githubusercontent.com/RhetTbull/osxphotos/refs/heads/main/examples/folder_tree.py
"""

import sys
from pathlib import Path

import osxphotos


def export_folder_hierarchy():
    """
    Export Photos library folder/album structure to a text file.

    Args:
        output_file: Path to output text file (default: photos_folders.txt)
    """
    # Initialize connection to Photos library
    photosdb = osxphotos.PhotosDB()

    # Get folders and albums
    folders = photosdb.folder_info
    albums = photosdb.album_info

    print(f"Found {len(folders)} folders and {len(albums)} albums", file=sys.stderr)

    # Build maps for folders
    folder_map = {f.uuid: {"obj": f, "children": [], "type": "folder"} for f in folders}

    # Add albums to the structure
    for album in albums:
        # Albums have folder_names property which is a list of folder names in the path
        if hasattr(album, "folder_names") and album.folder_names:
            # Try to find the parent folder by matching folder names
            # folder_names is a list like ['Top Folder', 'Sub Folder']
            # We want to match the first (top-level) folder name
            top_folder_name = album.folder_names[0] if album.folder_names else None

            if top_folder_name:
                # Find folder with matching title
                parent_folder = None
                for folder in folders:
                    if folder.title == top_folder_name:
                        parent_folder = folder
                        break

                if parent_folder and parent_folder.uuid in folder_map:
                    folder_map[parent_folder.uuid]["children"].append(
                        {
                            "obj": album,
                            "type": "album",
                            "title": album.title,
                            "folder_path": (" / ".join(album.folder_names) if album.folder_names else ""),
                        }
                    )

    # Recursive function to write hierarchy
    def write_item(f, item_data, level=0):
        """Write item and its children with proper indentation."""
        indent = "\t" * level

        if item_data["type"] == "folder":
            folder = item_data["obj"]
            f.write(f"{indent}{folder.title}/\n")
            # Sort children alphabetically
            children = sorted(
                item_data["children"],
                key=lambda x: x.get("title", x.get("obj").title).lower(),
            )
            for child in children:
                if child["type"] == "album":
                    # Write album with its folder path if nested
                    folder_path = child.get("folder_path", "")
                    if folder_path:
                        f.write(f"{indent}\t[{folder_path}] {child['title']}\n")
                    else:
                        f.write(f"{indent}\t{child['title']}\n")
                else:
                    write_item(f, child, level + 1)

    # Find root folders
    root_folders = [folder_map[f.uuid] for f in folders if f.parent is None]
    root_folders = sorted(root_folders, key=lambda x: x["obj"].title.lower())

    # Write to output file
    print("Photos Library Folder Hierarchy")
    print("=" * 50 + "\n")

    for root in root_folders:
        write_item(sys.stdout, root)

    print(f"Total top-level folders: {len(root_folders)}")


if __name__ == "__main__":
    export_folder_hierarchy()
