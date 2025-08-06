import subprocess
import sys
import pytest

def test_mcp_server_help():
    """Test that the mcp-server command shows help."""
    process = subprocess.run(
        [sys.executable, "-m", "osxphotos", "mcp-server", "--help"],
        capture_output=True,
        text=True,
    )
    assert process.returncode == 0
    assert "Usage: python -m osxphotos mcp-server" in process.stdout
