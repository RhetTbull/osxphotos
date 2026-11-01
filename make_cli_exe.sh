#!/bin/sh

# This will build an stand-alone executable called 'osxphotos' in your ./dist directory
# using pyinstaller
# If you need to install pyinstaller:
# python3 -m pip install --upgrade pyinstaller

set -e
pyinstaller osxphotos.spec

# Smoke test the executable before it is signed and packaged.
# Modules PyInstaller fails to bundle (e.g. dynamic imports, see #2283)
# only show up as a ModuleNotFoundError when the binary runs.
echo "Smoke testing dist/osxphotos"
EXPECTED_VERSION=$(python3 -c "import osxphotos; print(osxphotos.__version__)")
if ! VERSION_OUTPUT=$(./dist/osxphotos --version 2>&1); then
    echo "Smoke test failed: dist/osxphotos --version exited with an error:"
    echo "$VERSION_OUTPUT"
    exit 1
fi
if ! echo "$VERSION_OUTPUT" | grep -q "version $EXPECTED_VERSION"; then
    echo "Smoke test failed: expected version $EXPECTED_VERSION, got:"
    echo "$VERSION_OUTPUT"
    exit 1
fi
if ! HELP_OUTPUT=$(./dist/osxphotos --help 2>&1); then
    echo "Smoke test failed: dist/osxphotos --help exited with an error:"
    echo "$HELP_OUTPUT"
    exit 1
fi
# "osxphotos run" scripts can import modules that aren't loaded at startup
if ! RUN_OUTPUT=$(./dist/osxphotos run utils/smoke_test_run.py --package-dir osxphotos 2>&1); then
    echo "Smoke test failed: dist/osxphotos run utils/smoke_test_run.py exited with an error:"
    echo "$RUN_OUTPUT"
    exit 1
fi
echo "$RUN_OUTPUT"
echo "Smoke test passed: osxphotos $EXPECTED_VERSION"
