#!/bin/bash

# This script is very specific to my particular setup on my machine.
# It must be run after the package has been updated on PyPI.
# It uses `pyapp-runner.sh`, a simple CI script that runs via ssh,
# to build and sign the binaries for the package and then build the installer package.
#
# To run the script, run it from the project root directory:
# ./scripts/build_cli.sh
#

# Get the current version of the package from the source
PACKAGE_NAME="osxphotos"
VERSION=$(grep __version__ $PACKAGE_NAME/_version.py | cut -d "\"" -f 2)

# verify VERSION is valid
# PyApp will happily build with an invalid version number
# get directory of this script
# DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYPI_VERSION=$(python scripts/get_latest_pypi_version.py $PACKAGE_NAME)
if [ "$PYPI_VERSION" != "$VERSION" ]; then
    echo "Invalid version number: $VERSION"
    echo "Latest version on PyPI: $PYPI_VERSION"
    echo "Did you forget to run 'flit publish'?"
    exit 1
fi

# Build the binaries and package them
# arm64 binary built on a remote M1 Mac
# echo "Building version $VERSION for Apple Silicon"
# bash scripts/pyapp-runner.sh m1 $PACKAGE_NAME $VERSION

echo "Building version $VERSION for Intel"
bash scripts/pyapp-runner.sh macbook $PACKAGE_NAME $VERSION
