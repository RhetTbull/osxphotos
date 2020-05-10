# Tests for osxphotos #

## Running Tests ##
Tests require pytest and pytest-mock:
`pip install pytest`
`pip install pytest-mock`

To run the tests, do the following from the main source folder:
`python -m pytest tests/`

Running the tests this way allows the library to be tested without installing it.

## Skipped Tests ##
A few tests will look for certain environment variables to determine if they should run.

Some of the export tests rely on photos in my local library and will look for `OSXPHOTOS_TEST_EXPORT=1` to determine if they should run.

One test for locale does not run on GitHub's automated workflow and will look for `OSXPHOTOS_TEST_LOCALE=1` to determine if it should be run.  If you want to run this test, set the environment variable.  

## Attribution ##
These tests utilize a test Photos library. The test library is populated with photos from [flickr](https://www.flickr.com).  All images used are licensed under Creative Commons 2.0 Attribution [license](https://creativecommons.org/licenses/by/2.0/).  

Images used from:
- [Jeff Hitchcock](https://www.flickr.com/photos/arbron/48353451872/)
- [Carlos Montesdeoca](https://www.flickr.com/photos/carlosmontesdeocastudio)
- [Rydale Clothing](https://www.flickr.com/photos/rydaleclothing)
- [Marco Verch](https://www.flickr.com/photos/30478819@N08/48228222317/)
- [K M](https://www.flickr.com/photos/153387643@N08/49334338022/)


