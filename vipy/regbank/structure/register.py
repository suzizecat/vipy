from .field import Field
from copy import copy


class Register:
	DEFAULT_SIZE = 32

	def __init__(self, name : str, offset : int, reg_size : int = None, reset_value = 0):
		"""
		This class represent an RTL register with its name, offset, size, reset value and the list of its fields.

		:param name: Name of the register. While its value is not important here, it is recommended to use a valid identifier.
		:param offset: Offset (address) of the register in its register bank.
		:param reg_size: Number of bits that can be held by the register. Cannot be changed after initialization.
		:param reset_value: Value at hard reset, default to 0.
		"""

		self.offset : int = offset
		self.reset_value : int = reset_value

		"""Register name. Should be valid identifier"""
		self.name : str = name

		"""Register size, default to REGISTER.DEFAULT_SIZE. Cannot be changed after initialization."""
		self._size = reg_size if reg_size is not None else copy(Register.DEFAULT_SIZE)

		"""List of fields, referenced by field name"""
		self.fields : dict[str,Field] = dict()

	def __len__(self) -> int :
		"""Register size"""
		return self._size

	def add_field(self, field : Field):
		"""
		Add the given field to the current register
		:param field: Field to add
		"""
		prev_mask = self.used_mask
		# New field mask should only cover "0" in the register used mask, so OR and XOR should yield the same values.
		union_mask = prev_mask | field.size.placed_mask
		inter_mask = prev_mask ^ field.size.placed_mask

		if union_mask != inter_mask :
			raise ValueError(f"Trying to add a conflicting field {field!r}. Overlapping bits are : 0b{union_mask^inter_mask:0{len(self):d}b}")
		if field.size.end >= len(self) :
			raise ValueError(f"Trying to add a field {field!r} which doesn't fit the register {self.name}. Register size is {self._size}")
		self.fields[field.name] = field

	def __getitem__(self, item:str):
		"""Get a field by its name/path"""
		if item.strip() == "" :
			return self
		path = item.split(".")
		return self.fields[path[0]]

	def __iter__(self):
		"""Iter through all the stored fields"""
		return self.fields.values().__iter__()

	def reset(self):
		"""Apply the register reset value to all the fields"""
		self.value = self.reset_value

	@property
	def used_mask(self):
		"""
		:return: The mask matching the union of all placed mask of the fields of the register
		"""
		ret = 0
		for f in self :
			ret |= f.size.placed_mask
		return ret

	@property
	def value(self):
		""":return: The value of the register, computed from the value of each of its fields"""
		ret = 0
		for f in self :
			ret += f.placed_value
		return ret

	@value.setter
	def value(self, val : int):
		"""
		Set the value to the register to the given value by setting the value of all of its field.
		Therefore, it is possible for the following assertion to fail::

			myregister.value = new_value
			assert myregister.value == new_value , "Might fail if the register is not full."
			assert myergister.value == (new_value & myregister.used_mask) , "This should not fail"

		:param val: Value to assign the register to.
		"""
		for f in self :
			f.placed_value = val

	@property
	def mask(self):
		"""
		:return: The mask of the maximum value that might be held by the register when its full.
		When the register is full, mask == used_mask.
		"""
		return (2**self._size) - 1

	@property
	def is_full(self):
		""":return: True if all potential bits of the register are actually covered by a field."""
		return self.mask == self.used_mask

	def write_value(self, value):
		"""
		Set the register to the provided value, takind into account the access type of the register.
		:param value: Value to set the register to.
		"""
		for f in self :
			if f.access.is_writable_by_itf :
				f.placed_value = value
