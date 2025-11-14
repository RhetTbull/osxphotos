""" Kill all instances of the Photos app and detect whether the kill succeeded. """
import subprocess
from .cli_commands import echo_error


def kill_photos():
    """ Run 'killall Photos' when Photos generates too many errors in response
    to operations like Import. 
    """
    try:
        # Run 'killall Photos' and capture output
        result = subprocess.run(
            ["killall", "Photos"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        # Exit code 0 means success (process found and killed)
        if result.returncode == 0:
            echo_error("✅  Photos app was terminated successfully.")
            return True
        # Exit code 1 usually means "no matching process"
        if "No matching processes" in result.stderr:
            echo_error("ℹ️  Photos app was not running.")
            return False

        # Unknown issue/error
        echo_error(f"⚠️  Unknown issue:\n{result.stderr}")
        return False

    # Command killall not found
    except FileNotFoundError:
        echo_error("❌  'killall' command not found. Are you running on macOS?")
        return False
