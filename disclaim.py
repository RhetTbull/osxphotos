def _pyi_rthook():
    import sys
    if sys.platform != 'darwin':
        return

    # Avoid redundant disclaims
    import os
    if os.environ.get('PYI_DISCLAIMED'):
        return
    os.environ['PYI_DISCLAIMED'] = '1'

    # The bootloader has cleared the _MEIPASS2 environment variable by the
    # time we get here, which means re-launching the executable disclaimed
    # will unpack the binary again. To avoid this we reset _MEIPASS2 again,
    # so that our re-launch will pick up at second stage of the bootstrap.
    os.environ['_MEIPASS2'] = sys._MEIPASS

    import ctypes
    library_path = os.path.join(sys._MEIPASS, 'libdisclaim.dylib')
    libdisclaim = ctypes.cdll.LoadLibrary(library_path)
    libdisclaim.disclaim()

_pyi_rthook()
del _pyi_rthook
