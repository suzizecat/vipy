import typing as T
from .register import Register
from .access import Access


class ShadowGroup:

	TRIGGER_FIRST = 0
	TRIGGER_LAST = -1

	def __init__(self, name, trigger_position = TRIGGER_FIRST):
		"""
		This class represent a group of shadow registers
		Those registers are indirectly accessed, through a cache that shall be updated when reading/writing on a trigger.
		"""
		self.name = name

		self.included_registers : T.List[Register] = list()
		self.trigger_position = trigger_position

	def __len__(self) -> int:
		return len(self.included_registers)

	def __iter__(self):
		return self.included_registers.__iter__()

	@property
	def trigger(self) -> Register:
		"""Return the trigger used for the shadow cache update"""
		return self.included_registers[self.trigger_position]

	def add_register(self, reg : Register):
		"""
		Add a new register to the group, the register list is kept sorted
		:param reg: Register to add
		"""
		if reg not in self:
			self.included_registers.append(reg)
			self.included_registers.sort()

	def __contains__(self, item):
		if isinstance(item,str) :
			return item in [r.name for r in self]
		elif isinstance(item,Register) :
			return item.name in self
		else:
			raise TypeError(f"Unsupported type {type(item).__name__}")

	@property
	def included_accesses(self) -> T.List[Access]:
		"""
		:return: a list of all unique accesses in included registers,
		"""
		ret = set()
		for r in self :
			ret.update([f.access for f in r if f.access.is_shadow])
		return list(ret)

	def get_register_position(self, reg : T.Union[Register,str]) -> int :
		"""
		:param reg: Register to lookup
		:return: Position of the register
		"""
		if isinstance(reg,Register):
			return self.get_register_position(reg.name)
		pos = 0
		for r in self :
			if r.name == reg :
				return pos
			else :
				pos += 1
		raise KeyError(f"Register {reg} not found in shadow group {self.name}")