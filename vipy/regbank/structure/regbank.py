from .register import Register
from .field import Field


class RegisterBank:
	def __init__(self,prefix : str, addr_width:int):
		self.registers : dict[str,Register] = dict()

		self.address_width = addr_width
		self.prefix = prefix

	def add_register(self, reg : Register):
		self.registers[reg.name] = reg

	def get_address(self,regname):
		return self[regname].offset

	def get_register(self, name) :
		target = name.split(".")[0]
		return self[target]

	def __getitem__(self, item:str):
		if item.strip() == "" :
			return self
		path = item.split(".")
		return self.registers[path[0]][".".join(path[1:]) if len(path) > 1 else ""]

