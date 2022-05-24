#!/bin/sh

# script to help build osxphotos release
# this is unique to my own dev setup

echo "Cleaning old build and dist directories"
rm -rf dist
rm -rf build

echo "Updated phototemplate.md"
cog -d -o osxphotos/phototemplate.md osxphotos/phototemplate.cog.md

echo "Updating README.md"
python3 utils/update_readme.py

echo "Updating API_README.md"
cog -r API_README.md

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
echo "Building docs"
(cd docsrc && make github && make pdf)

# copy docs to osxphotos/docs/docs.zip for use with `osxphotos docs` command
echo "Zipping docs to osxphotos/docs/docs.zip"
rm osxphotos/docs/docs.zip
zip -r osxphotos/docs/docs.zip docs/*

# build the package
echo "Building package"
python3 -m build

# build CLI executable
echo "Building CLI executable"
./make_cli_exe.sh
