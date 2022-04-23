#!/bin/sh

# script to help build osxphotos release
# this is unique to my own dev setup

rm -rf dist; rm -rf build
python3 utils/update_readme.py

# stage and convert markdown to rst
echo "Copying osxphotos/tutorial.md to docsrc/source/tutorial.md"
cp osxphotos/tutorial.md docsrc/source/tutorial.md
rm docsrc/source/tutorial.rst
m2r2 docsrc/source/tutorial.md
rm docsrc/source/tutorial.md

echo "Generating template help docs"
rm docsrc/source/template_help.rst
python3 utils/generate_template_docs.py
m2r2 docsrc/source/template_help.md
rm docsrc/source/template_help.md

# build docs
(cd docsrc && make github && make docs && make pdf)

# build the package
python3 -m build

# build CLI executable
./make_cli_exe.sh
