import logging
from math import ceil

from .register import Register
from .shadow_register_group import ShadowGroup
from .field import Field

import typing as T


class RegbankFieldsIterator:
	def __init__(self, register_bank : "RegisterBank"):
		self.rb = register_bank
		self.iter = None

	def __iter__(self) -> T.Iterable[Field]:
		self.iter = list()
		for reg in self.rb :
			self.iter.extend([f for f in reg])

		return self.iter.__iter__()

class RegisterBank:
	def __init__(self, prefix: str, addr_width: int, data_width : int = 32):
		"""
		This class represent a register bank and hold all the registers, a name and some interface details.
		:param prefix: The "name" of the register bank
		:param addr_width: The width of the address bus, in bits
		"""

		"""Registers, indexed by name"""
		self._registers : dict[str,Register] = dict()

		"""Registers, indexed by offset"""
		self._addr_map : dict[int,Register] = dict()

		self.clk_name = "i_clk"
		self.rst_name = "i_rst_n"
		self.itf_wr_name = "sif_reg_wrchan"
		self.itf_rd_name = "sif_reg_rdchan"
		self.itf_wr_mask = f"{self.itf_wr_name}.bmask"
		self.itf_wr_data = f"{self.itf_wr_name}.data"
		self.itf_wr_addr = f"{self.itf_wr_name}.addr"
		self.itf_wr_req = f"{self.itf_wr_name}.write"
		self.itf_rd_data = f"{self.itf_rd_name}.data"
		self.itf_rd_addr = f"{self.itf_rd_name}.addr"
		self.itf_rd_valid = f"{self.itf_rd_name}.valid"
		self.itf_rd_req = f"{self.itf_rd_name}.read"
		self.itf_input_type = f"{prefix}_regbank_in_if"
		self.itf_output_type = f"{prefix}_regbank_out_if"
		self.itf_input = f"sif_regbank_in"
		self.itf_output = f"sif_regbank_out"

		self.address_width = addr_width
		self.data_width = data_width
		self.prefix = prefix

		self.shadow_groups : T.Dict[str,ShadowGroup] = dict()

		self.multireg_addr_offset = data_width // 8

	def add_register(self, reg : Register):
		"""Add a register to the register bank"""
		if reg.name in self._registers:
			raise ValueError(f"Register name {reg.name} is already used in the {self.prefix} register bank.")
		if reg.offset in self._addr_map:
			raise ValueError(f"Register offset {reg.offset} of {reg.name} is already used in the {self.prefix} register bank.")

		self._registers[reg.name] = reg
		self._addr_map[reg.offset] = reg

	def add_shadow_group(self,group : T.Union[str,ShadowGroup]) -> ShadowGroup:
		"""
		Create a shadow group with the provided name if it doesn't exists.
		:param group: Group or name of the shadow group to create
		:return: The created or existing shadow group if `group` is a string. The passed group otherwise.
		:raises KeyError: If group is a ShadowGroup and there is already a shadow group with that name.
		"""
		if isinstance(group,str) :
			if group not in self.shadow_groups:
				self.shadow_groups[group] = ShadowGroup(group)
			return self.shadow_groups[group]
		elif isinstance(group,ShadowGroup):
			if group.name not in self.shadow_groups :
				self.shadow_groups[group.name] = group
				return group
			else :
				raise KeyError(f"There is already a group named {group.name}. Try using a string to retrieve the existing group")

	def delete_register(self,reg : T.Union[int,str,Register]) -> Register:
		"""
		Properly delete a register from the register bank and return it
		:param reg: Register, register name or register offset to delete.
		:return: The removed register
		:raises KeyError: if the provided register does not match anything in the regbank.
		"""
		found_reg = self.get_register(reg)
		if found_reg is None :
			raise KeyError(f"Register {reg!r} not found")
		self._addr_map.pop(found_reg.offset)
		return self._registers.pop(found_reg.name)

	def rename_register(self,reg : T.Union[int,str,Register], new_name : str):
		"""
		This function rename a register
		:param reg: Register to rename
		:param new_name: New name to provide
		"""
		rb_register = self.delete_register(reg)
		rb_register.name = new_name
		self.add_register(rb_register)

	def get_address(self, regname) -> int:
		"""
		:param regname: Name of the register to look for
		:return: address (offset) of the register
		:raises KeyError: if regname does not exists
		"""
		return self[regname].offset

	def get_register(self, target: T.Union[Register,str,int]) -> T.Union[None,Register]:
		"""
		Safely get a register object through its name (if a register or a string is passed as target) or its offset
		(if target is an int)
		:param target: Register object, register name as a string or register offset as an int.
		:return: The found register object, or None if nothing is found.
		"""
		if isinstance(target, Register) :
			target = target.name
		# Target has been converted to string if it was a register
		if isinstance(target,str) :
			# If we get a string, we want to potentially extract the register from a path
			target = target.split(".")[0]

		if target in self :
			return self[target]
		else :
			return None

	def flatten_all_multiregisters(self):
		"""
		Flatten all multiregisters.
		"""
		for register in [r for r in self if r.multireg.is_valid]:
			self.flatten_multiregister(register)

	def flatten_nontrivial_multiregisters(self):
		"""
		Select all 'non-trivial' multiregisters (registers with size specification
		in other place than the end of the name) and flatten them.
		"""
		for register in [r for r in self if r.multireg.is_valid and not r.multireg.is_simple]:
			self.flatten_multiregister(register)

	def flatten_multiregister(self,register : Register):
		"""
		Remove provided register if it is a multiregister and create all appropriate copy, unlinking fields in the process.
		:param register: Register to flatten
		"""
		to_add_list = list()

		if register.multireg.is_valid :
			new_offset = register.offset
			for name in [register.multireg.specialized_name(x) for x in register.multireg] :
				reg = Register(name,new_offset,register.size,register.reset_value)
				for f in register :
					nfield = Field(f.name,f.size,f.access.name,f.virtual)
					nfield.access_attributes = f.access_attributes
					reg.add_field(nfield)
				new_offset += self.multireg_addr_offset
				to_add_list.append(reg)

			self.delete_register(register)

			for new_reg in to_add_list :
				self.add_register(new_reg)


	def reset(self):
		"""This function call the "reset" of all included registers"""
		for r in self :
			r.reset()

	def write(self,register : T.Union[int,str,Register],value : int) -> int:
		"""
		Write a value to the given register, considering field accesses
		:param register: Register to write to
		:param value: Value to write
		:return: The expected read-back value. 0 if the register is not found.
		"""
		rb_reg : Register = self.get_register(register)
		if rb_reg is None :
			return 0
		else :
			rb_reg.write_value(value)
			return rb_reg.read_value

	def read(self,register : T.Union[int,str,Register]) -> int:
		"""
		Read the value of a given register
		:param register:
		:return:
		"""
		rb_reg : Register = self.get_register(register)

		if rb_reg is None :
			return 0
		else:
			return rb_reg.read_value

	def __contains__(self, item : T.Union[int,str,Register]) -> bool:
		"""
		Try to find a register in the register bank.
		If item is a register, the lookup will be done using the 'in' operator of the dictionary, rather than looking up
		the register name.
		:param item: Register object, register name as a string or register offset as an int.
		:return: True if match found. False otherwise
		"""
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

	def __iter__(self) -> T.Iterator[Register]:
		"""Iterator, use the dict iterator"""
		return self._registers.values().__iter__()

	def __getitem__(self, item:T.Union[str,int]):
		"""
		Get an item contained in the regbank using a register offset or an item path
		:param item: Register offset (int) or resource path, with item separated by dots such as MY_REGISTER.My_FIELD
		:return: If the item is an integer, return the register matching this offset. If it is a ressource path, return the
		item (Register, Field or other) that matches this path.
		:raises KeyError: if item does not match anything.
		"""
		if isinstance(item,int) :
			return self._addr_map[item]

		if item.strip() == "" :
			return self
		path = item.split(".")
		return self._registers[path[0]][".".join(path[1:]) if len(path) > 1 else ""]

	@property
	def fields(self):
		return RegbankFieldsIterator(self)

	def fill_registers(self):
		"""
		Fill all holes in all registers
		"""
		for register in self :
			print(f"Filling register {register.name}")
			register.fill()

	@property
	def as_report(self) -> str:
		"""
		:return: a report of the content of the register bank
		"""
		ret = ""
		ret += f"{'':#<80s}\n" \
		       f"#{self.prefix + ' register bank': ^78s}#\n" \
			   f"{'':#<80s}\n"
		for reg in self:
			addr = f"(0x{id(reg):X}) @ 0x{reg.offset:0{ceil(self.address_width/4)}X}"
			rname = f"Register {reg.name}"
			ret += f"{rname} {addr:.>{80-1-len(rname)}s}\n"
			for field in reg :
				descr = f"{field.access.name:10s} {str(field.size):7s}"
				fname = f"    field {field.name}"
				ret += f"{fname}{descr: >{70-len(fname)}s}\n"

		ret += f"{'':#<80s}\n" \
			   f"#{self.prefix + ' shadow groups': ^78s}#\n" \
			   f"{'':#<80s}\n"

		for shd_name, shd_grp in self.shadow_groups.items() :
			ret += f"Shadow group {shd_name}\n"
			for reg in shd_grp :
				field : Field
				rname = f"    {reg.name}"
				if reg is shd_grp.trigger :
					rname += " (TRIGGER)"
				addr = f"(0x{id(reg):X}) @ 0x{reg.offset:0{ceil(self.address_width / 4)}X}"
				ret += f"{rname} {addr:.>{80 - 1 - len(rname)}s}\n"
				for field in [f for f in sorted(reg) if f.access.is_shadow] :
					name = f"        {field.name}"
					access = field.access.name
					ret += f"{name}{access: >{55-len(name)}s}\n"
		ret += f"{'':#<80s}\n"
		return ret

