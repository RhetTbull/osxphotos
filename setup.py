#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# setup.py script for osxphotos
#
# Copyright (c) 2019, 2020, 2021 Rhet Turnbull, rturnbull+git@gmail.com
# All rights reserved.
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import platform

from setuptools import find_packages, setup

# python version as 2-digit float (e.g. 3.6)
py_ver = float(".".join(platform.python_version_tuple()[:2]))

# holds config info read from disk
about = {}
this_directory = os.path.abspath(os.path.dirname(__file__))

# get version info from _version
with open(
    os.path.join(this_directory, "osxphotos", "_version.py"), mode="r", encoding="utf-8"
) as f:
    exec(f.read(), about)

# read README.md into long_description
with open(os.path.join(this_directory, "README.rst"), encoding="utf-8") as f:
    about["long_description"] = f.read()

setup(
    name="osxphotos",
    version=about["__version__"],
    description="Export photos from Apple's macOS Photos app and query the Photos library database to access metadata about images.",
    long_description=about["long_description"],
    long_description_content_type="text/x-rst",
    author="Rhet Turnbull",
    author_email="rturnbull+git@gmail.com",
    url="https://github.com/RhetTbull/",
    project_urls={"GitHub": "https://github.com/RhetTbull/osxphotos"},
    download_url="https://github.com/RhetTbull/osxphotos",
    packages=find_packages(exclude=["tests", "examples", "utils"]),
    license="License :: OSI Approved :: MIT License",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: MacOS X",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=[
        "Click>=8.0.4,<9.0",
        "Mako>=1.1.4,<1.2.0",
        "PyYAML>=5.4.1,<5.5.0",
        "bitmath>=1.3.3.1,<1.4.0.0",
        "bpylist2==3.0.2",
        "more-itertools>=8.8.0,<9.0.0",
        "objexplore>=1.6.3,<2.0.0",
        "osxmetadata>=0.99.34,<1.0.0",
        "pathvalidate>=2.4.1,<3.0.0",
        "photoscript>=0.1.4,<0.2.0",
        "ptpython>=3.0.20,<4.0.0",
        "pyobjc-core>=7.3,<9.0",
        "pyobjc-framework-AVFoundation>=7.3,<9.0",
        "pyobjc-framework-AppleScriptKit>=7.3,<9.0",
        "pyobjc-framework-AppleScriptObjC>=7.3,<9.0",
        "pyobjc-framework-Cocoa>=7.3,<9.0",
        "pyobjc-framework-CoreServices>=7.2,<9.0",
        "pyobjc-framework-Metal>=7.3,<9.0",
        "pyobjc-framework-Photos>=7.3,<9.0",
        "pyobjc-framework-Quartz>=7.3,<9.0",
        "pyobjc-framework-Vision>=7.3,<9.0",
        "rich>=11.2.0,<12.0.0",
        "textx>=2.3.0,<3.0.0",
        "toml>=0.10.2,<0.11.0",
        "wurlitzer>=2.1.0,<3.0.0",
    ],
    entry_points={"console_scripts": ["osxphotos=osxphotos.__main__:cli"]},
    include_package_data=True,
)
