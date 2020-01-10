-- Dumps UUID and other info about every photo in Photos.app to a tet file (see theFile below)
-- Use output of this script with check_uuid.py to help with debugging differences in Photos and osxphoto

tell application "Photos"
	activate
	
	set theDelimiter to ";"
	set theBackup to AppleScript's text item delimiters
	
	-- Set the new delimiter
	set AppleScript's text item delimiters to theDelimiter
	
	set theFile to (((path to desktop folder) as string) & "photoslib1.txt")
	set theOpenedFile to open for access file theFile with write permission
	
	set results to selection
	repeat with _item in results
		
		
		set _keywords to keywords of _item
		if _keywords is not {} then
			_keywords = (_keywords as text)
		else
			_keywords = "none"
		end if
		
		set _str to (((((id of _item) as text) & ", " & (filename of _item) as text) & ", " & _keywords & ", " & (name of _item) as text) & ", " & (description of _item) as text) & "
"
		--		display dialog _str
		write _str to theOpenedFile starting at eof
		
		-- writeTextToFile(_str, theFile, false)
	end repeat
	
	-- Restore the original delimiter
	set AppleScript's text item delimiters to theBackup
	close access theOpenedFile
	
end tell


