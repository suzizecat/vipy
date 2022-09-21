from .field import Field
from copy import copy


class Register:
	DEFAULT_SIZE = 32

	def __init__(self, name : str, offset : int, reg_size : int = None):
		self.name = name
		self.offset = offset

		self._size = reg_size if reg_size is not None else copy(Register.DEFAULT_SIZE)

		self.fields : dict[str,Field] = dict()

	def __len__(self):
		return self._size

	def add_field(self, field : Field):
		self.fields[field.name] = field

	def __getitem__(self, item:str):
		if item.strip() == "" :
			return self
		path = item.split(".")
		return self.fields[path[0]]

	def __iter__(self):
		return self.fields.values().__iter__()

	@property
	def value(self):
		ret = 0
		for f in self :
			ret += f.int_value
		return ret

	@value.setter
	def value(self, val):
		for f in self :
			f.int_value = val

	@property
	def mask(self):
		return (2**self._size) - 1