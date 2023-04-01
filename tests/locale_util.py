""" Helpers for running locale-dependent tests """

import locale

import pytest


def setlocale(typ, name):
    try:
        try:
            locale.setlocale(typ, name)
        except: pass
        # On Linux UTF-8 locales are separate
        locale.setlocale(typ, name + ".UTF-8")
    except locale.Error:
        pytest.skip(f"Locale {name} not available")
