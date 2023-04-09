# Developer Notes for osxphotos

These are notes for developers working on osxphotos. They're mostly to help me remember how to do things in this repo but will be useful to anyone who wants to contribute to osxphotos.

## Installing osxphotos

- Clone the repo: `git clone git@github.com:RhetTbull/osxphotos.git`
- Create a virtual environment and activate it: `python3 -m venv venv` then `source venv/bin/activate`.  I use [pyenv](https://github.com/pyenv/pyenv) with [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) to manage my virtual environments
- Install the requirements: `pip install -r requirements.txt`
- Install the development requirements: `pip install -r dev_requirements.txt`
- Install osxphotos: `pip install -e .`

## Running tests

- Run all tests: `pytest`

See the [test README.md](tests/README.md) for more information on running tests.

## Building the package

- Run `./build.sh` to run the build script.

## Other Notes

[cogapp](https://nedbatchelder.com/code/cog/index.html) is used to update the README.md and other files. cog will be called from the build script as needed.
