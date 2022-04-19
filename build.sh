#!/bin/sh

# script to help build osxphotos release
# this is unique to my own dev setup

# source venv/bin/activate
rm -rf dist; rm -rf build
python3 utils/update_readme.py
(cd docsrc && make github && make docs && make pdf)
# python3 setup.py sdist bdist_wheel
python3 -m build
./make_cli_exe.sh
