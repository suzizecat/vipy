from .register import Register
from .field import Field

import typing as T


class RegisterBank:
	def __init__(self,prefix : str, addr_width:int):
		self._registers : dict[str,Register] = dict()

		self._addr_map : dict[int,Register] = dict()
		self.address_width = addr_width
		self.prefix = prefix

	def add_register(self, reg : Register):
		self._registers[reg.name] = reg
		self._addr_map[reg.offset] = reg

	def get_address(self,regname):
		return self[regname].offset

	def get_register(self, target) :
		if target not in self :
			return None
		if isinstance(target, Register) :
			target = target.name
		elif isinstance(target,int) :
			return self[target]

		target = target.split(".")[0]
		return self[target]

	def reset(self):
		for r in self :
			r.reset()

	def __contains__(self, item):
		if isinstance(item,int) :
			return item in self._addr_map
		if isinstance(item,str) :
			try :
				t = self[item]
			except KeyError :
				return False
			else :
				return True
		else :
			return item in self._registers.values()

	def __iter__(self):
		return self._registers.values().__iter__()

	def __getitem__(self, item:T.Union[str,int]):
		if isinstance(item,int) :
			return self._addr_map[item]

		if item.strip() == "" :
			return self
		path = item.split(".")
		return self._registers[path[0]][".".join(path[1:]) if len(path) > 1 else ""]

