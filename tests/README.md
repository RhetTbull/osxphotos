# Tests for osxphotos #

## Running Tests ##
To set up a dev environment to work on osxphotos code or run tests follow these steps.  This assumes you have python 3.7 or later installed.  If you need to install python, you can do so with the XCode command lines tools (`xcode-select --install`) or from [python.org](https://www.python.org/downloads/macos/).

- `git clone git@github.com:RhetTbull/osxphotos.git`
- `cd osxphotos`
- `python3 -m venv venv`
- `source venv/bin/activate`
- `python3 -m pip install -r dev_requirements.txt`
- `python3 -m pip install -e .`

To run the tests, do the following from the main source folder:
`python3 -m pytest tests/`


## Skipped Tests ##
A few tests will look for certain environment variables to determine if they should run.

Some of the export tests rely on photos in my local library and will look for `OSXPHOTOS_TEST_EXPORT=1` to determine if they should run.

One test for locale does not run on GitHub's automated workflow and will look for `OSXPHOTOS_TEST_LOCALE=1` to determine if it should be run.  If you want to run this test, set the environment variable.  

## Test Photo Libraries
**Important**: The test code uses several test photo libraries created on various version of MacOS.  If you need to inspect one of these or modify one for a test, make a copy of the library (for example, copy it to your ~/Pictures folder) then open the copy in Photos.  Once done, copy the revised library back to the tests/ folder.  If you do not do this, the Photos background process photoanalysisd will forever try to process the library resulting in updates to the database which will cause git to see changes to the file you didn't intend.  I'm not aware of any way to disassociate photoanalysisd from the library once you've opened it in Photos.

## Attribution ##
These tests utilize a test Photos library. The test library is populated with photos from [flickr](https://www.flickr.com) and from my own photo library.  All images used are licensed under Creative Commons 2.0 Attribution [license](https://creativecommons.org/licenses/by/2.0/).  

Flickr images used from:
- [Jeff Hitchcock](https://www.flickr.com/photos/arbron/48353451872/)
- [Carlos Montesdeoca](https://www.flickr.com/photos/carlosmontesdeocastudio)
- [Rydale Clothing](https://www.flickr.com/photos/rydaleclothing)
- [Marco Verch](https://www.flickr.com/photos/30478819@N08/48228222317/)
- [K M](https://www.flickr.com/photos/153387643@N08/49334338022/)
- [Shelby Mash](https://www.flickr.com/photos/shelbzyleigh/3809603052)
- [Rory MacLeod](https://www.flickr.com/photos/macrj/6969547134)
- [Md. Al Amin](https://www.flickr.com/photos/alamin_bd/45207044465)
- [Fatlum Haliti](https://www.flickr.com/photos/lumlumi/363449752)
- [Benny Mazur](https://www.flickr.com/photos/benimoto/399012465)
- [Sara Cooper PR](https://www.flickr.com/photos/saracooperpr/6422472677)
- [herval](https://www.flickr.com/photos/herval/2403994289)
- [Vox Efx](https://www.flickr.com/photos/vox_efx/141137669)
- [Bill Strain](https://www.flickr.com/photos/billstrain/5117042252)
- [Guilherme Yagui](https://www.flickr.com/photos/yagui7/15895161088/)
- [Deborah Austin](https://www.flickr.com/photos/littledebbie11/8703591799/)
- [We Are Social](https://www.flickr.com/photos/wearesocial/23309711462/)
- [cloud.shepherd](https://www.flickr.com/photos/exnucboy1/31017877125)

