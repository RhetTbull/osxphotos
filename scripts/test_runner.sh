#!/bin/bash

# OSXPhotos Test Runner
# Provides an interactive menu for running different test suites

set -e

# Function to safely kill Photos and related processes
cleanup_photos() {
    echo "Cleaning up Photos processes..."
    # Kill Photos app (ignore errors if not running)
    killall Photos 2>/dev/null || true
    sleep 2
    # launch Photos
    open -a Photos
}

echo "==============================================="
echo "           OSXPhotos Test Runner"
echo "==============================================="
echo
echo "Select which tests to run:"
echo
echo "1) Normal tests (default - just press Enter)"
echo "2) Add Album tests (--addalbum)"
echo "3) Timewarp tests (--timewarp)"
echo "4) Photodates tests (--photodates)"
echo "5) Import tests (--test-import)"
echo "6) Import Takeout tests (--test-import-takeout)"
echo "7) Sync tests (--test-sync)"
echo "8) Add Locations tests (--test-add-locations)"
echo "9) Batch Edit tests (--test-batch-edit)"
echo "q) Quit"
echo

read -p "Enter your choice [1]: " choice

# Default to option 1 if just Enter is pressed
choice=${choice:-1}

case $choice in
    1|"")
        echo "Running normal tests..."
        python -m pytest -vv
        ;;
    2)
        echo "Running add album tests..."
        echo "NOTE: These tests require interaction with Photos and configuring a specific test library."
        echo "Currently these run only on Catalina. Only one interactive test can be run at a time."
        cleanup_photos
        python -m pytest -vv tests/test_photosalbum_unicode.py tests/test_cli_add_to_album.py --addalbum
        ;;
    3)
        echo "Running timewarp tests..."
        echo "NOTE: These tests require interaction with Photos and configuring a specific test library."
        echo "Only one interactive test can be run at a time."
        cleanup_photos
        python -m pytest -vv --timewarp tests/test_cli_timewarp.py
        ;;
    4)
        echo "Running photodates tests..."
        echo "NOTE: These tests require interaction with Photos and configuring a specific test library."
        echo "Only one interactive test can be run at a time."
        cleanup_photos
        python -m pytest -vv --photodates tests/test_photodates.py
        ;;
    5)
        echo "Running import tests..."
        echo "NOTE: These tests require interaction with Photos and configuring a specific test library."
        echo "Only one interactive test can be run at a time."
        cleanup_photos
        python -m pytest -vv --test-import tests/test_cli_import.py
        ;;
    6)
        echo "Running import takeout tests..."
        echo "NOTE: These tests require interaction with Photos and configuring a specific test library."
        echo "Only one interactive test can be run at a time."
        cleanup_photos
        python -m pytest -vv --test-import-takeout tests/test_cli_import.py
        ;;
    7)
        echo "Running sync tests..."
        echo "NOTE: These tests require interaction with Photos and configuring a specific test library."
        echo "Only one interactive test can be run at a time."
        cleanup_photos
        python -m pytest -vv --test-sync tests/test_cli_sync.py
        ;;
    8)
        echo "Running add locations tests..."
        echo "NOTE: These tests require interaction with Photos and configuring a specific test library."
        echo "Only one interactive test can be run at a time."
        cleanup_photos
        python -m pytest -vv --test-add-locations tests/test_cli_add_locations.py
        ;;
    9)
        echo "Running batch edit tests..."
        echo "NOTE: These tests require interaction with Photos and configuring a specific test library."
        echo "Only one interactive test can be run at a time."
        cleanup_photos
        python -m pytest -vv --test-batch-edit -k batch
        ;;
    q|Q)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice. Please run the script again and select a valid option."
        exit 1
        ;;
esac

echo
echo "Test run completed!"
