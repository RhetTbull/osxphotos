""" Utilities for working with the Photokit framework on macOS """

import time

from osxphotos.platform import is_macos

if is_macos:
    from osxphotos.photokit import (
        check_photokit_authorization,
        request_photokit_authorization,
    )

# seconds to wait for user to grant authorization
WAIT_FOR_AUTHORIZATION_TIMEOUT = 10

# seconds to sleep between authorization check
AUTHORIZATION_SLEEP = 0.25


def wait_for_photokit_authorization() -> bool:
    """Request and wait for authorization to access Photos library."""
    if check_photokit_authorization():
        return True
    start_time = time.time()
    request_photokit_authorization()
    while not check_photokit_authorization():
        time.sleep(AUTHORIZATION_SLEEP)
        if time.time() > start_time + WAIT_FOR_AUTHORIZATION_TIMEOUT:
            return False
    return True
