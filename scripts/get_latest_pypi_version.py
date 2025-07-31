"""Given a PyPI package name, print the latest version number of the package.

This uses the standard library instead of requests to avoid adding a dependency to the project.
"""

from __future__ import annotations

import json
import ssl
import sys
import urllib.request

VERSION_INFO_URL = "https://pypi.org/pypi/{}/json"


def get_latest_version(package_name: str) -> str:
    """Get latest version of package_name from PyPI"""
    try:
        url = VERSION_INFO_URL.format(package_name)
        ssl_context = ssl._create_unverified_context()
        response = urllib.request.urlopen(url, context=ssl_context)
        data = json.load(response)
        return data["info"]["version"]
    except Exception as e:
        raise ValueError(f"Error retrieving version for {package_name}: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} PACKAGE_NAME")
        sys.exit(1)
    package_name = sys.argv[1]
    try:
        print(get_latest_version(package_name))
    except ValueError as e:
        print(e)
        sys.exit(1)
