#!/bin/sh

# This will build an stand-alone executable called 'osxphotos' in your ./dist directory
# using pyinstaller
# If you need to install pyinstaller:
# python3 -m pip install --upgrade pyinstaller

set -e
# mkdir -p build
# clang -shared -mmacosx-version-min=10.12 disclaim.cpp -o build/libdisclaim.dylib
pyinstaller osxphotos.spec
