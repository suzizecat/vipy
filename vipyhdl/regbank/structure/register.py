import typing as T

from .field import Field
from .field import FieldSize
from .access import Access
from copy import copy
import re

class MultiRegSizeDescriptor:
	_pattern = re.compile(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]")
	_simple_name_pattern = re.compile(r"^\w+(?:\[\s*\d+\s*:\s*\d+\s*\])*$")
	def __init__(self, descriptor : str):
		"""
		This class provides convenience functions to handle (multidimentionals) arrays of registers.
		The format of the descriptor should contain size specification in the form of `[a:b]` with a != b.
		:param descriptor: String containing the size descriptor. Can contain other stuff, in example "my_reg[3:0]"
		is valid
		"""
		self.descriptor = descriptor

		self._indexes : T.List[int] = list()
		self._init_values : T.List[int]= list()
		self._end_values : T.List[int] = list()
		self._incr_values = list()
		self._valid = False
		self._is_simple = False
		self._last_iter_reached = False
		self._parse()

	def _parse(self):
		"""
		Parse the descriptor and extract relevant informations
		"""
		self._init_values.clear()
		self._last_iter_reached = False
		self._end_values.clear()
		self._incr_values.clear()

		self._is_simple = self._simple_name_pattern.fullmatch(self.descriptor) is not None

		parsed_output = MultiRegSizeDescriptor._pattern.findall(self.descriptor)
		self._valid = len(parsed_output) > 0

		if self._valid :
			self._init_values, self._end_values = zip(*[(int(x),int(y)) for x,y in parsed_output])

			for start, end in parsed_output :
				self._incr_values.append(1 if start < end else -1)

	def __iter__(self):
		self._indexes = list(self._init_values)
		self._last_iter_reached = False
		return self

	def __next__(self) -> T.Tuple[int,...]:
		"""
		Iterating through the size descriptor will return tuples of positions, incrementing the 'LSB' value.
		The increment might be negative if the starting value is higher than the end value.
		:return: Tuple of ints, one value per size descriptor.
		"""
		if self._last_iter_reached :
			raise StopIteration
		ret = tuple(self._indexes)
		for i in reversed(range(len(self._indexes))) :
			if self._indexes[i] != self._end_values[i] :
				self._indexes[i] += self._incr_values[i]
				return ret
			else :
				self._indexes[i] = self._init_values[i]
		self._last_iter_reached = True
		return ret

	def __len__(self):
		ret = 1
		for i in range(len(self._end_values)) :
			ret *= (abs(self._end_values[i] - self._init_values[i]))
		return ret

	def specialized_name(self,idx : T.Tuple[int]) -> str:
		output = self.descriptor
		for i in range(len(self._indexes)) :
			output = self._pattern.sub(str(idx[i]),output,count=1)

		return output

	@property
	def is_valid(self) -> bool:
		return self._valid

	@property
	def is_simple(self) -> bool:
		return self._is_simple

	@property
	def is_trivial_multi(self) -> bool:
		return self._is_simple and self.is_valid

	@property
	def base_descriptor(self) -> str:
		if self.is_valid :
			if self.is_simple :
				return self.descriptor[:self.descriptor.find("[")]
			else :
				raise ValueError(f"Base descriptor is invalid on complex descriptor '{self.descriptor}'")
		else :
			return self.descriptor

	@property
	def boundaries(self) -> T.List[T.Tuple[int,int]]:
		"""
		:return: Return the list of (init_value,end_value) tuples
		"""
		return list(zip(self._init_values,self._end_values))


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
		self._name : str = name

		"""Register size, default to REGISTER.DEFAULT_SIZE. Cannot be changed after initialization."""
		self._size = reg_size if reg_size is not None else copy(Register.DEFAULT_SIZE)

		"""List of fields, referenced by field name"""
		self.fields : dict[str,Field] = dict()

		"""Hold the index of the last reserved field, to generate unique names"""
		self._reserved_counter = 0

		self.multireg = MultiRegSizeDescriptor(self.name)

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

	def remove_field(self,field : T.Union[str,Field]) -> Field:
		"""
		Remove reference to an existing field from the register and return the removed field object
		:param field: Field to remove
		:return: the removed field
		"""
		if isinstance(field,Field) :
			self.remove_field(field.name)
		else :
			return self.fields.pop(field)

	def __contains__(self, item):
		"""Check whether a field is in the current register"""
		if isinstance(item,Field):
			return item.name in self
		elif isinstance(item,str):
			return item in self.fields
		else:
			raise TypeError(f"Unsupported type {type(item).__name__}")

	def __getitem__(self, item:str):
		"""Get a field by its name/path"""
		if item.strip() == "" :
			return self
		path = item.split(".")
		return self.fields[path[0]]

	def __repr__(self):
		"""
		:return: Representation of internal values through text
		"""
		ret = f"<Register {self.name} of size {self._size} @ 0x{self.offset:0X}>"
		for field in self :
			ret += f"\n    {field!r}"
		return ret

	def __iter__(self) -> T.Iterator[Field]:
		"""Iter through all the stored fields"""
		return self.fields.values().__iter__()

	def __gt__(self, other : "Register"):
		return self.offset > other.offset

	def reset(self):
		"""Apply the register reset value to all the fields"""
		self.value = self.reset_value

	@property
	def name(self) -> str:
		return self._name

	@name.setter
	def name(self,new_name : str):
		self._name = new_name
		if self.multireg is not None :
			self.multireg.descriptor = new_name
			self.multireg._parse()

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
	def read_value(self) -> int:
		"""
		:return: the register value as seen by a read access
		"""
		ret = 0
		for f in self :
			if f.access.is_readable_by_itf:
				ret += f.placed_value
		return ret

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
			if f.access.is_writable_by_itf:
				f.placed_value = value

	def rename_field(self, target_field : T.Union[Field, str], new_name):
		"""
		This function safely rename a given (by name or by object) field and its associations in the current register
		:param target_field: Field to update
		:param new_name: New name for the field
		"""
		if new_name in self.fields:
			raise ValueError(f"Trying to rename a field while the new name {new_name} is already used.")

		self.fields[new_name] = self.remove_field(target_field)
		self.fields[new_name].name = new_name

	@property
	def sorted_fields(self) -> T.List[Field]:
		"""
		:return: List of contained fields, sorted by offset.
		"""
		return sorted(self.fields.values(), key=lambda x: x.size.offset)

	@property
	def size(self) -> int:
		"""
		:return: The size of the register, same as len(self)
		"""
		return self._size

	def add_reserved_field(self,pos : FieldSize) -> Field:
		"""
		Generate and place a reserved field of the provided size
		:param pos: Position and size of the desired field
		:return: The created field
		"""
		reserved_name = f"RESERVED{self._reserved_counter}"
		while reserved_name in self.fields :
			self._reserved_counter += 1
			reserved_name = f"RESERVED{self._reserved_counter}"

		new_field = Field(reserved_name,pos,"RESERVED")
		self.add_field(new_field)
		self._reserved_counter += 1

		return new_field

	def fill(self) -> bool:
		"""
		Fill the register with RESERVED words
		:return: True if any filling has been added
		"""
		next_pos = 0
		reserved_positions = list()
		for field in sorted(self):

			if field.size.offset > next_pos :
				reserved_positions.append(FieldSize(next_pos,field.size.offset - next_pos))
			next_pos = field.size.next
		if next_pos < self._size :
			reserved_positions.append(FieldSize(next_pos, self._size - next_pos))

		for position in reserved_positions :
			print(f"    Add filling on {position!s}")
			self.add_reserved_field(position)

		return len(reserved_positions) > 0

	def prefix_fields_name(self,prefix : str = None):
		"""
		Add a prefix to the name of each field.
		:param prefix: Prefix to add, if nothing is provided, the register name will be used as a prefix
		"""
		if prefix is None :
			prefix = self.multireg.base_descriptor + "_"
		for field_name in [f.name for f in self.active_fields] :
			self.rename_field(field_name,f"{prefix}{field_name}")

	@property
	def active_fields(self) -> T.List[Field]:
		"""
		:return: Non-reserved fields
		"""
		return [f for f in self if f.access.name != "RESERVED"]

	def access_mask(self,access : T.Union[Access,str]) -> int:
		"""
		:param access: Access to lookup
		:return: a mask matching all fields with given access
		"""
		if isinstance(access,str) :
			return sum([f.size.placed_mask for f in self if f.access.name == access])
		else :
			return sum([f.size.placed_mask for f in self if f.access == access])
