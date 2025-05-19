#!/usr/bin/env bash

# Copy an osxphotos test Photos library to the Pictures directory and activate it

set -euo pipefail

# Set LIB_DIR and PHOTOS_DIR if needed to match your environment

# Directory containing Photos libraries
# default to parent of where this script is located (tests/)
LIB_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
LIB_DIR="$(realpath "$LIB_DIR")"

# Photos Library directory
PHOTOS_DIR="$(realpath ~/Pictures)"

# Check if library directory exists
if [[ ! -d "$LIB_DIR" ]]; then
    echo "Library directory $LIB_DIR does not exist."
    exit 1
fi

# Gather all .photoslibrary directories
shopt -s nullglob
libs=()
for dir in "$LIB_DIR"/*.photoslibrary; do
    [[ -d "$dir" ]] && libs+=("$dir")
done
shopt -u nullglob

if [[ ${#libs[@]} -eq 0 ]]; then
    echo "No .photoslibrary files found in $LIB_DIR."
    exit 1
fi

# Prompt user to select a library by name
echo "Select a Photos library to switch to:"
PS3="Enter the number of your choice: "
# Build a list of library names (basename without extension)
names=()
for dir in "${libs[@]}"; do
    names+=( "$(basename "$dir" .photoslibrary)" )
done

select name in "${names[@]}"; do
    if [[ -n "${name:-}" ]]; then
        # Map selection back to full library path
        index=$((REPLY - 1))
        selected_lib="${libs[$index]}"
        break
    else
        echo "Invalid selection."
    fi
done

# Determine destination and ensure Pictures directory exists
dest="$PHOTOS_DIR/$(basename "$selected_lib")"
echo "Selected library: $selected_lib"
echo "Destination: $dest"
mkdir -p "$PHOTOS_DIR"

# Confirm overwrite if destination exists
if [[ -e "$dest" ]]; then
    read -r -p "$dest already exists. Overwrite? [y/N]: " confirm
    case "$confirm" in
        [yY]* ) rm -rf "$dest" ;;
        * ) echo "Aborting."; exit 0 ;;
    esac
fi

# Close Photos if running
if pgrep -x "Photos" > /dev/null; then
    echo "Closing Photos..."
    osascript -e 'tell application "Photos" to quit' || true
    while pgrep -x "Photos" > /dev/null; do sleep 1; done
else
    echo "Photos is not running."
fi

# Copy the selected library to Pictures via Finder (AppleScript) to preserve all metadata
echo "Copying library via Finder..."
osascript <<EOF
tell application "Finder"
  set srcLib to POSIX file "$selected_lib" as alias
  set destFolder to POSIX file "$HOME/Pictures" as alias
  set newLib to duplicate srcLib to destFolder with replacing
  set name of newLib to "$(basename "$selected_lib")"
end tell
EOF

# Open Photos with the new library
echo "Opening Photos with the new library..."
open -a "Photos" "$dest"

echo "Done."
