# Changelog

All notable changes to this project will be documented in this file.

## [v0.75.1](https://github.com/RhetTbull/osxphotos/compare/v0.75.0...v0.75.1)

Bug fixes, added `PhotoInfo.imported_by`, `{imported_by.name}`, `{imported_by.id}` templates, and `AlbumInfo.library_list_order`.

### 2026-01-03

#### Added

- Added `imported_by` property to `PhotoInfo` which returns tuple of display name and bundle ID of the app that imported the photo, e.g. (Halide, `com.lux.camera`), #1980
- Added `{imported_by.name}` and `{imported_by.id}` template fields for use in export templates, #1980
- Added `library_list_order` property to `AlbumInfo` and `FolderInfo` which returns the sort order of albums as they appear in the Photos library sidebar, #2054

#### Changed

- `osxphotos export` and `osxphotos import` now now handle original adjustment files (AAE files) for portrait photos that have not been edited, #2043

#### Removed

#### Fixed

- Fixed bug where `osxphotos import --exportdb` did not set favorite metadata if no other metadata (title, description, keywords) was present, #2059
- Fixed bug where album `folder_id` could be None, causing errors for iPhoto libraries, #2065
- Fixed `--added-after` and `--added-before` to accept dates without time when passed via TOML configuration files, #1925
- Fixed logging issue where osxphotos set root logging level to INFO, overriding settings in calling scripts, #2055

#### Contributors

* @RhetTbull [@RhetTbull](https://github.com/rhettbull)
* lynxbat [@lynxbat](https://github.com/lynxbat)

## [v0.75.0](https://github.com/RhetTbull/osxphotos/compare/v0.74.2...v0.75.0)

New exportdb commands, shell completions, better burst handling, multiple fixes.

### 2025-12-25

#### Added

- `--cleanup-command` to `osxphotos export` to run custom command on cleanup files, #1786
- `--missing` to `osxphotos exportdb` to print list of files missing from exportdb, #1988 
- `--uuid` to `osxphotos exportdb` to print UUID associated with a given filepath
- New `osxphotos shell-completion` command to install shell completions, #220
- Added new `burst_key_photo` property to `PhotoInfo` which returns the `PhotoInfo` object for the key photo if photo is a burst photo, #2032
- Added new `{burst}` template which returns the stem of the burst key photo for a burst group; this lets you do something like this: `--directory "{burst?{burst},}"` to output all burst photos into a folder named for the stem of the burst group key photo, #2032
- Added `--retry-wait` and `--retry-nas-alias` to export for better handling of flaky NAS connections, #2004

#### Changed

#### Removed

#### Fixed

- Fix for selection in full screen preview, #2044
- Fix for ai_caption in exportdb diff, #2046 
- Fix for live video file metadata, #2027 
- Fix for --cleanup so it doesn't delete dot files, #1506
- Fix `--version` for `osxphotos exportdb`, #1392
- Fix for `--append` with new CSV report, #2033
- Improved retry handling for export to NAS, #2004

#### Contributors

* @RhetTbull [@RhetTbull](https://github.com/rhettbull)
* @RhetTbull [@RhetTbull](https://github.com/rhettbull)
* @ZeliTheZealot [@ZeliTheZealot](https://github.com/ZeliTheZealot)

## [v0.74.2](https://github.com/RhetTbull/osxphotos/compare/v0.74.1...v0.74.2)

Enhancements to `--sidecar-template` and `--touch-file`, bug fixes.

### 2025-12-06

#### Added

#### Changed

- User sidecar templates, specified with `--sidecar-template` now have access to all variables that OSXPhotos uses when constructing the XMP sidecar (#2021)
- `osxphotos export --touch-file` now sets file creation date in addition to the file modification and access date when exporting on macOS (#1899)

#### Removed

#### Fixed

- Fix `--touch-file` regression for Synology NAS (#2017)
- Fix decoding of adjustment data in some cases (#2018) (thanks to @EriksRemess for the fix)
- Fix image and video captions where more than one caption was present (#2015) (thanks to @EriksRemess for the fix)

#### Contributors

* @RhetTbull [@RhetTbull](https://github.com/rhettbull).
* @EriksRemess [@EriksRemess](https://github.com/EriksRemess).

## [v0.74.1](https://github.com/RhetTbull/osxphotos/compare/v0.74.0...v0.74.1)

Updates to `osxphotos inspect` and `osxphotos albums`.

### 2025-11-21

#### Added

- Added `media_analysis` property to `PhotoInfo` which returns a dictionary of the AI analysis data produced by Photos' media analysis process.
- Added `ai_caption` property to `PhotoInfo` which returns the AI generated caption produced by the Photos media analysis process
- Added AI generated caption to `osxphotos inspect`

#### Changed

- `osxphotos albums` now prints the full path to albums contained in folders, for example, `Folder/Subfolder/Album` (#2008)
- New option `--size` for `osxphotos albums` to sort albums by size instead of the default alphabetical
- `osxphotos inspect --template` now adds the rendered template to the inspect output (#2010)

For example, the direction the photo was taken can be added to the `inspect` output using:

`osxphotos inspect -T "[bold]Direction:[/] {exiftool:EXIF:GPSImgDirection}"`

#### Removed

#### Fixed

- Better progress details on `osxphotos import` (thanks @oPromessa)
- `osxphotos sync --import` now creates folder structure for albums (thanks @oPromessa) (#1978)

#### Contributors

* @RhetTbull [@RhetTbull](https://github.com/rhettbull).
* @oPromessa [@oPromessa](https://github.com/oPromessa).

## [v0.74.0](https://github.com/RhetTbull/osxphotos/compare/v0.73.4...v0.74.0)

macOS 26.1 support

### 2025-11-04

#### Added

- Support for macOS 26.1, thanks to @EriksRemess for testing and code.

#### Changed

#### Removed

#### Fixed

- Updates for macOS 15.7.2, thanks to @oPromessa (#1972)
- Import hangs sometimes, thanks to @oPromessa kill and restart Photos (#1970)

#### Contributors

* @RhetTbull [@RhetTbull](https://github.com/rhettbull).
* @oPromessa [@oPromessa](https://github.com/oPromessa).
* @EriksRemess [@EriksRemess](https://github.com/EriksRemess).

## [v0.73.4](https://github.com/RhetTbull/osxphotos/compare/v0.73.3...v0.73.4)

Python 3.14 support

### 2025-10-15

#### Added

- Support for Python 3.14

#### Changed

#### Removed

#### Fixed

- Fixed import with numeric keywords (#1934), thanks to @oPromessa

#### Contributors

* @RhetTbull [@RhetTbull](https://github.com/rhettbull).
* @oPromessa [@oPromessa](https://github.com/oPromessa).

## [v0.73.3](https://github.com/RhetTbull/osxphotos/compare/v0.73.2...v0.73.3)

Fixed performance regression from v0.73.2

### v0.73.3 (2025-10-10)

#### Added

#### Changed

#### Removed

#### Fixed

-Fixed performance regression from v0.73.2

#### Contributors

* @RhetTbull [@RhetTbull](https://github.com/rhettbull).

## [v0.73.2](https://github.com/RhetTbull/osxphotos/compare/v0.73.1...v0.73.2)

Bug fix for non-can timezones in timewarp.

*NOTE* Version 0.73.2 was yanked due to a performance regression.

### v0.73.2 (2025-10-10)

#### Added

- Added `adjustment_type` property to `PhotoInfo` class. `adjustment_type` is an int representing the type of adjustment made to the photo. Normal edits appear to be type 2 while edits that happen automatically at the time of shooting such as cropping to 16:9 aspect ratio appear to be type 3.

#### Changed

#### Removed

#### Fixed

- Improved handling of non-canonical timezones in timewarp. (#1952)

#### Contributors

* @RhetTbull [@RhetTbull](https://github.com/rhettbull).

## [v0.73.1](https://github.com/RhetTbull/osxphotos/compare/v0.73.0...v0.73.1)

### v0.73.1 (2025-09-27)

Bug fixes for broken dependency.

#### Added

#### Changed

- All CLI commands check for macOS version before executing. (#1934)
- Allow export_cli to accept a PhotosDB for the db argument (#1915)
- `osxphotos timewarp` will not load database if `--uuid` or `--uuid-from-file` is specified (#1929)

#### Removed

#### Fixed

Fix broken whenever dependency (#1937)
Fix `export --delete-file` causes crash

#### Contributors

* @RhetTbull [@RhetTbull](https://github.com/rhettbull).
* @oPromessa [@oPromessa](https://github.com/oPromessa).

## [v0.73.0](https://github.com/RhetTbull/osxphotos/compare/v0.72.3...v0.73.0)

Adds limited set of query options for `timewarp` and `batch-edit` commands. Adds `--set-favorite`, `--clear-favorite` to batch-edit. Buf fix for edited photos in iPhoto libraries.

For example, to edit all photos in an album named "My Album" and set them as favorites:

```
osxphotos batch-edit --album "My Album" --set-favorite
```

Query options have also been added to `timewarp`. For example, to adjust the time on all photos added in the last 1 day:

```
osxphotos timewarp --time-delta "+1 hour" --added-in-last "1 day"
```

**NOTE**: This release includes breaking changes for `batch-edit` and `timewarp` commands and for the `--album` and `--folder` query options that apply to all commands including `query` and `export`.

Specifically, the `--album` option for `batch-edit` has been renamed to `--add-to-album`. The `--inspect` shot option in `timewarp` is now `-I` instead of `-i`.

Additionally, the `--album` and `--folder` query options in all commands that use query options now automatically split folders and albums. For example `--album "Folder/Album"` will only operate on the album "Album" in the folder "Folder". If the album name contains a slash, use a double slash `//` to escape it: `--album "Folder//Album"`.

### v0.73.0 (2025-09-17)

#### Added

* Implement query options for `timewarp`
* Implement query options for `batch-edit`
* Add `--set-favorite`, `--clear-favorite` to batch-edit (#1900)

#### Changed

* `--album` option for `batch-edit` renamed to `--add-to-album`
* `export_cli()` function can now accept either a path to the Photos library or a `PhotosDB()` instance. This allows custom usage for long-running use-cases.
* `--inspect` short option in `timewarp` is now `-I` instead of `-i`.
* `--album` and `--folder` query options in all commands that use query options now automatically split folders and albums on `/`, use `//` to escape a slash in the album or folder name.

#### Removed

#### Fixed

* Prioritize QuickTime:ContentCreateDate over EXIF:DateTimeOriginal for videos.
* Catch errors when creating backup database.
* Fixed `path_edited` for iPhotos.

#### Contributors

* @RhetTbull [@RhetTbull](https://github.com/rhettbull).
* @oPromessa [@oPromessa](https://github.com/oPromessa).

## [v0.72.3](https://github.com/RhetTbull/osxphotos/compare/v0.72.2...v0.72.3)

Bug fix for malformed photos.db file (again) and a few other fixes.

### v0.72.3 (2025-08-31)

#### Added

#### Changed

#### Removed

#### Fixed

- Fix for malformed or missing photos.db file (#1893)
- Fix for regex characters in file name on import (#1910)
- Fix for invalid values in burst properties (#1908)

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/rhettbull).

## [v0.72.2](https://github.com/RhetTbull/osxphotos/compare/v0.72.1...v0.72.2)

Bug fix for malformed photos.db file

### v0.72.2 (2025-08-24)

#### Added

#### Changed

- Updated documentation formatting for Sphinx.

#### Removed

#### Fixed

- Fix for malformed or missing photos.db file (#1805, #1893)

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/rhettbull).

## [v0.72.1](https://github.com/RhetTbull/osxphotos/compare/v0.72.1...v0.72.0)

Added homebrew install support.

### v0.72.1 (2025-06-16)

#### Added

- Support for installing osxphotos using homebrew.

```bash
# Add the tap
brew tap RhetTbull/osxphotos

# Install osxphotos
brew install osxphotos
```

#### Changed

#### Removed

#### Fixed

#### Contributors

- @scottrobertson [@scottrobertson](https://github.com/scottrobertson) for homebrew formula.

## [v0.72.0](https://github.com/RhetTbull/osxphotos/compare/v0.72.0...v0.71.0)

Initial support for macOS Tahoe (16 / 26)

### v0.72.0 (2025-06-12)

#### Added

- Initial support for macOS Tahoe (macOS 16 / 26). This is very much initial beta support for a beta release of macOS that is is likely to change. I have tested export and import but not other features. If you encounter any issues, please report them on GitHub.

#### Changed

- `osxphotos export` will no longer try to export syndicated photos that have not been saved to the library (these will always be missing and cannot be exported with --download-missing). Syndicated photos are photos shared in Messages app. They show up in the library but are not saved to the library until the user imports them. Previously, osxphotos was trying to export these photos which resulted in "missing" messages during export and this caused confusion for users.

#### Removed

#### Fixed

- Kill Photos app if it hangs during --download-missing multiple times (#1862)
- Fix --exiftool so it timesout if the exiftool process hangs (#1855)
- Skip missing syndicated photos on export (#1865)

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.

## [v0.71.0](https://github.com/RhetTbull/osxphotos/compare/v0.71.0...v0.70.0)

Fixed daylight savings time issues with `timewarp` command.

### v0.71.0 (2025-06-07)

#### Added

#### Changed

#### Removed

#### Fixed

  * Fixed timewarp to work correctly with daylight savings time. (#1777)

#### Contributors

  * @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.

### v0.70.0 (2025-05-10)

## [v0.70.0](https://github.com/RhetTbull/osxphotos/compare/v0.70.0...v0.69.2)

Fixes for macOS 15, import, timewarp

### v0.70.0 (2025-05-10)

#### Added

    * Added `--ignore-exportdb` option to the export command to skip checking for the `.osxphotos_export.db` file in the export folder. [#1775]
    * Improved performance of the `exportdb --history` query to speed up history lookups. [#1765]
    * Introduced `--set-timezone` in the import command for explicit timezone assignment. [#1797]
    * Refactored the `info` command to use the new `counts` module and restored compatibility with iPhoto libraries. [#1771]

#### Changed

    * Unified date/time parsing logic between the import and timewarp commands; fixed DST‐boundary parsing issues. [#1840]
    * Enhanced support for the latest Photos library database schema on macOS 15. [#1846]

#### Removed


#### Fixed

    * Fixed report generation so that `--report` and `--append` flags work together correctly. [#1850]
    * Resolved errors in comment processing to ensure shared‐owner and title data export correctly. [#1808]
    * Improved accuracy of photo timezone logging and corrected timezone detection in the `timewarp` command. [#1845, #1843]
    * Ensured `timewarp` and `batch-edit` only process the current selection when neither `--uuid` nor `--uuid-from-file` are specified. [#1781]
    * Fixed rare crashes during face‐region metadata export when a photo’s width or height is zero. [#1810]
    * Added an additional fix so that `pull-exif timezone` updates correctly when `offset_seconds == 0`. [#1773]
    * Fixed intermittent `utime` failures when updating file timestamps during export. [#1826]

#### Contributors

    * @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
    * @oPromessa [@oPromessa](https://github.com/oPromessa) for code.
    * @JxxIT [@JxxIT](https://github.com/JxxIT) for code.
    * @pl804 [@pl804](https://github.com/pl804) for tests and data.
    * @cstaubli [@cstaubli](https://github.com/cstaubli) for bug report.
    * @KeyPlayerMaek [@KeyPlayerMaek](https://github.com/KeyPlayerMaek) for bug report.
    * @dobernhardt [@dobernhardt](https://github.com/dobernhardt) for bug report.

## [v0.69.2](https://github.com/RhetTbull/osxphotos/compare/v0.69.2...v0.69.0)

Fix for crash on macOS 15.2

### v0.69.2 (2024-12-14)

#### Added

#### Changed

#### Removed

#### Fixed

- Fixed crash on macOS 15.2 (#1757)

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.

## [v0.69.0](https://github.com/RhetTbull/osxphotos/compare/v0.68.6...v0.69.0)

Added support for Python 3.13. Removed support for Python 3.9.

### v0.69.0 (2024-11-29)

#### Added

#### Changed

- Added support for Python 3.13.

#### Removed

- Removed Support for Python 3.9. OSPhotos may continue to work with Python 3.9 but it is no longer tested or supported.

#### Fixed

- Fix for timewarp pull-exif timezone fails to update Photos Timezone info when offset_seconds == 0 (#1703) (thanks to @oPromessa for the fix).
- Fix for "push-exif datetime" fails updating edited video (#1706) (thanks to @oPromessa for the fix).
- Added check for `osxphotos timewarp` to ensure `--inspect` and `--compare-exif` are mutually exclusive.
- Fix for exiftool code when `OffsetTimeOriginal` is invalid (thanks to @oPromessa for the fix).

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @oPromessa [@oPromessa](https://github.com/oPromessa) for code.

## [v0.68.6](https://github.com/RhetTbull/osxphotos/compare/v0.68.5...v0.68.6)

Various bug fixes for macOS 15 Sequoia.

### v0.68.6 (2024-09-18)

#### Added

#### Changed

- Check for AAE files for video files on import (#1653, thanks to @oPromessa)

#### Removed

#### Fixed

- Fix for error running on macOS 10.15 (#1680)
- Fix for `osxphotos import --auto-live` for some video files (#1670)
- Fix for edited photos on macOS 15 Sequoia (#1687)

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @oPromessa [@oPromessa](https://github.com/oPromessa) for code.

## [v0.68.5](https://github.com/RhetTbull/osxphotos/compare/v0.68.4...v0.68.5)

Hot fix for unknown UTI type during export. Also incorporates changes to the `sync` command
to allow syncing of location data.

#### Added

- Added support for syncing location data in `sync` command thanks to @oPromessa.

#### Changed

#### Removed

#### Fixed

- Fixed unknown UTI type during export (#1643).

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @oPromessa [@oPromessa](https://github.com/oPromessa) for code.

## [v0.68.4](https://github.com/RhetTbull/osxphotos/compare/v0.68.3...v0.68.4)

Hot fix for macOS 14.6 and 15.0/15.1. This release updates the Photos library database schema to support
macOS 14.6 and 15.0/15.1. It also fixes an issue with the `sync` command when the photo could not be found.

#### Added

#### Changed

- Updated Photos library database schema for macOS 14.6 and 15.0/15.1.

#### Removed

#### Fixed

- Fixed error when using `sync` command and photo could not be found via AppleScript (#1623).

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.

## [v0.68.3](https://github.com/RhetTbull/osxphotos/compare/v0.68.2...v0.68.3)

This release fixes errors when running on macOS 14.6 and 15.0 beta due to Photos database schema changes.
It also adds support for Screen Recording media type and fixes bugs with the `sync` command and changes
how face regions are handled to avoid exiftool warnings.

**Note**: The change to face region handling may cause exports using `--update` to re-export photos
and/or sidecars if `--exiftool` or `--sidecar` is in use as the face region data will be different.
If re-exported during `--update`, the subsequent export will have the correct face region data and should
not be re-exported again.

**Note**: When using the pre-built executable, the executable will now be the responsible process for
requesting permissions from the user to access the Photos library. This means you may see a dialog
box stating that osxphotos is requesting permission to access the Photos library. This is normal
and expected behavior. If you are using the Python package, the terminal will be the responsible
and will request permission to access the Photos library. If you have previously granted permissions
for osxphotos via the terminal, you will need to do this again the first time you run the pre-built
executable. Thank you to @torarnv for the code to make this change.

This will enable the eventual transition to [PyApp](https://github.com/ofek/pyapp) for building the
executable and for enabling PhotoKit support by default in a future release.
See [this discussion](https://github.com/RhetTbull/osxphotos/discussions/1558) for additional information.

### v0.68.3 (2024-08-04)

#### Added

- Added support for media type Screen Recording (`PhotoInfo.screen_recording` property)

#### Changed

- Ensure osxphotos executable is the responsible process for requesting permissions (applies only to pre-built binaries).
- Changed how face regions are handled to avoid exiftool warnings.

#### Removed

#### Fixed

- Fixed schema for macOS 14.6 and 15.0 beta.
- Fixed error when using `sync` command and photo could not be found via AppleScript (#1623).
- Fixed exiftool warning with face regions (#1619).

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @teh-hippo [@teh-hippo](https://github.com/teh-hippo) for testing.
- @dweston [@dweston](https://github.com/dweston) for testing.
- @oPromessa [@oPromessa](https://github.com/oPromessa) screen recording code.
- @torarnv[@torarnv](https://github.com/torarnv) for responsible process code.

## [v0.68.2](https://github.com/RhetTbull/osxphotos/compare/v0_68_1...v0.68.2)

Added alpha support for import command on macOS Sequoia

### v0.68.2 (2024-06-16)

#### Added

- Alpha support for macOS Sequoia dev preview with osxphotos import.

#### Changed

#### Removed

#### Fixed

#### Contributors

- @tural-ali [@tural-ali](https://github.com/tural-ali) for testing.

## [v0.68.1](https://github.com/RhetTbull/osxphotos/compare/v0_68_0...v0_68_1)

Added alpha support for macOS Sequoia. Some features not yet tested. This adds ability to read a Photos library created by Photos version 10, macOS Sequoia / 15.0.

### v0.68.1 (2024-06-11)

#### Added

- Alpha support for macOS Sequoia dev preview.

#### Changed

#### Removed

#### Fixed

#### Contributors

- @tural-ali [@tural-ali](https://github.com/tural-ali) for providing access to macOS Sequoia library for testing.

## [v0.68.0](https://github.com/RhetTbull/osxphotos/compare/v0.67.10...v0_68_0)

### v0.68.0 (2024-06-08)

The Importapalooza release. This release adds a number of new features to `osxphotos import` to support recreating a library from an osxphotos export and improve the import experience. It also includes some minor bug fixes and improvements in other parts of the code.

To export in a form that maximizes the ability to recreate the library, I suggest at a minimum using the following options:

```shell
osxphotos export /path/to/export --sidecar xmp --export-aae`
```

To import and preserve as much metadata as possible, use the following options:

```shell
osxphotos import /path/to/export --exportdb /path/to/export --exportdir /path/to/export --sidecar
```

This will preserve metadata such as titles, captions, keywords, favorites, and albums.

Technically, the use of `--sidecar` is not necessary if using `--exportdb` which reads metadata from the osxphotos export database but I'm a belt-and-suspenders kind of person and like to have the metadata in the sidecar files as well. The sidecar files provide compatibility with other software and can be used to recover metadata if the export database is lost or corrupted (with the exception of albums which are not currently exported to sidecars).

#### Added

- Added correct handling of live, edited, raw+jpeg, and burst files when importing (#1464, #1267)
- Added --exportdb, --exportdir to read metadata for imported photos from an export created by `osxphotos export`.
- Added --auto-live to automatically convert photo+video pairs to Live Photos upon import (#1399).
- Added --favorite-rating to set favorite status for imported photos (#1373).
- Added --signature to specify custom signature for comparing duplicates when importing (#1374).
- Added --edited-suffix to specify custom suffix for associating edited files when importing.

#### Fixed

- Apply --sidecar to edited files when importing (#1470)
- Normalize unicode characters in album names when importing (#1475)
- Handle missing PLModelVersion info in Photos library (#1557)

#### Changed

- Add list and set methods to PhotosAlbum (#1524)
- `osxphotos import` now accepts files or directories as arguments

#### Removed

#### Contributors

- Added @torarnv[@torarnv](https://github.com/torarnv) as new contributor for code.
- Added @odedia [@odedia](https://github.com/odedia) as a new contributor for ideas and research.
- @oPromessa [@oPromessa](https://github.com/oPromessa) for documentation and testing.

## [v0.67.10](https://github.com/RhetTbull/osxphotos/compare/v0.67.9...v0.67.10)

### v0.67.10 - 2024-03-30

Fixed bug for corrupt place info data.

#### Added

#### Fixed

- Fixed bug for corrupt place info data.
- Fixed doc string for `PhotoInfo.screenshot`.
- Fixed verbose output for export of AAE files.

#### Changed

#### Removed

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @axelkar [@axelkar](https://github.com/axelkar) for code and first contribution.

## [v0.67.9](https://github.com/RhetTbull/osxphotos/compare/v0.67.8...v0.67.9)

### v0.67.9 - 2024-03-24

Fixed bug for missing path for referenced Live Photos.

#### Added

#### Fixed

- Fixed bug for missing path for referenced Live Photos. (#1459)

#### Changed

#### Removed

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @oPromessa [@oPromessa](https://github.com/oPromessa) for reporting the bug with Live Photo path.

## [v0.67.8](https://github.com/RhetTbull/osxphotos/compare/v0.67.7...v0.67.8)

Combine Operator

### v0.67.8 - 2024-03-24

Adds new combine operator `&` to template language, ignores corrupt psi.sqlite in Photos library.

#### Added

- New combine operator `&` to template language, (#1453)

#### Fixed

- Ignore corrupt psi.sqlite in Photos library, (#1452)

#### Changed

#### Removed

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.

## [v0.67.7](https://github.com/RhetTbull/osxphotos/compare/v0.67.6...v0.67.7)

### v0.67.7 - 2024-03-17

A few bug fixes; update for macOS 14.4.

#### Added

#### Fixed

- Fix for improperly initialized export db, (#1435)
- Fix for album still created on export when --dry-run parameter is used (#1440)
- Attribute error during PhotoInfo.path (#1445)
- Update macOS tested version for 14.4 (#1429)

#### Changed

#### Removed

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @rajscode [@rajscode](https://github.com/rajscode) for fixing #1445.
- @jasonhollis [@jasonhollis](https://github.com/jasonhollis) for identifying #1435 and providing debug info.

## [v0.67.6](https://github.com/RhetTbull/osxphotos/compare/v0.67.5...v0.67.6)

### v0.67.6 - 2024-03-05

Hot fix for bug catching Ctrl+C when using --ramdb

#### Fixed

- Bug when using --ramdb that prevented user from exiting with Ctrl+C (#1432)

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @rajscode [@rajscode](https://github.com/rajscode) for reporting the bug

## [v0.67.5](https://github.com/RhetTbull/osxphotos/compare/v0.67.4...v0.67.5)

### [v0.67.5] - 2024-03-04

Adds new `osxphotos compare` command to compare two libraries.

Synopsis:

```bash
osxphotos compare [OPTIONS] LIBRARY1 LIBRARY2
```

```bash
osxphotos compare Test-13.5.1-compare-1.photoslibrary Test-13.5.1-compare-2.photoslibrary
library_a = Test-13.5.1-compare-1.photoslibrary
library_b = Test-13.5.1-compare-2.photoslibrary
in_a_not_b = 1 asset
in_b_not_a = 2 assets
in_a_and_b_same = 2 assets
in_a_and_b_different = 1 asset
```

```bash
osxphotos compare \
Test-13.5.1-compare-1.photoslibrary \
Test-13.5.1-compare-2.photoslibrary \
--csv --output compare.csv
```

#### Added

- New `osxphotos compare` command to compare two libraries. #939

#### Fixed

- Code comment in `export_db.py` thanks to @rajscode. #1422

#### Changed

- `osxphotos diff` and `osxphotos snap` commands are now hidden as these are primarily for osxphotos developers or those hacking on the Photos library. To see hidden commands, use `OSXPHOTOS_SHOW_HIDDEN=1 osxphotos help`. #1427

#### Removed

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @rajscode [@rajscode](https://github.com/rajscode) for fixing an incorrect comment in the code.

## [v0.67.4](https://github.com/RhetTbull/osxphotos/compare/v0.67.3...v0.67.4)

### [v0.67.4] - 2024-03-01

This release includes a few bug fixes as well as a new feature to fix photo orientation upon export. There's also a performance improvement for `osxphotos export`.

#### Added

- `--fix-orientation` flag to `osxphotos export` command to automatically adjust the orientation of exported photos to match the orientation stored in the Photos database. This is mostly useful for iPhoto libraries which do not treat orientation adjustments as edits and thus no edited image with the correct orientation is created. #1396

#### Fixed

- Unified the fingerprint code for `sync` and `import` which improves reliability and makes it possible to implement the `osxphotos compare` command. #1389
- If a path is invalid in the `osxphotos export` command and the passed path includes smart quotes, the error message will now tell the user to remove the smart quotes. This fixes a common user error when pasting from TextEdit or Notes that use smart quotes. #1408
- Fixed `osxphotos repl` to work when connected via SSH. #1332

#### Changed

- Added index to history table in export databasel; this should speed up exports with `--update` (migrates export database to version 9.1)

#### Removed

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @mlevin77 [@mlevin77](https://github.com/mlevin77) for suggesting the `--fix-orientation` flag.

## [v0.67.3](https://github.com/RhetTbull/osxphotos/compare/v0.67.2...v0.67.3)

### [v0.67.3] - 2024-01-13

Fixes for `--checkpoint` causing unnecessary slowdown.

#### Added

#### Removed

#### Changed

- `osxphotos export --checkpoint` no longer automatically checkpoints during export. See #1083.

#### Fixed

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @rajscode [@rajscode](https://github.com/rajscode) for finding the issue with checkpoint.

## [v0.67.2](https://github.com/RhetTbull/osxphotos/compare/v0.67.1...v0.67.2)

### [v0.67.2] - 2024-01-01

Fixes for `--sidecar`` when exporting edited photos.

#### Added

#### Removed

#### Changed

#### Fixed

- Sidecar not written for edited photo when exporting both original and edited photo. (#1346)

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @finestream [@finestream](https://github.com/finestream) for finding the bug with `--sidecar`.

## [v0.67.1](https://github.com/RhetTbull/osxphotos/compare/v0.67.0...v0.67.1)

### [v0.67.1] - 2023-12-31

Fixes for iPhoto export and Google Takeout import.

#### Added

#### Removed

#### Changed

- iPhoto export will now write the photo rating to the `XMP:Rating` field with `--sidecar` and `--exiftool` options. (#1353)
- `osxphotos import --sidecar-template` renamed to `--sidecar-filename` to avoid ambiguity with the `osxphotos export` option `--sidecar-template`. (#1351)
- Photos in shared albums are now excluded from `--not-incloud` as this caused confusion for usesrs (#1366)

#### Fixed

- Fixed query could sometimes fail with iPhoto library.
- Fixed Google Takeout was importing timestamps incorrectly. (#1356)

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code.
- @LunarLanding [@LunarLanding](https://github.com/LunarLanding) for finding bug in import and submitting the fix.
- @mlevin77 [@mlevin77](https://github.com/mlevin77) for idea to use `XMP:Rating` field with iPhoto.
- @finestream [@finestream](https://github.com/finestream) for suggesting the change to `--sidecar-template` for import.

## [v0.67.0](https://github.com/RhetTbull/osxphotos/compare/v0.66.0...v0.67.0)

Import support for sidecars, Google Takeout.

### [v0.67.0] - 2023-12-23

Several enhancements to `osxphotos import` that now allow it to be used to import a Google Takeout archive into Photos.app. Enhancements to `osxphotos export` to store the history of exported photos and videos in the export database and to allow checking and repairing the export database with `osxphotos exportdb`.

For example, to import a Google Takeout archive into Photos.app:

Download the Google Photos Takeout archive from Google and unzip it. This will create a folder with a name like `Takeout`. Inside this folder will be a folder named `Google Photos` which contains all the photos and videos.  You can import the photos and videos into Photos.app using the following command (assuming you unzipped the Takeout file in your Downloads folder):

```bash
osxphotos import ~/Downloads/Takeout/Google\ Photos --walk --album "{filepath.parent.name}" --skip-dups --dup-albums --sidecar --verbose --sidecar-ignore-date --keyword "{person}" --report takeout_import.csv
```

This will import all the photos and videos into Photos.app, creating albums with the same name as the folder they were in in the Takeout archive (which is how Google Takeout stores photos in albums). It will skip duplicates (Google Takeout exports duplicate copies of photos that are in more than one album) but add the duplicate photo that's already in the library to the albums it would have been added to if it were imported (`--skip-dups --dup-albums`).  It will also import metadata from the sidecar files (Google Takeout exports metadata in JSON format) (`--sidecar`).

The `--sidecar-ignore-date` option is optional but prevents osxphotos from setting the photo's date from the sidecar metadata. This is helpful because Google Takeout does not preserve the timezone of the photo in the Takeout metadata but converts all times to UTC. This will be handled by osxphotos by converting to local timezone upon import. However, if the photo's already have correct time in the EXIF data, `--sidecar-ignore-date` will prevent osxphotos from setting the date from the sidecar metadata, allowing Photos to set the date from the image.

The `--keyword "{person}"` option will add any people in the photo to the photo's keywords. The `osxphotos import` command cannot set person info in Photos (this is a limitation of Photos) but Google will preserve the person names if you've used the face naming feature. You can optionally include `--keyword "{person}"` to add keywords for the persons found in each image.

The `--report takeout_import.csv` option will create a report of the import in CSV format.

#### Added

- Added `--sidecar` and `--sidecar-template` to `osxphotos import` to import metadata from sidecar files during import. Supported sidecar formats are XMP, osxphotos JSON, exiftool JSON, and Google Takeout JSON. `--sidecar` will automatically find the sidecar (even with Google Takeout's weird naming scheme) and `--sidecar-template` allows to specify the sidecar file name using a template.
- Added `--dup-albums` to `osxphotos import` to add photos to the appropriate albums even if photo is skipped due to `--skip-dups`. This will add the duplicate photo already in the library to the albums the photo would have been added to if it were imported.
- Added `--parse-folder-date` to `osxphotos import` to parse date from folder name just as `--parse-date` can parse date from the filename. `--parse-folder-date` and `--parse-date` can be used together if part of the date is in the filename and part in the folder name. For example `--parse-folder-date "%Y/%m/%d" --parse-date "%H%M%S"` would parse a date from a folder name like `2021/01/01` and time from filename like `IMG_1234_125600.jpg`.
- Added `--check`, `--repair` to `osxphotos exportdb` to check and repair database
- Added `--history` to `osxphotos exportdb` to show history of exported photos and videos

#### Removed

#### Changed

- Export database now stores history of exported photos and videos which can be used with `osxphotos exportdb --history` to see why a specific file or UUID was exported or skipped and the history of the file.
- The report format for `osxphotos import` has changed (added photo date to report), thus if you use `--report --append` you'll need to archive the existing reports and start fresh with this version.

#### Fixed

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code
- @finestream [@finestream](https://github.com/finestream) for the idea to add `--sidecar` to `osxphotos import`
- @mikekenyon99 [@mikekenyon99](https://github.com/mikekenyon99) for the idea to add a repair option to `osxphotos exportdb`

## [v0.66.0](https://github.com/RhetTbull/osxphotos/compare/v0.65.0...v0.66.0)

Bug Fixes

### [v0.66.0] - 2023-12-10

#### Added

#### Removed

#### Changed

- Templates which return lists of strings such as `{album}` now return results in sorted order #1317

#### Fixed

- Fixed install issues for Monterey, #1324

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code

## [v0.65.0](https://github.com/RhetTbull/osxphotos/compare/v0.64.3...v0.65.0)

Thanksgiving Release: A cornucopia of new features and bug fixes for the Thanksgiving holiday. Thanks to all the contributors who helped make this release possible. Please note there are some breaking changes in this release, see notes below. If you have scripts or workflows that use `osxphotos` CLI commands, you may need to update them to specify the library with `--library` or `--db` instead of as a positional argument.

### [v0.65.0] - 2023-11-25

#### Added

- `osxphotos batch-edit --album` to add photos to an album (#1009)

This allows `batch-edit` to be used to sync albums between iCloud shared libraries (Photos does not sync albums between shared libraries). For example:

```bash
 osxphotos batch-edit --verbose --keyword "{album?album:{folder_album}}"
```

will write the album name in form `album:Folder/Album` to the keyword field.  Then on the other user's machine:

```bash
osxphotos batch-edit --verbose --album "{keyword|filter(startswith album:)|sslice(6:)}" --split-folder "/"
```

reads the album name from the keyword field and splits it into folder and album name and adds the photo to the album, creating album and folders as necessary.

Both commands can be run on each user's machine to sync albums between shared libraries. The commands can also be combined into a single command:

```bash
osxphotos batch-edit --verbose --album "{keyword|filter(startswith album:)|sslice(6:)}" --split-folder "/" --keyword "{album?album:{folder_album}}"
```

- `osxphotos export --checkpoint` to auto-save the export database during export when using `--ramdb`. This prevents data loss if the export is interrupted or crashes. If using `--ramdb` and `--checkpoint` is not identified, export database will be auto-saved every 1000 photos (#1051)
- `osxphotos push-exif --dry-run` to show what will be pushed without updating metadata (#1259)
- `osxphotos export --ignore-exportdb` to ignore warnings about exporting into a folder with an existing export database without using `--update` (#1285)
- `osxphotos export --no-exportdb` to export without creating an export database; use with caution as this is a "one time" export that will not work with `--update` in the future
- `osxphotos import --dry-run` to `osxphotos import` to show what would be imported without actually importing
- `osxphotos import --skip-dups` to skip importing photos that are already in the library (#1262, #1264)

#### Removed

- Removed photos library argument from CLI commands which had previously been deprecated; library must now be specified with `--library` or `--db`

**WARNING**: This is a breaking change if you have scripts that use `osxphotos` CLI commands and specify the library as a positional argument.  You must now specify the library with `--library` or `--db`.  For example, if you have a script that looks like this:

```bash
osxphotos export ~/Pictures/Photos\ Library.photoslibrary /path/to/export
```

you must now change it to:

```bash

osxphotos export --library ~/Pictures/Photos\ Library.photoslibrary /path/to/export
```

#### Changed

- `osxphotos import` now prints a message if the photo is already in the library (#1264)
- `osxphotos export` now checks if the destination is a Photos library and warns if it is (#1268)
- `osxphotos export` now checks if the destination is a folder with an existing export database and warns if exporting without `--update` (#1285)
- `export_cli()` can now be used to run the `osxphotos export` command as a stand-alone function in your own code (#1253):

```pycon
>>> from osxphotos.cli.export import export_cli
>>> export_cli(dest="/private/tmp", update=True)
```

- `--query-function` (`query`, `export`), `--post-function` (`export`), `--function` (`timewarp`), `osxphotos run`, and `{function}` template now all support providing a URL to a Python file containing the function (#1224).  This allows sharing of functions and makes it easier to give examples to new users. For example:
  - `osxphotos run https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/count_photos.py`
  - `osxphotos query --quiet --print "{function:https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/template_function.py::example}"`
  - `osxphotos query --query-function https://raw.githubusercontent.com/RhetTbull/osxphotos/main/examples/find_unnamed_faces.py::unnamed_faces --count`

- CLI commands now show progress when loading the Photos library to stderr. This is useful when running commands against a large database on a slow disk

#### Fixed

- Allow `library` to be specified in config TOML file (#1274)

#### Contributors

- Rhet Turnbull ([@RhetTbull](https://github.com/RhetTbull)) for code, documentation, and testing
- Added @nicad ([@nicad](https://github.com/nicad)) as a contributor for bug, test, and documentation
- Added @nkxco ([@nkxco](https://github.com/nkxco)) as a contributor for ideas
- Added @santiagoGPNC ([@santiagoGPNC](https://github.com/santiagoGPNC)) as a contributor for ideas
- Added @mikapietrus ([@mikapietrus](https://github.com/mikapietrus)) as a contributor for ideas

## [v0.64.3](https://github.com/RhetTbull/osxphotos/compare/v0.64.2...v0.64.3)

Adds `--alt-db` option to export. You probably (almost certainly) don't need this.

### [v0.64.3] - 2023-10-22

#### Added

- `--alt-db` option to export to specify a different database than the one in the Photos library. This is a niche option you likely don't need but enables certain use cases that previously weren't possible.

#### Removed

#### Changed

#### Fixed

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code and testing

## [v0.64.2](https://github.com/RhetTbull/osxphotos/compare/v0.64.0...v0.64.2)

Updated dependencies for Python 3.12

### [v0.64.2] - 2023-10-21

#### Added

#### Removed

#### Changed

#### Fixed

- Support for Python 3.12, #1254

#### Contributors

- @RhetTbull [@RhetTbull](https://github.com/RhetTbull) for code and testing

## [v0.64.0](https://github.com/RhetTbull/osxphotos/compare/v0.63.5...v0.64.0)

Adds support for exporting and querying iPhoto databases. iPhoto support only works on Python >= 3.10.

### [v0.64.0] - 2023-10-09

#### Fixed

#### Added

- osxphotos export, query, dump, info, persons, keywords, and albums commands now work with iPhoto libraries.

#### Removed

#### Changed

#### Contributors

- Special thanks to @jensb ([@jensb](https://github.com/jensb)) who kindly allowed me to use code from his [iphoto2xmp](https://github.com/jensb/iphoto2xmp) as a starting point for the osxphotos iPhoto support and allowed me to relicense this code under MIT License to be compatible with osxphotos.
- @RhetTbull ([@RhetTbull]((https://github.com/RhetTbull)) for code and tests.

## [v0.63.5](https://github.com/RhetTbull/osxphotos/compare/v0.63.4...v0.63.5)

Fixed `osxphotos keywords` to also show keywords with no associated photos.

### [v0.63.5] - 2023-09-24

#### Fixed

#### Added

- Added instructions for MacPorts install

#### Removed

#### Changed

- `osxphotos keywords` now shows keywords with no associated photos which may be useful for pruning keywords in Photos.

#### Contributors

- @RhetTbull [https://github.com/RhetTbull](https://github.com/RhetTbull) for code
- @dmd [https://github.com/dmd](https://github.com/dmd) for feature suggestion
- @breun [https://github.com/breun](https://github.com/breun) for docs explaining how to use MacPorts to install

## [v0.63.4](https://github.com/RhetTbull/osxphotos/compare/v0.63.3...v0.63.4)

Internal fix for get_system_library_path on Ventura. No changes to user interface.

### [v0.63.4] - 2023-09-15

#### Fixed

- Fix to internal function get_system_library_path

#### Added

#### Removed

#### Changed

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code

## [v0.63.3](https://github.com/RhetTbull/osxphotos/compare/v0.63.1...v0.63.3)

Fix for install problems with pipx

### [v0.63.3] - 2023-09-15

#### Fixed

- Fixed problems with install with pipx and python 3.11 (#1203)
- Fixed issue where PyPI source package was including unneeded screencast assets

#### Added

#### Removed

#### Changed

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code
- [@ZarK](https://github.com/ZarK) for reporting bug with pipx
- [@420gofOGKush](https://github.com/420gofOGKush) for reporting bug with pipx and user testing
- [@breun](https://github.com/breun) for finding @catap to create MacPorts port for osxphotos
- [@catap](https://github.com/catap) for doing the work to add an osxphotos port to MacPorts
- [@devlarosa](https://github.com/devlarosa) for reporting a bug

## [v0.63.1](https://github.com/RhetTbull/osxphotos/compare/v0.63.0...v0.63.1)

Fixes a bug with --ramdb for certain configurations.

### [v0.63.1] - 2023-09-14

#### Fixed

- Bug with --ramdb that would cause osxphotos to crash if export database was too large

#### Added

#### Removed

#### Changed

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code
- [@hydrrrrr](https://github.com/hydrrrrr) for reporting the --ramdb bug

## [v0.63.0](https://github.com/RhetTbull/osxphotos/compare/v0.62.3...v0.63.0)

Added push-exif command

### [v0.63.0] - 2023-09-03

#### Fixed

- Fixed exiftool warning for PNG images when using `--exiftool` (#1031)

#### Added

- `osxphotos push-exif` command to push metadata changes from Photos to the original files. (#160)
- Added `PhotoInfo.latitude` and `PhotoInfo.longitude` properties to get the latitude and longitude of a photo (`PhotoInfo.location` still works to return tuple of lat, lon)

#### Removed

- Removed `get_selected()` from `osxphotos repl` (#1179)

#### Changed

- In `osxphotos repl`, `selected` is now an instance of of `PhotosSelection` which dynamically updates when selection changes.

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code

## [v0.62.3](https://github.com/RhetTbull/osxphotos/compare/v0.62.2...v0.62.3)

Added macOS 13.5 to compatibility matrix.

### [0.62.3] - 2023-08-21

#### Fixed

- `--to-date` and `--to-time` are now exclusive (find files *before* date/time) (#590)

#### Added

- Support for macOS 13.5

#### Removed

#### Changed

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code

## [v0.62.2](https://github.com/RhetTbull/osxphotos/compare/v0.62.1...v0.62.2)

More support for shared iCloud libraries and `osxphotos template` REPL command.

### [v0.62.2] - 2023-08-20

#### Changed

- Added `-r` option to `osxphotos install` for use with requirements.txt files

#### Added

- Updated `osxphotos inspect` to include details about shared iCloud library photos
- Added `osxphotos template` command for interactive template REPL tool

#### Removed

#### Fixed

- Added clarifying note to help for `--push-exif` option

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code
- [@kvisle](https://github.com/kvisle) for testing & data to implement iCloud Shared Library features

## [v0.62.1](https://github.com/RhetTbull/osxphotos/compare/v0.62.0...v0.62.1)

Documentation Fixes

### [v0.62.1] - 2023-08-13

#### Changed

#### Added

#### Removed

#### Fixed

- Minor fixes to the documentation.

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull)

## [v0.62.0](https://github.com/RhetTbull/osxphotos/compare/v0.61.0...v0.62.0)

Initial support for iCloud Shared Libraries.

This release contains a lot of changes some of which may be breaking depending on your workflow. If you use `--sidecar-template`, you should look at the help for this option as the options have changed from boolean flags to named flags.

If you use `--report` with `--append` and you use CSV reports, you should archive the existing report and start a new one as the report now contains additional fields for user files.

If you use `--post-function`, the called function may now return an [ExportResults](https://rhettbull.github.io/osxphotos/reference.html#osxphotos.ExportResults) object with information about the files written, the files skipped, and any errors generated. If returned, these files will be included in `--report` and will be protected from cleanup with `--cleanup`.

Initial support for photos in Shared iCloud Libraries has been implemented. These photos can be queried via the `--shared-library` option.  Still working on decoding the participant information (who is sharing the photos).

### [v0.62.0] - 20230812

#### Added

- Support for iCloud shared libraries, PhotoInfo.shared_library, PhotoInfo.share_participants, PhotoInfo.share_info (#860)
- Shared moment, syndicated, shared library support to `osxphotos inspect`(#860)
- `--post-command-error` option to configure error handling of `--post-command` (#1142)
- `.osxphotos_keep` file can now be used to specify keep patterns for `--cleanup` (#1135)
- Option to `--sidecar-template` to skip zero length files

#### Removed

#### Changed

- Changed `--sidecar-template` options to use named options instead of boolean
- Changed signature of --post-function function to enable it to work with --report, --cleanup (#1136)
- Now can catch template errors with `catch_errors` option to `--sidecar-template`

#### Fixed

- Fixed bug with PhotoInfo.path_raw on Photos <= 4.0

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) - Code and testing
- [@neilpa](https://github.com/neilpa) - The idea for custom sidecars and suggestions to improve the feature
- [@kvisle](https://github.com/kvisle) - For user testing with iCloud shared libraries

## [v0.61.0](https://github.com/RhetTbull/osxphotos/compare/v0.60.10...v0.61.0)

Custom sidecars for osxphotos export

### [v0.61.0] - 20230725

#### Added

- `--sidecar-template` option to export to allow user to specify one or more Mako templates for creating custom sidecars. See [example](https://github.com/RhetTbull/osxphotos/blob/main/examples/custom_sidecar.mako for an example)

#### Removed

#### Changed

- Added `user_sidecar` field to all report formats. This means that if you are using a CSV report with `--append`, you should archive your current report and create a new one which will include the correct headers. For JSON reports, the JSON outpput will simply include a new key for new records. For SQLite reports, the `report` table will be altered to add the new column.

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) - Code and testing
- [@neilpa](https://github.com/neilpa) - The idea for custom sidecars

## [v0.60.10](https://github.com/RhetTbull/osxphotos/compare/v0.60.9...v0.60.10)

Support for syndicated photos on Monterey (Photos 7)

### [v0.60.10] - 2023-07-20

#### Added

#### Removed

#### Changed

- Added additional photo details to `osxphotos debug-dump`

#### Fixed

- Syndicated photos now work on Monterey (#1116)
- `osxphotos orphans` now also scans the scopes directory

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) - code
- [@neilpa](https://github.com/neilpa) - for testing and finding the bug with syndicated photos on Monterey

## [v0.60.9](https://github.com/RhetTbull/osxphotos/compare/v0.60.8...v0.60.9)

Fixed missing path for photos that are part of a shared moment (Ventura+)

### [v0.60.9] - 2023-07-16

#### Added

- `PhotoInfo.shared_moment` property (True if photo is part of a shared moment, otherwise False)
- `--shared-moment`, `--not-shared-moment` query options

#### Removed

#### Changed

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code
- [@neilpa](https://github.com/neilpa) for identifying the bug with shared moments

## [v0.60.8](https://github.com/RhetTbull/osxphotos/compare/v0.60.7...v0.60.8)

Adds support for working with Photos libraries on macOS Sonoma (14.0 preview)

### [v0.60.8] - 2023-07-16

#### Added

- Supports Photos libraries created by Photos 9.0 (macOS Sonoma)

#### Removed

#### Changed

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) - code changes and testing

## [v0.60.7](https://github.com/RhetTbull/osxphotos/compare/v0.60.6...v0.60.7)

AAE Export Support

### [v0.60.7] - 2023-07-15

#### Addeded

- `--export-aae` option for `osxphotos export` to export the raw adjustments plist files
- `PhotoInfo.adjustments_path` property for retrieving the path to the AAE file

#### Removed

#### Changed

#### Contributors

- [@dvdkon](https://github.com/dvdkon) - code changes to add support for AAE files.

## [v0.60.6](https://github.com/RhetTbull/osxphotos/compare/v0.60.5...v0.60.6)

Remove --library/--db from import command

### [v0.60.6] - 2023-07-02

#### Added

#### Removed

- Removed `--library/--db` options from `osxphotos import` as import does not allow user to specify a library; the last used library is always used for import

#### Changed

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) - Code and documentation
- [@msolo](https://github.com/msolo) - Bug report for `osxphotos import`

## [v0.60.5](https://github.com/RhetTbull/osxphotos/compare/v0.60.4...v0.60.5)

Unicode Fixes

### [v0.60.5] - 2023-06-24

#### Added

- Added `--count`to query to print count of query results and exit (#1098)

#### Removed

#### Changed

#### Fixed

- Normalize unicode for `osxphotos import` to avoid duplicate keywords and albums (#1087)

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull/osxphotos) - code & testing
- [@oPromessa](https://github.com/oPromessa) - for finding and documenting the unicode bugs

## [v0.60.4](https://github.com/RhetTbull/osxphotos/compare/v0.60.3...v0.60.4)

Updated testing / compatibility matrix to include macOS 13.4.

### [v0.60.4] - 2023-06-18

#### Fixed

#### Added

#### Removed

#### Changed

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull/osxphotos) - code & testing

## [v0.60.3](https://github.com/RhetTbull/osxphotos/compare/v0.60.2...v0.60.3)

Ventura introduced a "shared with you" album which shows photos shared via Messages (and possible other apps). These show up in the Photos library in the
"Shared with you" album but the images are stored in a different location that regular images so osxphotos could not previously access the images.
It can now do so.

### [v0.60.3] 2023-06-18

#### Fixed

#### Added

- `PhotoInfo.syndicated` property to identify syndicated photos.
- `PhotoInfo.saved_to_library` property to identify syndicated photos that have been saved to the library.
- `--syndicated`/`--not-syndicated`, `--saved-to-library`/`--not-saved-to-library` query options.
- `find()` function in `osxphotos repl` to search for files in the active Photos library directory.

#### Removed

#### Changed

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code.

## [v0.60.2](https://github.com/RhetTbull/osxphotos/compare/v0.60.1...v0.60.2)

Performance Improvements for --download-missing

### [v0.60.2] - 2023-06-17

#### Fixed

- Performance improvements for `osxphotos export` when used with `--download-missing` or `--sidecar XMP` options. (#1086)

#### Added

#### Changed

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code changes.
- [@MaxLyt](https://github.com/MaxLyt) for finding the issue.

## [v0.60.1](https://github.com/RhetTbull/osxphotos/compare/v0.60.0...v0.60.1)

Hot fix for a bug with in-memory database and --dry-run.

### 14 May 2023

#### Fixed

- Fixed crash with --dry-run with large export database (#1071)

#### Contributors

- @RhetTbull for code changes.
- @rajscode for identifying the bug and filing a detailed bug report.

## [v0.60.0](https://github.com/RhetTbull/osxphotos/compare/v0.59.3...v0.60.0)

Linux Support: adds support for using a subset of osxphotos capabilities on Linux.

### 07 May 2023

#### Added

- osxphotos now supports Linux (tested on Ubuntu 22.04); some commands are macOS only and will not be available (nor shown) on Linux. Huge thank you to [@dvdkon](https://github.com/dvdkon) for doing the Linux port!
- Added `PhotoTables` API and `tables` property to `PhotoInfo` to access underlying SQL tables for a photo.

#### Changed

- Added macOS 13.3 to supported versions table.

#### Contributors

- @dvdkon for Linux port.
- @RhetTbull for code changes.
- @pekingduck for bug report.
- @cclause for updating ruff test runner.

## [v0.59.3](https://github.com/RhetTbull/osxphotos/compare/v0.59.2...v0.59.3)

Bug fixes for memory leak, crash during export

### 10 April 2023

#### Fixed

- Fixed memory leak in export (#1047)
- Fixed crash during export (#1046)
- Fixed large crash log size (#1048)

#### Changed

- Added better help for no selection with --selected (#1036)
- Changed PhotoInfo.asdict() and PhotoInfo.json() to allow deep or shallow option (#1038)
- Updated development docs (#1043)

#### Contributors

- @RhetTbull for code changes
- @wernerzj for finding bug with memory leak
- @rajscode for finding export crash
- @oPromessa for development docs fix

## [v0.59.2](https://github.com/RhetTbull/osxphotos/compare/v0.59.1...v0.59.2)

Bug Fix for Export

### 08 April 2023

#### Fixed

- Fixed error on export when photo belonged to a project (#999)
- Fixed large increase in export database size (#999)

#### Changed

- Added indent, shallow args to PhotoInfo.json() (#1038)

#### Contributors

- @RhetTbull for code
- @oPromessa for finding bugs, running tests

## [v0.59.1](https://github.com/RhetTbull/osxphotos/compare/v0.59.0...v0.59.1)

Performance Boost

### 2 April 2023

#### Changed

- Removed lock files from export code (speed boost for NAS export, see #999); will need to eventually add this back for multithreaded export
- Optimized some code in export CLI to speed export
- Some linting fixed for move to ruff
-

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code changes.
- [@cclauss](https://github.com/cclauss) for linting fixes

## [v0.59.0](https://github.com/RhetTbull/osxphotos/compare/v0.58.2...v0.59.0)

### 1 April 2023

#### Added

- `PhotoInfo.export()` and `PhotoExporter.export()` now support exporting in concurrent threads on Python 3.11+. This applies only to the API. The `osxphotos export` CLI does not yet support concurrent export. See #999.

See example code in [concurrent_export.py](https://github.com/RhetTbull/osxphotos/blob/main/examples/concurrent_export.py).

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code changes.
- [@eecue](https://github.com/eecue) for testing and helping pinpoint the issues.

## [v0.58.2](https://github.com/RhetTbull/osxphotos/compare/v0.58.1...v0.58.2)

### 14 March 2023

#### Changed

- batch-edit no longer overwrites keywords but instead merges new keywords with existing keywords

#### Added

- added --replace-keywords flag to `osxphotos batch-edit` to force replacement of keywords

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code changes.
- [@pekingduck](https://github.com/pekingduck) for pointing out the deisgn flaw in `batch-edit --keywords` logic

## [v0.58.1](https://github.com/RhetTbull/osxphotos/compare/v0.58.0...v0.58.1)

### 09 March 2023

#### Fixed

- Null times in Photos database (#1014)

#### Added

- Added appends, prepends filter to template system (#1015)
- Added python and macOS versions to --version output (#1008)

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code changes.
- [@ianmmoir](https://github.com/ianmmoir) for finding null times bug

## [v0.58.0](https://github.com/RhetTbull/osxphotos/compare/v0.57.3...v0.58.0)

### 25 February 2023

#### Added

- Added `osxphotos batch-edit` command to batch edit metadata (title, description, keywords, location) on selected photos. See `osxphotos help batch-edit` for more information. (#949)
- Added `--date-added` and `--date-added-from-photo` to `osxphotos timewarp` command to adjust the date added for selected photos. This is useful for removing photos from the Recents folder, for example. (#998)

#### Fixed

- Bug fix for export when retry failed to close export database. Thanks to [@eecue](https://github.com/eecue) for reporting this. (#999)

#### Contributors

- [@RhetTbull](https://github.com/RhetTbull) for code changes.
- [@eecue](https://github.com/eecue) for finding export database bug.

## [v0.57.3](https://github.com/RhetTbull/osxphotos/compare/v0.57.2...v0.57.3)

### 20 February 2023

### Added `osxphotos show FILEPATH`

#### Added

- `osxphotos show FILEPATH` to show a photo in Photos from the filepath to an exported photo, exported with `osxphotos export`

#### Internal

- Fixed a bug in `echo_error()` that occurred only in certain circumstances.

#### Contributors To This Release

- [@RhetTbull](https://github.com/RhetTbull) for code changes.

## [v0.57.2](https://github.com/RhetTbull/osxphotos/compare/v0.57.1...v0.57.2)

### 20 February 2023

### Updated exportdb to add migrate library feature

#### Added

- `--migrate-photos-library` option added to `osxphotos exportdb` to migrate the export database from one Photos library to another. This is useful when moving to a new computer but maintaining the existing osxphotos export.  Thanks to @swduncan for the idea. (#990)

#### Fixed

- Fixed a bug in `osxphotos export --cleanup` to handle files which could not be deleted. Thanks to @oPromessa for finding this and suggesting the fix. (#987)

#### Internal

- Fixed a bug that caused `rich_echo()` to not display rich text if `--verbose` wasn't specified.

#### Contributors To This Release

- [@RhetTbull](https://github.com/RhetTbull) for code changes.
- [@Promessa](https://github.com/promessa) who found the cleanup bug and suggested a code fix.
- [@swduncan](https://github.com/swduncan) who suggested the library migrate use case.

## [v0.57.1](https://github.com/RhetTbull/osxphotos/compare/v0.57.0...v0.57.1)

### 12 February 2023

### Added show command, bug fix, refactoring

A bug fix and some refactoring to prepare for adding a parallel export mode. Also added `osxphotos show` command.

#### Added

- Implemented show command: `osxphotos show UUID_OR_NAME` finds the photo/album/folder in Photos and spotlights it in the Photos app (#964)
- `--uuid-from-file` can now read from stdin if the filename is `-` (#965)

#### Changed

- Added lock files to export to minimize name collisions. This will help with implementing a parallel/multi-process export mode later.

#### Fixed

- Fixed `osxphotos timewarp` bug if timezone was null in database (#976)

#### Contributors To This Release

- [@RhetTbull](https://github.com/RhetTbull)
- [@aa599](https://github.com/aa599) for reporting the timezone bug and suggesting change to `--uuid-from-file`

## [v0.57.0](https://github.com/RhetTbull/osxphotos/compare/v0.56.7...v0.57.0)

### 5 February 2023

### Bug Fix and Refactoring

This release included a lot of refactoring of the command line code to make it easier to maintain.
No new features were added. Because a lot of the code changed, it's more likely than usual that
some bugs got introduced (or reintroduced) this time so if you encounter any, let me know by
opening an [issue](https://github.com/RhetTbull/osxphotos/issues).

#### Fixed

- Fixed regression for exporting associated burst images (#640)

#### Changed

- Refactored much of the CLI code to make it more maintainable, specifically those commands that used QUERY_OPTIONS. (#602)
- Deprecated `osxphotos dump` (will be removed in a future release); added dump functionality to `osxphotos query` (#793)
- Deprecated use of the Photos database argument in favor of the `--db/--library` option. Will be removed in a future release.
- Added query options to `osxphotos debug-dump` (#966)
- Refactored --verbose to accept multiple counts. For example, `-VV` or `--verbose --verbose` will increase verbose level. (#931)
- QUERY_OPTIONS can exclude options (#930)

#### Added

- Added new [query_command and selection_command decorators](https://github.com/RhetTbull/osxphotos/blob/master/API_README.md#building-simple-command-line-tools)
for building simple command line tools.

#### Contributors

- @RhetTbull

## [v0.56.7](https://github.com/RhetTbull/osxphotos/compare/v0.56.6...v0.56.7)

### 28 January 2023

### Bug Fixes and A Few New Features

#### Added

- Added `--not-edited` option to query | Added corresponding tests for query and export ([@oPromessa](https://github.com/oPromessa))
- Implemented `{counter}` template [#957](https://github.com/RhetTbull/osxphotos/pull/957) ([@RhetTbull](https://github.com/RhetTbull))

#### Fixed

- Fixed --dry-run with --finder-tags-keywords and --xattr-template, #958

#### Changed

- Refactored verbose #931

#### Contributors to this release

- @oPromessa for adding `--not-edited`
- @pweaver - thanks for finding the bug with `--dry-run` and `--finder-tag-keywords`
- @eecue for providing testing data

## [v0.56.6](https://github.com/RhetTbull/osxphotos/compare/v0.56.5...v0.56.6)

### 22 January 2023

### TimeWarp Update

#### Added

- Added --parse-date to timewarp to parse date from filename (and optionally timezone) (#867)
- Added `PersonInfo.favorite` and `PersonInfo.feature_less` (#940)

#### Contributors

- Thanks to @eecue for the idea of `PersonInfo.feature_less`
- Release files for 0.56.6 [`#952`](https://github.com/RhetTbull/osxphotos/pull/952)
- Feature timewarp parse date 867 [`#951`](https://github.com/RhetTbull/osxphotos/pull/951)
- Feature person favorite 940 [`#950`](https://github.com/RhetTbull/osxphotos/pull/950)

## [v0.56.5](https://github.com/RhetTbull/osxphotos/compare/v0.56.4...v0.56.5)

### 21 January 2023

### Hotfix for osxphotos timewarp

#### Fixed

- Fixed iCloud sync for `osxphotos timewarp --timezone`

## [v0.56.4](https://github.com/RhetTbull/osxphotos/compare/v0.56.3...v0.56.4)

### 21 January 2023

### Speed up for import and better search info in Ventura

#### Added

- `osxphotos inspect` now shows all search info for selected photo (#934)
- Added PhotoInfo.SearchInfo.source to show source of photo (e.g. Messages, Instagram, ...) (#937)

#### Fixed

- Fixed incorrect SearchInfo categories for Ventura

#### Contributors

- Thanks to @djbeadle for idea of adding SearchInfo.source
- Thanks for @oPromessa for testing `import` speed-ups and providing test data

### [v0.56.3](https://github.com/RhetTbull/osxphotos/compare/v0.56.2...v0.56.3)

### 16 January 2023

### add-locations command

#### Added

- Added new `osxphotos add-locations` command to add missing locations to photos. Thanks to @eecue for the inspiration!

#### Fixed

- Fixed bug in `osxphotos sync` command to filter shared photos, which cannot be synced

## [v0.56.2](https://github.com/RhetTbull/osxphotos/compare/v0.56.1...v0.56.2)

### 15 January 2023

### Various Enhancements

#### Added

- Added score info to inspect, #899

#### Changed

- Updated PhotoScript version to use faster folder/album code

#### Fixed

- Fixed 'Photos 5 only' in help text
- Added note on `pipx ensurepath` to README.md
- On import consider GPS Location from XMP if EXIF is not available

#### Contributors to this release

- @RhetTbull - Added AI scores to `osxphotos inspect`
- @mave2k - Documentation fixes
- @oPromessa - Bug fix for metadata in `osxphotos import`

## [v0.56.1](https://github.com/RhetTbull/osxphotos/compare/v0.56.0...v0.56.1)

### 14 January 2023

### Sync Command

#### Added

- Added new `osxphotos sync` command to sync metadata between libraries (#887)

## [v0.56.0](https://github.com/RhetTbull/osxphotos/compare/v0.55.7...v0.56.0)

### 13 January 2023

### Ability to export photos in iCloud / not in iCloud

#### Added

- Added --incloud, --not-incloud, --not-missing, --cloudasset, --not-cloudasset to export (#800)
- Added PhotoInfo.fingerprint (#900)

#### Changed

- Added --profile, --watch, --breakpoint, --debug as global options; previously these worked only with export

#### New Contributors

- Added @oPromessa as a contributor for code
- Added @johnsturgeon as a contributor for bug, and doc
- Added @qkeddy as a contributor for ideas, and data

## [v0.55.7](https://github.com/RhetTbull/osxphotos/compare/v0.55.6...v0.55.7)

### 1 January 2023

### Bug fix for shared photos on Ventura

#### Fixed

- Fixes path for shared photos on Ventura
- Shared photos can now be exported on Ventura

## [v0.55.6](https://github.com/RhetTbull/osxphotos/compare/v0.55.5...v0.55.6)

### 30 December 2022

### Updates for timewarp and export when reading/writing QuickTime dates

#### Changed

- Added QuickTime:ContentCreateDate as a source for `osxphotos timewarp`
- Write QuickTime:ContentCreateDate when exporting with --exiftool for `osxphotos export`

#### Contributors

Thanks to @PetrochukM for identifying this and providing code!

## [v0.55.5](https://github.com/RhetTbull/osxphotos/compare/v0.55.3...v0.55.5)

> 24 December 2022

- Handle "Z" as EXIF offset time [`#881`](https://github.com/RhetTbull/osxphotos/pull/881)
- add fmckeogh as a contributor for code, and bug [`#882`](https://github.com/RhetTbull/osxphotos/pull/882)
- Version bump for release [`5f29870`](https://github.com/RhetTbull/osxphotos/commit/5f298709d7d87f00d0abf6401a6cb101a7ebe630)

## [v0.55.3](https://github.com/RhetTbull/osxphotos/compare/v0.55.2...v0.55.3)

> 19 December 2022

- Release files for 0.55.3 [`#879`](https://github.com/RhetTbull/osxphotos/pull/879)
- Partial implementation for #868, candidate paths [`#878`](https://github.com/RhetTbull/osxphotos/pull/878)
- Fix for #853, deleted files not in exportdb --report [`#877`](https://github.com/RhetTbull/osxphotos/pull/877)
- Fix for #872, duplicate results with --exif (and --name) [`#876`](https://github.com/RhetTbull/osxphotos/pull/876)
- fix: dev_requirements.txt to reduce vulnerabilities [`#836`](https://github.com/RhetTbull/osxphotos/pull/836)
- Added errors to export database, --update-errors to export, #872 [`#874`](https://github.com/RhetTbull/osxphotos/pull/874)
- Bug fix for missing RAW images during export [`8b9af7b`](https://github.com/RhetTbull/osxphotos/commit/8b9af7be6758292b03dc291261636f334ff407a4)
- Release files [`de584e3`](https://github.com/RhetTbull/osxphotos/commit/de584e3dec63025c583910e1fa4b247341b25379)
- Added Ventura 13.1 to support OS versions [`830da7b`](https://github.com/RhetTbull/osxphotos/commit/830da7b3b40c1908c10310c41005fd3cf318cecd)

## [v0.55.2](https://github.com/RhetTbull/osxphotos/compare/v0.55.1...v0.55.2)

> 13 December 2022

- Bug edited path bad mojave 859 [`#870`](https://github.com/RhetTbull/osxphotos/pull/870)
- Version bump, fix for #859, wrong edited path in Mojave [`aeb6283`](https://github.com/RhetTbull/osxphotos/commit/aeb6283b2bed243be3bb3de8863cb3e40b797140)
- Added template function example [`ee370f5`](https://github.com/RhetTbull/osxphotos/commit/ee370f5dfba78dd4f3a2835aa56e9d1bf2bc1d9a)
- Added timewarp --function example [`2afab9e`](https://github.com/RhetTbull/osxphotos/commit/2afab9e3b16642ed4486c7a2533aeb184b6ec1a1)
- Added edited live video path to inspect, #865 [`3c8d7e1`](https://github.com/RhetTbull/osxphotos/commit/3c8d7e13b92b8db4999e458aac2ce37eb706cc7b)
- Updated README for supported OS versions [`c3bd04f`](https://github.com/RhetTbull/osxphotos/commit/c3bd04f257f8fbdf93034f60342943a3ffbdeb5d)

## [v0.55.1](https://github.com/RhetTbull/osxphotos/compare/v0.55.0...v0.55.1)

> 11 December 2022

- Bug edited path bad mojave 859 [`#864`](https://github.com/RhetTbull/osxphotos/pull/864)
- Version bump, fix for #859, wrong edited path in Mojave [`e4faf37`](https://github.com/RhetTbull/osxphotos/commit/e4faf3779c6c56982fba909a0efda21b86890b73)
- Update tests.yml [`debc001`](https://github.com/RhetTbull/osxphotos/commit/debc001af9684d04a31836a6fa5705b706eb36f0)
- Fixed edit_resource_id for Photos 5+ [`025ee36`](https://github.com/RhetTbull/osxphotos/commit/025ee36086d1515aa16a0018aaa5ae371a8a332d)

## [v0.55.0](https://github.com/RhetTbull/osxphotos/compare/v0.54.4...v0.55.0)

> 11 December 2022

- Added Ventura to list of supported OS [`#863`](https://github.com/RhetTbull/osxphotos/pull/863)
- Partial fix for #859, missing path edited on Mojave [`#862`](https://github.com/RhetTbull/osxphotos/pull/862)
- add drodner as a contributor for bug, and userTesting [`#861`](https://github.com/RhetTbull/osxphotos/pull/861)
- Updated build for Ventura [`327f198`](https://github.com/RhetTbull/osxphotos/commit/327f19809ee0f8883977a27eb547dcc7f9e93e11)
- Added target architecture, #857 [`88e56bc`](https://github.com/RhetTbull/osxphotos/commit/88e56bc0b978d75b606a4adf36fa2d77ef16eb95)

## [v0.54.4](https://github.com/RhetTbull/osxphotos/compare/v0.54.3...v0.54.4)

> 24 November 2022

- Added --post-function to import, #842 [`#851`](https://github.com/RhetTbull/osxphotos/pull/851)
- Feature import parse date 847 [`#850`](https://github.com/RhetTbull/osxphotos/pull/850)
- Version bump for release [`cad4e1e`](https://github.com/RhetTbull/osxphotos/commit/cad4e1eeff54a37826c0e08e2be1b3df3b392f94)
- Added test for #848 [`d6fc8fc`](https://github.com/RhetTbull/osxphotos/commit/d6fc8fc3b1d276fd6b22550e50ec1bdeeb3acf6f)

## [v0.54.3](https://github.com/RhetTbull/osxphotos/compare/v0.54.2...v0.54.3)

> 16 November 2022

- add zephyr325 as a contributor for bug [`#844`](https://github.com/RhetTbull/osxphotos/pull/844)
- Version bump [`9ed1b39`](https://github.com/RhetTbull/osxphotos/commit/9ed1b394a9b2df1eca04f489c083ca3a71a7809c)
- Fix for timewarp failure on Ventura, #841 [`40de05c`](https://github.com/RhetTbull/osxphotos/commit/40de05c5fdbc8efd8e4bd21eb8b2e17d49f4864e)
- Updated search_info test [`f610d3c`](https://github.com/RhetTbull/osxphotos/commit/f610d3cc65a7909cfe3bd9ad4d5209f193c88a87)

## [v0.54.2](https://github.com/RhetTbull/osxphotos/compare/v0.54.1...v0.54.2)

> 14 November 2022

- Added --alt-copy method for #807 [`#835`](https://github.com/RhetTbull/osxphotos/pull/835)
- Version bump [`548071e`](https://github.com/RhetTbull/osxphotos/commit/548071e8a6f626b1f22ae7c92d209dd98bf83c27)
- Fixed help text for , #828 [`ea76297`](https://github.com/RhetTbull/osxphotos/commit/ea76297800f3e72e6584618c126fe818f21bc1ae)

## [v0.54.1](https://github.com/RhetTbull/osxphotos/compare/v0.54.0...v0.54.1)

> 13 November 2022

- Bug search info macos13 816 [`#831`](https://github.com/RhetTbull/osxphotos/pull/831)
- add dmd as a contributor for userTesting [`#829`](https://github.com/RhetTbull/osxphotos/pull/829)
- Updated docs [`155f29a`](https://github.com/RhetTbull/osxphotos/commit/155f29a3735e8c93eaa66f3d979cb1a12b7cd4f8)
- Updated build script, dev dependencies [`644582b`](https://github.com/RhetTbull/osxphotos/commit/644582b540c0b4928a2ece3eb3e56eb63af78877)
- Added tests for macOS 13 / Ventura, added test for labels on macOS 13, #816 [`831eecf`](https://github.com/RhetTbull/osxphotos/commit/831eecfdf70992a2aae8f2454a3b96a44ec85e9c)
- Version bump [`f957e43`](https://github.com/RhetTbull/osxphotos/commit/f957e43ee1242f6902b93e36150233b0cab8a42c)
- Updated dependencies for #832 [`0995076`](https://github.com/RhetTbull/osxphotos/commit/0995076fe78e11124b207e6d3796d834582d506f)

## [v0.54.0](https://github.com/RhetTbull/osxphotos/compare/v0.53.0...v0.54.0)

> 12 November 2022

- Version bump [`dc1a600`](https://github.com/RhetTbull/osxphotos/commit/dc1a600493b0b3ef598b34a321b0d25b9c7424ac)
- Updated dependencies for python 3.11, #817, #825 [`ff981dd`](https://github.com/RhetTbull/osxphotos/commit/ff981ddc0ae2280636e827e421ccee74ed8ad9e9)
- Updated dependencies for python 3.11, #817, #825 [`7d72499`](https://github.com/RhetTbull/osxphotos/commit/7d72499ac2700c5b53528f817af2f79b0f242057)

## [v0.53.0](https://github.com/RhetTbull/osxphotos/compare/v0.52.0...v0.53.0)

> 12 November 2022

- add dmd as a contributor for bug [`#824`](https://github.com/RhetTbull/osxphotos/pull/824)
- Bug labels ventura 816 [`#823`](https://github.com/RhetTbull/osxphotos/pull/823)
- Added ImportInfo __bool__, #820 [`dcc16c9`](https://github.com/RhetTbull/osxphotos/commit/dcc16c92c16e5e59f6551e6561eaf5824470f3c3)
- Added instructions for python 3.11/pipx [`2e38a56`](https://github.com/RhetTbull/osxphotos/commit/2e38a56f26b873e235db715a64149b5b7129d2d8)
- Updated example to match API [`6dbeaae`](https://github.com/RhetTbull/osxphotos/commit/6dbeaae54174bafce01897599f782d02787d6fe7)
- Update README.md [`2cd61dc`](https://github.com/RhetTbull/osxphotos/commit/2cd61dccf9d36db02c83cbd82743699b9bf8dda6)

## [v0.52.0](https://github.com/RhetTbull/osxphotos/compare/v0.51.8...v0.52.0)

> 6 November 2022

- add dalisoft as a contributor for code, and test [`#806`](https://github.com/RhetTbull/osxphotos/pull/806)
- fix: remove warning for macOS 11.7 [`#805`](https://github.com/RhetTbull/osxphotos/pull/805)
- Refactor update osxmetadata [`#804`](https://github.com/RhetTbull/osxphotos/pull/804)
- Version bump [`d91bf14`](https://github.com/RhetTbull/osxphotos/commit/d91bf14790616818dbb8b70431a4ee11601838aa)
- Updated dependencies [`61ac447`](https://github.com/RhetTbull/osxphotos/commit/61ac447e3e425b83a5eba986ed3dbe1d31c66105)
- Fixed typo in requirements.txt [`6fa07d4`](https://github.com/RhetTbull/osxphotos/commit/6fa07d48c55b615a695c309f007675d8b93ade2d)
- Bugfix for bare {filepath} template [`0ba8bc3`](https://github.com/RhetTbull/osxphotos/commit/0ba8bc3eb9caaa9fe7319fd694ef8d64263b9472)

## [v0.51.8](https://github.com/RhetTbull/osxphotos/compare/v0.51.7...v0.51.8)

> 25 September 2022

- Bugfix exportdb migration 794 [`#795`](https://github.com/RhetTbull/osxphotos/pull/795)
- Release 0.51.8, bug fix for exportdb migration [`00eb800`](https://github.com/RhetTbull/osxphotos/commit/00eb80044e4623330b07de174e710597544847d6)
- Updated dependencies [`43fcdbc`](https://github.com/RhetTbull/osxphotos/commit/43fcdbc371a1142dc2f9a002f45764c97f30db6e)
- Tested on 12.6, #792 [`eedc2f0`](https://github.com/RhetTbull/osxphotos/commit/eedc2f0b059617dcd6809dc6603b4d96dc397071)

## [v0.51.7](https://github.com/RhetTbull/osxphotos/compare/v0.51.6...v0.51.7)

> 11 September 2022

- Feature read iphone db #745 [`#791`](https://github.com/RhetTbull/osxphotos/pull/791)
- fix: requirements.txt to reduce vulnerabilities [`#789`](https://github.com/RhetTbull/osxphotos/pull/789)
- fix: dev_requirements.txt to reduce vulnerabilities [`#725`](https://github.com/RhetTbull/osxphotos/pull/725)
- Refactor phototemplate [`#788`](https://github.com/RhetTbull/osxphotos/pull/788)
- Refactored ExportResults [`#786`](https://github.com/RhetTbull/osxphotos/pull/786)
- Release 0.51.7, support for reading iPhone Photos.sqlite [`b5b7a28`](https://github.com/RhetTbull/osxphotos/commit/b5b7a2853940dbf68bfda8743ee6054f58fb88f8)
- Added QR code example [`74a730e`](https://github.com/RhetTbull/osxphotos/commit/74a730e420fc3e7ae23fba4394a5cfb4d27c8f76)
- Updated PhotosAlbum code [`d5a9001`](https://github.com/RhetTbull/osxphotos/commit/d5a900166103914f2d7c3e17ce4f14c38f6df9c3)
- Updated sqlitekvstore [`cee2aca`](https://github.com/RhetTbull/osxphotos/commit/cee2acad53af6762f234324c44bd28daf132b85f)
- Updated QR Code example [`83ce702`](https://github.com/RhetTbull/osxphotos/commit/83ce702a4690d3f5b570a26b0e684590789e28bb)

## [v0.51.6](https://github.com/RhetTbull/osxphotos/compare/v0.51.5...v0.51.6)

> 31 August 2022

- Added --resume to import, #768 [`#784`](https://github.com/RhetTbull/osxphotos/pull/784)
- Added release files for 0.51.5 [`3ca0e2b`](https://github.com/RhetTbull/osxphotos/commit/3ca0e2bb5b7f5333b55381aded3300ed09162e1c)
- Release 0.51.6, added --resume to import [`5794df0`](https://github.com/RhetTbull/osxphotos/commit/5794df00694370fc01b2f3001a1eb53ddf9f7e23)

## [v0.51.5](https://github.com/RhetTbull/osxphotos/compare/v0.51.4...v0.51.5)

> 27 August 2022

- Added --field to dump and query, #777 [`#779`](https://github.com/RhetTbull/osxphotos/pull/779)
- docs: add tkrunning as a contributor for code, bug [`#776`](https://github.com/RhetTbull/osxphotos/pull/776)
- docs: add jmuccigr as a contributor for bug, ideas [`#775`](https://github.com/RhetTbull/osxphotos/pull/775)

## [v0.51.4](https://github.com/RhetTbull/osxphotos/compare/v0.51.3...v0.51.4)

> 27 August 2022

- Release 0.51.4, added --print to dump [`bb480f6`](https://github.com/RhetTbull/osxphotos/commit/bb480f69914ed351b6f4309b0f6aa539add1a9fb)
- Added --print to dump, added {tab} [`5eaeb72`](https://github.com/RhetTbull/osxphotos/commit/5eaeb72c3ee296af6abc6ca6ddf8ad05baf02052)
- Fixed --print to work with {tab} [`af9311c`](https://github.com/RhetTbull/osxphotos/commit/af9311c9c86a3d0a5764ebd1539d40f14e62f2ec)

## [v0.51.3](https://github.com/RhetTbull/osxphotos/compare/v0.51.2...v0.51.3)

> 27 August 2022

- Added --print, --quiet, #769, #770 [`#773`](https://github.com/RhetTbull/osxphotos/pull/773)
- Release 0.51.3, added --print (#769), --quiet (#770) [`d576ca5`](https://github.com/RhetTbull/osxphotos/commit/d576ca54948c0cbbd16f04231459a294f0333f89)
- Added bump2version [`320fb86`](https://github.com/RhetTbull/osxphotos/commit/320fb8655980882fd75e354d33450f0904babf2a)

## [v0.51.2](https://github.com/RhetTbull/osxphotos/compare/v0.51.1...v0.51.2)

> 26 August 2022

- Release 0.51.2, added new filter(x) to template filters [`#772`](https://github.com/RhetTbull/osxphotos/pull/772)
- Feature filter filter 759 [`#771`](https://github.com/RhetTbull/osxphotos/pull/771)

## [v0.51.1](https://github.com/RhetTbull/osxphotos/compare/v0.51.0...v0.51.1)

> 22 August 2022

- Release 0.51.1, added --report to import [`#767`](https://github.com/RhetTbull/osxphotos/pull/767)
- Added --report to import command [`#766`](https://github.com/RhetTbull/osxphotos/pull/766)
- Fixed template function to work with import command [`#765`](https://github.com/RhetTbull/osxphotos/pull/765)
- Updated README [skip ci] [`b5f4c48`](https://github.com/RhetTbull/osxphotos/commit/b5f4c48ec98b344b5d7ed7c2a5e9a445d322df13)

## [v0.51.0](https://github.com/RhetTbull/osxphotos/compare/v0.50.13...v0.51.0)

> 21 August 2022

- Release 0.51.0 [`#763`](https://github.com/RhetTbull/osxphotos/pull/763)
- Feature add import 754 [`#762`](https://github.com/RhetTbull/osxphotos/pull/762)
- Updated tested versions [`#757`](https://github.com/RhetTbull/osxphotos/pull/757)
- Updated examples [skip ci] [`c7e3a55`](https://github.com/RhetTbull/osxphotos/commit/c7e3a552db60321fc9999153b6b5624bc1bb76dc)
- Updated xmp_rating example [`1e053aa`](https://github.com/RhetTbull/osxphotos/commit/1e053aa7086af44a207d1be045d698c7d10b97f5)
- Updated xmp_rating example [`46738d0`](https://github.com/RhetTbull/osxphotos/commit/46738d05b213d1d8ef390add71142623892385ce)

## [v0.50.13](https://github.com/RhetTbull/osxphotos/compare/v0.50.12...v0.50.13)

> 13 August 2022

- Release 0.50.13 [`#756`](https://github.com/RhetTbull/osxphotos/pull/756)
- Feature orphans [`#755`](https://github.com/RhetTbull/osxphotos/pull/755)
- Added bad_photos example [skip ci] [`2103d8b`](https://github.com/RhetTbull/osxphotos/commit/2103d8bcad65807d23f14315dbc4a76b3b6badfe)
- Add PhotosAlbumPhotosKit to __all__ [`26a9028`](https://github.com/RhetTbull/osxphotos/commit/26a9028497d147c047a4b73c5cf0fe964f7b2e00)
- Add PhotosAlbum to osxphotos __all__ [`e41f894`](https://github.com/RhetTbull/osxphotos/commit/e41f89480a37a19778c7b97fa0c8b0ceedfd56cd)

## [v0.50.12](https://github.com/RhetTbull/osxphotos/compare/v0.50.11...v0.50.12)

> 8 August 2022

- Hot fix for 749 [`#750`](https://github.com/RhetTbull/osxphotos/pull/750)
- Added strip_live.py example [`#747`](https://github.com/RhetTbull/osxphotos/pull/747)
- Added reddit badge for r/osxphotos [`#746`](https://github.com/RhetTbull/osxphotos/pull/746)

## [v0.50.11](https://github.com/RhetTbull/osxphotos/compare/v0.50.10...v0.50.11)

> 28 July 2022

- Feature not reference 738 [`#744`](https://github.com/RhetTbull/osxphotos/pull/744)
- docs: add nullpointerninja as a contributor for ideas [`#743`](https://github.com/RhetTbull/osxphotos/pull/743)
- docs: add franzone as a contributor for bug [`#742`](https://github.com/RhetTbull/osxphotos/pull/742)

## [v0.50.10](https://github.com/RhetTbull/osxphotos/compare/v0.50.9...v0.50.10)

> 27 July 2022

- Updated docs for v0.58.10 [skip-ci] [`#741`](https://github.com/RhetTbull/osxphotos/pull/741)
- Feature add keep 730 [`#740`](https://github.com/RhetTbull/osxphotos/pull/740)
- docs: add Se7enair as a contributor for ideas [`#737`](https://github.com/RhetTbull/osxphotos/pull/737)

## [v0.50.9](https://github.com/RhetTbull/osxphotos/compare/v0.50.8...v0.50.9)

> 23 July 2022

- Release files for #732, add --favorite-rating [`f8f9bd7`](https://github.com/RhetTbull/osxphotos/commit/f8f9bd7b933c077528649560d692ceb22d254768)
- Implemented --favorite-rating, #732 [`5d33dcd`](https://github.com/RhetTbull/osxphotos/commit/5d33dcdcc3af1ca9dfa11b7be2ab51f6906d9e61)

## [v0.50.8](https://github.com/RhetTbull/osxphotos/compare/v0.50.7...v0.50.8)

> 23 July 2022

- Added report_summary view to export report database [`7484c7b`](https://github.com/RhetTbull/osxphotos/commit/7484c7b9942d430089039d203fb7dc37004e8af9)
- Fixed report_summart view [`2e85f9b`](https://github.com/RhetTbull/osxphotos/commit/2e85f9be891e1d762b548abbea7b5ca2b3ed7da3)
- Added report_summary view to export report database [`f279217`](https://github.com/RhetTbull/osxphotos/commit/f279217118e2051ecdb54d14fb207c627ab36a7e)

## [v0.50.7](https://github.com/RhetTbull/osxphotos/compare/v0.50.6...v0.50.7)

> 23 July 2022

- docs: add infused-kim as a contributor for ideas [`#736`](https://github.com/RhetTbull/osxphotos/pull/736)
- Implemented #731, export_id in report database [`bd33b61`](https://github.com/RhetTbull/osxphotos/commit/bd33b61882fa746e9750be7cd80e6e2f785131b2)
- Refactored implementation for #731 [`855d417`](https://github.com/RhetTbull/osxphotos/commit/855d417e816d796165208658dc276ca378bf3337)
- Added live video and raw photo size to inspect, #734 [`7497a02`](https://github.com/RhetTbull/osxphotos/commit/7497a02aaf155bf719e4ccc2c9d3a443f351353a)
- Updated docs [skip ci] [`f3557d1`](https://github.com/RhetTbull/osxphotos/commit/f3557d1991021766dfa8a5018f95b3f7a95777b6)

## [v0.50.6](https://github.com/RhetTbull/osxphotos/compare/0.50.5...v0.50.6)

> 15 July 2022

- docs: add nullpointerninja as a contributor for bug [`#724`](https://github.com/RhetTbull/osxphotos/pull/724)
- Bug fix for #726 [`5a43fb7`](https://github.com/RhetTbull/osxphotos/commit/5a43fb7410c2fc5407bbe41f4b7c6e3cefb54f0d)
- Possible fix for #726 [`30bf06e`](https://github.com/RhetTbull/osxphotos/commit/30bf06e79489005f85a72fa45a5986cac506fdad)

## [0.50.5](https://github.com/RhetTbull/osxphotos/compare/v0.50.4...0.50.5)

> 1 July 2022

- Fix for large files and exiftool, #722 [`#723`](https://github.com/RhetTbull/osxphotos/pull/723)
- Added example [skip ci] [`c20a399`](https://github.com/RhetTbull/osxphotos/commit/c20a3994c01bddea2e3bc42a9656ac9e6c858f34)
- Updated README.md [skip ci] [`6b0db22`](https://github.com/RhetTbull/osxphotos/commit/6b0db223a7d43ab2dd0d2358e549f7014bf6dd32)
- Updated README.md [skip ci] [`7d84b3d`](https://github.com/RhetTbull/osxphotos/commit/7d84b3d6cc0305e381f5b4870a2a83640d3d7d2a)

## [v0.50.4](https://github.com/RhetTbull/osxphotos/compare/v0.50.3...v0.50.4)

> 17 June 2022

- Initial support for Ventura developer preview [`#715`](https://github.com/RhetTbull/osxphotos/pull/715)
- Added initial support for macOS Ventura/13.0 beta [`51317a6`](https://github.com/RhetTbull/osxphotos/commit/51317a607c5e3788f9b6ebbde83027fa2e31cc4f)
- Added example [skip ci] [`561c684`](https://github.com/RhetTbull/osxphotos/commit/561c6846e40b4bbbc58c46a802309d56553238e1)
- Updated examples [skip ci] [`04c2f61`](https://github.com/RhetTbull/osxphotos/commit/04c2f6121affc313f98562959be2aa74de93dbe6)
- Updated examples [skip ci] [`56435b1`](https://github.com/RhetTbull/osxphotos/commit/56435b101fb99893916728206ec74154fbc203b3)
- Updated examples [skip ci] [`f47aa72`](https://github.com/RhetTbull/osxphotos/commit/f47aa721654e4c002bdfd7bef5997011d86564ec)

## [v0.50.3](https://github.com/RhetTbull/osxphotos/compare/v0.50.2...v0.50.3)

> 29 May 2022

- Added --template to inspect command [`c2f02c3`](https://github.com/RhetTbull/osxphotos/commit/c2f02c3b7bf212c8c987868cd8a2374fcc8ffaf0)
- Fixed docs [`04e1149`](https://github.com/RhetTbull/osxphotos/commit/04e1149cadce034fc36fd6a593975432c6c99d07)

## [v0.50.2](https://github.com/RhetTbull/osxphotos/compare/v0.50.1...v0.50.2)

> 28 May 2022

- Added shortuuid, #314 [`7556826`](https://github.com/RhetTbull/osxphotos/commit/75568269bbd7b05a22f9fd00acd6f59691f1a507)
- Added slice, sslice filters [`9e9266e`](https://github.com/RhetTbull/osxphotos/commit/9e9266ec9c890ed6fb09d61b1a075be954bef7c1)
- Fixed shortuuid docs [`203dccb`](https://github.com/RhetTbull/osxphotos/commit/203dccb39fbe68b996d53126b52fd3fcedc5f0a1)

## [v0.50.1](https://github.com/RhetTbull/osxphotos/compare/v0.50.0...v0.50.1)

> 28 May 2022

- Updated README.md, #707 [skip ci] [`a049b99`](https://github.com/RhetTbull/osxphotos/commit/a049b99b0ef67803da917f92ecb24b18fbe6a6c9)
- Version 0.50.1 with --delete-file, --delete-uuid exportdb commands [`6c1650b`](https://github.com/RhetTbull/osxphotos/commit/6c1650b7cffefc223374f66012393f14d443fa72)
- Updated docs [skip ci] [`b6e7a75`](https://github.com/RhetTbull/osxphotos/commit/b6e7a75a8110e7f71ae615e50e91419d92f5b59e)

## [v0.50.0](https://github.com/RhetTbull/osxphotos/compare/v0.49.9...v0.50.0)

> 28 May 2022

- Version 0.50.0 with updated template engine [`175d7ea`](https://github.com/RhetTbull/osxphotos/commit/175d7ea223dcb650ad3f642b0ae23f0ed1cf2a37)
- Updated template language to match autofile [`0a973d6`](https://github.com/RhetTbull/osxphotos/commit/0a973d67f94a5c59ee7dbbf4fb18892c61666d5d)

## [v0.49.9](https://github.com/RhetTbull/osxphotos/compare/v0.49.8...v0.49.9)

> 26 May 2022

- Updated docs [`8d020cb`](https://github.com/RhetTbull/osxphotos/commit/8d020cbf09fcd2921cfb388a187bb6e891b263b2)
- Implemented retry for export db, #569 [`dae710b`](https://github.com/RhetTbull/osxphotos/commit/dae710b836a8ff0d3553052d9d7f9af6e1a94f02)
- Bug fix, #695 [`7926c8d`](https://github.com/RhetTbull/osxphotos/commit/7926c8d676d0ff38b60eda7c88409a932801f115)

## [v0.49.8](https://github.com/RhetTbull/osxphotos/compare/v0.49.7...v0.49.8)

> 23 May 2022

- Removed screencast, [skip ci] [`9d7a5e2`](https://github.com/RhetTbull/osxphotos/commit/9d7a5e22d92cd889c2a54b4c58828f6e499995de)

## [v0.49.7](https://github.com/RhetTbull/osxphotos/compare/v0.49.6...v0.49.7)

> 23 May 2022

- Bug fix, #695 [`e9cc6ce`](https://github.com/RhetTbull/osxphotos/commit/e9cc6ce137927664a42a3dfb1d93d7ba44d74e4d)
- Removed screencast, [skip ci] [`bc32b18`](https://github.com/RhetTbull/osxphotos/commit/bc32b1827f55b4481a49ea2db0530e5a77719028)
- Added screencast [skip ci] [`206ad8c`](https://github.com/RhetTbull/osxphotos/commit/206ad8c33c04e4b3074e8b32942266cb043aebd4)

## [v0.49.6](https://github.com/RhetTbull/osxphotos/compare/v0.49.5...v0.49.6)

> 22 May 2022

- Bug fix [`7a52d41`](https://github.com/RhetTbull/osxphotos/commit/7a52d413a3cb130a6d11413775fad88933249f36)
- Fixed detected_text for videos [`ab8b7b4`](https://github.com/RhetTbull/osxphotos/commit/ab8b7b4b198c00569b3852b9a21b0b032fad1940)

## [v0.49.5](https://github.com/RhetTbull/osxphotos/compare/v0.49.4...v0.49.5)

> 22 May 2022

- Feature inspect command [`#701`](https://github.com/RhetTbull/osxphotos/pull/701)
- Initial implementation of inspect command [`#700`](https://github.com/RhetTbull/osxphotos/pull/700)
- Added inspect command [`128e84c`](https://github.com/RhetTbull/osxphotos/commit/128e84c7a4b9745d70e71e3bb1c48c9952431dec)

## [v0.49.4](https://github.com/RhetTbull/osxphotos/compare/v0.49.3...v0.49.4)

> 21 May 2022

- Added timestamp to export_data in exportdb, #697 [`6400204`](https://github.com/RhetTbull/osxphotos/commit/64002044d2cbbd6fb3c2f0ab69ff6cd5ee2e8e25)
- Added warning on hardlinks to exiftool command [`4e40d4b`](https://github.com/RhetTbull/osxphotos/commit/4e40d4b74e9b244b8eee602f839e595af4f99dfb)

## [v0.49.3](https://github.com/RhetTbull/osxphotos/compare/v0.49.2...v0.49.3)

> 21 May 2022

- Updated docs [`0a7575b`](https://github.com/RhetTbull/osxphotos/commit/0a7575b889949f9e74ad716bc316e87f2599d4ad)
- Added --uuid-info, --uuid-files to exportdb [`c776f30`](https://github.com/RhetTbull/osxphotos/commit/c776f3070d40ed960eabe3c21c57c354108ff5e4)

## [v0.49.2](https://github.com/RhetTbull/osxphotos/compare/v0.49.1...v0.49.2)

> 21 May 2022

- Initial implementation of exiftool command, #691 [`#696`](https://github.com/RhetTbull/osxphotos/pull/696)
- Added exiftool command [`8e9f279`](https://github.com/RhetTbull/osxphotos/commit/8e9f27995b56489da8968e77018a8a3d1bbe76bd)
- Added example [skip ci] [`6d5af5c`](https://github.com/RhetTbull/osxphotos/commit/6d5af5c5e87aa0699da7291376cbf05c4237f6ec)
- Updated docs [skip ci] [`3473c2e`](https://github.com/RhetTbull/osxphotos/commit/3473c2ece2b6eea9885893c85aa9eceb16921b94)
- Updated test [`dfcb99f`](https://github.com/RhetTbull/osxphotos/commit/dfcb99f3774cb519c30a9fcf403ca9fdc3fed993)

## [v0.49.1](https://github.com/RhetTbull/osxphotos/compare/v0.49.0...v0.49.1)

> 17 May 2022

- Implemented #689 [`4ec9f6d`](https://github.com/RhetTbull/osxphotos/commit/4ec9f6d3e606f72962e351432a64a24ff9153d87)
- Unhid exportdb command [`5a9722b`](https://github.com/RhetTbull/osxphotos/commit/5a9722b37c8326bde7c6bde9870ce704aabb2a15)
- Added example [`72af96b`](https://github.com/RhetTbull/osxphotos/commit/72af96b48ee7552d5d35e6f5d619c5b7a55050ab)

## [v0.49.0](https://github.com/RhetTbull/osxphotos/compare/v0.48.8...v0.49.0)

> 15 May 2022

- Feature report writer #309 [`#690`](https://github.com/RhetTbull/osxphotos/pull/690)
- Added JSON, SQLite report formats, added  command [`1173b6c`](https://github.com/RhetTbull/osxphotos/commit/1173b6c0f294e12269d4015d2823b590df6f9696)
- --report can now accept a template, #339 [`391815d`](https://github.com/RhetTbull/osxphotos/commit/391815dd9401fb0b47c0f935cf844bbb85e5ae55)
- Fixed run command to allow passing args to the called python script [`b4dc7cf`](https://github.com/RhetTbull/osxphotos/commit/b4dc7cfcf6af1a4b88fc826b99a900318f5b1c84)
- Fixed test to run on MacOS &gt; Catalina [`a89c66b`](https://github.com/RhetTbull/osxphotos/commit/a89c66b3f773b31199febc3daf1d2441f3fdfa43)

## [v0.48.8](https://github.com/RhetTbull/osxphotos/compare/v0.48.7...v0.48.8)

> 8 May 2022

- version bump [`5cd74b5`](https://github.com/RhetTbull/osxphotos/commit/5cd74b5f2373b48c261bea3c6378945ee216531a)

## [v0.48.7](https://github.com/RhetTbull/osxphotos/compare/v0.48.6...v0.48.7)

> 8 May 2022

- Fixed path_derivatives for shared photos, #687 [`abbb200`](https://github.com/RhetTbull/osxphotos/commit/abbb200838535e03cf4adcb339ad3a2c18f32dc3)
- Added --no-keyword, #637 [`e7eefce`](https://github.com/RhetTbull/osxphotos/commit/e7eefce5c51e1e17e64ac44b6c0a9944873f68a3)
- Fixed typo in docs [`2ed6e11`](https://github.com/RhetTbull/osxphotos/commit/2ed6e1142644e686b6b645d3bedab3648e13f9df)

## [v0.48.6](https://github.com/RhetTbull/osxphotos/compare/v0.48.5...v0.48.6)

> 7 May 2022

- Added --limit, version bump [`5ab5c53`](https://github.com/RhetTbull/osxphotos/commit/5ab5c53b26207eb326191c110ac544592c980c32)

## [v0.48.5](https://github.com/RhetTbull/osxphotos/compare/v0.48.4...v0.48.5)

> 7 May 2022

- Added --limit, #592 [`#685`](https://github.com/RhetTbull/osxphotos/pull/685)

## [v0.48.4](https://github.com/RhetTbull/osxphotos/compare/v0.48.3...v0.48.4)

> 6 May 2022

- Feature metadata changed 621 [`#684`](https://github.com/RhetTbull/osxphotos/pull/684)
- Version bump, updated docs [`ff2e810`](https://github.com/RhetTbull/osxphotos/commit/ff2e810d49f9acffb81f3b7aea6271191d6762f9)

## [v0.48.3](https://github.com/RhetTbull/osxphotos/compare/v0.48.2...v0.48.3)

> 5 May 2022

- Added --added-after, --added-before, --added-in-last, #439 [`#683`](https://github.com/RhetTbull/osxphotos/pull/683)
- Updated to pytimeparse2, added tests for custom Click param types [`3ed658a`](https://github.com/RhetTbull/osxphotos/commit/3ed658a7d018b5ac61c1054e20a59576e8613609)

## [v0.48.2](https://github.com/RhetTbull/osxphotos/compare/v0.48.1...v0.48.2)

> 3 May 2022

- Added moment_info, #71 [`9bc5890`](https://github.com/RhetTbull/osxphotos/commit/9bc5890589b7ff45d7b1e8bca4f958a6b4dc5fad)
- Added --force to timewarp to bypass confirmation [`f42bee8`](https://github.com/RhetTbull/osxphotos/commit/f42bee84c08cf8c6883058a8c2d45dfe9c3e2357)
- Added confirmation for timewarp, #677 [`ac67ef2`](https://github.com/RhetTbull/osxphotos/commit/ac67ef23846fb2a35211be8b63f5201a5567c68e)

## [v0.48.1](https://github.com/RhetTbull/osxphotos/compare/v0.48.0...v0.48.1)

> 1 May 2022

- Feature timewarp function [`#678`](https://github.com/RhetTbull/osxphotos/pull/678)
- Updated docs [`6070616`](https://github.com/RhetTbull/osxphotos/commit/60706167173f719d70e21193acef89f6252767e6)

## [v0.48.0](https://github.com/RhetTbull/osxphotos/compare/v0.47.13...v0.48.0)

> 1 May 2022

- Feature timewarp [`#675`](https://github.com/RhetTbull/osxphotos/pull/675)
- Version bump [`d07aab5`](https://github.com/RhetTbull/osxphotos/commit/d07aab58d1b0ef8e8769740db089235bbc938a4e)
- Updated dependencies for rich_theme_manager [`8a3dc9b`](https://github.com/RhetTbull/osxphotos/commit/8a3dc9b3938f2363baba6dbf1f832ee55d57eb28)

## [v0.47.13](https://github.com/RhetTbull/osxphotos/compare/v0.47.12...v0.47.13)

> 24 April 2022

- Updated docs to use zipfile [`bd9a14a`](https://github.com/RhetTbull/osxphotos/commit/bd9a14a6f30042044345b91c5c3d5176ac6bc4ad)
- Added retry to export_db for #674 [`e4b6c0f`](https://github.com/RhetTbull/osxphotos/commit/e4b6c0f1e00123064575e39183cb5a209afee49d)
- Updated license [`ad13565`](https://github.com/RhetTbull/osxphotos/commit/ad13565dfded64fdf1dd72a001609d2522b64737)

## [v0.47.12](https://github.com/RhetTbull/osxphotos/compare/v0.47.11...v0.47.12)

> 23 April 2022

- Updated version [`a7ed7dd`](https://github.com/RhetTbull/osxphotos/commit/a7ed7dde54a10e7d277d1253f6c75e721aaacf83)

## [v0.47.11](https://github.com/RhetTbull/osxphotos/compare/v0.47.10...v0.47.11)

> 23 April 2022

- Added version command [`#672`](https://github.com/RhetTbull/osxphotos/pull/672)
- Added API_README [`ee6e460`](https://github.com/RhetTbull/osxphotos/commit/ee6e4602e4506fce63a4a207112c1224163eef8d)
- Updated docs build to use cog [`b8b4c15`](https://github.com/RhetTbull/osxphotos/commit/b8b4c15784b611ac170ebfc0ddff68f78c82f5d1)
- Updated docs with developer notes [`fa80ea3`](https://github.com/RhetTbull/osxphotos/commit/fa80ea3772fed00afe4cab0493e7d02c39291358)

## [v0.47.10](https://github.com/RhetTbull/osxphotos/compare/v0.47.9...v0.47.10)

> 22 April 2022

- Updated docs [`b1aa923`](https://github.com/RhetTbull/osxphotos/commit/b1aa9238d38a90afa3cb9d2f5f95cf8b1f344690)

## [v0.47.9](https://github.com/RhetTbull/osxphotos/compare/v0.47.8...v0.47.9)

> 20 April 2022

- Added --year query option, #593 [`#670`](https://github.com/RhetTbull/osxphotos/pull/670)
- Updated docs, version [`f4c02c3`](https://github.com/RhetTbull/osxphotos/commit/f4c02c39ba3bda2777f9a0919d8874f686dc8d1b)
- Open cli.html instead of index.html [`7e4977e`](https://github.com/RhetTbull/osxphotos/commit/7e4977e2c57f3646ad98cf5328e3467a893dace6)

## [v0.47.8](https://github.com/RhetTbull/osxphotos/compare/v0.47.7...v0.47.8)

> 19 April 2022

- Feature docs [`#665`](https://github.com/RhetTbull/osxphotos/pull/665)
- Added docs [`840a252`](https://github.com/RhetTbull/osxphotos/commit/840a2520837d30b30000d612c557fb9537d11212)
- Added validation for template string options [`afe5ed3`](https://github.com/RhetTbull/osxphotos/commit/afe5ed3dc04b692ef404e9d3eb11137a0f3dbb04)
- Added docs command, partial for #666 [`5b25284`](https://github.com/RhetTbull/osxphotos/commit/5b25284db2f3067b9839f2ef2781ae83fd52c424)
- Added osxphotos/docs [`91784ab`](https://github.com/RhetTbull/osxphotos/commit/91784ab982b74a3a4f993e25731dc279bc6e76a2)
- Added osxphotos/docs [`5ea708f`](https://github.com/RhetTbull/osxphotos/commit/5ea708f063b3153fcfdbb12189d1676d527a24e5)

## [v0.47.7](https://github.com/RhetTbull/osxphotos/compare/v0.47.6...v0.47.7)

> 17 April 2022

- Theme [`#664`](https://github.com/RhetTbull/osxphotos/pull/664)
- Updated docs [skip ci] [`b09323b`](https://github.com/RhetTbull/osxphotos/commit/b09323b9fbce53f6ea7ace949952772f81d79b70)
- Fixed typing in examples [`1f40161`](https://github.com/RhetTbull/osxphotos/commit/1f401619500fb56cf0bfc6b02b1af1a09a2dabd8)
- Version bump [`213d84e`](https://github.com/RhetTbull/osxphotos/commit/213d84e9648efcb5c37c48aa45e3d27d7cb76d80)
- Quoted path in repl [`d1aa4e9`](https://github.com/RhetTbull/osxphotos/commit/d1aa4e92bdc62948186dbee2cab40a644beb8112)
- Added cov.xml [skip ci] [`9c0b910`](https://github.com/RhetTbull/osxphotos/commit/9c0b910046e2b5702d09d42c89556ed970191f80)

## [v0.47.6](https://github.com/RhetTbull/osxphotos/compare/v0.47.5...v0.47.6)

> 27 March 2022

- fix verbose output when redirected to file, #661 [`382d097`](https://github.com/RhetTbull/osxphotos/commit/382d097285519e274bdb0cd16d6805152aa4a918)
- Updated docs [skip ci] [`6875427`](https://github.com/RhetTbull/osxphotos/commit/68754273de33ac9ed767fd43edcfe8b9c92e3a56)
- version bump [`d28a2fe`](https://github.com/RhetTbull/osxphotos/commit/d28a2fe9bb69034c19446c3dc70555b6043a43a0)

## [v0.47.5](https://github.com/RhetTbull/osxphotos/compare/v0.47.4...v0.47.5)

> 12 March 2022

- Richify [`#653`](https://github.com/RhetTbull/osxphotos/pull/653)
- Added --watch, --breakpoint [`#652`](https://github.com/RhetTbull/osxphotos/pull/652)
- Hack to fix #654 when utime fails on NAS [`#654`](https://github.com/RhetTbull/osxphotos/issues/654)
- Debug updates [`de1900f`](https://github.com/RhetTbull/osxphotos/commit/de1900f10aaac8d703ef5d850a64f18dd5e01d40)
- Updated docs [skip ci] [`fccd746`](https://github.com/RhetTbull/osxphotos/commit/fccd746c581a319a8d1d5063133cbb9d5a4e1778)
- Changed return val of _should_update_photo to enum for easier debugging [`bbcc3ac`](https://github.com/RhetTbull/osxphotos/commit/bbcc3acba9a4dd3a9ebcc8136782005d35e46255)
- Updated crash_reporter to include crash data [`1227465`](https://github.com/RhetTbull/osxphotos/commit/1227465aa7e1d5a2fdaba4fc45cf917728d31170)
- Fixed missing pdb.py issue for pyinstaller, partial for #659 [`e272e95`](https://github.com/RhetTbull/osxphotos/commit/e272e95a856e5b448eb6ac85818757b974dfd6d4)

## [v0.47.4](https://github.com/RhetTbull/osxphotos/compare/v0.47.3...v0.47.4)

> 2 March 2022

- Added --tmpdir, #650 [`#651`](https://github.com/RhetTbull/osxphotos/pull/651)
- Version bump [`6b342a1`](https://github.com/RhetTbull/osxphotos/commit/6b342a1733fa66d1663de2e3a234970f427a679f)
- Version bump [`f132e9a`](https://github.com/RhetTbull/osxphotos/commit/f132e9a8438023e4c69c7fb767d24dea7465db4d)

## [v0.47.3](https://github.com/RhetTbull/osxphotos/compare/v0.47.2...v0.47.3)

> 27 February 2022

- Help topic [`#644`](https://github.com/RhetTbull/osxphotos/pull/644)
- updated docs [skip ci] [`ce73c9c`](https://github.com/RhetTbull/osxphotos/commit/ce73c9cab81fdd223dd49f2ff38608d553198412)
- Added -v to pytest [`8be6a98`](https://github.com/RhetTbull/osxphotos/commit/8be6a98c3208b5da0fa620d1884a17275ab56599)

## [v0.47.2](https://github.com/RhetTbull/osxphotos/compare/v0.47.1...v0.47.2)

> 27 February 2022

- Updated README.md [`b275280`](https://github.com/RhetTbull/osxphotos/commit/b275280a1f3e1b1a61dcc95aefebd4e326a47377)
- Updated docs [skip ci] [`c95f682`](https://github.com/RhetTbull/osxphotos/commit/c95f682ca647f9b9e0718da658bdf7c735571f84)
- Fix for --load-config, #643 [`feb9538`](https://github.com/RhetTbull/osxphotos/commit/feb9538d1c5ad6569232e5900393befb8ec1a57e)

## [v0.47.1](https://github.com/RhetTbull/osxphotos/compare/v0.47.0...v0.47.1)

> 26 February 2022

- Fixed entry point [`d275367`](https://github.com/RhetTbull/osxphotos/commit/d2753672f36a0c84b7be143a47cc85cd6c99cb6d)

## [v0.47.0](https://github.com/RhetTbull/osxphotos/compare/v0.46.6...v0.47.0)

> 26 February 2022

- CLI refactor [`#642`](https://github.com/RhetTbull/osxphotos/pull/642)
- Updated docs [skip ci] [`6fae979`](https://github.com/RhetTbull/osxphotos/commit/6fae97906124c9284e382170e20c8ab9999105b0)
- Fixed 3.10 in yaml [`3704fc4`](https://github.com/RhetTbull/osxphotos/commit/3704fc4a23e83ff2d16d6d221fb6c752dabcedca)
- Dropped 3.7 [`7883fc1`](https://github.com/RhetTbull/osxphotos/commit/7883fc1911057df9a4c596375b498e85a73c1bec)

## [v0.46.6](https://github.com/RhetTbull/osxphotos/compare/v0.46.5...v0.46.6)

> 26 February 2022

- Updated tests [`43e1cb1`](https://github.com/RhetTbull/osxphotos/commit/43e1cb18cc65b1abe1f49b464563e816b2ed1cff)
- Updated docs [skip ci] [`3a990e3`](https://github.com/RhetTbull/osxphotos/commit/3a990e39971d838e52d5f19bf28b8253c4c7b811)
- Bug fix for bitmath types in saved config [`26f916e`](https://github.com/RhetTbull/osxphotos/commit/26f916e4cbf4f28154c47aa2de1fdbc0aebc65b3)

## [v0.46.5](https://github.com/RhetTbull/osxphotos/compare/v0.46.4...v0.46.5)

> 24 February 2022

- Updated tested versions [`4d1b1db`](https://github.com/RhetTbull/osxphotos/commit/4d1b1db2a7cf34afaa2dc5dbebc69021ff77964f)

## [v0.46.4](https://github.com/RhetTbull/osxphotos/compare/v0.46.1...v0.46.4)

> 24 February 2022

- Removed debug code from exiftool, fixed #641 [`#641`](https://github.com/RhetTbull/osxphotos/issues/641)
- Added debug output to exiftool [`39ba17d`](https://github.com/RhetTbull/osxphotos/commit/39ba17dd1cb4d8a61ab4dc8d5cff12ff9871eee0)
- Fixed export of bursts with --uuid and --selected, #640 [`5b66962`](https://github.com/RhetTbull/osxphotos/commit/5b66962ac1bc1f48106fb8eeb600e6010088dc3b)
- Added --sql command to exportdb [`c8ee679`](https://github.com/RhetTbull/osxphotos/commit/c8ee6797999af954c32e96ac3799a19002f4f0fe)
- Updated docs [skip ci] [`2966c9a`](https://github.com/RhetTbull/osxphotos/commit/2966c9a60fc828afdf34263b759159a3ade31897)
- Updated debug info [`6cb7ded`](https://github.com/RhetTbull/osxphotos/commit/6cb7dedd9be53d2c62489125fc44b9f4dccfb7ae)

## [v0.46.1](https://github.com/RhetTbull/osxphotos/compare/v0.46.0...v0.46.1)

> 21 February 2022

- Added --ramdb option [`#639`](https://github.com/RhetTbull/osxphotos/pull/639)

## [v0.46.0](https://github.com/RhetTbull/osxphotos/compare/v0.45.12...v0.46.0)

> 21 February 2022

- Exportdb refactor [`#638`](https://github.com/RhetTbull/osxphotos/pull/638)
- Updated docs [skip ci] [`5290fae`](https://github.com/RhetTbull/osxphotos/commit/5290fae2e0ad062750348aedfee4feaf7b2e769f)

## [v0.45.12](https://github.com/RhetTbull/osxphotos/compare/v0.45.11...v0.45.12)

> 14 February 2022

- Allow multiple characters as path_sep, #634 [`d8204e6`](https://github.com/RhetTbull/osxphotos/commit/d8204e65eb740cece468ef021cbdf45d896d954e)
- Added --debug and crash reporter to export, #628 [`060729c`](https://github.com/RhetTbull/osxphotos/commit/060729c4c4255651c6ee8149989d9de541d0a6aa)
- Added crash_reporter.py [`9c26e55`](https://github.com/RhetTbull/osxphotos/commit/9c26e5519b2d48f3a0ae80d1cc4a765c12b62d40)

## [v0.45.11](https://github.com/RhetTbull/osxphotos/compare/v0.45.10...v0.45.11)

> 13 February 2022

- beta fix for #633, fix face regions in exiftool [`afbda03`](https://github.com/RhetTbull/osxphotos/commit/afbda030bce87f914445ebbced3f0e110e2e203b)
- Updated docs [skip ci] [`65d51ab`](https://github.com/RhetTbull/osxphotos/commit/65d51ab1290e7c7804021e24829b93f5dce81245)

## [v0.45.10](https://github.com/RhetTbull/osxphotos/compare/v0.45.9...v0.45.10)

> 12 February 2022

- Added --force-update, #621 [`30abddd`](https://github.com/RhetTbull/osxphotos/commit/30abdddaf3765f1d604984d4781b78b7806871e1)

## [v0.45.9](https://github.com/RhetTbull/osxphotos/compare/v0.45.8...v0.45.9)

> 12 February 2022

- Added --force-update, #621 [`bfa888a`](https://github.com/RhetTbull/osxphotos/commit/bfa888adc5658a2845dcaa9b7ea360926ed4f000)
- Refactored fix for #627 [`5fb686a`](https://github.com/RhetTbull/osxphotos/commit/5fb686ac0c231932c2695fc550a0824307bd3c5f)
- Fix for #630 [`ac4083b`](https://github.com/RhetTbull/osxphotos/commit/ac4083bfbbabc8550718f0f7f8aadc635c05eb25)

## [v0.45.8](https://github.com/RhetTbull/osxphotos/compare/v0.45.6...v0.45.8)

> 5 February 2022

- Fixed exiftool to ignore unsupported file types, #615 [`1ae6270`](https://github.com/RhetTbull/osxphotos/commit/1ae627056113fc4655f1b24cfbbdf0efc04489e7)
- Updated tests [`55a601c`](https://github.com/RhetTbull/osxphotos/commit/55a601c07ea1384623c55d5c1d26b568df5d7823)
- Additional fix for #615 [`1d6bc4e`](https://github.com/RhetTbull/osxphotos/commit/1d6bc4e09e3c2359a21f842fadd781920606812e)

## [v0.45.6](https://github.com/RhetTbull/osxphotos/compare/v0.45.5...v0.45.6)

> 5 February 2022

- Fix for unicode in query strings, #618 [`9b247ac`](https://github.com/RhetTbull/osxphotos/commit/9b247acd1cc4b2def59fdd18a6fb3c8eb9914f11)
- Fix for --name searching only original_filename on Photos 5+, #594 [`cd02144`](https://github.com/RhetTbull/osxphotos/commit/cd02144ac33cc1c13a20358133971c84d35b8a57)

## [v0.45.5](https://github.com/RhetTbull/osxphotos/compare/v0.45.4...v0.45.5)

> 5 February 2022

- Fix for #561, no really, I mean it this time [`b3d3e14`](https://github.com/RhetTbull/osxphotos/commit/b3d3e14ffe41fbb22edb614b24f3985f379766a2)
- Updated docs [skip ci] [`2b9ea11`](https://github.com/RhetTbull/osxphotos/commit/2b9ea11701799af9a661a8e2af70fca97235f487)
- Updated tests for #561 [skip ci] [`77a49a0`](https://github.com/RhetTbull/osxphotos/commit/77a49a09a1bee74113a7114c543fbc25fa410ffc)

## [v0.45.4](https://github.com/RhetTbull/osxphotos/compare/v0.45.3...v0.45.4)

> 3 February 2022

- docs: add oPromessa as a contributor for ideas, test [`#611`](https://github.com/RhetTbull/osxphotos/pull/611)
- Fix for filenames with special characters, #561, #618 [`f3063d3`](https://github.com/RhetTbull/osxphotos/commit/f3063d35be3c96342d83dbd87ddd614a2001bff4)
- Updated docs [skip ci] [`06c5bbf`](https://github.com/RhetTbull/osxphotos/commit/06c5bbfcfdf591a4a5d43f1456adaa27385fe01a)
- Added progress counter, #601 [`7ab5007`](https://github.com/RhetTbull/osxphotos/commit/7ab500740b28594dcd778140e10991f839220e9d)
- Updated known issues [skip ci] [`e32090b`](https://github.com/RhetTbull/osxphotos/commit/e32090bf39cb786171b49443f878ffdbab774420)

## [v0.45.3](https://github.com/RhetTbull/osxphotos/compare/v0.45.2...v0.45.3)

> 29 January 2022

- Added --timestamp option for --verbose, #600 [`d8c2f99`](https://github.com/RhetTbull/osxphotos/commit/d8c2f99c06bc6f72bf2cb1a13c5765824fe3cbba)
- Updated docs [skip ci] [`5fc2813`](https://github.com/RhetTbull/osxphotos/commit/5fc28139ea0374bc3e228c0432b8a41ada430389)
- Updated formatting for elapsed time, #604 [`16d3f74`](https://github.com/RhetTbull/osxphotos/commit/16d3f743664396d43b3b3028a5e7a919ec56d9e1)

## [v0.45.2](https://github.com/RhetTbull/osxphotos/compare/v0.45.0...v0.45.2)

> 29 January 2022

- Implemented #605, refactor out export2 [`235dea3`](https://github.com/RhetTbull/osxphotos/commit/235dea329c98ab8fa61565c09a1b4a83e5d99043)
- Fix for #564, --preview with --download-missing [`5afdf6f`](https://github.com/RhetTbull/osxphotos/commit/5afdf6fc20a3cb6eb2b0217d8b3be20295eb7ba4)

## [v0.45.0](https://github.com/RhetTbull/osxphotos/compare/v0.44.13...v0.45.0)

> 28 January 2022

- Performance improvements and refactoring, #462, partial for #591 [`22964af`](https://github.com/RhetTbull/osxphotos/commit/22964afc6988166218413125d7a62348bb858a83)
- Refactored photoexporter for performance, #591 [`6843b86`](https://github.com/RhetTbull/osxphotos/commit/6843b8661d41d42368794c77304fc07194e7af18)
- Performance improvements, partial for #591 [`3bc53fd`](https://github.com/RhetTbull/osxphotos/commit/3bc53fd92b3222c6959e7aa12310811db41b83fe)

## [v0.44.13](https://github.com/RhetTbull/osxphotos/compare/v0.44.12...v0.44.13)

> 24 January 2022

- Removed exportdb requirement from PhotoTemplate [`6af124e`](https://github.com/RhetTbull/osxphotos/commit/6af124e4d3a0e26c48f435452920020cd42afa1c)
- Version bump [`bd31120`](https://github.com/RhetTbull/osxphotos/commit/bd3112056920806f565be2c0c12caf4f2aff5231)

## [v0.44.12](https://github.com/RhetTbull/osxphotos/compare/v0.44.11...v0.44.12)

> 23 January 2022

- Added query options to repl, #597 [`7855801`](https://github.com/RhetTbull/osxphotos/commit/785580115b29f5ccb895de22be1243f56dbb43dc)
- Added run command, #598 [`b4bd04c`](https://github.com/RhetTbull/osxphotos/commit/b4bd04c1461d0b427937f541403305bc979bcf4f)
- Bug fix for get_photos_library_version [`e88c6b8`](https://github.com/RhetTbull/osxphotos/commit/e88c6b8a59dfd947f6cf3c7eac9c92519ab781a3)

## [v0.44.11](https://github.com/RhetTbull/osxphotos/compare/v0.44.10...v0.44.11)

> 23 January 2022

- creat unit test for __all__ [`#599`](https://github.com/RhetTbull/osxphotos/pull/599)
- Performance improvements, added --profile [`7486823`](https://github.com/RhetTbull/osxphotos/commit/74868238f3b1ee18feb744f137f5c14ef8e36ffc)

## [v0.44.10](https://github.com/RhetTbull/osxphotos/compare/v0.44.9...v0.44.10)

> 22 January 2022

- Create __all__ for all python files [`#589`](https://github.com/RhetTbull/osxphotos/pull/589)
- Create __all__ for the file cli.py [`#587`](https://github.com/RhetTbull/osxphotos/pull/587)
- docs: add xwu64 as a contributor for code [`#585`](https://github.com/RhetTbull/osxphotos/pull/585)
- add __all__ to files "adjustmentsinfo.py" and "albuminfo.py" [`#584`](https://github.com/RhetTbull/osxphotos/pull/584)
- More refactoring of export code, #462 [`6261a7b`](https://github.com/RhetTbull/osxphotos/commit/6261a7b5c96ac43aece66b72b9e27a90854accfa)
- Added ExportOptions to photoexporter.py, #462 [`9517876`](https://github.com/RhetTbull/osxphotos/commit/9517876bd06572238648a6362a309063b86007e7)
- Blackified files [`3bafdf7`](https://github.com/RhetTbull/osxphotos/commit/3bafdf7bfd5f7992b2e0c12496c55e7be1f57455)
- More refactoring of export code, #462 [`c2d726b`](https://github.com/RhetTbull/osxphotos/commit/c2d726beafabe76cf4d5fb3213447c900129b8c0)
- Refactored photoexporter sidecar writing, #462 [`458da0e`](https://github.com/RhetTbull/osxphotos/commit/458da0e9b2b82a78cec30191c5bf1ee2ed993acf)

## [v0.44.9](https://github.com/RhetTbull/osxphotos/compare/v0.44.8...v0.44.9)

> 9 January 2022

- Added diff command [`3927f05`](https://github.com/RhetTbull/osxphotos/commit/3927f052670b2a1c31cced1f8278a0ffe519a3eb)
- Added uuid command [`a010ab5`](https://github.com/RhetTbull/osxphotos/commit/a010ab5a299470782b938e689a7ddc336513065e)

## [v0.44.8](https://github.com/RhetTbull/osxphotos/compare/v0.44.7...v0.44.8)

> 9 January 2022

- docs: add ahti123 as a contributor for code, bug [`#578`](https://github.com/RhetTbull/osxphotos/pull/578)
- changing photos_5 version constant to satisfy version 5001 [`#577`](https://github.com/RhetTbull/osxphotos/pull/577)
- Added grep command to CLI [`4dd838b`](https://github.com/RhetTbull/osxphotos/commit/4dd838b8bcb639eba3df9cb60a7cd28f45b22833)
- Added test for #576 [`92fced7`](https://github.com/RhetTbull/osxphotos/commit/92fced75da38f1c47be8d3d9d4ee22463ad029b9)
- Added sqlgrep [`53c701c`](https://github.com/RhetTbull/osxphotos/commit/53c701cc0ebd38db255c1ce694391b38dbb5fe01)
- Fix for #575, database version 5001 [`5a8105f`](https://github.com/RhetTbull/osxphotos/commit/5a8105f5a02080368ad22717c064afcb0748f646)
- Updated docs [skip ci] [`64a0760`](https://github.com/RhetTbull/osxphotos/commit/64a0760a47205a452e015a860f39f45bba67164a)

## [v0.44.7](https://github.com/RhetTbull/osxphotos/compare/v0.44.6...v0.44.7)

> 8 January 2022

- Fix for #576, error exporting edited live photos [`2e7db47`](https://github.com/RhetTbull/osxphotos/commit/2e7db47806683fdd0db4d1d75e42471d2f127d4d)

## [v0.44.6](https://github.com/RhetTbull/osxphotos/compare/v0.44.5...v0.44.6)

> 6 January 2022

- Fix for burst images with pick type = 0, partial fix for #571 [`d2d56a7`](https://github.com/RhetTbull/osxphotos/commit/d2d56a7f7118aeffa7ac81cc474fdd4fb4843065)

## [v0.44.5](https://github.com/RhetTbull/osxphotos/compare/v0.44.4...v0.44.5)

> 6 January 2022

- More refactoring of export code, #462 [`0c9bd87`](https://github.com/RhetTbull/osxphotos/commit/0c9bd8760261770e11b0fa59153f49f2d65e2c2f)
- Fix for #570 [`661a573`](https://github.com/RhetTbull/osxphotos/commit/661a573bf50353fb2393c604080ffe0790ade59c)
- version bump [skip ci] [`b4897ff`](https://github.com/RhetTbull/osxphotos/commit/b4897ff1b5d2bc00f34158345b2b5fe85f1490ac)

## [v0.44.4](https://github.com/RhetTbull/osxphotos/compare/v0.44.3...v0.44.4)

> 4 January 2022

- Refactored photoinfo, photoexporter; #462 [`a73dc72`](https://github.com/RhetTbull/osxphotos/commit/a73dc72558b77152f4c90f143b6a60924b8905c8)
- More refactoring of export code, #462 [`147b30f`](https://github.com/RhetTbull/osxphotos/commit/147b30f97308db65868dc7a8d177d77ad0d0ad40)
- Export DB can now reside outside export directory, #568 [`76aee7f`](https://github.com/RhetTbull/osxphotos/commit/76aee7f189b4b32e2e263a4e798711713ed17a14)

## [v0.44.3](https://github.com/RhetTbull/osxphotos/compare/v0.44.2...v0.44.3)

> 31 December 2021

- ImageConverter now uses generic context; #562 [`a3b2784`](https://github.com/RhetTbull/osxphotos/commit/a3b2784f3177a753b78965b8ca205ca9bbb08168)
- Updated tests and docs [`1391675`](https://github.com/RhetTbull/osxphotos/commit/1391675a3a45be0d6800a68c8bcc6d0d55d1ab7a)
- Updated docs [skip ci] [`cbe79ee`](https://github.com/RhetTbull/osxphotos/commit/cbe79ee98cae68e0789df275220f5a5870a8bd91)

## [v0.44.2](https://github.com/RhetTbull/osxphotos/compare/v0.44.1...v0.44.2)

> 31 December 2021

- Bug fix for #559 [`42426b9`](https://github.com/RhetTbull/osxphotos/commit/42426b95ee786b2d53482d3d931a0b962a4db20d)

## [v0.44.1](https://github.com/RhetTbull/osxphotos/compare/v0.44.0...v0.44.1)

> 31 December 2021

- Added --skip-uuid, --skip-uuid-from-file, #563 [`04930c3`](https://github.com/RhetTbull/osxphotos/commit/04930c3644da99c1923c4e3aaa9213902aeadfd1)

## [v0.44.0](https://github.com/RhetTbull/osxphotos/compare/v0.43.9...v0.44.0)

> 31 December 2021

- Added support for projects, implements #559 [`44594a8`](https://github.com/RhetTbull/osxphotos/commit/44594a8e437c20bae6fd8eecb74075d49da4b91f)
- Updated docs [skip ci] [`c4e3c5a`](https://github.com/RhetTbull/osxphotos/commit/c4e3c5a8beac1db00533f7820ab8249cf351aef0)
- Fixed test for #561 [`690d981`](https://github.com/RhetTbull/osxphotos/commit/690d981f310b083f5f58407cc879bca494730765)

## [v0.43.9](https://github.com/RhetTbull/osxphotos/compare/v0.43.8...v0.43.9)

> 28 December 2021

- Fix for accented characters in album names, #561 [`03f4e7c`](https://github.com/RhetTbull/osxphotos/commit/03f4e7cc3473c276dfd7c7e6ad64e4dfe5b32011)

## [v0.43.8](https://github.com/RhetTbull/osxphotos/compare/v0.43.7...v0.43.8)

> 26 December 2021

- Fixed #463 [`#463`](https://github.com/RhetTbull/osxphotos/issues/463)
- Updated docs [skip ci] [`181f678`](https://github.com/RhetTbull/osxphotos/commit/181f678d9eda8bc8acca11b4ebd470900f30bdcb)
- Added install/uninstall commands, #531 [`085f482`](https://github.com/RhetTbull/osxphotos/commit/085f482820af2d51f0d411c7e8a7a27329bf0722)
- Implement #323 [`debb17c`](https://github.com/RhetTbull/osxphotos/commit/debb17c9520bec25d725426feaa512745e9d4ec0)
- Updated docs [skip ci] [`0e54a08`](https://github.com/RhetTbull/osxphotos/commit/0e54a08ae07853c4cdb2c548bdba27335cfc32ba)
- Added get_photos_library_version [`b71c752`](https://github.com/RhetTbull/osxphotos/commit/b71c752e9d2c59412baf812bfc50e6358ea3f02e)

## [v0.43.7](https://github.com/RhetTbull/osxphotos/compare/v0.43.6...v0.43.7)

> 21 December 2021

- Adds missing f-string to retry message [`#553`](https://github.com/RhetTbull/osxphotos/pull/553)
- Update issue templates [`e7bd80e`](https://github.com/RhetTbull/osxphotos/commit/e7bd80e05f94238fd41e478e32c1709b442eb361)
- Partial fix for #556 [`a08a653`](https://github.com/RhetTbull/osxphotos/commit/a08a653f202a49853780ab4a686bf3dfbc32a491)
- Updated all-contributors [`e1f1772`](https://github.com/RhetTbull/osxphotos/commit/e1f1772080d24373ceb5791683615451cd390874)
- Version bump [`6ce1b83`](https://github.com/RhetTbull/osxphotos/commit/6ce1b83ca2c7f0c6f9c86757602b81df1d9bf453)

## [v0.43.6](https://github.com/RhetTbull/osxphotos/compare/v0.43.5...v0.43.6)

> 10 December 2021

- Fixes typo in README [`#548`](https://github.com/RhetTbull/osxphotos/pull/548)
- docs: add alandefreitas as a contributor for bug [`#551`](https://github.com/RhetTbull/osxphotos/pull/551)
- docs: add dgleich as a contributor for code [`#541`](https://github.com/RhetTbull/osxphotos/pull/541)
- Updated docs [`197e566`](https://github.com/RhetTbull/osxphotos/commit/197e5663df058a013ce2d6f8c5fd7ff71a5cc46e)
- Added test library for Monterey on M1 [`3e038bf`](https://github.com/RhetTbull/osxphotos/commit/3e038bf124b98d6b74f19dd4db0f8f1e3c48e787)
- Updated docs [skip ci] [`f6dedaa`](https://github.com/RhetTbull/osxphotos/commit/f6dedaa6197dc244616c5b4e9e8ce42ce6b7a252)
- Added MomentInfo for Photos 5+, #71 [`a52b4d2`](https://github.com/RhetTbull/osxphotos/commit/a52b4d2f43970086bf25659bd58dc8479b841704)
- Fixed error for missing photo path, #547 [`0906dbe`](https://github.com/RhetTbull/osxphotos/commit/0906dbe6370922b4c9649350014ed8a21d29c4fd)

## [v0.43.5](https://github.com/RhetTbull/osxphotos/compare/v0.43.4...v0.43.5)

> 25 November 2021

- Updated dependencies for pyobjc 8.0 [`7d92359`](https://github.com/RhetTbull/osxphotos/commit/7d923590ae4df941b1b9d35c21937c03eb7b4284)

## [v0.43.4](https://github.com/RhetTbull/osxphotos/compare/v0.43.3...v0.43.4)

> 11 November 2021

- Fix for --use-photokit with --skip-live, #537 [`0e6c92d`](https://github.com/RhetTbull/osxphotos/commit/0e6c92dbd951dd0e63cfb8b6d64e6ab96ece5955)

## [v0.43.3](https://github.com/RhetTbull/osxphotos/compare/v0.43.1...v0.43.3)

> 7 November 2021

- Updated docs [skip ci] [`fb583e2`](https://github.com/RhetTbull/osxphotos/commit/fb583e28e0fc2c23bf24052db8a5ee669d8c92f5)
- Updated OTL to MTL [`2ffcf1e`](https://github.com/RhetTbull/osxphotos/commit/2ffcf1e82bfc013a4a9e0e7a709a7c1395c074ce)
- Test fixes for Monterey/M1 [`51ba549`](https://github.com/RhetTbull/osxphotos/commit/51ba54971a874cfce00368aa5be5380b3439c254)

## [v0.43.1](https://github.com/RhetTbull/osxphotos/compare/v0.43.0...v0.43.1)

> 30 October 2021

- Dependency update for Monterey [`818f4f4`](https://github.com/RhetTbull/osxphotos/commit/818f4f45a4ce520b0ba1c688eabd2f4311be9540)
- Updated docs [skip ci] [`2cf19f6`](https://github.com/RhetTbull/osxphotos/commit/2cf19f6af1a03767e4d53eee556c4d3ed9af1776)

## [v0.43.0](https://github.com/RhetTbull/osxphotos/compare/v0.42.94...v0.43.0)

> 28 October 2021

- Updated for Monterey 12.0.1 release [`ef82c6e`](https://github.com/RhetTbull/osxphotos/commit/ef82c6e32b536b0677530133892f95b852c6dce0)

## [v0.42.94](https://github.com/RhetTbull/osxphotos/compare/v0.42.93...v0.42.94)

> 15 October 2021

- docs: add spencerc99 as a contributor for bug [`#527`](https://github.com/RhetTbull/osxphotos/pull/527)
- Fix for #526 with --update [`419b34e`](https://github.com/RhetTbull/osxphotos/commit/419b34ea73f15ccbe29f51896e11e9735ea5786b)
- Updated docs [skip ci] [`0e9b9d6`](https://github.com/RhetTbull/osxphotos/commit/0e9b9d625190b94c1dd68276e3b0e5367002d87c)
- Fixed FileUtil to use correct import [`f64c4ed`](https://github.com/RhetTbull/osxphotos/commit/f64c4ed374c120a95fe8adea26bd44852ca67e31)

## [v0.42.93](https://github.com/RhetTbull/osxphotos/compare/v0.42.92...v0.42.93)

> 11 October 2021

- Fix for #526 [`202bc11`](https://github.com/RhetTbull/osxphotos/commit/202bc1144bc842ddec825eef0745830d56170aba)
- Updated README.md [skip ci] [`a0c654e`](https://github.com/RhetTbull/osxphotos/commit/a0c654e43f4aa5389a96c3c84fd7037c33d23404)

## [v0.42.92](https://github.com/RhetTbull/osxphotos/compare/v0.42.91...v0.42.92)

> 11 October 2021

- docs: add oPromessa as a contributor for bug [`#525`](https://github.com/RhetTbull/osxphotos/pull/525)
- Fix for #524 [`04ac0a1`](https://github.com/RhetTbull/osxphotos/commit/04ac0a11215b275178013e60c6a61b9f1b3603c9)
- Fix for #525 [`d2b0bd4`](https://github.com/RhetTbull/osxphotos/commit/d2b0bd4e28cfdf3c930aa6ae3317549327b0e29c)
- Updated docs [skip ci] [`2bb677d`](https://github.com/RhetTbull/osxphotos/commit/2bb677dc19abaf254bc66e2cd788676e0613e548)

## [v0.42.91](https://github.com/RhetTbull/osxphotos/compare/v0.42.90...v0.42.91)

> 11 October 2021

- Updated docs [skip ci] [`b23e74f`](https://github.com/RhetTbull/osxphotos/commit/b23e74f8f5a8387564108c330c3f8ac11189860d)
- Added python 3.10 to supported versions [`3f81a3c`](https://github.com/RhetTbull/osxphotos/commit/3f81a3c179dde37e9811ef19c847920bb3bd514c)
- Updated dependencies [`a895833`](https://github.com/RhetTbull/osxphotos/commit/a895833c7f0a264488e671f1735f9e10d2618e2d)

## [v0.42.90](https://github.com/RhetTbull/osxphotos/compare/v0.42.89...v0.42.90)

> 30 September 2021

- Updated REPL, now with more cowbell [`c472698`](https://github.com/RhetTbull/osxphotos/commit/c472698b1d0d8ff9f4d1bde715859bf766f99290)
- Updated docs [skip ci] [`1ddb1de`](https://github.com/RhetTbull/osxphotos/commit/1ddb1de99841e65b690ffc1cbcc5e42e6e25f727)

## [v0.42.89](https://github.com/RhetTbull/osxphotos/compare/v0.42.88...v0.42.89)

> 26 September 2021

- Updated docs [skip ci] [`bfbc156`](https://github.com/RhetTbull/osxphotos/commit/bfbc156821d2d262b7bd9c4437e23e310da10769)
- Updated docs [skip ci] [`3abaa5a`](https://github.com/RhetTbull/osxphotos/commit/3abaa5ae84ca44cd900f1e3af4532ab405d41a09)
- Fixed AlbumInfo.owner, #239 [`bfd6274`](https://github.com/RhetTbull/osxphotos/commit/bfd627460255c65f870bca6d036401e8792d29d5)

## [v0.42.88](https://github.com/RhetTbull/osxphotos/compare/v0.42.87...v0.42.88)

> 26 September 2021

- Performance fix for #239, owner [`14710e3`](https://github.com/RhetTbull/osxphotos/commit/14710e31789d71b2c948a37722fb6054aca4d85e)
- version bump [`06138e1`](https://github.com/RhetTbull/osxphotos/commit/06138e15d0b87e4865a9ef0cc542303edb44c861)

## [v0.42.87](https://github.com/RhetTbull/osxphotos/compare/v0.42.86...v0.42.87)

> 26 September 2021

## [v0.42.86](https://github.com/RhetTbull/osxphotos/compare/v0.42.85...v0.42.86)

> 26 September 2021

- Fix for #517, #239 [`ac47df8`](https://github.com/RhetTbull/osxphotos/commit/ac47df8475762fe8c8f63ad5ffa83b1e20d116b8)
- Fixed formatting [`6adafb8`](https://github.com/RhetTbull/osxphotos/commit/6adafb8ce70e95a9f0bec1a3db6362742fcd1b0d)
- Updated docs [skip ci] [`725f7c8`](https://github.com/RhetTbull/osxphotos/commit/725f7c87351353efeee8c43c3c7f8a95acb14490)

## [v0.42.85](https://github.com/RhetTbull/osxphotos/compare/v0.42.84...v0.42.85)

> 25 September 2021

- Implemented PhotoInfo.owner, AlbumInfo.owner, #216, #239 [`c4b7c26`](https://github.com/RhetTbull/osxphotos/commit/c4b7c2623f077d9964d5d578ce6c01bb83fab088)
- Updated docs [skip ci] [`59ba325`](https://github.com/RhetTbull/osxphotos/commit/59ba325273b2f16935be944fd46c1237ce637bb8)

## [v0.42.84](https://github.com/RhetTbull/osxphotos/compare/v0.42.83...v0.42.84)

> 25 September 2021

- Fix for #516 [`e3e1da2`](https://github.com/RhetTbull/osxphotos/commit/e3e1da2fd898896595fc851288f905bd4e2150f8)
- Updated docs [skip ci] [`64c226b`](https://github.com/RhetTbull/osxphotos/commit/64c226b85529581e393a2d0604b41c37a8dc2eaf)
- Update docs [`c429a86`](https://github.com/RhetTbull/osxphotos/commit/c429a860b1ebeb77f3c3e36e9660fc9153d85d11)

## [v0.42.83](https://github.com/RhetTbull/osxphotos/compare/v0.42.82...v0.42.83)

> 15 September 2021

- Fixed detected_text to use image orientation if available [`dd08c7f`](https://github.com/RhetTbull/osxphotos/commit/dd08c7f701335a7e1e30fda251e6ad20ff781652)
- Added twine [`16335a6`](https://github.com/RhetTbull/osxphotos/commit/16335a6bd66eaa53fd1c390901e2fb028059d8e1)
- Added wheel [`e0f6d8e`](https://github.com/RhetTbull/osxphotos/commit/e0f6d8ecf27fe772b748c7b2f3108558fbc23e8a)

## [v0.42.82](https://github.com/RhetTbull/osxphotos/compare/v0.42.80...v0.42.82)

> 14 September 2021

- Fix for #515 [`93bf0c2`](https://github.com/RhetTbull/osxphotos/commit/93bf0c210cf01f351611427662025c86955ac373)
- Fix for #515, updated tests [`59c31ff`](https://github.com/RhetTbull/osxphotos/commit/59c31ff88d099b251cf1b571279d7a28a0aac138)
- Updated docs [`773dca8`](https://github.com/RhetTbull/osxphotos/commit/773dca849424c61a7447cb1bb87140708ab0a07c)

## [v0.42.80](https://github.com/RhetTbull/osxphotos/compare/v0.42.79...v0.42.80)

> 29 August 2021

- Bug fix for null title, #512 [`6bcc676`](https://github.com/RhetTbull/osxphotos/commit/6bcc67634ca50e84494539b8a25eb7925dcede62)
- Updated dependencies [`2eb6e70`](https://github.com/RhetTbull/osxphotos/commit/2eb6e70e57ff1dc79907a29618757953f5871145)
- Updated README [skip ci] [`81dd1a7`](https://github.com/RhetTbull/osxphotos/commit/81dd1a753062dacc83aaf4ce8a7667de2cda599b)

## [v0.42.79](https://github.com/RhetTbull/osxphotos/compare/v0.42.78...v0.42.79)

> 29 August 2021

## [v0.42.78](https://github.com/RhetTbull/osxphotos/compare/v0.42.77...v0.42.78)

> 29 August 2021

- docs: add dssinger as a contributor for bug [`#514`](https://github.com/RhetTbull/osxphotos/pull/514)
- Fix for newlines in exif tags, #513 [`f0d7496`](https://github.com/RhetTbull/osxphotos/commit/f0d7496bc66aae291337efc570a2e2c4b9b5529c)

## [v0.42.77](https://github.com/RhetTbull/osxphotos/compare/v0.42.74...v0.42.77)

> 28 August 2021

- Fixed --strip behavior, #511 [`dbb4dbc`](https://github.com/RhetTbull/osxphotos/commit/dbb4dbc0a7f7cb590ab3b2ce532c5c618c7fc249)
- Update test for #506 [`f1cea14`](https://github.com/RhetTbull/osxphotos/commit/f1cea1498b3b973aa500d874126b9668a8743f1f)
- Added {strip} template [`159d110`](https://github.com/RhetTbull/osxphotos/commit/159d1102aabd56def2caf6754747f7a4caa7d374)

## [v0.42.74](https://github.com/RhetTbull/osxphotos/compare/v0.42.73...v0.42.74)

> 23 August 2021

- Fix for #506 [`db5b34d`](https://github.com/RhetTbull/osxphotos/commit/db5b34d58950c65f95d22a0e81390b9d4fb7ccd7)
- Updated README [skip ci] [`fb4138c`](https://github.com/RhetTbull/osxphotos/commit/fb4138cfe6cfad02fead821b70b4b84d11b027e9)

## [v0.42.73](https://github.com/RhetTbull/osxphotos/compare/v0.42.72...v0.42.73)

> 15 August 2021

- Added inspect() to repl, closes #501 [`#501`](https://github.com/RhetTbull/osxphotos/issues/501)
- Updated docs for Text Detection [skip ci] [`c2b2476`](https://github.com/RhetTbull/osxphotos/commit/c2b2476e385fcd3773bd8abb942e788be2af8169)
- Updated README.md [skip ci] [`2041789`](https://github.com/RhetTbull/osxphotos/commit/2041789ff4a3979a73712b27a51a77e8a880efb8)

## [v0.42.72](https://github.com/RhetTbull/osxphotos/compare/v0.42.71...v0.42.72)

> 2 August 2021

- Improved caching of detected_text results [`fa2027d`](https://github.com/RhetTbull/osxphotos/commit/fa2027d45308738d2335d4b5a72c3ef5c478491a)

## [v0.42.71](https://github.com/RhetTbull/osxphotos/compare/v0.42.70...v0.42.71)

> 29 July 2021

- Updated text_detection to detect macOS version [`7376223`](https://github.com/RhetTbull/osxphotos/commit/7376223eb87a4919fd54cc685a3f263e83626879)
- Updated detected_text docs to make it clear this only works on Catalina+ [`ecd0b8e`](https://github.com/RhetTbull/osxphotos/commit/ecd0b8e22f8bf1f8d1e98d64834bebf0394dd903)
- Fix for #500, check for macOS version before loading Vision [`673243c`](https://github.com/RhetTbull/osxphotos/commit/673243c6cd1c267b6b741b5429cdb63c062648d1)

## [v0.42.70](https://github.com/RhetTbull/osxphotos/compare/v0.42.69...v0.42.70)

> 29 July 2021

- Added error logging to {detected_text} processing, #499 [`b1c0fb3`](https://github.com/RhetTbull/osxphotos/commit/b1c0fb3e8284600394ddbfdd7dfa94916a843c81)
- Updated README.md [skip ci] [`1ee3e03`](https://github.com/RhetTbull/osxphotos/commit/1ee3e035c42d687158f7cf73382f0f263516dc37)
- Removed unneeded test file [skip ci] [`607cf80`](https://github.com/RhetTbull/osxphotos/commit/607cf80dda37ad529edd91fe92af3885b04b9a37)

## [v0.42.69](https://github.com/RhetTbull/osxphotos/compare/v0.42.67...v0.42.69)

> 28 July 2021

- Added {detected_text} template [`c233523`](https://github.com/RhetTbull/osxphotos/commit/c2335236be7a1eecf4f25a9dcb844df4d6372b5c)
- Added PhotoInfo.detected_text() [`123340e`](https://github.com/RhetTbull/osxphotos/commit/123340eadabb0fb07209c4207ccad13a53de3619)
- Updated dependencies [`0c8fbd6`](https://github.com/RhetTbull/osxphotos/commit/0c8fbd69af7a0d696de5224bf3c302e0c240905f)

## [v0.42.67](https://github.com/RhetTbull/osxphotos/compare/v0.42.66...v0.42.67)

> 24 July 2021

- Added {album_seq} and {folder_album_seq}, #496 [`12f39db`](https://github.com/RhetTbull/osxphotos/commit/12f39dbaf520ad767e3da667257ce00af60fdd7e)
- Fixed {album_seq} and {folder_album_seq} help text [`077d577`](https://github.com/RhetTbull/osxphotos/commit/077d577c9890c4840a60c3e450dcd4167aa669ea)

## [v0.42.66](https://github.com/RhetTbull/osxphotos/compare/v0.42.65...v0.42.66)

> 23 July 2021

- Updated docs [`666b6ca`](https://github.com/RhetTbull/osxphotos/commit/666b6cac33fb8a2d0fc602609f11e190e11c538f)
- Added {id} sequence number template, #154 [`e95c096`](https://github.com/RhetTbull/osxphotos/commit/e95c0967846106f6da2adaa0b85520df8b351bb0)
- Updated example [skip ci] [`8216c33`](https://github.com/RhetTbull/osxphotos/commit/8216c33b596dba35007168cda4e8de34d9f4b2ea)

## [v0.42.65](https://github.com/RhetTbull/osxphotos/compare/v0.42.64...v0.42.65)

> 20 July 2021

- Fixed album sort order for custom sort, #497 [`e27c40c`](https://github.com/RhetTbull/osxphotos/commit/e27c40c7724dc47a7c95d1a417808c2b1f13adb0)
- Updated test data [`a05e7be`](https://github.com/RhetTbull/osxphotos/commit/a05e7be14e080af0cef80831c3ff7fa0a897a1b2)
- Updated example [skip ci] [`6f4cab6`](https://github.com/RhetTbull/osxphotos/commit/6f4cab6721ca3091031d8010e29d959e3afdecb2)

## [v0.42.64](https://github.com/RhetTbull/osxphotos/compare/v0.42.63...v0.42.64)

> 18 July 2021

- Pass dest_path to template function via RenderOptions, enable implementation of #496 [`2d899ef`](https://github.com/RhetTbull/osxphotos/commit/2d899ef0453c0800ff9b9d374b2b7db0948688fe)

## [v0.42.63](https://github.com/RhetTbull/osxphotos/compare/v0.42.62...v0.42.63)

> 18 July 2021

- Added album_sort_order example [`b04ea81`](https://github.com/RhetTbull/osxphotos/commit/b04ea8174d049d9f3783aac6bbc397ed71584965)
- Updated README.md [skip ci] [`88099de`](https://github.com/RhetTbull/osxphotos/commit/88099de688bcb6a1ddcad6c340833f1627aff268)
- Added RenderOptions to {function} template, #496 [`173a0fc`](https://github.com/RhetTbull/osxphotos/commit/173a0fce28e91177dec114d0dba001adfb76834a)

## [v0.42.62](https://github.com/RhetTbull/osxphotos/compare/v0.42.61...v0.42.62)

> 16 July 2021

- Upgraded osxmetadata to add new extended attributes [`7d81b94`](https://github.com/RhetTbull/osxphotos/commit/7d81b94c16623d11312aaf1b0c47fb580d01bc66)
- Updated tutorial with --regex example [skip ci] [`bf208bb`](https://github.com/RhetTbull/osxphotos/commit/bf208bbe4b965a2d39fc1836335b7b65f402af30)
- Update README.md [`d627cfc`](https://github.com/RhetTbull/osxphotos/commit/d627cfc4fa22497769babc3d686393c6043d1f37)

## [v0.42.61](https://github.com/RhetTbull/osxphotos/compare/v0.42.60...v0.42.61)

> 7 July 2021

- Added --selected, closes #489 [`#489`](https://github.com/RhetTbull/osxphotos/issues/489)

## [v0.42.60](https://github.com/RhetTbull/osxphotos/compare/v0.42.59...v0.42.60)

> 6 July 2021

- docs: add mkirkland4874 as a contributor for example [`#492`](https://github.com/RhetTbull/osxphotos/pull/492)
- Updated README.md [skip ci], closes #488 [`#488`](https://github.com/RhetTbull/osxphotos/issues/488)
- Added example for {function} template [`016297d`](https://github.com/RhetTbull/osxphotos/commit/016297d2ffcf2e8db0d659ccfe7411ecff3dd41b)
- Fixed cleanup to delete empty folders, #491 [`1bf11b0`](https://github.com/RhetTbull/osxphotos/commit/1bf11b0414a7fcf785c792b98f6231821bdad4d4)

## [v0.42.59](https://github.com/RhetTbull/osxphotos/compare/v0.42.58...v0.42.59)

> 4 July 2021

- Re-enabled try/except in cli export [`d497b94`](https://github.com/RhetTbull/osxphotos/commit/d497b94ad506bf6cf044bbabe7fcbf4ab9d5b9e7)
- Added test for try/except block in cli export [`2e32d62`](https://github.com/RhetTbull/osxphotos/commit/2e32d62237f59b16a9be422104347d6a1332865c)

## [v0.42.58](https://github.com/RhetTbull/osxphotos/compare/v0.42.57...v0.42.58)

> 4 July 2021

- Added --preview-if-missing, #446 [`632169f`](https://github.com/RhetTbull/osxphotos/commit/632169f2774558ef8487eb7fb9323aecbadedd88)

## [v0.42.57](https://github.com/RhetTbull/osxphotos/compare/v0.42.54...v0.42.57)

> 4 July 2021

- Refactored export2, #485, #486 [`28c681a`](https://github.com/RhetTbull/osxphotos/commit/28c681aa96874588bc59335b2a0db3b8be6eabaa)
- Added --preview, #470 [`7e2d09b`](https://github.com/RhetTbull/osxphotos/commit/7e2d09bf123428c09a669d8d581e1a35e374273d)
- Fixed path_derivatives to always return jpeg if photo is a photo [`b4dbad5`](https://github.com/RhetTbull/osxphotos/commit/b4dbad5e7451447480699105fb62b157dce8195d)

## [v0.42.54](https://github.com/RhetTbull/osxphotos/compare/v0.42.52...v0.42.54)

> 2 July 2021

- Removed _applescript, #461 [`1d26ac9`](https://github.com/RhetTbull/osxphotos/commit/1d26ac9630dd0a414c01cc4f89a080e4efd7fd97)
- Removed _applescript, #461 [`03b4f59`](https://github.com/RhetTbull/osxphotos/commit/03b4f59549de54da91c36feba613d69f9e86e47b)
- Added get_selected() to REPL [`2e1c91c`](https://github.com/RhetTbull/osxphotos/commit/2e1c91cd672eefe84063933437e5d691f5ad1db1)

## [v0.42.52](https://github.com/RhetTbull/osxphotos/compare/v0.42.51...v0.42.52)

> 2 July 2021

- docs: add jcommisso07 as a contributor for data [`#483`](https://github.com/RhetTbull/osxphotos/pull/483)
- docs: add mkirkland4874 as a contributor for bug [`#482`](https://github.com/RhetTbull/osxphotos/pull/482)
- Fix for path_raw when file is reference, #480 [`4cc3220`](https://github.com/RhetTbull/osxphotos/commit/4cc322028790b3beefce42af5e35c23976b1a35a)
- Updated README.md [skip ci] [`6339e3c`](https://github.com/RhetTbull/osxphotos/commit/6339e3c70ee174394af356710de4bf9442bad9fc)

## [v0.42.51](https://github.com/RhetTbull/osxphotos/compare/v0.42.46...v0.42.51)

> 30 June 2021

- Alpha support for Monterey/macOS 12 [`08147e9`](https://github.com/RhetTbull/osxphotos/commit/08147e91d92013c9cd179187a447f81bc08de3af)
- Refactored UTI utils to get ready for Monterey [`d034605`](https://github.com/RhetTbull/osxphotos/commit/d0346057843aae3a72a79695819df31385db596f)
- Updated photokit code to work with raw+jpeg, #478 [`a73db3a`](https://github.com/RhetTbull/osxphotos/commit/a73db3a1bbc2a320d68dcf7f31f1074bc23a242a)

## [v0.42.46](https://github.com/RhetTbull/osxphotos/compare/v0.42.45...v0.42.46)

> 23 June 2021

- Bug fix for template functions #477 [`4931758`](https://github.com/RhetTbull/osxphotos/commit/49317582c4582e291463d368425513b09a799058)
- Updated README.md [skip ci] [`64fd852`](https://github.com/RhetTbull/osxphotos/commit/64fd85253508b51c3f945f4c8ff02585f1b90aab)
- Fixed deprecation warning [`3fbfc55`](https://github.com/RhetTbull/osxphotos/commit/3fbfc55e84756844070f4080ce415ba77d5c7665)

## [v0.42.45](https://github.com/RhetTbull/osxphotos/compare/v0.42.44...v0.42.45)

> 20 June 2021

- Implemented --query-function, #430 [`07da803`](https://github.com/RhetTbull/osxphotos/commit/07da8031c63487eb42cb3e524f20971e6d2fc929)
- Added query function [skip ci] [`be363b9`](https://github.com/RhetTbull/osxphotos/commit/be363b9727d6fca6e747b0d952cd3252ddfe6e3b)
- Updated README.md [skip ci] [`377e165`](https://github.com/RhetTbull/osxphotos/commit/377e165be48b84c7678ca2f86fc2ffdcbcb93736)

## [v0.42.44](https://github.com/RhetTbull/osxphotos/compare/v0.42.43...v0.42.44)

> 20 June 2021

- Added --location, --no-location, #474 [`870a59a`](https://github.com/RhetTbull/osxphotos/commit/870a59a2fa10766361b384216594af36d3605850)

## [v0.42.43](https://github.com/RhetTbull/osxphotos/compare/v0.42.42...v0.42.43)

> 20 June 2021

- Implemented --post-function, #442 [`987c91a`](https://github.com/RhetTbull/osxphotos/commit/987c91a9ff4b9936d479d7d238a5e5b842265dec)
- Added post_function.py [`233942c`](https://github.com/RhetTbull/osxphotos/commit/233942c9b6836fb6fa9907e9264ec3513322930b)
- Fixed function names to work around Click.runner issue [`821e338`](https://github.com/RhetTbull/osxphotos/commit/821e338b7575c6e053b8d3d958c481dfa62a00bc)

## [v0.42.42](https://github.com/RhetTbull/osxphotos/compare/v0.42.41...v0.42.42)

> 19 June 2021

- Bug fix for --download-missing, #456 [`0cd8f32`](https://github.com/RhetTbull/osxphotos/commit/0cd8f32893046b679ea6280822f4dba5aa7de1fd)
- Updated README.md [skip ci] [`37dc023`](https://github.com/RhetTbull/osxphotos/commit/37dc023fcbfddca8abd2b72119138d72e0bfed53)
- Added isort cfg to match black [`904acbc`](https://github.com/RhetTbull/osxphotos/commit/904acbc576b27d7d05d770e061a6c01a439b8fad)

## [v0.42.41](https://github.com/RhetTbull/osxphotos/compare/v0.42.40...v0.42.41)

> 19 June 2021

- Added repl command to CLI; closes #472 [`#472`](https://github.com/RhetTbull/osxphotos/issues/472)
- Updated README.md [skip ci] [`130df1a`](https://github.com/RhetTbull/osxphotos/commit/130df1a76794f77bc0e8f148185c6407d6b480bc)

## [v0.42.40](https://github.com/RhetTbull/osxphotos/compare/v0.42.39...v0.42.40)

> 19 June 2021

- Added tutorial, closes #432 [`#432`](https://github.com/RhetTbull/osxphotos/issues/432)

## [v0.42.39](https://github.com/RhetTbull/osxphotos/compare/v0.42.38...v0.42.39)

> 18 June 2021

- Updated help text, #469 [`42c551d`](https://github.com/RhetTbull/osxphotos/commit/42c551de8a1e6f682c04b6071c1147eb8039ed3a)

## [v0.42.38](https://github.com/RhetTbull/osxphotos/compare/v0.42.37...v0.42.38)

> 18 June 2021

- Added error handling for --add-to-album [`bc5cd93`](https://github.com/RhetTbull/osxphotos/commit/bc5cd93e974214e2327d604ff92b3c6b6ce62f04)
- Updated README.md [skip ci] [`62d49a7`](https://github.com/RhetTbull/osxphotos/commit/62d49a7138971c43625e55518f069b1b36b787ff)

## [v0.42.37](https://github.com/RhetTbull/osxphotos/compare/v0.42.36...v0.42.37)

> 18 June 2021

- Added additional info to error message for --add-to-album [`64bb07a`](https://github.com/RhetTbull/osxphotos/commit/64bb07a0267f2fdd024a7150fe1788b07218ac2f)

## [v0.42.36](https://github.com/RhetTbull/osxphotos/compare/v0.42.35...v0.42.36)

> 18 June 2021

- Fix for #471 [`8e3f8fc`](https://github.com/RhetTbull/osxphotos/commit/8e3f8fc7d089b644b85e8e52fe220519133d2bea)
- Updated README.md [skip ci] [`f1902b7`](https://github.com/RhetTbull/osxphotos/commit/f1902b7fd4d22c47bcf9fd101b077bbbabb71a9a)

## [v0.42.35](https://github.com/RhetTbull/osxphotos/compare/v0.42.34...v0.42.35)

> 18 June 2021

- Added --post-command, implements #443 [`fa29f51`](https://github.com/RhetTbull/osxphotos/commit/fa29f51aeb89b3f14176693a9d0a5ff8c3565b71)
- Added matrix for GitHub action OS [`ee0b369`](https://github.com/RhetTbull/osxphotos/commit/ee0b3690869e9dbf48e733353540c19d44da51e3)
- Added macos 10.15 and 11 [`2fc45c2`](https://github.com/RhetTbull/osxphotos/commit/2fc45c2468ecf09bb9370f1c2057d63157501839)

## [v0.42.34](https://github.com/RhetTbull/osxphotos/compare/v0.42.31...v0.42.34)

> 14 June 2021

- Refactored PhotoTemplate to support pathlib templates [`2cdec3f`](https://github.com/RhetTbull/osxphotos/commit/2cdec3fc78155a10362e6c65c2ec0e7ebf61ee38)
- Added {filepath} template field in prep for --post-command and other goodies [`c0bd0ff`](https://github.com/RhetTbull/osxphotos/commit/c0bd0ffc9fa3c8aeefd1452cbb9b82511393004f)
- Fixed missing more-itertools, #466 [`1009732`](https://github.com/RhetTbull/osxphotos/commit/10097323e5372939e1af69849dc1d4ddaf3c6667)

## [v0.42.31](https://github.com/RhetTbull/osxphotos/compare/v0.42.30...v0.42.31)

> 12 June 2021

- Cleaned up tests, fixed bug in PhotosDB.query [`0758f84`](https://github.com/RhetTbull/osxphotos/commit/0758f84dc4bae74854c2321bc71c033d71acd4e2)
- Added --duplicate flag to find possible duplicates [`83892e0`](https://github.com/RhetTbull/osxphotos/commit/83892e096a2987a99c2bb2dc08e7bb8ab569a289)
- Updated README.md [skip ci] [`1a46cdf`](https://github.com/RhetTbull/osxphotos/commit/1a46cdf63ce6defbd8cd6cbacc65fa5779102582)

## [v0.42.30](https://github.com/RhetTbull/osxphotos/compare/v0.42.28...v0.42.30)

> 9 June 2021

- Refactored PhotoInfo.export2 [`d7a9ad1`](https://github.com/RhetTbull/osxphotos/commit/d7a9ad1d0a6d1c4327e9d43b7719d860abd34836)
- Updated dependencies to minimize pyobjc requirements [`61943d0`](https://github.com/RhetTbull/osxphotos/commit/61943d051b8e37397eb009c8ae0b0ba86c0ab3a3)
- Fix for --convert-to-jpeg with use_photos_export, #460 [`4b6c35b`](https://github.com/RhetTbull/osxphotos/commit/4b6c35b5f939f18c0147fb034ab619f7c4f9b124)

## [v0.42.28](https://github.com/RhetTbull/osxphotos/compare/v0.42.27...v0.42.28)

> 1 June 2021

- Added PhotoInfo.duplicates [`7accfdb`](https://github.com/RhetTbull/osxphotos/commit/7accfdb06654184e74517033749787ed049d8b7f)
- Added CONTRIBUTING.md [`99f4394`](https://github.com/RhetTbull/osxphotos/commit/99f4394f8e71f636f6e090ecb508672f672205e8)

## [v0.42.27](https://github.com/RhetTbull/osxphotos/compare/v0.42.26...v0.42.27)

> 29 May 2021

- Fix for #455 [`b48133c`](https://github.com/RhetTbull/osxphotos/commit/b48133cd8309ce7e9a6dbab283d484a552135e33)
- Updated README.md [skip ci] [`9161739`](https://github.com/RhetTbull/osxphotos/commit/9161739ee61b0098a6930df34ec5cfd5a9abd722)
- Updated README.rst for PyPI [`71cf8be`](https://github.com/RhetTbull/osxphotos/commit/71cf8be94a4387676135d8f2e108a9de7f7cf4df)

## [v0.42.26](https://github.com/RhetTbull/osxphotos/compare/v0.42.24...v0.42.26)

> 28 May 2021

- docs: add kaduskj as a contributor [`#453`](https://github.com/RhetTbull/osxphotos/pull/453)
- Fixed bug in imageconverter exception handling, closes #440 [`#440`](https://github.com/RhetTbull/osxphotos/issues/440)
- PhotoInfo.exiftool now returns ExifToolCaching, closes #450 [`#450`](https://github.com/RhetTbull/osxphotos/issues/450)
- Fixes for #454 [`2d68594`](https://github.com/RhetTbull/osxphotos/commit/2d68594b7811a60fedf002e712c48b1a0ca87361)
- Updated tested versions to 11.3 [`a298772`](https://github.com/RhetTbull/osxphotos/commit/a2987725151a0e4b6e399ccfeaedceac33afd5c6)
- Updated README.md [skip ci] [`24ccf79`](https://github.com/RhetTbull/osxphotos/commit/24ccf798c2aefd8cafa8645c1bff4c0a5776f0b1)
- Updated README.md [skip ci] [`b026147`](https://github.com/RhetTbull/osxphotos/commit/b026147c9ad4ba01129a243a1d2d60044b0181d3)

## [v0.42.24](https://github.com/RhetTbull/osxphotos/compare/v0.42.23...v0.42.24)

> 23 May 2021

- Bug fix for #452 [`be8fe9d`](https://github.com/RhetTbull/osxphotos/commit/be8fe9d0595c4b4a1a9d15899774b4400b725106)
- Updated README.md [skip ci] [`a724e15`](https://github.com/RhetTbull/osxphotos/commit/a724e15dd63d3acf2224260c431ee6b954892c4e)
- Updated README.md [`a54e051`](https://github.com/RhetTbull/osxphotos/commit/a54e051d41ec3e05df76122de94efd99bbfd09ca)

## [v0.42.23](https://github.com/RhetTbull/osxphotos/compare/v0.42.22...v0.42.23)

> 23 May 2021

- Fixed #451, path_derivatives for Photos version &lt;= 4 [`#451`](https://github.com/RhetTbull/osxphotos/issues/451)
- README.md update [skip ci] [`9603750`](https://github.com/RhetTbull/osxphotos/commit/96037508c130cbdfbba0deb2b4a6cd90d45df037)

## [v0.42.22](https://github.com/RhetTbull/osxphotos/compare/v0.42.20...v0.42.22)

> 19 May 2021

- Cleanup exiftool processes when exiting, #449 [`9f2268f`](https://github.com/RhetTbull/osxphotos/commit/9f2268fb2bc6d8f49167d2ce6eb487fa82dd3b03)
- Added osxphotos related template fields, partial fix for #444 [`df167c0`](https://github.com/RhetTbull/osxphotos/commit/df167c00ebd32e1550559d63de13e1057b2022d2)
- Update README.md [`e8f9cda`](https://github.com/RhetTbull/osxphotos/commit/e8f9cda0c6acd4125d024d068c252aa10420040e)

## [v0.42.20](https://github.com/RhetTbull/osxphotos/compare/v0.42.19...v0.42.20)

> 9 May 2021

- Updated path_derivatives to return results in sorted order (largest to smallest) [`f24e4a7`](https://github.com/RhetTbull/osxphotos/commit/f24e4a7e3c586ff0efb4a5b6593f085cc99c9ce5)

## [v0.42.19](https://github.com/RhetTbull/osxphotos/compare/v0.42.17...v0.42.19)

> 8 May 2021

- Added path_derivatives for Photos 5, issue #50 [`63834ab`](https://github.com/RhetTbull/osxphotos/commit/63834ab8ab82ca42e84b1db49e15ba52b9843d82)
- Updated docs [`78c411a`](https://github.com/RhetTbull/osxphotos/commit/78c411a643b7948b21e0c2011440f3e75b75708c)
- Added path_derivatives for Photos &lt;= 4 [`6bdf15b`](https://github.com/RhetTbull/osxphotos/commit/6bdf15b41eca487102ee4c3f1e51d3b6c068ae1c)

## [v0.42.17](https://github.com/RhetTbull/osxphotos/compare/v0.42.15...v0.42.17)

> 7 May 2021

- Added date_added for Photos 4, #439 [`0e22ce5`](https://github.com/RhetTbull/osxphotos/commit/0e22ce54ab51635617dd546d02fc69c471fa726f)
- Added date_added, #439 [`0f41588`](https://github.com/RhetTbull/osxphotos/commit/0f415887010191bd4a86e7680ba3219f495ab730)
- Updated docs [`b23cfa3`](https://github.com/RhetTbull/osxphotos/commit/b23cfa32bb5ac589f4d243cba925312fa521b305)

## [v0.42.15](https://github.com/RhetTbull/osxphotos/compare/v0.42.14...v0.42.15)

> 2 May 2021

- Added --add-to-album to query [`9a0cc3e`](https://github.com/RhetTbull/osxphotos/commit/9a0cc3e8fa024b485010dbe47791435acf0f7163)
- Updated docs [skip ci] [`c4fec00`](https://github.com/RhetTbull/osxphotos/commit/c4fec00f6711fa1422c39ec61384ba39418085ff)

## [v0.42.14](https://github.com/RhetTbull/osxphotos/compare/v0.42.13...v0.42.14)

> 1 May 2021

- Add --add-exported-to-album, # 428 [`cd8dd55`](https://github.com/RhetTbull/osxphotos/commit/cd8dd552a479905348555f5a17d2ad3a3f25ac69)
- Updated tutorial [`3e06e0e`](https://github.com/RhetTbull/osxphotos/commit/3e06e0e344595fbb084503c8202bc04229e4289b)
- Updated tutorial [`aa9f652`](https://github.com/RhetTbull/osxphotos/commit/aa9f6520d4d3959dfe98b465a082f6d57cc3a70d)

## [v0.42.13](https://github.com/RhetTbull/osxphotos/compare/v0.42.12...v0.42.13)

> 25 April 2021

- Added read-only ExifToolCaching class, to implement #325 [`91804d5`](https://github.com/RhetTbull/osxphotos/commit/91804d53eaafddb7bff83b065014099827bb9d43)
- Added normalized flag to ExifTool.asdict() [`3d26206`](https://github.com/RhetTbull/osxphotos/commit/3d26206d91d51a0a57670212b25afa4786953c02)
- Updated docs [`dc0bbd5`](https://github.com/RhetTbull/osxphotos/commit/dc0bbd5fd689f38d19cae16fce0a6ee11819ca08)

## [v0.42.12](https://github.com/RhetTbull/osxphotos/compare/v0.42.11...v0.42.12)

> 24 April 2021

- Added {edited_version} template field, closes #420 [`#420`](https://github.com/RhetTbull/osxphotos/issues/420)

## [v0.42.11](https://github.com/RhetTbull/osxphotos/compare/v0.42.9...v0.42.11)

> 24 April 2021

- Bump py from 1.8.0 to 1.10.0 [`#434`](https://github.com/RhetTbull/osxphotos/pull/434)
- Fixed handling of burst image selected/key/default, closes #401 (again) [`#401`](https://github.com/RhetTbull/osxphotos/issues/401)
- Added tutorial to README [`f54205f`](https://github.com/RhetTbull/osxphotos/commit/f54205ff49a37bbef4dfca435602a50fbb4ebd02)
- Refactored export_photo to enable work on #420 [`48c229b`](https://github.com/RhetTbull/osxphotos/commit/48c229b52c9a1881832d61434fcf38284ade918c)
- Refactored README.md to improve Template System section [`1d14fc8`](https://github.com/RhetTbull/osxphotos/commit/1d14fc8041ae0a2b7db3b95bb08a5986176de649)
- Updated tutorial [`aad435d`](https://github.com/RhetTbull/osxphotos/commit/aad435da3683834e17cb18b87c2aa7d1306e068e)
- Fixed typo in tutorial [`131105d`](https://github.com/RhetTbull/osxphotos/commit/131105d82cf74bdf2dbf67077fd317d775c5b74e)

## [v0.42.9](https://github.com/RhetTbull/osxphotos/compare/v0.42.8...v0.42.9)

> 20 April 2021

- Added --regex query option, closes #433 [`#433`](https://github.com/RhetTbull/osxphotos/issues/433)

## [v0.42.8](https://github.com/RhetTbull/osxphotos/compare/v0.42.6...v0.42.8)

> 18 April 2021

- Added function filter to template system, closes #429 [`#429`](https://github.com/RhetTbull/osxphotos/issues/429)
- Updated docs [skip ci] [`3f57514`](https://github.com/RhetTbull/osxphotos/commit/3f57514fa37bdaf372f52e02dbf76f1bc2b66b9b)
- Updated docs [`50fa851`](https://github.com/RhetTbull/osxphotos/commit/50fa851f23f5a40f116d520fc70b1f523636b9a3)
- Added template_filter.py to examples [`9371db0`](https://github.com/RhetTbull/osxphotos/commit/9371db094e40c3d64745b705b8b3ebdcbd04267d)
- Fixed docs for function: filter [`1cdf4ad`](https://github.com/RhetTbull/osxphotos/commit/1cdf4addade706b5bf3105441a70fc9d529608a9)
- Version bump [`a483b8a`](https://github.com/RhetTbull/osxphotos/commit/a483b8a900de66b6124e91d53c44260e3c3dfea8)

## [v0.42.6](https://github.com/RhetTbull/osxphotos/compare/v0.42.4...v0.42.6)

> 18 April 2021

- Refactored _query to PhotosDB.query() [`345c052`](https://github.com/RhetTbull/osxphotos/commit/345c052353ee191272f98deda33a04a4d7945f1e)
- Cleaned up queryoptions.py [`81fd51c`](https://github.com/RhetTbull/osxphotos/commit/81fd51c793c93d6bfe781eb21a8b8562b54db1cd)
- Added re to photosdb for use with query_eval [`c8ea0b0`](https://github.com/RhetTbull/osxphotos/commit/c8ea0b0452b22154cc70813014c63c5d1d63c43c)

## [v0.42.4](https://github.com/RhetTbull/osxphotos/compare/v0.42.3...v0.42.4)

> 17 April 2021

- Added --min-size, --max-size query options, #425 [`7ae5b8a`](https://github.com/RhetTbull/osxphotos/commit/7ae5b8aae78621c5b7501f9faa5e0f7f4d815ba1)
- Updated docs, added build.sh [`2e189d7`](https://github.com/RhetTbull/osxphotos/commit/2e189d771edaf18c1ebffd558e3e84e43bff2f08)
- Fixed setup.py [`952f1a6`](https://github.com/RhetTbull/osxphotos/commit/952f1a6c3c3f3c7a55c0a270e73a13c4da6d2375)

## [v0.42.3](https://github.com/RhetTbull/osxphotos/compare/v0.42.2...v0.42.3)

> 17 April 2021

- Updated docs, closes #424 [`#424`](https://github.com/RhetTbull/osxphotos/issues/424)
- Added {newline}, #426 [`7fa7de1`](https://github.com/RhetTbull/osxphotos/commit/7fa7de15631958a973514fe1a9c2cbf4301b6301)

## [v0.42.2](https://github.com/RhetTbull/osxphotos/compare/v0.42.1...v0.42.2)

> 17 April 2021

- Fixed bug for multi-field templates and --xattr-template, #422 [`6a28867`](https://github.com/RhetTbull/osxphotos/commit/6a288676a14ce23380181d43db19128afdda7731)
- Add @ubrandes  as a contributor [`874ad2f`](https://github.com/RhetTbull/osxphotos/commit/874ad2fa34d8306c071cd479625a9aa97f6488b2)

## [v0.42.1](https://github.com/RhetTbull/osxphotos/compare/v0.41.11...v0.42.1)

> 14 April 2021

- Implements conditional expressions for template system, #417 [`03f8b2b`](https://github.com/RhetTbull/osxphotos/commit/03f8b2bc6ed53d3176f9d1ac51c3e4469db3e94b)
- Added {function} template, #419 [`21dc0d3`](https://github.com/RhetTbull/osxphotos/commit/21dc0d388f508c33526ba7510d78c71abd1151a9)
- Added template_function.py to examples [`eff8e7a`](https://github.com/RhetTbull/osxphotos/commit/eff8e7a63ff77e80fff0ce53fe56f5a010f55ab5)

## [v0.41.11](https://github.com/RhetTbull/osxphotos/compare/v0.41.10...v0.41.11)

> 11 April 2021

- Doc updates [`958f8c3`](https://github.com/RhetTbull/osxphotos/commit/958f8c343a93ba60c1182df32727143a750f7b15)
- Added {photo} template, partial fix for issue #417 [`aa1a96d`](https://github.com/RhetTbull/osxphotos/commit/aa1a96d20118916a558b08e7f8ec87c43abf789b)
- Added {favorite} template, partial fix for #289 [`d9f2430`](https://github.com/RhetTbull/osxphotos/commit/d9f24307acc9f3f7cfa01c5e47f161b3aa390a81)

## [v0.41.10](https://github.com/RhetTbull/osxphotos/compare/v0.41.9...v0.41.10)

> 8 April 2021

- Added --query-eval, implements #280 [`b4bc906`](https://github.com/RhetTbull/osxphotos/commit/b4bc906b6a1c3444c5f5a5d9d908ab8c955c8f7e)

## [v0.41.9](https://github.com/RhetTbull/osxphotos/compare/v0.41.8...v0.41.9)

> 5 April 2021

- Bug fix for #414, exiftool str replace [`032dff8`](https://github.com/RhetTbull/osxphotos/commit/032dff89677f049a234d9f498951b8b402d1b31c)

## [v0.41.8](https://github.com/RhetTbull/osxphotos/compare/v0.41.7...v0.41.8)

> 3 April 2021

- Added --name to search filename, closes #249, #412 [`#249`](https://github.com/RhetTbull/osxphotos/issues/249)

## [v0.41.7](https://github.com/RhetTbull/osxphotos/compare/v0.41.6...v0.41.7)

> 2 April 2021

- Bump pygments from 2.6.1 to 2.7.4 [`#408`](https://github.com/RhetTbull/osxphotos/pull/408)
- Removed logging.debug code [`e21a78c`](https://github.com/RhetTbull/osxphotos/commit/e21a78c2b39ee82610394b447a9aa697e489c3e4)
- Added test for #409 [`db27aac`](https://github.com/RhetTbull/osxphotos/commit/db27aac14bbaff0b2db44f8b2d41022ebcad18a7)
- Update phototemplate.py [`d174547`](https://github.com/RhetTbull/osxphotos/commit/d17454772cebbd6edd5d8e0f04e80feecbdb2355)

## [v0.41.6](https://github.com/RhetTbull/osxphotos/compare/v0.41.5...v0.41.6)

> 27 March 2021

- Added --retry, issue #406 [`b330e27`](https://github.com/RhetTbull/osxphotos/commit/b330e27fb838b702cefcbdb588c2fbb924b4cbc4)

## [v0.41.5](https://github.com/RhetTbull/osxphotos/compare/v0.41.4...v0.41.5)

> 27 March 2021

- Bump pyyaml from 5.1.2 to 5.4 [`#402`](https://github.com/RhetTbull/osxphotos/pull/402)
- Fixed albums for burst images, closes #401, #403, #404 [`#401`](https://github.com/RhetTbull/osxphotos/issues/401)

## [v0.41.4](https://github.com/RhetTbull/osxphotos/compare/v0.41.3...v0.41.4)

> 21 March 2021

- Bump pillow from 7.2.0 to 8.1.1 [`#399`](https://github.com/RhetTbull/osxphotos/pull/399)
- Added --from-time, --to-time, closes #400 [`#400`](https://github.com/RhetTbull/osxphotos/issues/400)

## [v0.41.3](https://github.com/RhetTbull/osxphotos/compare/v0.41.2...v0.41.3)

> 14 March 2021

- docs: add AaronVanGeffen as a contributor [`#398`](https://github.com/RhetTbull/osxphotos/pull/398)
- Use original filename to export photos by default [`#396`](https://github.com/RhetTbull/osxphotos/pull/396)
- Updated docs for --cleanup, #394 [`17ac594`](https://github.com/RhetTbull/osxphotos/commit/17ac5949e15057379eb13b979d4d7498bbb94d67)
- Add --cleanup files to report, #395 [`5b95476`](https://github.com/RhetTbull/osxphotos/commit/5b9547669ed6622ae06607e024315e383c0b2d98)

## [v0.41.2](https://github.com/RhetTbull/osxphotos/compare/v0.41.1...v0.41.2)

> 14 March 2021

- Fix for long descriptions with exiftool, #393 [`ffb9af1`](https://github.com/RhetTbull/osxphotos/commit/ffb9af1965668bcfc2422f08b2462964a7dae3e2)

## [v0.41.1](https://github.com/RhetTbull/osxphotos/compare/v0.41.0...v0.41.1)

> 4 March 2021

- Bug fix, convert PosixPath to str, #392 [`595307a`](https://github.com/RhetTbull/osxphotos/commit/595307a003c8ae5d3bee3ad161bb880d884b3cc3)

## [v0.41.0](https://github.com/RhetTbull/osxphotos/compare/v0.40.19...v0.41.0)

> 21 February 2021

- Template refactor [`#385`](https://github.com/RhetTbull/osxphotos/pull/385)

## [v0.40.19](https://github.com/RhetTbull/osxphotos/compare/v0.40.18...v0.40.19)

> 20 February 2021

- Better exception handling for AdjustmentsInfo [`44a1e3e`](https://github.com/RhetTbull/osxphotos/commit/44a1e3e7a7f765bf91c2341e423ec9e5a9e3c1bd)

## [v0.40.18](https://github.com/RhetTbull/osxphotos/compare/v0.40.17...v0.40.18)

> 20 February 2021

- docs: add neilpa as a contributor [`#383`](https://github.com/RhetTbull/osxphotos/pull/383)
- Added AdjustmentsInfo, #150, #379 [`5ee6aff`](https://github.com/RhetTbull/osxphotos/commit/5ee6affc0525db1975cb5095f62494ef10d92f7e)
- docs: update .all-contributorsrc [skip ci] [`ebac9d0`](https://github.com/RhetTbull/osxphotos/commit/ebac9d0bfb43f59f046aacdd0290d1fcd29a3b5e)
- docs: update README.md [skip ci] [`29716c5`](https://github.com/RhetTbull/osxphotos/commit/29716c52726a4e699c03d43ecc67db57f55b36f8)
- Version bump [`fbe8229`](https://github.com/RhetTbull/osxphotos/commit/fbe822910370652975ab83b82344169df4c3027c)

## [v0.40.17](https://github.com/RhetTbull/osxphotos/compare/v0.40.16...v0.40.17)

> 17 February 2021

- Updated docs for --ignore-signature, #286 [`e5f1c29`](https://github.com/RhetTbull/osxphotos/commit/e5f1c299742fcfa0a855a33df7b266aa2c39e48b)
- Added depth_state to _info [`b3a7869`](https://github.com/RhetTbull/osxphotos/commit/b3a7869bd3cc13e40cb3f68ff8caf12edda9a49c)

## [v0.40.16](https://github.com/RhetTbull/osxphotos/compare/v0.40.14...v0.40.16)

> 13 February 2021

- Write description to ITPC:CaptionAbstract (#380) [`4b7a53f`](https://github.com/RhetTbull/osxphotos/commit/4b7a53faa8d7ff2e941e7653554f61bcbd416fc9)
- Removed orientation from XMP, #378 [`70848e1`](https://github.com/RhetTbull/osxphotos/commit/70848e1ff6def928b052271b47c1697c23a8c73f)
- Added image orientation bug to Known Bugs [`1316866`](https://github.com/RhetTbull/osxphotos/commit/1316866dc47486ac61db8903d2d7d006f2598a77)

## [v0.40.14](https://github.com/RhetTbull/osxphotos/compare/v0.40.13...v0.40.14)

> 12 February 2021

- Fix for issue #366, --jpeg-ext, --convert-to-jpeg bug [`3027350`](https://github.com/RhetTbull/osxphotos/commit/30273509d40a270d2610b662ed9238449350064c)
- Added test for #374 [`2691902`](https://github.com/RhetTbull/osxphotos/commit/2691902d5c7a4f4f81e3a9b36fd560ff0a07aec1)

## [v0.40.13](https://github.com/RhetTbull/osxphotos/compare/v0.40.12...v0.40.13)

> 9 February 2021

- Bug fix for --jpeg-ext, #374 [`da47821`](https://github.com/RhetTbull/osxphotos/commit/da47821fae7ee7b2d6d89f5542e729e01d3338df)

## [v0.40.12](https://github.com/RhetTbull/osxphotos/compare/v0.40.11...v0.40.12)

> 8 February 2021

- Fixed --exiftool-option, #369, for real this time [`857e3db`](https://github.com/RhetTbull/osxphotos/commit/857e3db6ccce810d682cd4632ac9bc8448c4f86b)

## [v0.40.11](https://github.com/RhetTbull/osxphotos/compare/v0.40.10...v0.40.11)

> 8 February 2021

- Fixed --exiftool-option, #369 [`198adda`](https://github.com/RhetTbull/osxphotos/commit/198addaa07a86ac5b0fd82787fdffff0a0fc19c6)

## [v0.40.10](https://github.com/RhetTbull/osxphotos/compare/v0.40.9...v0.40.10)

> 7 February 2021

- Fix for issue #366 [`5c3360f`](https://github.com/RhetTbull/osxphotos/commit/5c3360f29d52df2f804c70f37a2ca9a3f102d93c)

## [v0.40.9](https://github.com/RhetTbull/osxphotos/compare/v0.40.8...v0.40.9)

> 7 February 2021

- Fixed unnecessary warning for long keywords, issue #365 [`f8616ac`](https://github.com/RhetTbull/osxphotos/commit/f8616acf167b5e73ab3e4b68dcfbf578230c330d)

## [v0.40.8](https://github.com/RhetTbull/osxphotos/compare/v0.40.7...v0.40.8)

> 4 February 2021

- Implemented --in-album, --not-in-album, issue #364 [`addd952`](https://github.com/RhetTbull/osxphotos/commit/addd952aa315007852945a352b2c7c451ba5f21a)
- Updated docs [`7fa5fba`](https://github.com/RhetTbull/osxphotos/commit/7fa5fbaa5b7c9aa1412eceef56e068dc044c91e0)
- Updated docs Makefile [skip ci] [`683dfe7`](https://github.com/RhetTbull/osxphotos/commit/683dfe7f3ffd235659b58f403562ce2d51123cfb)

## [v0.40.7](https://github.com/RhetTbull/osxphotos/compare/v0.40.6...v0.40.7)

> 2 February 2021

- Bump bleach from 3.1.4 to 3.3.0 [`#362`](https://github.com/RhetTbull/osxphotos/pull/362)
- Fixed XMP template for issue #361 [`43af4d2`](https://github.com/RhetTbull/osxphotos/commit/43af4d205a7264e530bc2b2789d297be633391e1)
- Updated sidecar test data [`591f9bc`](https://github.com/RhetTbull/osxphotos/commit/591f9bcc62720f7eddebba3b3dcff265907550dd)
- Added tests for --only-new, #358 [`adc4b05`](https://github.com/RhetTbull/osxphotos/commit/adc4b056029794faddd464d22022a2a17298a924)
- Updated tests for ExportDB, #358 [`48d2223`](https://github.com/RhetTbull/osxphotos/commit/48d2223edde4850830cc6a3f9776ce08f81a6636)
- Added 11.2 to tested versions, #360 [`2284598`](https://github.com/RhetTbull/osxphotos/commit/2284598a24f63232c01dcf27b9982002123834ca)

## [v0.40.6](https://github.com/RhetTbull/osxphotos/compare/v0.40.5...v0.40.6)

> 2 February 2021

- Add @davidjroos  as a contributor [`8dbedef`](https://github.com/RhetTbull/osxphotos/commit/8dbedef1874882815afb4a885184249aae73bf9f)
- Fixed documentation, #359 [`77371b6`](https://github.com/RhetTbull/osxphotos/commit/77371b6e5d8a9b8662b7b7d540378beb897f6988)

## [v0.40.5](https://github.com/RhetTbull/osxphotos/compare/v0.40.3...v0.40.5)

> 1 February 2021

- Restructured docs [`3a4a8bd`](https://github.com/RhetTbull/osxphotos/commit/3a4a8bdb0bdd995c937e0a15f5d8f1685b73407f)
- Refactored __main__, added sphinx docs [`51f6958`](https://github.com/RhetTbull/osxphotos/commit/51f69585be60d12f912ba08f138b9c1f74481dbd)
- Implemented --only-new, #358 [`5c093c4`](https://github.com/RhetTbull/osxphotos/commit/5c093c43528193ed1704ed4ef1b8d841a95a81cf)

## [v0.40.3](https://github.com/RhetTbull/osxphotos/compare/v0.40.2...v0.40.3)

> 23 January 2021

- Fix for issue #348 [`5a69636`](https://github.com/RhetTbull/osxphotos/commit/5a696366fa37fc6eafebb64fa154eee7624819a7)
- Fixed sidecar test data [`ebe2fc5`](https://github.com/RhetTbull/osxphotos/commit/ebe2fc544d3c89050924da331921dc6f6fa5d79a)
- Version bump [`4e47de7`](https://github.com/RhetTbull/osxphotos/commit/4e47de7589f9df54ea1802275eabf7f9b5d943dd)

## [v0.40.2](https://github.com/RhetTbull/osxphotos/compare/v0.39.25...v0.40.2)

> 22 January 2021

- Added face regions to XMP sidecars [`80f3829`](https://github.com/RhetTbull/osxphotos/commit/80f382906fb7790750ac25061f98cc60293e29e9)
- Fix for issue #353, #354 [`a287bfb`](https://github.com/RhetTbull/osxphotos/commit/a287bfb41f0ee1ab19db39e6f3eb7183093599a9)
- Updated test data [`6d55851`](https://github.com/RhetTbull/osxphotos/commit/6d55851f75cc1818cbbdd0ab356dc9b5cc078b68)

## [v0.39.25](https://github.com/RhetTbull/osxphotos/compare/v0.39.24...v0.39.25)

> 19 January 2021

- face region fixes for mirrored images [`bdc4b23`](https://github.com/RhetTbull/osxphotos/commit/bdc4b23f42f5636834d1246234fa0f88089c71a4)

## [v0.39.24](https://github.com/RhetTbull/osxphotos/compare/v0.39.23...v0.39.24)

> 18 January 2021

- Fixed face regions for exif orientation 6, 8 [`86018d5`](https://github.com/RhetTbull/osxphotos/commit/86018d5cc0d964760fd64047ce52f1f54fc28dc0)
- version bump [`2f86625`](https://github.com/RhetTbull/osxphotos/commit/2f866256adfdf39244241ca6bbcc7a8d072555b9)

## [v0.39.23](https://github.com/RhetTbull/osxphotos/compare/v0.39.22...v0.39.23)

> 18 January 2021

- Fixed face region orientation [`875f79b`](https://github.com/RhetTbull/osxphotos/commit/875f79b92d9510e59fe8ca0aa21a42abc7600f70)
- Updated documentation for new face region properties [`3a110bb`](https://github.com/RhetTbull/osxphotos/commit/3a110bb6d3d23d1c9fd8612b4201144046fed567)

## [v0.39.22](https://github.com/RhetTbull/osxphotos/compare/v0.39.21...v0.39.22)

> 18 January 2021

- Beta fix for Digikam reading XMP [`3799594`](https://github.com/RhetTbull/osxphotos/commit/379959447373f951ffca372598ea8f1d5834fe52)
- Add @martinhrpi  as a contributor [`db43017`](https://github.com/RhetTbull/osxphotos/commit/db430173b59732f944ca52b53c928370684580df)

## [v0.39.21](https://github.com/RhetTbull/osxphotos/compare/v0.39.20...v0.39.21)

> 17 January 2021

- Added beta support for face regions in xmp [`2773ff7`](https://github.com/RhetTbull/osxphotos/commit/2773ff73815ef4667f88a45b016539e490d31769)
- Fixed osxphotos.spec datas [`f58f8dd`](https://github.com/RhetTbull/osxphotos/commit/f58f8dd804f432d07048b98e5dcedca57fec0a5e)

## [v0.39.20](https://github.com/RhetTbull/osxphotos/compare/v0.39.19...v0.39.20)

> 15 January 2021

- Added isreference property and --is-reference, #321 [`651ed50`](https://github.com/RhetTbull/osxphotos/commit/651ed50a076bd3685c7d7a568e53960363d5c30b)
- version bump [`9c18cee`](https://github.com/RhetTbull/osxphotos/commit/9c18cee37e961d2e1059490ad1dbe4e45c501002)

## [v0.39.19](https://github.com/RhetTbull/osxphotos/compare/v0.39.18...v0.39.19)

> 15 January 2021

- Added retry to use_photos_export, issue #351 [`ddce731`](https://github.com/RhetTbull/osxphotos/commit/ddce731a5d354e833d56a64d06cdbc39711f693e)

## [v0.39.18](https://github.com/RhetTbull/osxphotos/compare/v0.39.17...v0.39.18)

> 15 January 2021

- Fixed XMP sidecars to conform with exiftool format, #349, #350 [`1fd0fe5`](https://github.com/RhetTbull/osxphotos/commit/1fd0fe5ea477ccea43c78086af440bd32dc702d8)
- Added update_readme.py to auto-build README [`fd5976b`](https://github.com/RhetTbull/osxphotos/commit/fd5976b75c79a3d205db2e8132c388de95632b77)
- Added modified.strftime template, refactored test_template.py [`088476c`](https://github.com/RhetTbull/osxphotos/commit/088476c59126c6d6fe75551ff122e81aababf818)

## [v0.39.17](https://github.com/RhetTbull/osxphotos/compare/v0.39.16...v0.39.17)

> 12 January 2021

- Fixed test for M1, added about command, closes #315 [`#315`](https://github.com/RhetTbull/osxphotos/issues/315)
- Fixed time zone for tests [`165f9b0`](https://github.com/RhetTbull/osxphotos/commit/165f9b08f5056d1f0b2ca7c74cec84d42b635663)
- Add @narensankar0529 as a contributor [`039118c`](https://github.com/RhetTbull/osxphotos/commit/039118c1aaa217f46354b351ea36b0729e3e1c35)
- Update @narensankar0529 as a contributor [`61f649e`](https://github.com/RhetTbull/osxphotos/commit/61f649e59d53a3e3011602476b72cc64951d38c0)

## [v0.39.16](https://github.com/RhetTbull/osxphotos/compare/v0.39.15...v0.39.16)

> 11 January 2021

- Added version check for M1 macs [`27f779b`](https://github.com/RhetTbull/osxphotos/commit/27f779b16c850cdbda2691e5fae8cd14405653b3)

## [v0.39.15](https://github.com/RhetTbull/osxphotos/compare/v0.39.13...v0.39.15)

> 11 January 2021

- Completed implementation of --jpeg-ext, fixed --dry-run, closes #330, #346 [`#330`](https://github.com/RhetTbull/osxphotos/issues/330)
- Added --jpeg-ext, implements #330 [`55c088e`](https://github.com/RhetTbull/osxphotos/commit/55c088eea2ddecb14e362221da9e2a7c0f403780)

## [v0.39.13](https://github.com/RhetTbull/osxphotos/compare/v0.39.12...v0.39.13)

> 9 January 2021

- Fixed leaky memory in PhotoKit, issue #276 [`db1947d`](https://github.com/RhetTbull/osxphotos/commit/db1947dd1e3d47a487eeb68a5ceb5f7098f1df10)

## [v0.39.12](https://github.com/RhetTbull/osxphotos/compare/v0.39.11...v0.39.12)

> 9 January 2021

- Force cleanup of objects in write_jpeg (fix memory leak) [`#344`](https://github.com/RhetTbull/osxphotos/pull/344)
- doc: Recorded screencast and updated of readme [skip ci] [`#328`](https://github.com/RhetTbull/osxphotos/pull/328)
- Added PhotoInfo.visible, PhotoInfo.date_trashed, closes #333, #334 [`#333`](https://github.com/RhetTbull/osxphotos/issues/333)
- Create terminalizer-demo.yml [`5dc2eea`](https://github.com/RhetTbull/osxphotos/commit/5dc2eeaf9a7265873c81db23bbc86d3023189a26)
- Force cleanup of objects with autorelease pool [`b67f11a`](https://github.com/RhetTbull/osxphotos/commit/b67f11a3bb95c08a39a185b6d884092870e949f2)
- doc: Recorded screencast and updated of readme [`658e8ac`](https://github.com/RhetTbull/osxphotos/commit/658e8ac096d141fce48483dbfc1426bea317d806)
- doc: fixed toc in readme [`aba50c5`](https://github.com/RhetTbull/osxphotos/commit/aba50c5c733420dc30f861d866a2c0bdc8933714)
- Add @Rott-Apple as a contributor [`71cb015`](https://github.com/RhetTbull/osxphotos/commit/71cb01572d2d946df18dd7b36f95b2f2e5b48f86)

## [v0.39.11](https://github.com/RhetTbull/osxphotos/compare/v0.39.10...v0.39.11)

> 8 January 2021

- All contributors/add kradalby [`#343`](https://github.com/RhetTbull/osxphotos/pull/343)
- Ensure keyword list only contains strings, @all-contributors please add @kradalby for code [`#342`](https://github.com/RhetTbull/osxphotos/pull/342)
- Added README.rst, closes #331 [`#331`](https://github.com/RhetTbull/osxphotos/issues/331)
- Ensure merge_exif_keywords are str not int [`123ebb2`](https://github.com/RhetTbull/osxphotos/commit/123ebb2cb752bb94291ac2b77e4a327cee996df1)
- docs: update .all-contributorsrc [skip ci] [`5e676d3`](https://github.com/RhetTbull/osxphotos/commit/5e676d3507c3e2e1f1cd9da7d8843005865c0d4c)
- docs: update README.md [skip ci] [`935865d`](https://github.com/RhetTbull/osxphotos/commit/935865dc6572bc8e80a8eb1ab8f000342ded0a2b)
- Updated tests workflow badge link [`a7678df`](https://github.com/RhetTbull/osxphotos/commit/a7678df3974ff539050f5acb4c94817f525dcd56)
- Ensure keyword list only contains string [`7b6a0af`](https://github.com/RhetTbull/osxphotos/commit/7b6a0af3146202030069ed5823061ee221ab41bc)

## [v0.39.10](https://github.com/RhetTbull/osxphotos/compare/v0.39.9...v0.39.10)

> 6 January 2021

- Refactored ExportResults [`568d1b3`](https://github.com/RhetTbull/osxphotos/commit/568d1b36a631df33317dc00f27126b507c90bf51)
- Improved handling of deleted photos, #332 [`792247b`](https://github.com/RhetTbull/osxphotos/commit/792247b51cc2263221ba8c2e741d2ec454c75ca8)
- Added error_str to ExportResults [`d78097c`](https://github.com/RhetTbull/osxphotos/commit/d78097ccc0686680baf5fffa91f9e082e44b576e)

## [v0.39.9](https://github.com/RhetTbull/osxphotos/compare/v0.39.8...v0.39.9)

> 4 January 2021

- Added test for Big Sur 16.0.1 database changes [`7deac58`](https://github.com/RhetTbull/osxphotos/commit/7deac581b1f1fb3dc59885b6e1ab9a63b382408d)
- Updated all-contributors [`2bf83e4`](https://github.com/RhetTbull/osxphotos/commit/2bf83e4b1fcfadb664ba8988bca4fef7e4c7da12)
- Added additional warning to _photoinfo_export [`fb5fb8e`](https://github.com/RhetTbull/osxphotos/commit/fb5fb8ebc73f96548975432333dfdf01c4794d51)

## [v0.39.8](https://github.com/RhetTbull/osxphotos/compare/v0.39.7...v0.39.8)

> 3 January 2021

- Updated README, version [`b93d682`](https://github.com/RhetTbull/osxphotos/commit/b93d6822ac5366c57d9142cba9b809b4ab99ad98)

## [v0.39.7](https://github.com/RhetTbull/osxphotos/compare/v0.39.6...v0.39.7)

> 3 January 2021

- doc: start with examples before the export reference, thanks to @synox  [`#327`](https://github.com/RhetTbull/osxphotos/pull/327)
- Added tag_groups arg to ExifTool.asdict(), issue #324 [`2480f2a`](https://github.com/RhetTbull/osxphotos/commit/2480f2a325dbb09689f8c417618b7b9e976bfcb9)
- doc: start with examples before the export reference [`7c7bf1b`](https://github.com/RhetTbull/osxphotos/commit/7c7bf1be6b6382a995a4e17906adfd8720d0a1c3)
- Updated dependencies in README.md [`b1cab32`](https://github.com/RhetTbull/osxphotos/commit/b1cab32ff4c7b65ae4c9a5a9a11c175dbd487c0a)
- remove extra spaces [`a59bb5b`](https://github.com/RhetTbull/osxphotos/commit/a59bb5b02f10fa554dae346a7271be37f50d8bcc)
- Adding back  dependency <https://github.com/RhetTbull/PhotoScript>) [`7c8bfc8`](https://github.com/RhetTbull/osxphotos/commit/7c8bfc811ab3a93dabadf1655f7d0e217d6c7b01)

## [v0.39.6](https://github.com/RhetTbull/osxphotos/compare/v0.39.5...v0.39.6)

> 3 January 2021

- Make readme easier for beginners, thanks to @synox  [`#326`](https://github.com/RhetTbull/osxphotos/pull/326)
- doc simplify readme [`02ef0f9`](https://github.com/RhetTbull/osxphotos/commit/02ef0f9a254e83a3729a09cea1ae523407074896)
- Added exception handling/capture for convert-to-jpeg, issue #322 [`05f111a`](https://github.com/RhetTbull/osxphotos/commit/05f111a287e882ed6b451a550a87753501316aba)
- Cleanup up the readme [`38842ff`](https://github.com/RhetTbull/osxphotos/commit/38842ff9249e6f5b3069a88a759c8df97ddce51c)
- Add @synox as a contributor [`83915c6`](https://github.com/RhetTbull/osxphotos/commit/83915c65abb880036f80ebd830eb1e34292f9599)

## [v0.39.5](https://github.com/RhetTbull/osxphotos/compare/v0.39.4...v0.39.5)

> 3 January 2021

## [v0.39.4](https://github.com/RhetTbull/osxphotos/compare/v0.39.3...v0.39.4)

> 3 January 2021

- Implemented text replacement for templates, issue #316 [`478715a`](https://github.com/RhetTbull/osxphotos/commit/478715a363f5009e4a38148e832bf0ad3c4cc4f8)

## [v0.39.3](https://github.com/RhetTbull/osxphotos/compare/v0.39.2...v0.39.3)

> 31 December 2020

- Fixed modified template to use creation time if no modificationd date, issue #312 [`2f57abd`](https://github.com/RhetTbull/osxphotos/commit/2f57abd23cabe57bcf667a1713c37689b330a702)

## [v0.39.2](https://github.com/RhetTbull/osxphotos/compare/v0.39.1...v0.39.2)

> 31 December 2020

- Added --xattr-template, closes #242 [`#242`](https://github.com/RhetTbull/osxphotos/issues/242)

## [v0.39.1](https://github.com/RhetTbull/osxphotos/compare/v0.39.0...v0.39.1)

> 30 December 2020

- Fixed --exiftool-path bug, issue #311, #313 [`3394c52`](https://github.com/RhetTbull/osxphotos/commit/3394c527682d8fdd2f20f4f778d802dab86b6372)

## [v0.39.0](https://github.com/RhetTbull/osxphotos/compare/v0.38.22...v0.39.0)

> 30 December 2020

- Added Finder tags, partial implementation for issue #242  [`#310`](https://github.com/RhetTbull/osxphotos/pull/310)
- Added tests for Finder tags [`29e4245`](https://github.com/RhetTbull/osxphotos/commit/29e424575a522ae03efe5a140be46bfd0a1346c5)
- Initial implementation for Finder tags [`5885b23`](https://github.com/RhetTbull/osxphotos/commit/5885b23d3249cf91953092a6b1ce967da2667e29)
- Updated README for finder tags [`f25a299`](https://github.com/RhetTbull/osxphotos/commit/f25a2993097ad7b2b8ab2d1c787db58c0d799a41)
- Updated requirements.txt [`ea373c4`](https://github.com/RhetTbull/osxphotos/commit/ea373c4197ce1cce00e89157fe560d1366f7e764)

## [v0.38.22](https://github.com/RhetTbull/osxphotos/compare/v0.38.21...v0.38.22)

> 30 December 2020

- Fixed --exiftool-path bug, issue #308 [`5dccdf7`](https://github.com/RhetTbull/osxphotos/commit/5dccdf7750611c78de5356bb02f6023d4fc382c5)

## [v0.38.21](https://github.com/RhetTbull/osxphotos/compare/v0.38.20...v0.38.21)

> 29 December 2020

- Fixed --exiftool-path to work with --exiftool-merge-keywords/persons [`3872e7a`](https://github.com/RhetTbull/osxphotos/commit/3872e7ae649f42d849de472a7dbf78a241d54407)

## [v0.38.20](https://github.com/RhetTbull/osxphotos/compare/v0.38.19...v0.38.20)

> 29 December 2020

- Added --exiftool-path to CLI [`4897fc4`](https://github.com/RhetTbull/osxphotos/commit/4897fc4b05cc7a3bea314f9cce8a2163bf3922b2)

## [v0.38.19](https://github.com/RhetTbull/osxphotos/compare/v0.38.18...v0.38.19)

> 29 December 2020

- Added exiftool signature to JSON output, issue #303 [`fa58af8`](https://github.com/RhetTbull/osxphotos/commit/fa58af8b883da11fdfa723d2da75a600d927d46e)

## [v0.38.18](https://github.com/RhetTbull/osxphotos/compare/v0.38.17...v0.38.18)

> 28 December 2020

- Added --exiftool-merge-keywords/persons, issue #299, #292 [`b1cb99f`](https://github.com/RhetTbull/osxphotos/commit/b1cb99f83f55128a314d265d4588134cb79026c6)

## [v0.38.17](https://github.com/RhetTbull/osxphotos/compare/v0.38.16...v0.38.17)

> 28 December 2020

- Added --sidecar-drop-ext, issue #291 [`dce002c`](https://github.com/RhetTbull/osxphotos/commit/dce002cdfe12fa5fa4ada4d5097828a5375c2ecd)
- Updated Template Substitution table [`7bd189e`](https://github.com/RhetTbull/osxphotos/commit/7bd189e9b22a2ad5a8a80deb7cb93c61be37c771)

## [v0.38.16](https://github.com/RhetTbull/osxphotos/compare/v0.38.15...v0.38.16)

> 28 December 2020

- Added searchinfo templates, issue #302 [`0d086bf`](https://github.com/RhetTbull/osxphotos/commit/0d086bf85102ce78b3111c64bfa88673fbc19559)

## [v0.38.15](https://github.com/RhetTbull/osxphotos/compare/v0.38.14...v0.38.15)

> 28 December 2020

- Added --sidecar exiftool, issue #303 [`d833c14`](https://github.com/RhetTbull/osxphotos/commit/d833c14ef4b3f9375a85034cf0fb0f85a68cabb4)
- Refactored sidecar code [`ade98fc`](https://github.com/RhetTbull/osxphotos/commit/ade98fc15051684bfb54d0199d9c370481b70dcc)
- Refactored export2 to use sidecar bit field [`0d66759`](https://github.com/RhetTbull/osxphotos/commit/0d66759b1c200f1ecda202e28c259f88fd3db599)

## [v0.38.14](https://github.com/RhetTbull/osxphotos/compare/v0.38.13...v0.38.14)

> 27 December 2020

- Bug fix for --description-template, issue #304 [`4cc40d2`](https://github.com/RhetTbull/osxphotos/commit/4cc40d24cfb11ef8668c5d3c3bab40371fdd0436)

## [v0.38.13](https://github.com/RhetTbull/osxphotos/compare/v0.38.12...v0.38.13)

> 27 December 2020

- Set XMP:Subject to match Keywords, issue #302 [`75888cd`](https://github.com/RhetTbull/osxphotos/commit/75888cd6633d3f0180d24fef4f6776986a136f0f)

## [v0.38.12](https://github.com/RhetTbull/osxphotos/compare/v0.38.11...v0.38.12)

> 26 December 2020

- Fixed city/sub-locality for SearchInfo [`f9f699b`](https://github.com/RhetTbull/osxphotos/commit/f9f699ba3500d58494f955d4e5d8118e336e6a2c)

## [v0.38.11](https://github.com/RhetTbull/osxphotos/compare/v0.38.9...v0.38.11)

> 26 December 2020

- Exposed SearchInfo, closes #121 [`#121`](https://github.com/RhetTbull/osxphotos/issues/121)
- Added version to --verbose, closes #297 [`#297`](https://github.com/RhetTbull/osxphotos/issues/297)
- Added --exportdb [`2a49255`](https://github.com/RhetTbull/osxphotos/commit/2a49255277d3c6bd3b0d5f8288afd7de7dab0320)
- Updated README.md [`f469ccc`](https://github.com/RhetTbull/osxphotos/commit/f469cccc4b4561db7611c3e9abf5aefc3ab0f648)
- Fixed help text [`f3b7134`](https://github.com/RhetTbull/osxphotos/commit/f3b7134af1e3d07fb956eaccccd9d60bd075d3bf)

## [v0.38.9](https://github.com/RhetTbull/osxphotos/compare/v0.38.8...v0.38.9)

> 21 December 2020

- Added --exiftool-option to CLI, closes #298 [`#298`](https://github.com/RhetTbull/osxphotos/issues/298)

## [v0.38.8](https://github.com/RhetTbull/osxphotos/compare/v0.38.7...v0.38.8)

> 20 December 2020

- remove duplicate keywords with --exiftool and --sidecar, closes #294 [`#294`](https://github.com/RhetTbull/osxphotos/issues/294)

## [v0.38.7](https://github.com/RhetTbull/osxphotos/compare/v0.38.6...v0.38.7)

> 20 December 2020

- Added better exiftool error handling, closes #300 [`#300`](https://github.com/RhetTbull/osxphotos/issues/300)
- README.md updates for tested versions [`8d1ccda`](https://github.com/RhetTbull/osxphotos/commit/8d1ccda0c897f84342caf612c1070d78bff421f5)
- version bump [`ef94933`](https://github.com/RhetTbull/osxphotos/commit/ef94933dd87b9ad2a516163ca50a36753dacd55a)

## [v0.38.6](https://github.com/RhetTbull/osxphotos/compare/v0.38.5...v0.38.6)

> 17 December 2020

- Documentation fix for #293. Thanks to @finestream  [`#295`](https://github.com/RhetTbull/osxphotos/pull/295)
- Patch 1 [`#1`](https://github.com/RhetTbull/osxphotos/pull/1)
- Added additional test cases for #286, --ignore-signature [`880a9b6`](https://github.com/RhetTbull/osxphotos/commit/880a9b67a14787ef23ae68ad3164d7eda1af16ec)
- Add @finestream as a contributor [`ad860b1`](https://github.com/RhetTbull/osxphotos/commit/ad860b1500dffd846322e05562ba4f2019cd1017)
- Fixed issue #296 [`a7c688c`](https://github.com/RhetTbull/osxphotos/commit/a7c688cfc2221833e0252d71bbe596eee5f9a6e8)
- Updated README.md [`d40b16a`](https://github.com/RhetTbull/osxphotos/commit/d40b16a456c64014674505b7c715c80b977da76a)
- Update __main__.py [`e097f3a`](https://github.com/RhetTbull/osxphotos/commit/e097f3aad546b5be5eabab529bd2c35ce3056876)

## [v0.38.5](https://github.com/RhetTbull/osxphotos/compare/v0.38.4...v0.38.5)

> 16 December 2020

- Implemented --ignore-signature, issue #286 [`e394d8e`](https://github.com/RhetTbull/osxphotos/commit/e394d8e6be7607a1668029bcb37ccb30a4fa792f)

## [v0.38.4](https://github.com/RhetTbull/osxphotos/compare/v0.38.3...v0.38.4)

> 13 December 2020

- Fix for issue #263 [`d5730dd`](https://github.com/RhetTbull/osxphotos/commit/d5730dd8ae92bc819b61ab4df9b10ae64e23569f)

## [v0.38.3](https://github.com/RhetTbull/osxphotos/compare/v0.38.2...v0.38.3)

> 12 December 2020

- Fix for QuickTime date/time, issue #282 [`d8593a0`](https://github.com/RhetTbull/osxphotos/commit/d8593a01e210a0b914d5668ad5f70976fc43b217)

## [v0.38.2](https://github.com/RhetTbull/osxphotos/compare/v0.38.0...v0.38.2)

> 12 December 2020

- Added --save-config, --load-config [`#290`](https://github.com/RhetTbull/osxphotos/pull/290)
- removed extended_attributes reference [`6559c4d`](https://github.com/RhetTbull/osxphotos/commit/6559c4d8f64ad41df925182f9f24f6f67eecd1df)
- This is why I never use branches [`baf45cc`](https://github.com/RhetTbull/osxphotos/commit/baf45ccd2aa24858bb1a8f95ef798121ee80af30)
- Initial implementation of configoptions for --save-config, --load-config [`22355fd`](https://github.com/RhetTbull/osxphotos/commit/22355fd44609f42e412c580dfc9e5e0b7cf6c464)
- Refactoring of save-config/load-config code [`37b1e5c`](https://github.com/RhetTbull/osxphotos/commit/37b1e5ca472e9679301fa96d2b7fdd8c4ad438b2)
- Added tests for configoptions.py [`0262e0d`](https://github.com/RhetTbull/osxphotos/commit/0262e0d97e06ee36786b4491efa178608afb5de5)

## [v0.38.0](https://github.com/RhetTbull/osxphotos/compare/v0.37.7...v0.38.0)

> 10 December 2020

- Refactored FileUtil to use copy-on-write no APFS, issue #287 [`ec4b53e`](https://github.com/RhetTbull/osxphotos/commit/ec4b53ed9dd2bc1e6b71349efdaf0b81c6d797e5)

## [v0.37.7](https://github.com/RhetTbull/osxphotos/compare/v0.37.6...v0.37.7)

> 6 December 2020

- Fix for issue #262 [`11f563a`](https://github.com/RhetTbull/osxphotos/commit/11f563a47926798295e24872bc0efcaaba35906f)

## [v0.37.6](https://github.com/RhetTbull/osxphotos/compare/v0.37.5...v0.37.6)

> 5 December 2020

- Added --cleanup, issue #262 [`e5d6f21`](https://github.com/RhetTbull/osxphotos/commit/e5d6f21d8e85f092fd0cc06ea4a0eaa12834c011)

## [v0.37.5](https://github.com/RhetTbull/osxphotos/compare/v0.37.4...v0.37.5)

> 5 December 2020

- Fix for issue #257, #275 [`1b6a03a`](https://github.com/RhetTbull/osxphotos/commit/1b6a03a9f8c76cb5e50caab6eb138a56ccd841dd)

## [v0.37.4](https://github.com/RhetTbull/osxphotos/compare/v0.37.3...v0.37.4)

> 5 December 2020

- Implement fix for issue #282, QuickTime metadata [`4cce9d4`](https://github.com/RhetTbull/osxphotos/commit/4cce9d4939a00ad2d265a510a2c6f0c8e6a8c655)
- Implement fix for issue #282, QuickTime metadata [`cfb07cb`](https://github.com/RhetTbull/osxphotos/commit/cfb07cbfafaac493f6221be482c432812534ddfa)
- Updated README.md [`1eff6ba`](https://github.com/RhetTbull/osxphotos/commit/1eff6bae9ec19aa626d56d1961e71880c792595a)

## [v0.37.3](https://github.com/RhetTbull/osxphotos/compare/v0.37.2...v0.37.3)

> 29 November 2020

- Removed --use-photokit authorization check, issue 278 [`ed3a971`](https://github.com/RhetTbull/osxphotos/commit/ed3a9711dc0805aed1aacc30e01eeb9c1077d9e1)

## [v0.37.2](https://github.com/RhetTbull/osxphotos/compare/v0.37.1...v0.37.2)

> 29 November 2020

- Catch errors in export_photo [`d9dcf09`](https://github.com/RhetTbull/osxphotos/commit/d9dcf0917a541725d1e472e7f918733e4e2613d0)
- Added --missing to export, see issue #277 [`25eacc7`](https://github.com/RhetTbull/osxphotos/commit/25eacc7caddd6721232b3f77a02532fcd35f7836)

## [v0.37.1](https://github.com/RhetTbull/osxphotos/compare/v0.37.0...v0.37.1)

> 28 November 2020

- Added --report option to CLI, implements #253 [`d22eaf3`](https://github.com/RhetTbull/osxphotos/commit/d22eaf39edc8b0b489b011d6d21345dcedcc8dff)
- Updated template values [`af827d7`](https://github.com/RhetTbull/osxphotos/commit/af827d7a5769f41579d300a7cc511251d86b7eed)

## [v0.37.0](https://github.com/RhetTbull/osxphotos/compare/v0.36.25...v0.37.0)

> 27 November 2020

- Added {exiftool} template, implements issue #259 [`48acb42`](https://github.com/RhetTbull/osxphotos/commit/48acb42631226a71bfc636eea2d3151f1b7165f4)

## [v0.36.25](https://github.com/RhetTbull/osxphotos/compare/v0.36.24...v0.36.25)

> 26 November 2020

- Added --original-suffix for issue #263 [`399d432`](https://github.com/RhetTbull/osxphotos/commit/399d432a66354b9c235f30d10c6985fbde1b7e4f)

## [v0.36.24](https://github.com/RhetTbull/osxphotos/compare/v0.36.23...v0.36.24)

> 26 November 2020

- Initial implementation for issue #265 [`382fca3`](https://github.com/RhetTbull/osxphotos/commit/382fca3f92a3c251c12426dd0dc6d7dc21b691cf)
- More work on issue #265 [`d5a9f76`](https://github.com/RhetTbull/osxphotos/commit/d5a9f767199d25ebd9d5925d05ee39ea7e51ac26)
- Simplified sidecar table in export_db [`0632a97`](https://github.com/RhetTbull/osxphotos/commit/0632a97f55af67c7e5265b0d3283155c7c087e89)

## [v0.36.23](https://github.com/RhetTbull/osxphotos/compare/v0.36.22...v0.36.23)

> 25 November 2020

- Fix for missing original_filename, issue #267 [`fa33218`](https://github.com/RhetTbull/osxphotos/commit/fa332186ab3cdbe1bfd6496ff29b652ef984a5f8)
- version bump [`b5195f9`](https://github.com/RhetTbull/osxphotos/commit/b5195f9d2b81cf6737b65e3cd3793ea9b0da13eb)
- Updated test [`aa2ebf5`](https://github.com/RhetTbull/osxphotos/commit/aa2ebf55bb50eec14f86a532334b376e407f4bbc)

## [v0.36.22](https://github.com/RhetTbull/osxphotos/compare/v0.36.21...v0.36.22)

> 25 November 2020

- Add XML escaping to XMP sidecar export, thanks to @jstrine for the fix! [`#272`](https://github.com/RhetTbull/osxphotos/pull/272)
- Fix EXIF GPS format for XMP sidecar, thanks to @jstrine for the fix! [`#270`](https://github.com/RhetTbull/osxphotos/pull/270)
- Continue even if the original filename is None, thanks to @jstrine for the fix! [`#268`](https://github.com/RhetTbull/osxphotos/pull/268)
- Added test for missing original_filename [`116cb66`](https://github.com/RhetTbull/osxphotos/commit/116cb662fbddf9153f6858c6ea97dc7f65c77705)
- Add @jstrine as a contributor [`7460bc8`](https://github.com/RhetTbull/osxphotos/commit/7460bc88fcc5e1e7435c9b9bcdf7ec9c7c5e39ea)
- Escape characters which cause XML parsing issues [`c42050a`](https://github.com/RhetTbull/osxphotos/commit/c42050a10cac40b0b5ac70c587e07f257a9b50dd)
- Fix tests for apostrophe [`d0d2e80`](https://github.com/RhetTbull/osxphotos/commit/d0d2e8080096bf66f93a830386800ce713680c51)
- Fix test for XMP sidecar with GPS info [`c27cfb1`](https://github.com/RhetTbull/osxphotos/commit/c27cfb1223fa82b9e5549b93c283e9444693270a)

## [v0.36.21](https://github.com/RhetTbull/osxphotos/compare/v0.36.20...v0.36.21)

> 25 November 2020

- Exposed --use-photos-export and --use-photokit [`e951e53`](https://github.com/RhetTbull/osxphotos/commit/e951e5361e59060229787bb1ea3fc4e088ffff99)

## [v0.36.20](https://github.com/RhetTbull/osxphotos/compare/v0.36.19...v0.36.20)

> 23 November 2020

- Added photokit export as hidden --use-photokit option [`26f96d5`](https://github.com/RhetTbull/osxphotos/commit/26f96d582c01ce9816b1f54f0e74c8570f133f7c)

## [v0.36.19](https://github.com/RhetTbull/osxphotos/compare/v0.36.18...v0.36.19)

> 18 November 2020

- Removed debug statement in _photoinfo_export [`8cb15d1`](https://github.com/RhetTbull/osxphotos/commit/8cb15d15551094dcaf1b0ef32d6ac0273be7fd37)

## [v0.36.18](https://github.com/RhetTbull/osxphotos/compare/v0.36.17...v0.36.18)

> 14 November 2020

- Moved AppleScript to photoscript [`3c85f26`](https://github.com/RhetTbull/osxphotos/commit/3c85f26f901645ce297685ccd639792757fbc995)
- Fixed missing data file for photoscript [`2d9429c`](https://github.com/RhetTbull/osxphotos/commit/2d9429c8eefabe6233fc580f65511c48ee6c01e5)
- Version bump, updated requirements [`3b6dd08`](https://github.com/RhetTbull/osxphotos/commit/3b6dd08d2bb2b20a55064bf24fe7ce788e7268ef)

## [v0.36.17](https://github.com/RhetTbull/osxphotos/compare/v0.36.15...v0.36.17)

> 12 November 2020

- Fixed path for photos actually missing off disk [`5d4d7d7`](https://github.com/RhetTbull/osxphotos/commit/5d4d7d7db7ca1109b6230803fe777d7a30882efe)
- Fixed erroneous attempt to export edited with --download-missing [`8dc59cb`](https://github.com/RhetTbull/osxphotos/commit/8dc59cbc35c33e71d0d912f4139e855180ac4fbd)
- version bump [`802e2f0`](https://github.com/RhetTbull/osxphotos/commit/802e2f069a5f8b37ddc6b3b8ba07519ce10f88a7)

## [v0.36.15](https://github.com/RhetTbull/osxphotos/compare/v0.36.14...v0.36.15)

> 11 November 2020

- Avoid copying db files if not necessary [`ea9b41b`](https://github.com/RhetTbull/osxphotos/commit/ea9b41bae41a05aad53454f67871c5e6c9a49f79)

## [v0.36.14](https://github.com/RhetTbull/osxphotos/compare/v0.36.13...v0.36.14)

> 8 November 2020

- Fix for issue #247 [`38397b5`](https://github.com/RhetTbull/osxphotos/commit/38397b507b456169cf3be2d2dc6743ec8653feb3)

## [v0.36.13](https://github.com/RhetTbull/osxphotos/compare/v0.36.11...v0.36.13)

> 8 November 2020

- Refactored phototemplate.py to add PATH_SEP option [`3636fcb`](https://github.com/RhetTbull/osxphotos/commit/3636fcbc76100d9898a59f24ed6e9b1965cc6022)
- More work on phototemplate.py to add inline expansion [`a6231e2`](https://github.com/RhetTbull/osxphotos/commit/a6231e29ff28b2c7dc3239445f41afcb35926a7a)

## [v0.36.11](https://github.com/RhetTbull/osxphotos/compare/v0.36.10...v0.36.11)

> 7 November 2020

- Implemented boolean type template fields [`7fa3704`](https://github.com/RhetTbull/osxphotos/commit/7fa3704840f7800689b4ac5f8edee8210eb3e8db)
- Bug fix in handling missing edited photos [`e829212`](https://github.com/RhetTbull/osxphotos/commit/e829212987bbc1a88f845922abcffef70c159883)
- Fixed message in CLI [`df37a01`](https://github.com/RhetTbull/osxphotos/commit/df37a017a8efdc8d0b9bc8d00a4452dc4cb892b3)

## [v0.36.10](https://github.com/RhetTbull/osxphotos/compare/v0.36.9...v0.36.10)

> 7 November 2020

- Implemented issue #255 [`ae2fd2e`](https://github.com/RhetTbull/osxphotos/commit/ae2fd2e3db984756e6cc3f7b3338b8ba819ce28c)

## [v0.36.9](https://github.com/RhetTbull/osxphotos/compare/v0.36.8...v0.36.9)

> 7 November 2020

- Refactored regex in phototemplate [`653b7e6`](https://github.com/RhetTbull/osxphotos/commit/653b7e6600e0738ecd00f74d510a893e0d447ca4)
- Fix for exporting slow mo videos, issue #252 [`9d38885`](https://github.com/RhetTbull/osxphotos/commit/9d38885416b528bd8c91bb09120be85a8b109f29)

## [v0.36.8](https://github.com/RhetTbull/osxphotos/compare/v0.36.7...v0.36.8)

> 4 November 2020

- Refactored exiftool.py [`2202f1b`](https://github.com/RhetTbull/osxphotos/commit/2202f1b1e9c4f83558ef48e58cb94af6b3a38cdd)
- README.md update [`a509ef1`](https://github.com/RhetTbull/osxphotos/commit/a509ef18d3db2ac15a661e763a7254974cf8d84a)

## [v0.36.7](https://github.com/RhetTbull/osxphotos/compare/v0.36.6...v0.36.7)

> 3 November 2020

- Implemented context manager for ExifTool, closes #250 [`#250`](https://github.com/RhetTbull/osxphotos/issues/250)

## [v0.36.6](https://github.com/RhetTbull/osxphotos/compare/v0.36.5...v0.36.6)

> 2 November 2020

- Fix for issue #39 [`c7c5320`](https://github.com/RhetTbull/osxphotos/commit/c7c5320587e31070b55cc8c7e74f30b0f9e61379)

## [v0.36.5](https://github.com/RhetTbull/osxphotos/compare/v0.36.4...v0.36.5)

> 1 November 2020

- Added --ignore-date-modified flag, issue #247 [`663e33b`](https://github.com/RhetTbull/osxphotos/commit/663e33bc1709f767e1a08242f6bfe86a3fc78552)

## [v0.36.4](https://github.com/RhetTbull/osxphotos/compare/v0.36.2...v0.36.4)

> 31 October 2020

- Updated --exiftool to set dates/times as Photos does, issue #247 [`11459d1`](https://github.com/RhetTbull/osxphotos/commit/11459d1da4d7d13e36e9db4bdc940b74baad9d11)
- Partial fix for issue #247 on Mojave [`6ac3111`](https://github.com/RhetTbull/osxphotos/commit/6ac311199e9f7afe6170cbbd68ceaa1bb9f0682b)
- Add @mwort as a contributor [`9cff8e8`](https://github.com/RhetTbull/osxphotos/commit/9cff8e89c6e939d3d371a4f60649f6e5595a55b9)

## [v0.36.2](https://github.com/RhetTbull/osxphotos/compare/v0.36.1...v0.36.2)

> 31 October 2020

- Fixed handling of date_modified for Catalina, issue #247 [`0cce234`](https://github.com/RhetTbull/osxphotos/commit/0cce234a8cbba63dc1cba439c06fe9de078ff480)

## [v0.36.1](https://github.com/RhetTbull/osxphotos/compare/v0.36.0...v0.36.1)

> 29 October 2020

- Added --has-comment/--has-likes to CLI, issue #240 [`c5dba8c`](https://github.com/RhetTbull/osxphotos/commit/c5dba8c89bba35d7a77e087b180b2a3d7b94280a)
- Cleaned up as_dict/asdict, issue #144, #188 [`603dabb`](https://github.com/RhetTbull/osxphotos/commit/603dabb8f420a89e993d5aadcd3a5614bbb262dd)
- Updated README.md [`d16932d`](https://github.com/RhetTbull/osxphotos/commit/d16932d0fd8d160ccf44e9842329d5933dc25b36)

## [v0.36.0](https://github.com/RhetTbull/osxphotos/compare/v0.35.7...v0.36.0)

> 25 October 2020

- Added verbose to PhotosDB(), partial fix for #110 [`d87b8f3`](https://github.com/RhetTbull/osxphotos/commit/d87b8f30a45cbb6fdb315a12f8585e2bdc21be6b)
- Added comments/likes, implements #214 [`23de6b5`](https://github.com/RhetTbull/osxphotos/commit/23de6b58908371d9ca55d1d1999c6d56de454180)
- Cleaned up constructor for PhotosDB [`667c89e`](https://github.com/RhetTbull/osxphotos/commit/667c89e32c3f96baeafebc03e83517ea05693b00)

## [v0.35.7](https://github.com/RhetTbull/osxphotos/compare/v0.35.6...v0.35.7)

> 24 October 2020

- Fix for issue #238 [`48f29e1`](https://github.com/RhetTbull/osxphotos/commit/48f29e138e4e9da3eba78f3681ee9b8cb28910df)

## [v0.35.6](https://github.com/RhetTbull/osxphotos/compare/v0.35.5...v0.35.6)

> 24 October 2020

- Fixed shared, not_shared in cli [`8551981`](https://github.com/RhetTbull/osxphotos/commit/8551981f68f0cd2a3a081cc21ae287ff981b9b4b)

## [v0.35.5](https://github.com/RhetTbull/osxphotos/compare/v0.35.4...v0.35.5)

> 21 October 2020

- Added get_shared_photo_comments.py to examples [`15e0914`](https://github.com/RhetTbull/osxphotos/commit/15e0914af6301a945bc751173aef6718487d9637)
- Fix for issue #237 [`a416de2`](https://github.com/RhetTbull/osxphotos/commit/a416de29e4ac39a5c323f7913b05a8c38ad205be)
- Added test for issue #235 [`ea68229`](https://github.com/RhetTbull/osxphotos/commit/ea68229ddac2e2301ac2d5607451cf7d00207d5d)

## [v0.35.4](https://github.com/RhetTbull/osxphotos/compare/v0.35.3...v0.35.4)

> 17 October 2020

- refactored template code to fix #213 [`#213`](https://github.com/RhetTbull/osxphotos/issues/213)

## [v0.35.3](https://github.com/RhetTbull/osxphotos/compare/v0.35.2...v0.35.3)

> 15 October 2020

- Fix for issue #235, #236 [`41b2399`](https://github.com/RhetTbull/osxphotos/commit/41b23991df3d1d553b70889ede237f83b6874519)

## [v0.35.2](https://github.com/RhetTbull/osxphotos/compare/v0.35.1...v0.35.2)

> 12 October 2020

- Fix for issue #234 [`da100f9`](https://github.com/RhetTbull/osxphotos/commit/da100f93a9b849ca4750336d7f90e9023e39dd07)

## [v0.35.1](https://github.com/RhetTbull/osxphotos/compare/v0.35.0...v0.35.1)

> 11 October 2020

- Fix for issue #230 [`dcbf8f2`](https://github.com/RhetTbull/osxphotos/commit/dcbf8f25f61e21bcf1040046aa9d6ddba4ac9735)

## [v0.35.0](https://github.com/RhetTbull/osxphotos/compare/v0.34.5...v0.35.0)

> 11 October 2020

- Convert to jpeg [`#233`](https://github.com/RhetTbull/osxphotos/pull/233)
- Updated tests, closes #231 [`#231`](https://github.com/RhetTbull/osxphotos/issues/231)
- --convert-to-jpeg initial version working [`38f201d`](https://github.com/RhetTbull/osxphotos/commit/38f201d0fb70bf299a828c1dd0d034a119e380c4)
- Added tests, fixed bug in export_db [`5a13605`](https://github.com/RhetTbull/osxphotos/commit/5a13605f850bb947c8888246f06a5ca4e6aa5f10)
- Updated tests [`b2b39aa`](https://github.com/RhetTbull/osxphotos/commit/b2b39aa6075df11861cf5d8945b657204f120e87)
- Fixed path_edited for Big Sur [`c389207`](https://github.com/RhetTbull/osxphotos/commit/c389207daa4fec555fbf9d2aee8347997f9a8412)
- Added HEIC test image [`ddc1e69`](https://github.com/RhetTbull/osxphotos/commit/ddc1e69b4a4ac712e1af312b865c4216f9ad350c)

## [v0.34.5](https://github.com/RhetTbull/osxphotos/compare/v0.34.3...v0.34.5)

> 6 October 2020

- Fix for issue #230 [`42a6373`](https://github.com/RhetTbull/osxphotos/commit/42a6373f8ded6800ff3e8ff970123c49868402c0)
- version bump [`9515736`](https://github.com/RhetTbull/osxphotos/commit/95157360193e9bb4fae54fe30a43ace3090481ab)

## [v0.34.3](https://github.com/RhetTbull/osxphotos/compare/v0.34.2...v0.34.3)

> 28 September 2020

- Update exiftool.py to preserve file modification time, thanks to @hhoeck  [`#223`](https://github.com/RhetTbull/osxphotos/pull/223)
- Added tests for 10.15.6 [`432da7f`](https://github.com/RhetTbull/osxphotos/commit/432da7f139a5e4b37eeb358f4ede45314407f8e5)
- Fixed bug related to issue #222 [`c939df7`](https://github.com/RhetTbull/osxphotos/commit/c939df717159e8b97955c0b267327cd56a9ed56c)
- Version bump for bug fix [`62d54cc`](https://github.com/RhetTbull/osxphotos/commit/62d54cc0beabd0141545608184d4b2c658eedf0f)
- Update README.md [`6883fec`](https://github.com/RhetTbull/osxphotos/commit/6883fec2b2236d892b88327e1b4e9da1237f7dea)
- Update exiftool.py [`3d21dad`](https://github.com/RhetTbull/osxphotos/commit/3d21dadf4102e9101e48a0c6f739a544f7f9d9de)

## [v0.34.2](https://github.com/RhetTbull/osxphotos/compare/v0.34.1...v0.34.2)

> 13 September 2020

- Partial fix for issue #213 [`459d91d`](https://github.com/RhetTbull/osxphotos/commit/459d91d7b11dbd4b0564906c1689b60dc5b64642)

## [v0.34.1](https://github.com/RhetTbull/osxphotos/compare/v0.34.0...v0.34.1)

> 13 September 2020

- Fixed exception handling in export [`eb00ffd`](https://github.com/RhetTbull/osxphotos/commit/eb00ffd73737ef4832229e4e6fd8dc4ccb0b8539)
- Updated README.md [`a1776fa`](https://github.com/RhetTbull/osxphotos/commit/a1776fa14850275ad6b02ece80bbe8ce908fa836)

## [v0.34.0](https://github.com/RhetTbull/osxphotos/compare/v0.33.8...v0.34.0)

> 7 September 2020

- Added --skip-original-if-edited for issue #159 [`5f2d401`](https://github.com/RhetTbull/osxphotos/commit/5f2d401048850fd68f31b37a7e71abc11ca80dc5)
- Still working on issue #208 [`58b3869`](https://github.com/RhetTbull/osxphotos/commit/58b3869a7cce7cb3f211599e544d7e5426ceb4a6)

## [v0.33.8](https://github.com/RhetTbull/osxphotos/compare/v0.33.7...v0.33.8)

> 31 August 2020

- Fixed sidecar collisions, closes #210 [`#210`](https://github.com/RhetTbull/osxphotos/issues/210)

## [v0.33.7](https://github.com/RhetTbull/osxphotos/compare/v0.33.5...v0.33.7)

> 31 August 2020

- typo fix - thanks to @dmd  [`#212`](https://github.com/RhetTbull/osxphotos/pull/212)
- Normalize unicode for issue #208 [`a36eb41`](https://github.com/RhetTbull/osxphotos/commit/a36eb416b19284477922b6a5f837f4040327138b)
- Added force_download.py to examples [`b611d34`](https://github.com/RhetTbull/osxphotos/commit/b611d34d19db480af72f57ef55eacd0a32c8d1e8)
- Added photoshop:SidecarForExtension to XMP, partial fix for #210 [`60d96a8`](https://github.com/RhetTbull/osxphotos/commit/60d96a8f563882fba2365a6ab58c1276725eedaa)
- Updated README.md [`c9b1518`](https://github.com/RhetTbull/osxphotos/commit/c9b15186a022d91248451279e5f973e3f2dca4b4)
- Update README.md [`42e8fba`](https://github.com/RhetTbull/osxphotos/commit/42e8fba125a3c6b1bd0d538f2af511aabfbeb478)

## [v0.33.5](https://github.com/RhetTbull/osxphotos/compare/v0.33.3...v0.33.5)

> 25 August 2020

- Fixed DST handling for from_date/to_date, closes #193 (again) [`#193`](https://github.com/RhetTbull/osxphotos/issues/193)
- Added raw timestamps to PhotoInfo._info [`0f457a4`](https://github.com/RhetTbull/osxphotos/commit/0f457a4082a4eebc42a5df2160a02ad987b6f96c)

## [v0.33.3](https://github.com/RhetTbull/osxphotos/compare/v0.33.2...v0.33.3)

> 23 August 2020

- Fixed portrait for Catalina/Big Sur; see issue #203 [`1f717b0`](https://github.com/RhetTbull/osxphotos/commit/1f717b05794c2088c7c15d2aab0c5d24b6309c06)

## [v0.33.2](https://github.com/RhetTbull/osxphotos/compare/v0.33.0...v0.33.2)

> 23 August 2020

- Closes issue #206, adds --touch-file [`#207`](https://github.com/RhetTbull/osxphotos/pull/207)
- Touch files - fixes #194 -- thanks to @PabloKohan  [`#205`](https://github.com/RhetTbull/osxphotos/pull/205)
- Refactor/cleanup _export_photo - thanks to @PabloKohan  [`#204`](https://github.com/RhetTbull/osxphotos/pull/204)
- Finished --touch-file, closes #206 [`#206`](https://github.com/RhetTbull/osxphotos/issues/206)
- Merge pull request #205 from PabloKohan/touch_files__fix_194 [`#194`](https://github.com/RhetTbull/osxphotos/issues/194)
- --touch-file now working with --update [`6c11e3f`](https://github.com/RhetTbull/osxphotos/commit/6c11e3fa5b5b05b98b9fdbb0e59e3a78c7dff980)
- Refactor/cleanup _export_photo [`eefa1f1`](https://github.com/RhetTbull/osxphotos/commit/eefa1f181f4fd7b027ae69abd2b764afb590c081)
- Fixed touch tests [`1bf7105`](https://github.com/RhetTbull/osxphotos/commit/1bf7105737fbd756064a2f9ef4d4bbd0b067978c)
- Working on issue 206 [`ebd878a`](https://github.com/RhetTbull/osxphotos/commit/ebd878a075983ef3df0b1ead1a725e01508721f8)
- Working on issue #206 [`c9c9202`](https://github.com/RhetTbull/osxphotos/commit/c9c920220545dc27c8cb1379d7bde15987cce72c)

## [v0.33.0](https://github.com/RhetTbull/osxphotos/compare/v0.32.0...v0.33.0)

> 16 August 2020

- Replaced call to which, closes #171 [`#171`](https://github.com/RhetTbull/osxphotos/issues/171)
- Added contributors to README.md, closes #200 [`#200`](https://github.com/RhetTbull/osxphotos/issues/200)
- Added tests for 10.15.6 [`d2deeff`](https://github.com/RhetTbull/osxphotos/commit/d2deefff834e46e1a26adc01b1b025ac839dbc78)
- Added ImportInfo for Photos 5+ [`98e4170`](https://github.com/RhetTbull/osxphotos/commit/98e417023ec5bd8292b25040d0844f3706645950)
- Update README.md [`360c8d8`](https://github.com/RhetTbull/osxphotos/commit/360c8d8e1b4760e95a8b71b3a0bf0df4fb5adaf5)
- Update README.md [`868cda8`](https://github.com/RhetTbull/osxphotos/commit/868cda8482ce6b29dd00e04a209d40550e6b128b)

## [v0.32.0](https://github.com/RhetTbull/osxphotos/compare/v0.31.2...v0.32.0)

> 9 August 2020

- Alpha support for MacOS Big Sur/10.16, see issue #187 [`6acf9ac`](https://github.com/RhetTbull/osxphotos/commit/6acf9acd6364e1996158179493d128ec0958e652)

## [v0.31.2](https://github.com/RhetTbull/osxphotos/compare/v0.31.0...v0.31.2)

> 8 August 2020

- Fixed from_date and to_date to be timezone aware, closes #193 [`#193`](https://github.com/RhetTbull/osxphotos/issues/193)
- Added test for valid XMP file, closes #197 [`#197`](https://github.com/RhetTbull/osxphotos/issues/197)
- Dropped py36 due to datetime.fromisoformat [`a714ae0`](https://github.com/RhetTbull/osxphotos/commit/a714ae0af089b13acf70c4f29934393aa48ed222)
- Added --uuid-from-file to CLI [`840e993`](https://github.com/RhetTbull/osxphotos/commit/840e9937bede407ef55972a361618683245e086b)
- Added write_uuid_to_file.applescript to utils [`bea770b`](https://github.com/RhetTbull/osxphotos/commit/bea770b322d21cf3f8245d20e182006247cb71d6)
- Updated README.md [`002fce8`](https://github.com/RhetTbull/osxphotos/commit/002fce8e93edd936d4b866118ae6d4c94e5d6744)
- Added py37 [`d0ec862`](https://github.com/RhetTbull/osxphotos/commit/d0ec8620c721fe7576ab7d519a5eaac4d17a317e)

## [v0.31.0](https://github.com/RhetTbull/osxphotos/compare/v0.30.13...v0.31.0)

> 27 July 2020

- Initial FaceInfo support for Issue #21 [`6f29cda`](https://github.com/RhetTbull/osxphotos/commit/6f29cda99f1b8d94a95597c7046620cf21fecae4)
- Updated Github Actions to run on PR [`9fc4f76`](https://github.com/RhetTbull/osxphotos/commit/9fc4f762193699dd45b586b51aa2d3066928aab1)

## [v0.30.13](https://github.com/RhetTbull/osxphotos/compare/v0.30.12...v0.30.13)

> 23 July 2020

- Fix findfiles not to fail on missing/invalid dir [`#192`](https://github.com/RhetTbull/osxphotos/pull/192)
- Revert "Fix FileExistsError when filename differs only in case and export-as-hardlink (Bug#133)" [`#191`](https://github.com/RhetTbull/osxphotos/pull/191)
- Fix FileExistsError when filename differs only in case and export-as-hardlink (Bug#133) [`#190`](https://github.com/RhetTbull/osxphotos/pull/190)
- Revert "Merge pull request #191 from RhetTbull/revert-190-Fix133" [`27040d1`](https://github.com/RhetTbull/osxphotos/commit/27040d16046dc95483f39ca983d2133461e80d5e)
- Fix FileExistsError when filename differs only in case and export-as-hardlink [`d52b387`](https://github.com/RhetTbull/osxphotos/commit/d52b387a294e68ebf0580a202ea70b97205560ef)
- Version bump for bug fix [`cf4dca1`](https://github.com/RhetTbull/osxphotos/commit/cf4dca10c02d5f3f6132ab1572a698379b667e48)

## [v0.30.12](https://github.com/RhetTbull/osxphotos/compare/v0.30.10...v0.30.12)

> 18 July 2020

- Implemented PersonInfo, closes #181 [`#181`](https://github.com/RhetTbull/osxphotos/issues/181)
- Updated dependencies, now supports py36, py37, py38 [`6688d1f`](https://github.com/RhetTbull/osxphotos/commit/6688d1ff6491f2e7e155946b265ef8b5d8929441)
- Update README.md [`3526881`](https://github.com/RhetTbull/osxphotos/commit/3526881ec872cc009b0d8936f366afcfff166d42)

## [v0.30.10](https://github.com/RhetTbull/osxphotos/compare/v0.30.9...v0.30.10)

> 6 July 2020

- Bug fix for empty albums [`1ef518c`](https://github.com/RhetTbull/osxphotos/commit/1ef518cc3e9efbe9d4c16aa3d36c6dc6db86798e)

## [v0.30.9](https://github.com/RhetTbull/osxphotos/compare/v0.30.7...v0.30.9)

> 6 July 2020

- Refactored person processing to enable implementation of #181 [`fcff8ec`](https://github.com/RhetTbull/osxphotos/commit/fcff8ec5f8286b28e7d8559b40b5808a7b59cc15)
- AlbumInfo.photos now returns photos in album sort order [`9d820a0`](https://github.com/RhetTbull/osxphotos/commit/9d820a0557944340d0c664a6c3497d138c6100d5)

## [v0.30.7](https://github.com/RhetTbull/osxphotos/compare/v0.30.6...v0.30.7)

> 4 July 2020

- Bug fix for keywords, persons in deleted photos [`df75a05`](https://github.com/RhetTbull/osxphotos/commit/df75a05645a88b31daa411f960d99ade71efc908)

## [v0.30.6](https://github.com/RhetTbull/osxphotos/compare/v0.30.5...v0.30.6)

> 3 July 2020

- Added height, width, orientation, filesize to json, str) [`8c3af0a`](https://github.com/RhetTbull/osxphotos/commit/8c3af0a4e4e49d9bbb33e809973d958334e44dca)

## [v0.30.5](https://github.com/RhetTbull/osxphotos/compare/v0.30.4...v0.30.5)

> 3 July 2020

- Added height, width, orientation, filesize, closes #163 [`#163`](https://github.com/RhetTbull/osxphotos/issues/163)

## [v0.30.4](https://github.com/RhetTbull/osxphotos/compare/v0.30.3...v0.30.4)

> 3 July 2020

- Added GPS location to XMP sidecar, closes #175 [`#175`](https://github.com/RhetTbull/osxphotos/issues/175)
- Updated README.md [`7806e05`](https://github.com/RhetTbull/osxphotos/commit/7806e05673775ded231e65f53f3a1d5095a4b4e1)

## [v0.30.3](https://github.com/RhetTbull/osxphotos/compare/v0.30.2...v0.30.3)

> 28 June 2020

- Added --description-template to CLI, closes #166 [`#166`](https://github.com/RhetTbull/osxphotos/issues/166)
- Added expand_inplace to PhotoTemplate.render [`ff03287`](https://github.com/RhetTbull/osxphotos/commit/ff0328785f3ea14b1c8ae2b7d1a9b07e8aef0777)
- Updated README.md [`5950707`](https://github.com/RhetTbull/osxphotos/commit/59507077bafe39a17bc23babe6d6c52e1f502a53)

## [v0.30.2](https://github.com/RhetTbull/osxphotos/compare/v0.30.1...v0.30.2)

> 28 June 2020

- Added --deleted, --deleted-only to CLI, closes #179 [`#179`](https://github.com/RhetTbull/osxphotos/issues/179)

## [v0.30.1](https://github.com/RhetTbull/osxphotos/compare/v0.30.0...v0.30.1)

> 27 June 2020

- Changed default to PhotosDB.photos(movies=True), closes #177 [`#177`](https://github.com/RhetTbull/osxphotos/issues/177)

## [v0.30.0](https://github.com/RhetTbull/osxphotos/compare/v0.29.30...v0.30.0)

> 27 June 2020

- added intrash support for issue #179 [`185483e`](https://github.com/RhetTbull/osxphotos/commit/185483e1aa9ed107402bfb178f264417e6926b46)
- Removed pdf filter on process_database_4 [`c1d1204`](https://github.com/RhetTbull/osxphotos/commit/c1d12047bde84740b96c8531110e7b2d2fe41f2e)

## [v0.29.30](https://github.com/RhetTbull/osxphotos/compare/v0.29.29...v0.29.30)

> 23 June 2020

- Added test for issue #178 [`46c87ee`](https://github.com/RhetTbull/osxphotos/commit/46c87eeed56d5765317dec4992d2e16323c711ad)
- Additional fix for issue #178 [`fd4c990`](https://github.com/RhetTbull/osxphotos/commit/fd4c99032dbbedd6325aabacb0bc800b24ede413)

## [v0.29.29](https://github.com/RhetTbull/osxphotos/compare/v0.29.28...v0.29.29)

> 23 June 2020

- version bump [`d6fee89`](https://github.com/RhetTbull/osxphotos/commit/d6fee89fd9dd07c4788562ed551d0a3f2b5d697d)
- Bug fix for issue #178 [`b8618cf`](https://github.com/RhetTbull/osxphotos/commit/b8618cf272efc174b7fa872f233b561bd9e7243e)

## [v0.29.28](https://github.com/RhetTbull/osxphotos/compare/v0.29.26...v0.29.28)

> 22 June 2020

- Closes #174 [`#174`](https://github.com/RhetTbull/osxphotos/issues/174)
- Added today to template system, closes #167 [`#167`](https://github.com/RhetTbull/osxphotos/issues/167)
- Minor refactoring in photoinfo.py [`a8e996e`](https://github.com/RhetTbull/osxphotos/commit/a8e996e66072e94de93fd4ea78a456bc61831f52)

## [v0.29.26](https://github.com/RhetTbull/osxphotos/compare/v0.29.25...v0.29.26)

> 21 June 2020

- Bug fix for issue #172 [`1ebf995`](https://github.com/RhetTbull/osxphotos/commit/1ebf99583397617f0d3a234c898beae1c14f5a63)

## [v0.29.25](https://github.com/RhetTbull/osxphotos/compare/v0.29.24...v0.29.25)

> 21 June 2020

- More PhotoInfo.albums refactoring, closes #169 [`#169`](https://github.com/RhetTbull/osxphotos/issues/169)

## [v0.29.24](https://github.com/RhetTbull/osxphotos/compare/v0.29.23...v0.29.24)

> 20 June 2020

- Refactored album code in photosdb to fix issue #169 [`cfabd0d`](https://github.com/RhetTbull/osxphotos/commit/cfabd0dbead62c8ab6a774899239e5da5bfe1203)

## [v0.29.23](https://github.com/RhetTbull/osxphotos/compare/v0.29.22...v0.29.23)

> 20 June 2020

- Fixed PhotoInfo.albums, album_info for issue #169 [`1212fad`](https://github.com/RhetTbull/osxphotos/commit/1212fad4adde0b4c6b2887392eed829d8d96d61d)

## [v0.29.22](https://github.com/RhetTbull/osxphotos/compare/v0.29.19...v0.29.22)

> 18 June 2020

- Don't raise KeyError when SystemLibraryPath is absent [`#168`](https://github.com/RhetTbull/osxphotos/pull/168)
- Added check for export db in directory branch, closes #164 [`#164`](https://github.com/RhetTbull/osxphotos/issues/164)
- Added OSXPhotosDB.get_db_connection() [`43d28e7`](https://github.com/RhetTbull/osxphotos/commit/43d28e78f394fa33f8d88f64b56b7dc7258cd454)
- Added show() to photos_repl.py [`e98c3fe`](https://github.com/RhetTbull/osxphotos/commit/e98c3fe42912ac16d13675bf14154981089d41ea)
- Fixed get_last_library_path and get_system_library_path to not raise KeyError [`5a83218`](https://github.com/RhetTbull/osxphotos/commit/5a832181f73e082927c80864f2063e554906b06b)

## [v0.29.19](https://github.com/RhetTbull/osxphotos/compare/v0.29.18...v0.29.19)

> 14 June 2020

- Added computed aesthetic scores, closes #141, closes #122 [`#141`](https://github.com/RhetTbull/osxphotos/issues/141) [`#122`](https://github.com/RhetTbull/osxphotos/issues/122)

## [v0.29.18](https://github.com/RhetTbull/osxphotos/compare/v0.29.17...v0.29.18)

> 13 June 2020

- Added --label to CLI, closes #157 [`#157`](https://github.com/RhetTbull/osxphotos/issues/157)

## [v0.29.17](https://github.com/RhetTbull/osxphotos/compare/v0.29.16...v0.29.17)

> 13 June 2020

- Extende --ignore-case to --person, --keyword, --album, closes #162 [`#162`](https://github.com/RhetTbull/osxphotos/issues/162)
- Updated README.md to document template system [`0004250`](https://github.com/RhetTbull/osxphotos/commit/0004250e74eacc19f7986742712225116530a67e)

## [v0.29.16](https://github.com/RhetTbull/osxphotos/compare/v0.29.14...v0.29.16)

> 13 June 2020

- Added hour, min, sec, strftime templates, closes #158 [`#158`](https://github.com/RhetTbull/osxphotos/issues/158)
- Added hour, min, sec to template system, issue #158 [`5387f8e`](https://github.com/RhetTbull/osxphotos/commit/5387f8e2f970ff7fa1967ccad87b45a4f7e50d32)

## [v0.29.14](https://github.com/RhetTbull/osxphotos/compare/v0.29.13...v0.29.14)

> 13 June 2020

- Updated DatetimeFormatter to include hour/min/sec [`cf2615d`](https://github.com/RhetTbull/osxphotos/commit/cf2615da62801f1fbde61c7905431963e121e2e9)
- Added test for issue #156 [`4ba1982`](https://github.com/RhetTbull/osxphotos/commit/4ba1982d745f0d532ead090177051d928465ed03)
- Bug fix for issue #136 [`06fa1ed`](https://github.com/RhetTbull/osxphotos/commit/06fa1edcae7139b543e17ec63810c37c18cc2780)

## [v0.29.13](https://github.com/RhetTbull/osxphotos/compare/v0.29.12...v0.29.13)

> 7 June 2020

- Added hidden debug-dump command to CLI [`7cd7b51`](https://github.com/RhetTbull/osxphotos/commit/7cd7b5159845fce15d50a7bfc0ac50d122bee527)

## [v0.29.12](https://github.com/RhetTbull/osxphotos/compare/v0.29.9...v0.29.12)

> 7 June 2020

- Refactoring with sourceryAI [`5c7a0c3`](https://github.com/RhetTbull/osxphotos/commit/5c7a0c3a246cd5fec329b4fd4979d2b77352f916)
- Partial fix for #155 [`2271d89`](https://github.com/RhetTbull/osxphotos/commit/2271d8935507ecc27e6227b11b4796f2f4d2f10d)
- Partial fix for #155 [`62d096b`](https://github.com/RhetTbull/osxphotos/commit/62d096b5a1a7e960195ec5c48fc9cffbebf2c735)

## [v0.29.9](https://github.com/RhetTbull/osxphotos/compare/v0.29.8...v0.29.9)

> 31 May 2020

- Added --filename to CLI, closes #89 [`#89`](https://github.com/RhetTbull/osxphotos/issues/89)

## [v0.29.8](https://github.com/RhetTbull/osxphotos/compare/v0.29.5...v0.29.8)

> 30 May 2020

- Added --edited-suffix to CLI, closes #145 [`#145`](https://github.com/RhetTbull/osxphotos/issues/145)
- refactored render_template, closes #149 [`#149`](https://github.com/RhetTbull/osxphotos/issues/149)
- Added test for Photos 5 on 10.15.5 [`2243395`](https://github.com/RhetTbull/osxphotos/commit/2243395bff9e1cc379626cc5007e44e6e63b95e0)
- Refactored template code out of PhotoInfo into PhotoTemplate [`16f802b`](https://github.com/RhetTbull/osxphotos/commit/16f802bf717610e13712b8aa477d05d94b14d294)
- Added test for SearchInfo on 10.15.5 [`3a8bef1`](https://github.com/RhetTbull/osxphotos/commit/3a8bef1572e4d83b1e0a4b85c8f06e329cc7e8de)
- performance improvements for update and export_db [`42b89d3`](https://github.com/RhetTbull/osxphotos/commit/42b89d34f3d14818daefbd3bfabc1be9344d2e1a)
- More refactoring in PhotoTemplate [`f35ea70`](https://github.com/RhetTbull/osxphotos/commit/f35ea70b72e8c6743b1f6009466d2a15d40338ac)

## [v0.29.5](https://github.com/RhetTbull/osxphotos/compare/v0.29.2...v0.29.5)

> 25 May 2020

- added created.dow (day of week) to template [`#147`](https://github.com/RhetTbull/osxphotos/pull/147)
- Added --dry-run option to CLI export, closes #91 [`#91`](https://github.com/RhetTbull/osxphotos/issues/91)
- added created.dd and modified.dd to template system, closes #135 [`#135`](https://github.com/RhetTbull/osxphotos/issues/135)
- Catch exception in folder processing to address #148 [`46fdc94`](https://github.com/RhetTbull/osxphotos/commit/46fdc94398c80b157048649434c7312074ce5c58)
- Added test for DateTimeFormatter.dow [`09c7d18`](https://github.com/RhetTbull/osxphotos/commit/09c7d18901b61669d8b9242babd82eba6987c89a)

## [v0.29.2](https://github.com/RhetTbull/osxphotos/compare/v0.29.1...v0.29.2)

> 23 May 2020

- Added try/except for bad datettime values [`1d095d7`](https://github.com/RhetTbull/osxphotos/commit/1d095d7284bae57037b8b200c8b3422835c611b2)

## [v0.29.1](https://github.com/RhetTbull/osxphotos/compare/v0.29.0...v0.29.1)

> 23 May 2020

- Catch illegal timestamp value [`#146`](https://github.com/RhetTbull/osxphotos/pull/146)

## [v0.29.0](https://github.com/RhetTbull/osxphotos/compare/v0.28.19...v0.29.0)

> 23 May 2020

- Made --exiftool and --export-as-hardlink incompatible in CLI to fix #132 [`#132`](https://github.com/RhetTbull/osxphotos/issues/132)
- Added --update to CLI export; reference issue #100 [`b1171e9`](https://github.com/RhetTbull/osxphotos/commit/b1171e96cc06362555725995bb311317eb163e49)
- Added as_dict to PlaceInfo [`8c4fe40`](https://github.com/RhetTbull/osxphotos/commit/8c4fe40aa6850f166e526cffaa088550884399af)
- Updated README.md [`11d368a`](https://github.com/RhetTbull/osxphotos/commit/11d368a69cbe67e909e64b020f0334fc09dd3ac4)
- version bump [`c06c230`](https://github.com/RhetTbull/osxphotos/commit/c06c230a469754691d11fff1034fb02daeeba649)
- Test library update [`f416418`](https://github.com/RhetTbull/osxphotos/commit/f416418546a12bc6c1bda13f6b712758584d06dc)

## [v0.28.19](https://github.com/RhetTbull/osxphotos/compare/v0.28.18...v0.28.19)

> 15 May 2020

- Added label and label_normalized to template system, closes #130 [`#130`](https://github.com/RhetTbull/osxphotos/issues/130)
- Revert "test library updates" [`48e9c32`](https://github.com/RhetTbull/osxphotos/commit/48e9c32add549e66c3ef8c65f8821f5033b55b11)
- test library updates [`d125854`](https://github.com/RhetTbull/osxphotos/commit/d125854f2a04e37747af3e0796370a565c1c9bd0)
- version bump [`bd9d5a2`](https://github.com/RhetTbull/osxphotos/commit/bd9d5a26f3bfcbb33896a139fa86cdab46768103)
- Update README.md [`85760dc`](https://github.com/RhetTbull/osxphotos/commit/85760dc4fe2274d826ed80494fd4e66866398609)
- Update README.md [`be07f90`](https://github.com/RhetTbull/osxphotos/commit/be07f90e5a8179e452730ea654e4c9627b1f6ebc)

## [v0.28.18](https://github.com/RhetTbull/osxphotos/compare/v0.28.17...v0.28.18)

> 14 May 2020

- Implemented PhotoInfo.exiftool [`a80dee4`](https://github.com/RhetTbull/osxphotos/commit/a80dee401c7eb959f6ad6d93a3272657ed28f521)

## [v0.28.17](https://github.com/RhetTbull/osxphotos/compare/v0.28.15...v0.28.17)

> 13 May 2020

- Added ExifInfo (Photos 5 only) [`53304d7`](https://github.com/RhetTbull/osxphotos/commit/53304d702317d007056c1d12064503c3ec4ae6f6)
- Added as_dict to ExifTool [`d1af14d`](https://github.com/RhetTbull/osxphotos/commit/d1af14dbb4d441a62d352123774e51fa3538db97)

## [v0.28.15](https://github.com/RhetTbull/osxphotos/compare/v0.28.13...v0.28.15)

> 10 May 2020

- fixed some minor findings... [`#127`](https://github.com/RhetTbull/osxphotos/pull/127)
- added --export-as-hardlink option [`#126`](https://github.com/RhetTbull/osxphotos/pull/126)
- Added test for folder_names on 10.15.4, closes #119 [`#119`](https://github.com/RhetTbull/osxphotos/issues/119)
- Refactored photosdb and photoinfo to add SearchInfo and labels [`98b3f63`](https://github.com/RhetTbull/osxphotos/commit/98b3f63a92aa2105f8fa97af992fc6fe2d78b973)
- Added additional test for --export-as-hardlink [`57315d4`](https://github.com/RhetTbull/osxphotos/commit/57315d44497fde977956f76f667470208f11aa2d)
- Updated a couple of tests to use pytest-mock [`397db0d`](https://github.com/RhetTbull/osxphotos/commit/397db0d72fb218669a9ecbff134fa9b392a14661)
- added test for export using hardlinks, fixed a test that failed if users locale settings were different to en_US [`b0ec6c6`](https://github.com/RhetTbull/osxphotos/commit/b0ec6c6b36d8cfe05723d47b210d9d7c5aabdfe5)
- Added link to original work by @simonw [`ca8f2b8`](https://github.com/RhetTbull/osxphotos/commit/ca8f2b8d5c55b5a554fd1337b1070c97ec381916)

## [v0.28.13](https://github.com/RhetTbull/osxphotos/compare/v0.28.10...v0.28.13)

> 1 May 2020

- added --keyword-template [`65674f5`](https://github.com/RhetTbull/osxphotos/commit/65674f57bc174c078e6c47f12ba3aaba87bfa3a4)
- Fixed bug related to issue #119 [`7af1ccd`](https://github.com/RhetTbull/osxphotos/commit/7af1ccd4ed22ea7f0f86973bfba7f108b6650291)
- test library updates [`1b6f661`](https://github.com/RhetTbull/osxphotos/commit/1b6f661e6b59c003d3b8cb35226ffb51469be508)

## [v0.28.10](https://github.com/RhetTbull/osxphotos/compare/v0.28.8...v0.28.10)

> 28 April 2020

- Bug fix for albums in Photos &lt;= 4 to address issue #116 [`a57da23`](https://github.com/RhetTbull/osxphotos/commit/a57da2346b282d731ed41db600bfc5cbeb1a0992)
- version bump for pypi [`3fe03cd`](https://github.com/RhetTbull/osxphotos/commit/3fe03cd12752c2a7769007b6d934f1efe9f9c4d2)

## [v0.28.8](https://github.com/RhetTbull/osxphotos/compare/v0.28.7...v0.28.8)

> 28 April 2020

- Fixed implementation of use_albums_as_keywords and use_persons_as_keywords, closes #115 [`#115`](https://github.com/RhetTbull/osxphotos/issues/115)
- Update README.md [`5cc98c3`](https://github.com/RhetTbull/osxphotos/commit/5cc98c338bcc19fd05bf293eb3afe24c07c8b380)
- Updated README.md [`a800711`](https://github.com/RhetTbull/osxphotos/commit/a80071111f810a1d7d6e2d735839e85499091ea4)
- Update README.md [`1c9d4f2`](https://github.com/RhetTbull/osxphotos/commit/1c9d4f282beea2ac12273c8d0f9453bad1255c2c)

## [v0.28.7](https://github.com/RhetTbull/osxphotos/compare/v0.28.6...v0.28.7)

> 27 April 2020

- Added --album-keyword and --person-keyword to CLI, closes #61 [`#61`](https://github.com/RhetTbull/osxphotos/issues/61)
- Updated test libraries [`54d5d4b`](https://github.com/RhetTbull/osxphotos/commit/54d5d4b7ba99204f58e723231309ab6e306be28c)
- Updated tests/README.md [`56a0006`](https://github.com/RhetTbull/osxphotos/commit/56a000609f2f08d0f8800fec49cada2980c3bb9d)

## [v0.28.6](https://github.com/RhetTbull/osxphotos/compare/v0.28.5...v0.28.6)

> 26 April 2020

- Fixed locale bug in templates, closes #113 [`#113`](https://github.com/RhetTbull/osxphotos/issues/113)
- Updated test to avoid issue with GitHub workflow [`9be0f84`](https://github.com/RhetTbull/osxphotos/commit/9be0f849b73061d053d30274ff3295b79c88f0b6)
- Update pythonpackage.yml to remove older pythons [`ccb5f25`](https://github.com/RhetTbull/osxphotos/commit/ccb5f252d14e9335ae04a2e338a6d527b80c9a93)

## [v0.28.5](https://github.com/RhetTbull/osxphotos/compare/0.28.2...v0.28.5)

> 20 April 2020

- added __len__ to PhotosDB, closes #44 [`#44`](https://github.com/RhetTbull/osxphotos/issues/44)
- Updated use of _PHOTOS_4_VERSION, closes #106 [`#106`](https://github.com/RhetTbull/osxphotos/issues/106)
- Updated tests and test library with RAW images [`9b9b54e`](https://github.com/RhetTbull/osxphotos/commit/9b9b54e590e43ae49fb3ae41d493a1f8faec4181)
- Updated setup.py to resolve issue with bpylist2 on python &lt; 3.8 [`8e4b88a`](https://github.com/RhetTbull/osxphotos/commit/8e4b88ad1fc18438f941e045bfc8aeac878914f9)
- Added cli.py for use with pyinstaller [`cf28cb6`](https://github.com/RhetTbull/osxphotos/commit/cf28cb6452de17f2ef8d80435386e8d5a1aabd34)
- added raw_is_original handling [`a337e79`](https://github.com/RhetTbull/osxphotos/commit/a337e79e13802b4824c2f088ce9db1c027d6f3c5)
- Updated setup.py and README with install instructions [`85d2baa`](https://github.com/RhetTbull/osxphotos/commit/85d2baac104fbd0db5cccc0888a55805a2385b9a)

## [0.28.2](https://github.com/RhetTbull/osxphotos/compare/v0.28.1...0.28.2)

> 18 April 2020

- Added folder support for Photos &lt;= 4, closes #93 [`#93`](https://github.com/RhetTbull/osxphotos/issues/93)
- cleaned up SQL statements in _process_database4 [`6f28171`](https://github.com/RhetTbull/osxphotos/commit/6f281711e2001a63ffad076d7b9835272d5d09da)
- Fixed suffix check on export to be case insensitive [`4b30b3b`](https://github.com/RhetTbull/osxphotos/commit/4b30b3b4260e2c7409e18825e5b626efe646db16)
- test library update [`3bac106`](https://github.com/RhetTbull/osxphotos/commit/3bac106eb7a180e9e39643a89087d92bf2a437d0)

## [v0.28.1](https://github.com/RhetTbull/osxphotos/compare/v0.27.4...v0.28.1)

> 17 April 2020

- Initial work on suppport for associated RAW images [`7e42ebb`](https://github.com/RhetTbull/osxphotos/commit/7e42ebb2402d45cd5d20bdd55bddddaa9db4679f)
- Initial support for RAW photos in Photos 4 to address issue #101 [`9d15147`](https://github.com/RhetTbull/osxphotos/commit/9d151478d610291b8d482aafae3d445dfd391fca)
- replaced CLI option --original-name with --current-name [`36c2821`](https://github.com/RhetTbull/osxphotos/commit/36c2821a0fa62eaaa54cf1edc2d9c6da98155354)

## [v0.27.4](https://github.com/RhetTbull/osxphotos/compare/v0.27.3...v0.27.4)

> 12 April 2020

- Added {folder_album} to template and --folder to CLI [`b7c7b9f`](https://github.com/RhetTbull/osxphotos/commit/b7c7b9f0664e69c743bdd8a228ad2936cf6b7600)
- Test library update [`21e7020`](https://github.com/RhetTbull/osxphotos/commit/21e7020fec406b0f3926d7adc8a1451bfe77e75a)

## [v0.27.3](https://github.com/RhetTbull/osxphotos/compare/v0.27.1...v0.27.3)

> 12 April 2020

- Added additional tests for album_info [`97362fc`](https://github.com/RhetTbull/osxphotos/commit/97362fc0f13b2867abc013f4ba97ae60b0700894)
- Fixed bug with handling of deleted albums [`9fef12e`](https://github.com/RhetTbull/osxphotos/commit/9fef12ed37634a7bdb11232976b4b2ddccd1a7cb)

## [v0.27.1](https://github.com/RhetTbull/osxphotos/compare/v0.27.0...v0.27.1)

> 12 April 2020

- Changed AlbumInfo and FolderInfo interface to maintain backwards compatibility with PhotosDB.albums [`e09f0b4`](https://github.com/RhetTbull/osxphotos/commit/e09f0b40f1671d70ee399cdc519492b04fac8adc)

## [v0.27.0](https://github.com/RhetTbull/osxphotos/compare/v0.26.1...v0.27.0)

> 11 April 2020

- Update README.md [`#95`](https://github.com/RhetTbull/osxphotos/pull/95)
- Added tests and README for AlbumInfo and FolderInfo [`d6a22b7`](https://github.com/RhetTbull/osxphotos/commit/d6a22b765ab17f6ef1ba8c50b77946f090979968)
- Added albuminfo.py for AlbumInfo and FolderInfo classes [`9636572`](https://github.com/RhetTbull/osxphotos/commit/96365728c2ff42abfb6828872ffac53b4c3c8024)
- Update README.md TOC [`8544667`](https://github.com/RhetTbull/osxphotos/commit/8544667c729ea0d7fe39671d909e09cda519e250)

## [v0.26.1](https://github.com/RhetTbull/osxphotos/compare/v0.26.0...v0.26.1)

> 10 April 2020

- Bug fix for PhotosDB.photos() query [`1c9da5e`](https://github.com/RhetTbull/osxphotos/commit/1c9da5ed6ffa21f0577906b65b7da08951725d1f)
- Updated test library [`d74f7f4`](https://github.com/RhetTbull/osxphotos/commit/d74f7f499bf59f37ec81cfa9d49cbbf3aafb5961)

## [v0.26.0](https://github.com/RhetTbull/osxphotos/compare/v0.25.1...v0.26.0)

> 10 April 2020

- Added test for 10.15.4 [`1820715`](https://github.com/RhetTbull/osxphotos/commit/182071584904d001a9b199eef5febfb79e00696e)
- Changed PhotosDB albums interface as prep for adding folders [`3e50626`](https://github.com/RhetTbull/osxphotos/commit/3e5062684ab6d706d91d4abeb4e3b0ca47867b70)
- Update README.md [`626e460`](https://github.com/RhetTbull/osxphotos/commit/626e460aabb97b30af87cea2ec4f93e5fb925bec)

## [v0.25.1](https://github.com/RhetTbull/osxphotos/compare/v0.25.0...v0.25.1)

> 5 April 2020

- Added --no-extended-attributes option to CLI, closes #85 [`#85`](https://github.com/RhetTbull/osxphotos/issues/85)
- Fixed CLI help for invalid topic, closes #76 [`#76`](https://github.com/RhetTbull/osxphotos/issues/76)
- Updated test library [`bae0283`](https://github.com/RhetTbull/osxphotos/commit/bae0283441f04d71aa78dbd1cf014f376ef1f91a)

## [v0.25.0](https://github.com/RhetTbull/osxphotos/compare/v0.24.2...v0.25.0)

> 4 April 2020

- Added places, --place, --no-place to CLI, closes #87, #88 [`#87`](https://github.com/RhetTbull/osxphotos/issues/87)
- Updated render_filepath_template to support multiple values [`6a89888`](https://github.com/RhetTbull/osxphotos/commit/6a898886ddadc9d5bc9dbad6ee7365270dd0a26d)
- Added {album}, {keyword}, and {person} to template system [`507c4a3`](https://github.com/RhetTbull/osxphotos/commit/507c4a374014f999ca19789bce0df0c14332e021)
- Added places command to CLI [`fd5e748`](https://github.com/RhetTbull/osxphotos/commit/fd5e748dca759ea1c3a7329d447f363afe8418b7)
- Updated export example [`01cd7fe`](https://github.com/RhetTbull/osxphotos/commit/01cd7fed6d7fc0c61c171a05319c211eb0a9f7c1)
- Fixed typo in help text [`c02953e`](https://github.com/RhetTbull/osxphotos/commit/c02953ef5fe1aee219e0557bfd8c3322f1900a81)

## [v0.24.2](https://github.com/RhetTbull/osxphotos/compare/v0.24.1...v0.24.2)

> 28 March 2020

- added {place.country_code} to template system [`be2e167`](https://github.com/RhetTbull/osxphotos/commit/be2e16769d5d2c75af6d7792f1311f5a65c3bc67)

## [v0.24.1](https://github.com/RhetTbull/osxphotos/compare/v0.23.4...v0.24.1)

> 28 March 2020

- Added detailed place data in PlaceInfo.names [`c06dd42`](https://github.com/RhetTbull/osxphotos/commit/c06dd4233f917f068c087f5604013d371b0a826a)
- Template system now supports default values [`67a9a9e`](https://github.com/RhetTbull/osxphotos/commit/67a9a9e21bd05d01a3202b0a1279487f5d04c9d9)
- Replaced template renderer with regex-based renderer [`427c4c0`](https://github.com/RhetTbull/osxphotos/commit/427c4c0bc49f671477866d30eee74834c67d7bc5)

## [v0.23.4](https://github.com/RhetTbull/osxphotos/compare/v0.23.3...v0.23.4)

> 22 March 2020

- Added export_by_album.py to examples [`908fead`](https://github.com/RhetTbull/osxphotos/commit/908fead8a2fbcef3b4a387f34d83d88c507c5939)
- Updated pathvalidate calls [`d066435`](https://github.com/RhetTbull/osxphotos/commit/d066435e3df4062be6a0a3d5fa7308f293e764d5)
- Updated example [`8f0307f`](https://github.com/RhetTbull/osxphotos/commit/8f0307fc24345ca0e87017ac76791c9bbe8db25e)

## [v0.23.3](https://github.com/RhetTbull/osxphotos/compare/v0.23.1...v0.23.3)

> 22 March 2020

- Initial version of templating system for CLI [`2feb099`](https://github.com/RhetTbull/osxphotos/commit/2feb0999b3f9ffd9a24e37238f780239a027aa49)
- Added __str__ to place [`ad58b03`](https://github.com/RhetTbull/osxphotos/commit/ad58b03f2d31daf33849b141570dd0fb5e0a262e)
- Test library updates [`e90d9c6`](https://github.com/RhetTbull/osxphotos/commit/e90d9c6e11fce7a4e4aa348dcc5f57420c0b6c44)

## [v0.23.1](https://github.com/RhetTbull/osxphotos/compare/v0.23.0...v0.23.1)

> 21 March 2020

- Fixed requirements.txt for bplist2 [`cda5f44`](https://github.com/RhetTbull/osxphotos/commit/cda5f446933ea2272409d1f153e2a7811626ada6)
- Updated requirements.txt [`9da7ad6`](https://github.com/RhetTbull/osxphotos/commit/9da7ad6dcc021fdafe358d74e1c52f69dc49ade8)
- still trying to debug github actions fail [`960487f`](https://github.com/RhetTbull/osxphotos/commit/960487f2961f97f6b24d253472dcedf74dfc7797)

## [v0.23.0](https://github.com/RhetTbull/osxphotos/compare/v0.22.23...v0.23.0)

> 21 March 2020

- Added PhotoInfo.place for reverse geolocation data [`b338b34`](https://github.com/RhetTbull/osxphotos/commit/b338b34d5055a7621e4ebe4fbbae12227d77af6d)
- Update pythonpackage.yml [`92e5bdd`](https://github.com/RhetTbull/osxphotos/commit/92e5bdd2e986e5de2a710abf60ba0dc99c6a6730)
- Removed flake8 [`a723881`](https://github.com/RhetTbull/osxphotos/commit/a723881dd3beaa79d6881a50e11031260c1f678b)

## [v0.22.23](https://github.com/RhetTbull/osxphotos/compare/v0.22.21...v0.22.23)

> 15 March 2020

- Lots of work on export code [`0940f03`](https://github.com/RhetTbull/osxphotos/commit/0940f039d3e628dc4f25c69bf27ce413807d3f71)
- test library update [`1e08a74`](https://github.com/RhetTbull/osxphotos/commit/1e08a7449e69965a37373dadabb37c993d93fc69)

## [v0.22.21](https://github.com/RhetTbull/osxphotos/compare/v0.22.17...v0.22.21)

> 14 March 2020

- Working on export edited bug for issue #78 [`8542e1a`](https://github.com/RhetTbull/osxphotos/commit/8542e1a97f6b640f287b37af9e50fd05f964ec4d)
- Fixed download-missing to only download when actually missing [`dd20b8d`](https://github.com/RhetTbull/osxphotos/commit/dd20b8d8ac3b16d3b72a26b97dcc620b11e3a7c0)
- test library updates [`e99391a`](https://github.com/RhetTbull/osxphotos/commit/e99391a68e844adb63edde3efb921cffa3928aeb)

## [v0.22.17](https://github.com/RhetTbull/osxphotos/compare/v0.22.16...v0.22.17)

> 14 March 2020

- Added MANIFEST.in [`279ab36`](https://github.com/RhetTbull/osxphotos/commit/279ab369295cfe1c778b38e212248271e4fc659e)
- version bump [`783e097`](https://github.com/RhetTbull/osxphotos/commit/783e097da35a210a2aa5c75865a8599541b9da0b)

## [v0.22.16](https://github.com/RhetTbull/osxphotos/compare/v0.22.13...v0.22.16)

> 14 March 2020

- removed activate from --download-missing-photos Applescript, closes #69 [`#69`](https://github.com/RhetTbull/osxphotos/issues/69)
- Added media type specials to json and string output, closes #68 [`#68`](https://github.com/RhetTbull/osxphotos/issues/68)
- Added query/export options for special media types [`2b7d84a`](https://github.com/RhetTbull/osxphotos/commit/2b7d84a4d103982ad874d875bafbc34d654d539a)
- README.md update [`a27ce33`](https://github.com/RhetTbull/osxphotos/commit/a27ce33473df3260dfb7ed26e28295cbf87d1e78)
- Test library updates [`2d7d0b8`](https://github.com/RhetTbull/osxphotos/commit/2d7d0b86e0008cae043e314937504f36ad882990)
- Fixed bug in --download-missing related to burst images [`1f13ba8`](https://github.com/RhetTbull/osxphotos/commit/1f13ba837fe36ff4eeb48cca02f5312a88a0a765)
- test library update [`acb6b9e`](https://github.com/RhetTbull/osxphotos/commit/acb6b9e72f7f6b8f4f1d64b46f270a4d3e984fef)

## [v0.22.13](https://github.com/RhetTbull/osxphotos/compare/v0.22.12...v0.22.13)

> 8 March 2020

- Added media type specials, closes #60 [`#60`](https://github.com/RhetTbull/osxphotos/issues/60)
- Updated README.md [`1f8fd6e`](https://github.com/RhetTbull/osxphotos/commit/1f8fd6e929cc0edd3dd2f222416454d26955bf2a)

## [v0.22.12](https://github.com/RhetTbull/osxphotos/compare/0.22.10...v0.22.12)

> 7 March 2020

- Added exiftool [`8dea419`](https://github.com/RhetTbull/osxphotos/commit/8dea41961bad285be7058a68e5f7199e5cfb740e)
- Added --exiftool to CLI export [`ef79961`](https://github.com/RhetTbull/osxphotos/commit/ef799610aea67b703a7d056b7eee227534ba78a5)
- Updated test library [`9a0fc0d`](https://github.com/RhetTbull/osxphotos/commit/9a0fc0db3e79359610fd0f124a97b03fcf97d8a7)

## [0.22.10](https://github.com/RhetTbull/osxphotos/compare/v0.22.9...0.22.10)

> 8 February 2020

- Fixed bug in --download-missing to fix issue #64 [`c654e3d`](https://github.com/RhetTbull/osxphotos/commit/c654e3dc61283382b37b6892dab1516ec517143a)
- removed commented out code [`69addc3`](https://github.com/RhetTbull/osxphotos/commit/69addc34649f992c6a4a0e0e334754a72530f0ba)
- Cleaned up comments and unneeded test code [`e3c40bc`](https://github.com/RhetTbull/osxphotos/commit/e3c40bcbaaf3560d53091cf46ed851d90ff82cfa)

## [v0.22.9](https://github.com/RhetTbull/osxphotos/compare/v0.22.7...v0.22.9)

> 1 February 2020

- Updated PhotosDB to only copy database if locked, speed improvement for cases where DB not locked; closes #34 [`#34`](https://github.com/RhetTbull/osxphotos/issues/34)
- Changed temp file handling to use tempfile.TemporaryDirectory, closes #59 [`#59`](https://github.com/RhetTbull/osxphotos/issues/59)
- Slight refactor to PhotosDB.photos() [`91d5729`](https://github.com/RhetTbull/osxphotos/commit/91d5729beaa0f0c2583e6320b18d958429e66075)
- Test library updates [`6e563e2`](https://github.com/RhetTbull/osxphotos/commit/6e563e214c569ba7838f7464de9258c3bba5db23)
- Removed _tmp_file code that's no longer needed [`27994c9`](https://github.com/RhetTbull/osxphotos/commit/27994c9fd372303833a5794f1de9815f425c762e)
- Updated photos_repl.py [`fdf636a`](https://github.com/RhetTbull/osxphotos/commit/fdf636ac8864ebb2cc324b1f9d3c6c82ee3910f9)
- Added PhotosDB() behavior to open last library if no args passed but also added cautionary note to README [`46d3c7d`](https://github.com/RhetTbull/osxphotos/commit/46d3c7dbdaf848d5c340ce8a362ff296a36c552d)

## [v0.22.7](https://github.com/RhetTbull/osxphotos/compare/v0.22.4...v0.22.7)

> 26 January 2020

- Corrected Panorama Flag [`#58`](https://github.com/RhetTbull/osxphotos/pull/58)
- Jan 20 Updates [`#1`](https://github.com/RhetTbull/osxphotos/pull/1)
- Added XMP sidecar option to export, closes #51 [`#51`](https://github.com/RhetTbull/osxphotos/issues/51)
- Test library updates, closes #52 [`#52`](https://github.com/RhetTbull/osxphotos/issues/52)
- Added XMP sidecar to export [`4dfb131`](https://github.com/RhetTbull/osxphotos/commit/4dfb131a21b1b1efefe3b918ecb06fc6fcb03f2c)
- Added date_modified to PhotoInfo [`67b0ae0`](https://github.com/RhetTbull/osxphotos/commit/67b0ae0bf679815372d415c3064e21d46a5b8718)
- Added date_modified to PhotoInfo [`4d36b3b`](https://github.com/RhetTbull/osxphotos/commit/4d36b3b31f3e0e74d9d111b6b691771e19f94086)
- Updated CLI options with more descriptive metavar names [`e79cb92`](https://github.com/RhetTbull/osxphotos/commit/e79cb92693758c984dc789d5fa5d2e87e381e921)
- CLI now looks for photos library to use if non specified by user [`50b7e69`](https://github.com/RhetTbull/osxphotos/commit/50b7e6920a694aa45f478d1131868525c9147919)

## [v0.22.4](https://github.com/RhetTbull/osxphotos/compare/v0.22.0...v0.22.4)

> 20 January 2020

- Add --from-date and --to-date to query and export command [`#57`](https://github.com/RhetTbull/osxphotos/pull/57)
- Refactor CLI [`#55`](https://github.com/RhetTbull/osxphotos/pull/55)
- Refactor cli: singular --db, --json and query options. [`e214746`](https://github.com/RhetTbull/osxphotos/commit/e214746063271e6f9f586286103ed051ada49d85)
- Implement from_date and to_date in PhotosDB as well as query and export command. Some refactoring of CLI as well. [`cfa2b4a`](https://github.com/RhetTbull/osxphotos/commit/cfa2b4a828facf0aff5bc19f777457ad776c4a05)
- Refactored _query.  Still hairy, but less so. [`b9dee49`](https://github.com/RhetTbull/osxphotos/commit/b9dee4995c6d89fadb3d2482374b7098f2ab5ed9)
- Updated README.md [`0aff83f`](https://github.com/RhetTbull/osxphotos/commit/0aff83ff21c20e293c0b75bacf2863090a0fb725)
- Started adding tests for CLI [`f0b18c3`](https://github.com/RhetTbull/osxphotos/commit/f0b18c3d29b2141d348be0495013c51c072c6251)

## [v0.22.0](https://github.com/RhetTbull/osxphotos/compare/v0.21.5...v0.22.0)

> 17 January 2020

- Refactored PhotosDB and CLI to require explicity passing the database to avoid non-deterministic behavior when last database can't be found.  This may break existing code. [`ede56ff`](https://github.com/RhetTbull/osxphotos/commit/ede56ffc31cf98811b3d4d16e22406ac0eae0315)
- Changed get_system_library_path to return None if could not get system library [`646ea4f`](https://github.com/RhetTbull/osxphotos/commit/646ea4f24ca1119b27280af1445e31adcd0690f0)
- Fix to setup to specify versions of required packages [`de05323`](https://github.com/RhetTbull/osxphotos/commit/de05323a153fe49723b39e48b9038c1fb9535a72)

## [v0.21.5](https://github.com/RhetTbull/osxphotos/compare/v0.21.0...v0.21.5)

> 12 January 2020

- Fixed search for edited photo in path_edited [`edb31f7`](https://github.com/RhetTbull/osxphotos/commit/edb31f796a76912e6ed8182b691396cf4ec62ffa)
- Added tests for live photos [`5473f3b`](https://github.com/RhetTbull/osxphotos/commit/5473f3b3fd745d4772721dfd1ed821ab0660bf72)
- Added incloud and iscloudasset for Photos 4 [`e089d13`](https://github.com/RhetTbull/osxphotos/commit/e089d135d3e04320bf98b2c9b11875343e68be04)

## [v0.21.0](https://github.com/RhetTbull/osxphotos/compare/v0.20.0...v0.21.0)

> 4 January 2020

- Added live photo support for both Photos 4 & 5 [`d5eaff0`](https://github.com/RhetTbull/osxphotos/commit/d5eaff02f2a29a9d105ab72e9a9aeffbc9a3425b)
- Added support for burst photos; added export-bursts to CLI [`593983a`](https://github.com/RhetTbull/osxphotos/commit/593983a09940e67fb9347bf345cfd7289465fa0a)
- Added live-photo option to CLI query and export [`6f6d37c`](https://github.com/RhetTbull/osxphotos/commit/6f6d37ceacf71a52a2c0216f0ad75afee244946a)

## [v0.20.0](https://github.com/RhetTbull/osxphotos/compare/v0.19.0...v0.20.0)

> 31 December 2019

- Added support for filtering only movies or photos to CLI; added search for UTI to CLI [`9cd5363`](https://github.com/RhetTbull/osxphotos/commit/9cd5363a800dd85f333219788c661745b2ce88ad)
- Added support for bust photos; added export-bursts to CLI [`1136f84`](https://github.com/RhetTbull/osxphotos/commit/1136f84d9b5ea454115ba3d2720625722671e63b)
- Temporary fix to filter out unselected burst photos [`a550ba0`](https://github.com/RhetTbull/osxphotos/commit/a550ba00d6ff43a819cb18446e532f10ded81834)

## [v0.19.0](https://github.com/RhetTbull/osxphotos/compare/v0.18.0...v0.19.0)

> 29 December 2019

- Added support for movies for Photos 5; fixed bugs in ismissing and path [`6f4d129`](https://github.com/RhetTbull/osxphotos/commit/6f4d129f07046c4a34d3d6cf6854c8514a594781)
- Added support for movies for Photos 5; fixed bugs in ismissing and path [`b030966`](https://github.com/RhetTbull/osxphotos/commit/b030966051af93be380ff967ac047bf566e5d817)
- Initial support for movies [`dbe363e`](https://github.com/RhetTbull/osxphotos/commit/dbe363e4d754253a0405fb1df045677e8780d630)

## [v0.18.0](https://github.com/RhetTbull/osxphotos/compare/v0.15.1...v0.18.0)

> 26 December 2019

- Restructured entire code base to make it easier to maintain. Closes #16 [`#16`](https://github.com/RhetTbull/osxphotos/issues/16)
- Added TOC to README; closes #24 [`#24`](https://github.com/RhetTbull/osxphotos/issues/24)
- removed old applescript code and files [`1839593`](https://github.com/RhetTbull/osxphotos/commit/18395933a583314d5d992492713752003852e75c)
- Added test cases and documentation for shared photos and shared albums [`6d20e9e`](https://github.com/RhetTbull/osxphotos/commit/6d20e9e36185aa027d82237cadfe3b55614ba96f)
- Refactored PhotoInfo to use properties instead of methods--major update [`1ddd90c`](https://github.com/RhetTbull/osxphotos/commit/1ddd90cbdc824afc5df9d2347e730bd9f86350ee)
- Moved PhotosDB attributes to properties instead of methods [`d95acdf`](https://github.com/RhetTbull/osxphotos/commit/d95acdf9f8764a1720bcba71a6dad29bf668eaf9)
- changed interface for export, prepped for exiftool_json_sidecar [`1fe8859`](https://github.com/RhetTbull/osxphotos/commit/1fe885962e8a9a420e776bdd3dc640ca143224b2)

## [v0.15.1](https://github.com/RhetTbull/osxphotos/compare/v0.15.0...v0.15.1)

> 14 December 2019

## [v0.15.0](https://github.com/RhetTbull/osxphotos/compare/v0.14.21...v0.15.0)

> 14 December 2019

- Added PhotoInfo.export(); closes #10 [`#10`](https://github.com/RhetTbull/osxphotos/issues/10)
- refactored private vars in PhotoInfo [`d5a5bd4`](https://github.com/RhetTbull/osxphotos/commit/d5a5bd41b3d3e184d3f9a9d05a32a51fcbe1ef0a)
- Updated export example [`bf8aed6`](https://github.com/RhetTbull/osxphotos/commit/bf8aed69cfff61733e4cfd5ed2058bb20e3f5299)

## [v0.14.21](https://github.com/RhetTbull/osxphotos/compare/v0.14.8...v0.14.21)

> 8 December 2019

- Added list option to cmd_line. Closes #14 [`#14`](https://github.com/RhetTbull/osxphotos/issues/14)
- added edited and external_edit to cmd_line and __str__, to_json; closes #12 [`#12`](https://github.com/RhetTbull/osxphotos/issues/12)
- Cleaned up logic in cmd_line query(). Closes #17 [`#17`](https://github.com/RhetTbull/osxphotos/issues/17)
- Added get_db_path and get_library_path to PhotosDB [`1d006a4`](https://github.com/RhetTbull/osxphotos/commit/1d006a4b50ed58b01c6116734bef5f740655a063)
- Updated PhotosDB.__init__() to accept positional or named arg for dbfile and added associated tests [`9118043`](https://github.com/RhetTbull/osxphotos/commit/911804317b98bf485a39b8588c772be14314aa51)
- Updated album code in process_database4 and process_database5 to use album uuid [`1cf3e4b`](https://github.com/RhetTbull/osxphotos/commit/1cf3e4b9540c15f8bda2545deb183912bcda40a7)
- Updated get_db_version and associated tests [`eb563ad`](https://github.com/RhetTbull/osxphotos/commit/eb563ad29738f29f3514ebfb4747baa2dc5356be)
- Added external_edit for Photos 5 [`42baa29`](https://github.com/RhetTbull/osxphotos/commit/42baa29c18fe2ff16e4d684f87ef7a85993898c1)

## [v0.14.8](https://github.com/RhetTbull/osxphotos/compare/v0.14.6...v0.14.8)

> 30 November 2019

- Added path_edited() for Photos 5, still needs to be added for Photos &lt;= 4.0 [`68eef42`](https://github.com/RhetTbull/osxphotos/commit/68eef42599c737e180d2d0ead936630abd5a8a65)
- Fixed path_edited() for Photos 4.0 [`37dfc1e`](https://github.com/RhetTbull/osxphotos/commit/37dfc1e1513c93088fca7cc6def1219d32694468)
- cleaned up commented out code [`3dc0943`](https://github.com/RhetTbull/osxphotos/commit/3dc09434535b98a7989c2051a28ecf3ebdc772cc)

## [v0.14.6](https://github.com/RhetTbull/osxphotos/compare/v0.14.4...v0.14.6)

> 28 November 2019

- Added tests for hidden and favorite to both 14.6 and 15.1 [`51e720d`](https://github.com/RhetTbull/osxphotos/commit/51e720dce9238c2a2b44a7ae956e40f0cd6452d7)
- Added location (latitude/longitude), closes issue #2 [`44321da`](https://github.com/RhetTbull/osxphotos/commit/44321da243e374c5239e9bcd28c3515e32e1076a)
- cleaned up test code [`b2242da`](https://github.com/RhetTbull/osxphotos/commit/b2242da9b7031f614c73be3fb5446a97f69b1d0d)

## [v0.14.4](https://github.com/RhetTbull/osxphotos/compare/v0.14.0...v0.14.4)

> 24 November 2019

- Added name and description to cmd_line [`5af2b3e`](https://github.com/RhetTbull/osxphotos/commit/5af2b3e039e5e5a92b858592b8b968568d82e40f)
- removed loguru code [`aa73c2f`](https://github.com/RhetTbull/osxphotos/commit/aa73c2f0559de6bcdc521e9345e07898b36795bb)
- Added hidden/favorite/missing to cmd_line [`b36b7e7`](https://github.com/RhetTbull/osxphotos/commit/b36b7e7eb2a258f864f34363de4b6d9228ee6090)

## [v0.14.0](https://github.com/RhetTbull/osxphotos/compare/v0.12.3...v0.14.0)

> 23 November 2019

- added test for 10.15/Catalina [`243492d`](https://github.com/RhetTbull/osxphotos/commit/243492df88409566c46cbc02ca01d509e711bcdd)
- moved process_photos to process_photos4 and process_photos5 [`7eff015`](https://github.com/RhetTbull/osxphotos/commit/7eff015439361f3f7be99777d878713afd10c480)
- basic Photos 5 info now being read [`a4b5f2a`](https://github.com/RhetTbull/osxphotos/commit/a4b5f2a501d9c98f9609de96757481f323b31ab0)

## [v0.12.3](https://github.com/RhetTbull/osxphotos/compare/v0.12.2...v0.12.3)

> 24 August 2019

- fixed typo in README [`39ef8dd`](https://github.com/RhetTbull/osxphotos/commit/39ef8ddf3fdf8e9d22566c51783f9b78fab4f439)

## [v0.12.2](https://github.com/RhetTbull/osxphotos/compare/v0.10.4-beta...v0.12.2)

> 24 August 2019

- Added tests for 10.14.6 [`fb2c12d`](https://github.com/RhetTbull/osxphotos/commit/fb2c12d9818fbec74f947638b1b60a2c3f73effb)
- Added support and tests for 10.12 [`58f5283`](https://github.com/RhetTbull/osxphotos/commit/58f52833d62672ed13fcfa16be5d999e75f37e2b)
- Added osxphotos command line tool [`0e65ab5`](https://github.com/RhetTbull/osxphotos/commit/0e65ab5452d96dc9913683d90d1fb2c833cd75b8)

## [v0.10.4-beta](https://github.com/RhetTbull/osxphotos/compare/v0.10.1-alpha...v0.10.4-beta)

> 27 July 2019

- Added test for 10.14 mojave [`af122e9`](https://github.com/RhetTbull/osxphotos/commit/af122e9392d45387e302ebb79b28e045dd3fa61a)
- update requirements.txt [`81be373`](https://github.com/RhetTbull/osxphotos/commit/81be373505ad858ae8ef1196ccfb5e6f04bf6bfc)
- Updated README, added os & db version tests, updated test library for 10.13 [`a58ac14`](https://github.com/RhetTbull/osxphotos/commit/a58ac149f313ece99ff2d32a8c22e8b8b75eaebc)

## v0.10.1-alpha

> 26 July 2019

- first commit [`8b61d57`](https://github.com/RhetTbull/osxphotos/commit/8b61d573ed4dbb3fd44b94ee265767b2011fcf90)
- Added tests [`3023f56`](https://github.com/RhetTbull/osxphotos/commit/3023f568b73733fb3dfbba4f519a7c2d1995784f)
- Updated README, added PhotoInfo.hasadjustments() [`9efa83c`](https://github.com/RhetTbull/osxphotos/commit/9efa83c5cd3f23cf681c459f73a466496c552396)
