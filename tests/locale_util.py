""" Helpers for running locale-dependent tests """

import locale

import pytest


def setlocale(typ, name):
    try:
        with contextlib.suppress(Exception):
            locale.setlocale(typ, name)
        # On Linux UTF-8 locales are separate
        locale.setlocale(typ, f"{name}.UTF-8")
    except locale.Error:
        pytest.skip(f"Locale {name} not available")
