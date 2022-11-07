import re
import typing as T
from vipy.regbank.structure.access import Access
from vipy.regbank.structure.access import access_mapping


class FieldSize:
	_RE_PAT = re.compile(r"\[?\s*(\d+)\s*:\s*(\d+)\s*\]?")

	@classmethod
	def from_specifier(cls,spec : str):
		"""
		Generate a field size object based upon a size specifier.
		:param spec: The specifier. Format is either:
		<ul>
			<li> a single number (providing a single-bit field with the provided value as offset.</li>
			<li>
				a ``x:y`` expression that may be surrounded by square brackets, providing a field with the lowest
				value as offset and the highest value as end of the field.
			</li>
		</ul>

		:return: A fully initialized field size specifier object.
		"""
		ret = cls()
		find = FieldSize._RE_PAT.search(spec)
		if find is None :
			ret.offset = int(spec)
		else :
			(ret.offset,ret.end) = sorted([int(x) for x in find.groups()])
		return ret

	def __init__(self, offset : int = 0, length : int = 1):
		"""
		This class is an helper to manipulate field sizes and values.
		It specifies a field length and offset, thus representing is memory placement.
		"""

		"""First (lowest) bit in the word to be used by the field."""
		self.offset = offset

		"""Number of bits to be included in the field."""
		self.length = length

	@property
	def end(self) -> int:
		"""
		:return: Last (highest) bit position being included in the field.
		For a field of length = 1, end == offset.
		"""
		return self.offset + self.length - 1

	@end.setter
	def end(self,value : int) -> None:
		"""
		Set the length of the field to match the desired end value.
		The offset is left unchanged.

		If the end is lower than the offset, an error is raised.
		:param value: Position to set the end of the field to. Must be superior or equal to the field offset.
		:raises ValueError: The provided value is lower than the offset.
		"""
		length = 1 + value - self.offset
		if length < 1 :
			raise ValueError(f"Impossible to set an end value {value} inferior to the field offset {self.offset}.")
		else :
			self.length = length

	@property
	def next(self) -> int:
		"""
		:return: The next (high) bit available for use after the current field.
		The value will be <code>self.end +1</code>
		"""
		return self.offset + self.length

	@property
	def mask(self) -> int :
		"""
		Generate and return the mask matching the specified size only (not the offset)::

			field = FieldSize(offset=4, length=2).mask
			field.mask
			# 0x3

		:return: A binary mask long enough for the hold value. This mask is not aligned with regard to the offset.
		"""
		return (2**self.length) - 1

	@property
	def placed_mask(self) -> int:
		"""
		Generate and return the mask matching the specified size and offset::

			field = FieldSize(offset=4, length=2)
			field.placed_mask
			# 0x30

		:return: The binary mask matching the specified size (in length and aligned on the offset).
		:seealso: map_placed_value
		"""
		return  self.mask << self.offset

	def place_value(self,val : int) -> int:
		"""
		Map the provided value to the field offset and mask.
		Any overflowing bit will be truncated::

			field = FieldSize(offset=4, length=2)
			field.place_value(0xF)
			# 0x30

		:param val: Value to place, not shifted.
		:return: Placed and truncated value
		"""
		return (val & self.mask) << self.offset

	def map_placed_value(self, val : int) -> int:
		"""
		Map the provided value to the field, taking into account the offset and the mask.
		An example of use is::

			field = FieldSize(offset=4, length=2)
			field.map_placed_value(0xF0)
			# 0x3

		:param val: Value to map. Provided as if it was a register assignation.
		:return: Value affected to the field, derived from the register assignation.
		"""
		return (val & self.placed_mask) >> self.offset


class Field:
	def __init__(self,name : str, size : T.Union[str,FieldSize], access : str = "RW"):
		"""
		Describes a register field with its name, size, access specifier and value.

		:param name: Field name.
		:param size: Field size specifier.
		:param access: Access specifier

		:raises ValueError: if the size specifier, passed as a string, is invalid.
		"""

		"""Field name, should be a valid identifier for further implementation, but no filtering here"""
		self.name : str = name

		"""Field size specifier. Should be a valid FieldSize object or a valid size specifier."""
		self.size : FieldSize = size  if isinstance(size,FieldSize) else FieldSize.from_specifier(size)

		"""Access specifier"""
		self.access : Access = access_mapping[access]

		"""Held value, should be changed through accessors"""
		self._value = 0

	def __len__(self):
		"""
		:return: The amount of bits used by the field.
		"""
		return self.size.length

	@property
	def value(self) -> int:
		"""
		:return: The held value. It assumes that the mask matching is already done.
		"""
		return self._value

	@value.setter
	def value(self,val : int):
		"""
		Set the field value. The provided new value is truncated to fit the mask,
		but it is assumes that the LSB matches the field LSB.
		:param val: Value to set the field to.
		"""
		self._value = val & self.size.mask

	@property
	def placed_value(self) -> int:
		"""
		:return: The held value, shifted by the offset.
		"""
		return self._value << self.size.offset

	@placed_value.setter
	def placed_value(self, value : int):
		"""
		Bind the provided value to the field, taking into account the offset and the mask.

		:param value: Value to bind
		"""
		self._value = self.size.map_placed_value(value)

	def apply_simulated_value_to(self, field_value, register_value) -> int :
		"""
		Apply a given "field" value (without offset) to a "register" value as if the current field was in the register and
		was affected the field_value::

			field = Field(foo,"7:4")
			field.apply_simulated_value_to(0x3,0xFFF)
			# 0xF3F

		This function doesn't change the value held by the field.
		:param field_value: Value to simulate
		:param register_value: Value to apply the simulated value to.
		:return: Modified "register" value
		"""
		ret = register_value & ~self.size.placed_mask
		return ret | self.size.place_value(field_value)

	def apply_value_to(self, register_value):
		"""
		Apply the held value to the "register" value, as if the field was in a register holding the "register" value.
		No change are applied to any value.

			field = Field(foo,"7:4")
			field.value = 0x3
			field.apply_value_to(0xFFF)
			# 0xF3F

		:param register_value: Reference value to apply the field value onto.
		:return: Changed register value.
		"""
		return self.apply_simulated_value_to(self._value, register_value)
