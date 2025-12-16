# Linux Testing with Docker

This directory contains scripts for running osxphotos tests in a Linux environment using Docker and Colima.

## Prerequisites

```bash
brew install colima docker docker-buildx
```

## First Time Setup

Build the custom Docker image with all dependencies pre-installed:

```bash
# Build for Python 3.13 (default)
./scripts/run_linux_tests.sh --build

# Build for a specific Python version
./scripts/run_linux_tests.sh --python 3.12 --build
```

This creates a cached image with exiftool, uv, and all Python dependencies installed. The image is named `osxphotos-test:VERSION`.

## Running Tests

After the image is built, run tests without the `--build` flag for faster execution:

```bash
# Run all tests with Python 3.13
./scripts/run_linux_tests.sh

# Run with specific Python version
./scripts/run_linux_tests.sh --python 3.12

# Pass pytest arguments
./scripts/run_linux_tests.sh -k export
./scripts/run_linux_tests.sh -vv tests/test_export.py::test_export_1

# Combine options
./scripts/run_linux_tests.sh --python 3.11 -k "test_export and not slow"
```

## Rebuilding the Image

Rebuild when dependencies change:

```bash
./scripts/run_linux_tests.sh --build
```

## How It Works

1. **Dockerfile.linux-tests**: Defines the test environment with all system and Python dependencies
2. **run_linux_tests.sh**:
   - Manages Colima lifecycle (starts if not running, preserves if already running)
   - Builds the Docker image if needed (first run or with `--build`)
   - Mounts the current directory and runs pytest with your arguments

## Available Images

Build separate images for each Python version you need to test:

```bash
./scripts/run_linux_tests.sh --python 3.11 --build
./scripts/run_linux_tests.sh --python 3.12 --build
./scripts/run_linux_tests.sh --python 3.13 --build
```

Each creates a tagged image: `osxphotos-test:3.11`, `osxphotos-test:3.12`, `osxphotos-test:3.13`
