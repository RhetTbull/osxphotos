#!/bin/bash

#################################################################################
# PyApp Runner
# Very simple CI for building/packaging python project on Mac via PyApp and AppleCrate
# This script is used to build and copy the PyApp executable from a remote server.
# It also packages the executable with applecrate, signs it, and
# copies it back to the local machine.
#
# Usage: pyapp-runner.sh SERVER PROJECT_NAME PROJECT_VERSION
#
# SERVER is the nick name of the remote server and will be combined with
# $PYAPP_SERVER_ to get the actual server name
# In my case, I have the following values for the server in my ~/.zshrc file:
# export PYAPP_SERVER_INTEL="address of Intel Mac"
# export PYAPP_SERVER_ARM="address of Apple Silicon Mac"
# export PYAPP_USER="username" # the username to use for ssha
#
# The remote server must have the following environment variables set in the ~/.zshenv:
# export PYAPP="/Users/johndoe/code/pyapp-latest" # the install location of pyapp
# export DEVELOPER_ID_APPLICATION="Developer ID Application: John Doe (XXXXXXXX)" # signing identity
# export KEYCHAIN_PASSWORD="password" # password for the keychain where signing identity is stored
# export CODE_DIR="/Users/johndoe/code" # the directory where the code is located
# This script assumes the code for the project is located in the directory
#   $CODE_DIR/$PROJECT_NAME
#
# For code signing to work via ssh, you must first run this one time on the machine via GUI
#
# References:
# See https://ofek.dev/pyapp/latest/how-to/ for more information on PyApp.
# See https://github.com/RhetTbull/applecrate for more information on AppleCrate.
# See https://developer.apple.com/forums/thread/712005 for more information on signing via ssh
#################################################################################

# Check that all 3 arguments are provided
if [ $# -ne 3 ]; then
    echo "Usage: $0 SERVER PROJECT_NAME PROJECT_VERSION"
    exit 1
fi

SERVER=$1
PROJECT_NAME=$2
PROJECT_VERSION=$3

# verify PROJECT_VERSION is valid
# PyApp will happily build with an invalid version number
# get directory of this script
# DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYPI_VERSION=$(python scripts/get_latest_pypi_version.py $PROJECT_NAME)
if [ "$PYPI_VERSION" != "$PROJECT_VERSION" ]; then
    echo "Invalid version number: $PROJECT_VERSION"
    echo "Latest version on PyPI: $PYPI_VERSION"
    echo "Did you forget to run 'flit publish'?"
    exit 1
fi

# define the remote server and user
# assumes ssh keys are setup for the user
# Set these directly or read from environment variables
USER=$PYAPP_USER

SERVER=$(echo $SERVER | tr '[:lower:]' '[:upper:]')
SERVER=PYAPP_SERVER_$SERVER
SERVER=${!SERVER}

if [ -z "$SERVER" ]; then
    echo "Server not found: $1"
    exit 1
fi

echo "Building on $SERVER"

# Connect to the remote server
ssh ${USER}@${SERVER} 'bash -l -s' << ENDSSH
# Commands to run on remote host
cd \$PYAPP

# clean the build directory
rm -f target/release/pyapp

# build the project
PYAPP_PROJECT_NAME=${PROJECT_NAME} PYAPP_PROJECT_VERSION=${PROJECT_VERSION} cargo build --release

if [ \$? -ne 0 ]; then
    echo "Build failed"
    exit 1
fi

# sign the binary
# For this to work via ssh, you must first run this one time on the machine via GUI
# Then click "Always Allow" when prompted to always allow codesign to access the key in the future

echo "Unlocking keychain"
security unlock-keychain -p \$KEYCHAIN_PASSWORD

if [ \$? -ne 0 ]; then
    echo "Failed to unlock keychain"
    exit 1
fi

echo "Signing the binary with \$DEVELOPER_ID_APPLICATION"
codesign --force -s "\$DEVELOPER_ID_APPLICATION" target/release/pyapp

if [ \$? -ne 0 ]; then
    echo "Codesign failed"
    exit 1
fi

# package the binary
mkdir -p "\${CODE_DIR}/${PROJECT_NAME}/build"
TARGET="\${CODE_DIR}/${PROJECT_NAME}/build/${PROJECT_NAME}-${PROJECT_VERSION}-\$(uname -m)"
echo "Copying target/release/pyapp to \$TARGET"
cp "target/release/pyapp" \$TARGET

echo "Changing to \${CODE_DIR}/${PROJECT_NAME}"
cd \${CODE_DIR}/${PROJECT_NAME}
echo "Pulling latest code and building package"
git pull
applecrate build

if [ \$? -ne 0 ]; then
    echo "Package build failed"
    exit 1
fi

echo "Done building $PROJECT_NAME"

ENDSSH

if [ $? -ne 0 ]; then
    echo "Build failed"
    exit 1
fi

# Copy the binary from the remote server
# If server IP is same as local IP, then skip the copy
LOCAL_IP=$(ipconfig getifaddr en0)
REMOTE_IP=$(ssh ${USER}@${SERVER} 'ipconfig getifaddr en0')
if [ "$LOCAL_IP" == "$REMOTE_IP" ]; then
    echo "Building on local machine, skipping copy from $SERVER to $LOCAL_IP"
    exit 0
fi
PYAPP_PATH=$(ssh ${USER}@${SERVER} 'echo $PYAPP')
PYAPP_ARCH=$(ssh ${USER}@${SERVER} 'uname -m')
CODE_DIR_SERVER=$(ssh ${USER}@${SERVER} 'echo "${CODE_DIR%/}"')
mkdir -p dist
PACKAGE="${PROJECT_NAME}-${PROJECT_VERSION}-${PYAPP_ARCH}-installer.pkg"
TARGET="dist/${PACKAGE}"
echo "Copying $PACKAGE from $SERVER to $TARGET"
scp ${USER}@${SERVER}:"${CODE_DIR_SERVER}/${PROJECT_NAME}/dist/$PACKAGE" $TARGET

echo "Done: ${TARGET}"
