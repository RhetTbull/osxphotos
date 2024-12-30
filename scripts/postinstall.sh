#!/bin/bash

# This script used by applecrate to install the applecrate executable
# into the /usr/local/bin directory
# It will link the correct executable depending on machine CPU
# The applecrate binaries should be named as follows:
# {{ app }}-{{ version }}-x86_64 or {{ app }}-{{ version }}-arm64
# and they should be installed with the following directory structure:
# /Library/Application Support/{{ app }}/{{ version }}/{{ app }}-{{ version }}-x86_64
# /Library/Application Support/{{ app }}/{{ version }}/{{ app }}-{{ version }}-arm64


# CPU will be x86_64 or arm64
CPU=$(uname -m)

ln -s "/Library/Application Support/{{ app }}/{{ version }}/{{ app }}-{{ version }}-$CPU" "/usr/local/bin/applecrate"
chmod 755 "/usr/local/bin/applecrate"
