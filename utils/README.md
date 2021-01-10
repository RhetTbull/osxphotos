# Utils

These are various utilities used in my development workflow. They may or may not be useful to you if you're working on osxphotos.  If using the AppleScripts to get data from Photos, I highly recommend the excellent [FastScripts](https://redsweater.com/fastscripts/) from Red Sweater Software.

## Files

|File | Description |
|-----|-------------|
|build_help_table.py| Builds the template substitutions table used in main README.md |
|check_uuid.py| Use with output file created by dump_photo_info.scpt to check ouput of osxphotos vs what Photos reports|
|copy_uuid_to_clipboard.applescript| Copy UUID of selected photo in Photos to the Clipboard|
|dump_photo_info.applescript| Dumps UUID and other info about every photo in Photos.app to a test file; see check_uuid.py|
|dump_photo_info.scpt| Compiled version of dump_photo_info.applescript|
|gen_face_test_data.py| Generate test data for test_faceinfo.py|
|generate_search_info_test_data.py | Create the test data needed for test_search_info_10_15_7.py|
|get_photo_info.applescript| Displays  UUID and other info about selected photos, useful for debugging|
|get_photo_info.scpt| Compiled version of above|
|write_uuid_to_file.applescript| Writes the UUIDs of selected images in Photos to a text file; can generate input for --uuid-from-file|
