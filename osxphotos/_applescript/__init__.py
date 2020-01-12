""" applescript -- Easy-to-use Python wrapper for NSAppleScript """

import sys

from Foundation import NSAppleScript, NSAppleEventDescriptor, NSURL, \
		NSAppleScriptErrorMessage, NSAppleScriptErrorBriefMessage, \
		NSAppleScriptErrorNumber, NSAppleScriptErrorAppName, NSAppleScriptErrorRange

from .aecodecs import Codecs, fourcharcode, AEType, AEEnum
from . import kae

__all__ = ['AppleScript', 'ScriptError', 'AEType', 'AEEnum', 'kMissingValue', 'kae']


######################################################################


class AppleScript:
	""" Represents a compiled AppleScript. The script object is persistent; its handlers may be called multiple times and its top-level properties will retain current state until the script object's disposal.
	
	
	"""

	_codecs = Codecs()
	
	def __init__(self, source=None, path=None):
		"""
			source : str | None -- AppleScript source code
			path : str | None -- full path to .scpt/.applescript file
			
			Notes:
			
			- Either the path or the source argument must be provided.
			
			- If the script cannot be read/compiled, a ScriptError is raised.
		"""
		if path:
			url = NSURL.fileURLWithPath_(path)
			self._script, errorinfo = NSAppleScript.alloc().initWithContentsOfURL_error_(url, None)
			if errorinfo:
				raise ScriptError(errorinfo)
		elif source:
			self._script = NSAppleScript.alloc().initWithSource_(source)
		else:
			raise ValueError("Missing source or path argument.")
		if not self._script.isCompiled():
			errorinfo = self._script.compileAndReturnError_(None)[1]
			if errorinfo:
				raise ScriptError(errorinfo)
	
	def __repr__(self):
		s = self.source
		return 'AppleScript({})'.format(repr(s) if len(s) < 100 else '{}...{}'.format(repr(s)[:80], repr(s)[-17:]))
	
	##
	
	def _newevent(self, suite, code, args):
		evt = NSAppleEventDescriptor.appleEventWithEventClass_eventID_targetDescriptor_returnID_transactionID_(
						fourcharcode(suite), fourcharcode(code), NSAppleEventDescriptor.nullDescriptor(), 0, 0)
		evt.setDescriptor_forKeyword_(self._codecs.pack(args), fourcharcode(kae.keyDirectObject))
		return evt
	
	def _unpackresult(self, result, errorinfo):
		if not result:
			raise ScriptError(errorinfo)
		return self._codecs.unpack(result)

	##
	
	source = property(lambda self: str(self._script.source()), doc="str -- the script's source code")
	
	def run(self, *args):
		""" Run the script, optionally passing arguments to its run handler.
			
				args : anything -- arguments to pass to script, if any; see also supported type mappings documentation
				Result : anything | None -- the script's return value, if any
			
			Notes:
			
			- The run handler must be explicitly declared in order to pass arguments.
			
			- AppleScript will ignore excess arguments. Passing insufficient arguments will result in an error.
			
			- If execution fails, a ScriptError is raised.
		"""
		if args:
			evt = self._newevent(kae.kCoreEventClass, kae.kAEOpenApplication, args)
			return self._unpackresult(*self._script.executeAppleEvent_error_(evt, None))
		else:
			return self._unpackresult(*self._script.executeAndReturnError_(None))
	
	def call(self, name, *args):
		""" Call the specified user-defined handler.
				
				name : str -- the handler's name (case-sensitive)
				args : anything -- arguments to pass to script, if any; see documentation for supported types
				Result : anything | None -- the script's return value, if any
			
			Notes:
			
			- The handler's name must be a user-defined identifier, not an AppleScript keyword; e.g. 'myCount' is acceptable; 'count' is not.
			
			- AppleScript will ignore excess arguments. Passing insufficient arguments will result in an error.
			
			- If execution fails, a ScriptError is raised.
		"""
		evt = self._newevent(kae.kASAppleScriptSuite, kae.kASPrepositionalSubroutine, args)
		evt.setDescriptor_forKeyword_(NSAppleEventDescriptor.descriptorWithString_(name), 
						fourcharcode(kae.keyASSubroutineName))
		return self._unpackresult(*self._script.executeAppleEvent_error_(evt, None))


##


class ScriptError(Exception):
	""" Indicates an AppleScript compilation/execution error. """
	
	def __init__(self, errorinfo):
		self._errorinfo = dict(errorinfo)
	
	def __repr__(self):
		return 'ScriptError({})'.format(self._errorinfo)
	
	@property
	def message(self):
		""" str -- the error message """
		msg = self._errorinfo.get(NSAppleScriptErrorMessage)
		if not msg:
			msg = self._errorinfo.get(NSAppleScriptErrorBriefMessage, 'Script Error')
		return msg
	
	number = property(lambda self: self._errorinfo.get(NSAppleScriptErrorNumber),
			doc="int | None -- the error number, if given")
	
	appname = property(lambda self: self._errorinfo.get(NSAppleScriptErrorAppName),
			doc="str | None -- the name of the application that reported the error, where relevant")
	
	@property
	def range(self):
		""" (int, int) -- the start and end points (1-indexed) within the source code where the error occurred """
		range = self._errorinfo.get(NSAppleScriptErrorRange)
		if range:
			start = range.rangeValue().location
			end = start + range.rangeValue().length
			return (start, end)
		else:
			return None
	
	def __str__(self):
		msg = self.message
		for s, v in [(' ({})', self.number), (' app={!r}', self.appname), (' range={0[0]}-{0[1]}', self.range)]:
			if v is not None:
				msg += s.format(v)
		return msg.encode('ascii', 'replace') if sys.version_info.major < 3 else msg # 2.7 compatibility


##


kMissingValue = AEType(kae.cMissingValue) # convenience constant

