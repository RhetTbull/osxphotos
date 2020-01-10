-- Displays  UUID and other info about selected photos
-- Useful for debugging with osxphotos

tell application "Photos"
	activate
	
	set theDelimiter to ";"
	set theBackup to AppleScript's text item delimiters
	
	-- Set the new delimiter
	set AppleScript's text item delimiters to theDelimiter
	
	set theResults to selection
	repeat with theItem in theResults
		
		
		set theKeywords to keywords of theItem
		if theKeywords is not {} then
			theKeywords = (theKeywords as text)
		else
			theKeywords = "none"
		end if
		
		set theStr to (((((id of theItem) as text) & ", " & (filename of theItem) as text) & ", " & theKeywords & ", " & (name of theItem) as text) & ", " & (description of theItem) as text) & "
"
		display dialog theStr
		
	end repeat
	
	set AppleScript's text item delimiters to theBackup
	
end tell


