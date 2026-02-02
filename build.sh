#!/bin/sh

# script to help build osxphotos release
# this is unique to my own dev setup

echo "Cleaning old build and dist directories"
rm -rf dist
rm -rf build

echo "Clear Sphinx caches"
# find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
rm -rf docsrc/_build

echo "Updated phototemplate.md"
cog -d -o osxphotos/phototemplate.md osxphotos/phototemplate.cog.md

echo "Updating README.md"
python3 utils/update_readme.py
cog -r README.md

echo "Updating API_README.md"
cog -r API_README.md

echo "Updating overview.rst"
cog -d -o docsrc/source/overview.rst docsrc/source/overview.cog.rst

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

echo "Copying API_README.md to docsrc/source/API_README.md"
rm docsrc/source/API_README.rst
cp API_README.md docsrc/source/API_README.md
m2r2 docsrc/source/API_README.md
rm docsrc/source/API_README.md
# Convert all named hyperlink references to anonymous references
# to avoid "Duplicate explicit target name" Sphinx warnings
sed -i '' -E 's/(\`[^<]+<[^>]+>\`)_([^_])/\1__\2/g' docsrc/source/API_README.rst

# build docs
echo "Building docs"
(cd docsrc && make clean && make github)

# copy docs to osxphotos/docs/docs.zip for use with `osxphotos docs` command
echo "Zipping docs to osxphotos/docs/docs.zip"
rm osxphotos/docs/docs.zip
zip -r osxphotos/docs/docs.zip docs/* -x "docs/screencast/*"

# build the package
echo "Building package"
python3 -m build

# build CLI executable
echo "Building CLI executable"
./make_cli_exe.sh

# sign the executable
echo "Signing CLI executable"
codesign --force --sign "$DEVELOPER_ID_APPLICATION" dist/osxphotos

# zip up CLI executable
echo "Zipping CLI executable"
OSXPHOTOSVERSION=$(python3 -c "import osxphotos; print(osxphotos.__version__)")
ARCHSTR=$(uname -m)
ZIPNAME=osxphotos_MacOS_exe_darwin_${ARCHSTR}_v${OSXPHOTOSVERSION}.zip
echo "Zipping CLI executable to $ZIPNAME"
cd dist && zip $ZIPNAME osxphotos && cd ..
rm dist/osxphotos
