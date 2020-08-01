-- Writes the UUIDs of selected images in Photos to a text file
-- Useful with the --uuid-from-file option of osxphotos

tell application "Photos"
	activate
	
	set theResults to selection
	set theVersion to version of application "Photos"
	set theBackup to AppleScript's text item delimiters
	
	-- In Photos 5, uuid is in form DB7DED61-C0CC-4FC7-952C-CEA9E01AB106/L0/001 
	-- but we need only the part before the "/"
	if theVersion ³ 5 then
		-- Set the new delimiter
		set AppleScript's text item delimiters to "/"
	end if
	
	set outputFile to (choose file name with prompt "Save As File" default name "uuid.txt" default location path to desktop) as text
	if outputFile does not end with ".txt" then set outputFile to outputFile & ".txt"
	
	set theOutput to open for access file outputFile with write permission
	set eof of theOutput to 0
	set theCount to 0
	
	repeat with theItem in theResults
		
		set theID to ((id of theItem) as text)
		if theVersion ³ 5 then
			set theID to text item 1 of theID
		end if
		write theID & "
" to theOutput
		set theCount to theCount + 1
		
	end repeat
	
	close access theOutput
	set AppleScript's text item delimiters to theBackup
	display dialog "Done. Wrote " & theCount & " UUIDs to file " & outputFile
	
end tell


