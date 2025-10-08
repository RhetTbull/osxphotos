#!/bin/bash
# Run linux tests on macOS
# Requires colima and docker to be installed:
# brew install colima docker
#
# Usage: ./run_linux_tests.sh [--python VERSION] [PYTEST_ARGS...]
# Example: ./run_linux_tests.sh --python 3.13 -vv -k export

# Default arguments
PYTHON_VERSION="3.13"
PYTEST_ARGS="-vv tests/"

# Memory in GB for the Docker container; tests fail if run with default 2GB
CONTAINER_MEMORY=8

while [[ $# -gt 0 ]]; do
  case $1 in
    --python)
      PYTHON_VERSION="$2"
      shift 2
      ;;
    *)
      # First non-option argument starts pytest args
      PYTEST_ARGS="$@"
      break
      ;;
  esac
done

# Check if colima is already running
COLIMA_WAS_RUNNING=false
if colima status 2>&1 | grep -q "colima is running"; then
  COLIMA_WAS_RUNNING=true
else
  colima start --memory ${CONTAINER_MEMORY}
fi

docker run --rm -it \
    -e TZ=America/Chicago \
  -v "$(pwd):/workspace" \
  -w /workspace \
  python:${PYTHON_VERSION} \
  bash -c "
    # Install system dependencies
    apt-get update && apt-get install -y libimage-exiftool-perl curl tzdata &&

    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh &&
    source \$HOME/.local/bin/env &&

    # Install Python dependencies
    uv pip install --system -r requirements.txt &&
    uv pip install --system -r dev_requirements.txt &&

    # Run tests
    python -m pytest ${PYTEST_ARGS}
  "

# Only stop colima if we started it
if [ "$COLIMA_WAS_RUNNING" = false ]; then
  colima stop
fi
