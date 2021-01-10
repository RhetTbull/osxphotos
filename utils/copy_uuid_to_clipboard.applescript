-- Copies UUID of selected photo to the clipboard, if more than one selection, copies uuid from the last item
-- Useful for debugging with osxphotos


tell application "Photos"
	set uuid to ""
	set theSelection to selection
	repeat with theItem in theSelection
		set uuid to ((id of theItem) as text)
		set oldDelimiter to AppleScript's text item delimiters
		set AppleScript's text item delimiters to "/"
		set theTextItems to every text item of uuid
		set uuid to first item of theTextItems
		set AppleScript's text item delimiters to oldDelimiter
	end repeat
	set the clipboard to uuid
	
end tell


