""" aecodecs -- Convert from common Python types to Apple Event Manager types and vice-versa. """

import datetime, struct, sys

from Foundation import NSAppleEventDescriptor, NSURL

from . import kae


__all__ = ['Codecs', 'AEType', 'AEEnum']


######################################################################


def fourcharcode(code):
	""" Convert four-char code for use in NSAppleEventDescriptor methods.
		
		code : bytes -- four-char code, e.g. b'utxt'
		Result : int -- OSType, e.g. 1970567284
	"""
	return struct.unpack('>I', code)[0]


#######


class Codecs:
	""" Implements mappings for common Python types with direct AppleScript equivalents. Used by AppleScript class. """

	kMacEpoch = datetime.datetime(1904, 1, 1)
	kUSRF = fourcharcode(kae.keyASUserRecordFields)

	def __init__(self):
		# Clients may add/remove/replace encoder and decoder items:
		self.encoders = {
				NSAppleEventDescriptor.class__(): self.packdesc,
				type(None): self.packnone,
				bool: self.packbool,
				int: self.packint,
				float: self.packfloat,
				bytes: self.packbytes,
				str: self.packstr,
				list: self.packlist,
				tuple: self.packlist,
				dict: self.packdict,
				datetime.datetime: self.packdatetime,
				AEType: self.packtype,
				AEEnum: self.packenum,
		}
		if sys.version_info.major < 3: # 2.7 compatibility
			self.encoders[unicode] = self.packstr
		
		self.decoders = {fourcharcode(k): v for k, v in {
				kae.typeNull: self.unpacknull,
				kae.typeBoolean: self.unpackboolean,
				kae.typeFalse: self.unpackboolean,
				kae.typeTrue: self.unpackboolean,
				kae.typeSInt32: self.unpacksint32,
				kae.typeIEEE64BitFloatingPoint: self.unpackfloat64,
				kae.typeUTF8Text: self.unpackunicodetext,
				kae.typeUTF16ExternalRepresentation: self.unpackunicodetext,
				kae.typeUnicodeText: self.unpackunicodetext,
				kae.typeLongDateTime: self.unpacklongdatetime,
				kae.typeAEList: self.unpackaelist,
				kae.typeAERecord: self.unpackaerecord,
				kae.typeAlias: self.unpackfile,
				kae.typeFSS: self.unpackfile,
				kae.typeFSRef: self.unpackfile,
				kae.typeFileURL: self.unpackfile,
				kae.typeType: self.unpacktype,
				kae.typeEnumeration: self.unpackenumeration,
		}.items()}
	
	def pack(self, data):
		"""Pack Python data.
			data : anything -- a Python value
			Result : NSAppleEventDescriptor -- an AE descriptor, or error if no encoder exists for this type of data
		"""
		try:
			return self.encoders[data.__class__](data) # quick lookup by type/class
		except (KeyError, AttributeError) as e:
			for type, encoder in self.encoders.items(): # slower but more thorough lookup that can handle subtypes/subclasses
				if isinstance(data, type):
					return encoder(data)
		raise TypeError("Can't pack data into an AEDesc (unsupported type): {!r}".format(data))
	
	def unpack(self, desc):
		"""Unpack an Apple event descriptor.
			desc : NSAppleEventDescriptor
			Result : anything -- a Python value, or the original NSAppleEventDescriptor if no decoder is found
		"""
		decoder = self.decoders.get(desc.descriptorType())
		# unpack known type
		if decoder:
			return decoder(desc)
		# if it's a record-like desc, unpack as dict with an extra AEType(b'pcls') key containing the desc type
		rec = desc.coerceToDescriptorType_(fourcharcode(kae.typeAERecord))
		if rec:
			rec = self.unpackaerecord(rec)
			rec[AEType(kae.pClass)] = AEType(struct.pack('>I', desc.descriptorType()))
			return rec
		# return as-is
		return desc
	
	##
	
	def _packbytes(self, desctype, data):
		return NSAppleEventDescriptor.descriptorWithDescriptorType_bytes_length_(
			fourcharcode(desctype), data, len(data))
	
	def packdesc(self, val):
		return val
	
	def packnone(self, val):
		return NSAppleEventDescriptor.nullDescriptor()
	
	def packbool(self, val):
		return NSAppleEventDescriptor.descriptorWithBoolean_(int(val))
	
	def packint(self, val):
		if (-2**31) <= val < (2**31):
			return NSAppleEventDescriptor.descriptorWithInt32_(val)
		else:
			return self.pack(float(val))
	
	def packfloat(self, val):
		return self._packbytes(kae.typeFloat, struct.pack('d', val))
	
	def packbytes(self, val):
		return self._packbytes(kae.typeData, val)
	
	def packstr(self, val):
		return NSAppleEventDescriptor.descriptorWithString_(val)
	
	def packdatetime(self, val):
		delta = val - self.kMacEpoch
		sec = delta.days * 3600 * 24 + delta.seconds
		return self._packbytes(kae.typeLongDateTime, struct.pack('q', sec))
	
	def packlist(self, val):
		lst = NSAppleEventDescriptor.listDescriptor()
		for item in val:
			lst.insertDescriptor_atIndex_(self.pack(item), 0)
		return lst
	
	def packdict(self, val):
		record = NSAppleEventDescriptor.recordDescriptor()
		usrf = desctype = None
		for key, value in val.items():
			if isinstance(key, AEType):
				if key.code == kae.pClass and isinstance(value, AEType): # AS packs records that contain a 'class' property by coercing the packed record to the descriptor type specified by the property's value (assuming it's an AEType)
					desctype = value
				else:
					record.setDescriptor_forKeyword_(self.pack(value), fourcharcode(key.code))
			else:
				if not usrf:
					usrf = NSAppleEventDescriptor.listDescriptor()
				usrf.insertDescriptor_atIndex_(self.pack(key), 0)
				usrf.insertDescriptor_atIndex_(self.pack(value), 0)
		if usrf:
			record.setDescriptor_forKeyword_(usrf, self.kUSRF)
		if desctype:
			newrecord = record.coerceToDescriptorType_(fourcharcode(desctype.code))
			if newrecord:
				record = newrecord
			else: # coercion failed for some reason, so pack as normal key-value pair
				record.setDescriptor_forKeyword_(self.pack(desctype), fourcharcode(key.code))
		return record
	
	def packtype(self, val):
		return NSAppleEventDescriptor.descriptorWithTypeCode_(fourcharcode(val.code))
	
	def packenum(self, val): 
		return NSAppleEventDescriptor.descriptorWithEnumCode_(fourcharcode(val.code))
	
	#######
	
	def unpacknull(self, desc):
		return None
	
	def unpackboolean(self, desc):
		return desc.booleanValue()
	
	def unpacksint32(self, desc):
		return desc.int32Value()
	
	def unpackfloat64(self, desc):
		return struct.unpack('d', bytes(desc.data()))[0]
	
	def unpackunicodetext(self, desc):
		return desc.stringValue()
	
	def unpacklongdatetime(self, desc):
		return self.kMacEpoch + datetime.timedelta(seconds=struct.unpack('q', bytes(desc.data()))[0])
	
	def unpackaelist(self, desc):
		return [self.unpack(desc.descriptorAtIndex_(i + 1)) for i in range(desc.numberOfItems())]
	
	def unpackaerecord(self, desc):
		dct = {}
		for i in range(desc.numberOfItems()):
			key = desc.keywordForDescriptorAtIndex_(i + 1)
			value = desc.descriptorForKeyword_(key)
			if key == self.kUSRF:
				lst = self.unpackaelist(value)
				for i in range(0, len(lst), 2):
					dct[lst[i]] = lst[i+1]
			else:
				dct[AEType(struct.pack('>I', key))] = self.unpack(value)
		return dct
	
	def unpacktype(self, desc):
		return AEType(struct.pack('>I', desc.typeCodeValue()))
	
	def unpackenumeration(self, desc):
		return AEEnum(struct.pack('>I', desc.enumCodeValue()))
	
	def unpackfile(self, desc):
		url = bytes(desc.coerceToDescriptorType_(fourcharcode(kae.typeFileURL)).data()).decode('utf8')
		return NSURL.URLWithString_(url).path()


#######


class AETypeBase:
	""" Base class for AEType and AEEnum.
	
		Notes:
		
		- Hashable and comparable, so may be used as keys in dictionaries that map to AE records.
	"""
	
	def __init__(self, code):
		"""
			code : bytes -- four-char code, e.g. b'utxt'
		"""
		if not isinstance(code, bytes):
			raise TypeError('invalid code (not a bytes object): {!r}'.format(code))
		elif len(code) != 4:
			raise ValueError('invalid code (not four bytes long): {!r}'.format(code))
		self._code = code
	
	code = property(lambda self:self._code, doc="bytes -- four-char code, e.g. b'utxt'")
	
	def __hash__(self): 
		return hash(self._code)
	
	def __eq__(self, val):
		return val.__class__ == self.__class__ and val.code == self._code
	
	def __ne__(self, val):
		return not self == val
		
	def __repr__(self):
		return "{}({!r})".format(self.__class__.__name__, self._code)


##


class AEType(AETypeBase):
	"""An AE type. Maps to an AppleScript type class, e.g. AEType(b'utxt') <=> 'unicode text'."""


class AEEnum(AETypeBase):
	"""An AE enumeration. Maps to an AppleScript constant, e.g. AEEnum(b'yes ') <=> 'yes'."""

