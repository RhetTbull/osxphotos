# Library files

This directory contains pre-built binary libraries used by osxphotos.

The `libdisclaim_arm64.dylib` and `libdisclaim_x86_64.dylib` libraries are loaded by `disclaim.py`
to allow osxphotos to be responsible for it's own permission handling. This allows osxphotos to
prompt the user to provide access to the Photos library instead of relying on the Terminal to do so.

## Building the libraries

To build these libraries, run the following command:

On Intel Mac:

```bash
clang -shared -mmacosx-version-min=10.12 disclaim.cpp -o osxphotos/lib/libdisclaim_x86_64.dylib
```

On Apple Silicon Mac:

```bash
clang -shared -mmacosx-version-min=10.12 disclaim.cpp -o osxphotos/lib/libdisclaim_arm64.dylib
```
