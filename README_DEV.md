# Developer Notes for osxphotos

These are notes for developers working on osxphotos. They're mostly to help me remember how to do things in this repo but will be useful to anyone who wants to contribute to osxphotos.

## Installing osxphotos

- Clone the repo: `git clone git@github.com:RhetTbull/osxphotos.git`
- Create a virtual environment and activate it: `python3 -m venv venv` then `source venv/bin/activate`.  I use [pyenv](https://github.com/pyenv/pyenv) with [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) to manage my virtual environments
- Install the requirements: `python3 -m pip install -r requirements.txt`
- Install the development requirements: `python3 -m pip install -r dev_requirements.txt`
- Install osxphotos: `python3 -m pip install -e .`

## Running tests

- Run all tests: `pytest`

See the [test README.md](tests/README.md) for more information on running tests.

## Opening a pull request

If you want to contribute to osxphotos, please open a pull request. Here's how to do it:

- Fork the repo on GitHub
- Clone your fork: `git clone git@github.com:YOUR_USERNAME/osxphotos.git`
- Create a virtual environment and install osxphotos as described above
- Create a branch for your changes: `git checkout -b my_branch`
- Make your changes
- Add tests for your changes
- Run the tests: `pytest`
- Format the code: `isort .` then `black .`
- Update the README.md and other files as needed
- Add your changes using `git add`
- Commit your changes: `git commit -m "My changes description"`
- Push your changes to your fork: `git push origin my_branch`
- Open a [pull request on GitHub](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request)

## Building the package and executable

**Note**: Do not do this unless you are releasing a new version of osxphotos. This should not be run for normal pull requests. In general, only the maintainer should run the build script.

- Run `./build.sh` to run the build script.

## Other Notes

[cogapp](https://nedbatchelder.com/code/cog/index.html) is used to update the README.md and other files. cog will be called from the build script as needed.

There are some pre-built libraries in the `osxphotos/lib` directory. These are used by osxphotos to handle permissions. If you need to rebuild these libraries, see the [README_DEV.md](osxphotos/lib/README_DEV.md) file in the `osxphotos/lib` directory.
