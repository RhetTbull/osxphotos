# Run linux tests on macOS
# Requires colima and docker to be installed:
# brew install colima docker

colima stop
colima start --memory 8
docker run --rm -it \
    -e TZ=America/Chicago \
  -v "$(pwd):/workspace" \
  -w /workspace \
  python:3.13 \
  bash -c "
    # Install system dependencies
    apt-get update && apt-get install -y exiftool curl &&

    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh &&
    source \$HOME/.local/bin/env &&

    # Install Python dependencies
    uv pip install --system -r requirements.txt &&
    uv pip install --system -r dev_requirements.txt &&

    # Run tests
    python -m pytest -v tests/
  "
  colima stop
