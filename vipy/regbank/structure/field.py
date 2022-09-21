import re
from .access import Access
from .access import access_mapping

class FieldSize:
	RE_PAT = re.compile(r"\[?\s*(\d+)\s*:\s*(\d+)\s*\]?")

	@classmethod
	def from_specifier(cls,spec : str):
		ret = cls()
		find = FieldSize.RE_PAT.search(spec)
		if find is None :
			ret.offset = int(spec)
		else :
			(ret.offset,ret.end) = sorted([int(x) for x in find.groups()])
		return ret

	def __init__(self):
		self.offset = 0
		self.length = 1

	@property
	def end(self):
		return self.offset + self.length - 1

	@end.setter
	def end(self,value):
		self.length = 1 + value - self.offset

	@property
	def next(self):
		return self.offset + self.length

	@property
	def mask(self):
		return (2**self.length) - 1

	@property
	def int_mask(self):
		return  self.mask << self.offset

	def map_int(self,val):
		return (val & self.int_mask) >> self.offset


class Field:
	def __init__(self,name : str, size : FieldSize, access : str = "RW"):
		self.name = name
		self.size = size

		self.access = access_mapping[access]

		self._value = 0

	def __len__(self):
		return self.size.length

	@property
	def value(self):
		return self._value

	@value.setter
	def value(self,value):
		self._value = value & self.size.mask

	@property
	def int_value(self):
		return self._value << self.size.offset

	@int_value.setter
	def int_value(self,value):
		self._value = self.size.map_int(value)

	def apply_value_to(self,fieldval,origine):
		ret = origine & ~self.size.mask

		return ret | (fieldval & self.size.mask) << self.size.offset