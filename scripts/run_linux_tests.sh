#!/bin/bash
# Run linux tests on macOS
# Requires colima and docker to be installed:
# brew install colima docker docker-buildx
#
# docker-buildx is a Docker plugin. For Docker to find the plugin, add "cliPluginsExtraDirs" to ~/.docker/config.json:
#    "cliPluginsExtraDirs": [
#      "$HOMEBREW_PREFIX/lib/docker/cli-plugins"
#    ]
#
# NOTE: in above, replace "$HOMEBREW_PREFIX" with the actual path to your Homebrew installation, for example '/opt/homebrew' on Apple Silicon
#
# Usage: ./run_linux_tests.sh [--python VERSION] [--build] [PYTEST_ARGS...]
# Example: ./run_linux_tests.sh --python 3.13 -vv -k export
#
# Use --build to rebuild the custom Docker image with dependencies
# First time setup: ./run_linux_tests.sh --python 3.13 --build
# If you need to rebuild the image, use the --build flag
# Once built, you can run tests with ./run_linux_tests.sh
# You should only need to rebuild the image if you change the Dockerfile or the dependencies in requirements.txt
#

# Default arguments
PYTHON_VERSION="3.13"
PYTEST_ARGS=""
BUILD_IMAGE=false

# Memory in GB for the Docker container; tests fail if run with default 2GB
CONTAINER_MEMORY=8

while [[ $# -gt 0 ]]; do
  case $1 in
    --python)
      PYTHON_VERSION="$2"
      shift 2
      ;;
    --build)
      BUILD_IMAGE=true
      shift
      ;;
    *)
      # All remaining arguments are pytest args
      PYTEST_ARGS="$@"
      break
      ;;
  esac
done

# Use default pytest args if none provided
if [ -z "$PYTEST_ARGS" ]; then
  PYTEST_ARGS="-vv tests/"
fi

# Check if colima is already running
COLIMA_WAS_RUNNING=false
if colima status 2>&1 | grep -q "colima is running"; then
  COLIMA_WAS_RUNNING=true
else
  colima start --memory ${CONTAINER_MEMORY}
fi

# Image name for cached container
IMAGE_NAME="osxphotos-test:${PYTHON_VERSION}"

# Build custom image if requested or if it doesn't exist
if [ "$BUILD_IMAGE" = true ] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
  echo "Building Docker image: $IMAGE_NAME"
  docker buildx build \
    --load \
    --build-arg PYTHON_VERSION=${PYTHON_VERSION} \
    -t "$IMAGE_NAME" \
    -f scripts/Dockerfile.linux-tests \
    .
fi

docker run --rm -it \
  -e TZ=America/Chicago \
  -v "$(pwd):/workspace" \
  -w /workspace \
  "$IMAGE_NAME" \
  bash -c "
    # Run tests
    python -m pytest ${PYTEST_ARGS}
  "

# Only stop colima if we started it
if [ "$COLIMA_WAS_RUNNING" = false ]; then
  colima stop
fi
