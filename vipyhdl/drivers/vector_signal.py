from dataclasses import dataclass
from cocotb.handle import ModifiableObject
from cocotb.triggers import *
from vipyhdl.structure import GenericDriver, GlobalEnv, drive_method
from vipyhdl.utils.workarounds import *
import typing as T
from cocotb.binary import BinaryValue
from cocotb.utils import *


class VectorDriver(GenericDriver):
	@dataclass
	class Interface:
		sig : ModifiableObject

	def __init__(self,net : ModifiableObject,dim : T.List[int], reset_state : T.List[int] = None, read_only = False,signed=False):
		super().__init__()

		if reset_state is None :
			reset_state = list()
		self.reset_state = [reset_state[t] if t < len(reset_state) else 0 for t in range(dim[0])]

		self.itf = VectorDriver.Interface(net)
		self.dim = dim
		self._is_cocotb_handled = hasattr(self.itf.sig,"__iter__")
		self.register_itf_as_driven()

		self.signed = signed

		self._cached_value = self.reset_state
		self._last_updated = -1
		self._user_active = not read_only

	async def reset(self):
		self._log.llow(f"Reset command")
		self.value = self.reset_state

	async def set(self,value):
		self.value = value

	@property
	def value(self):
		if self._is_cocotb_handled :
			return self.itf.sig.value
		else :
			self._update_cache()
			return [BinaryValue(x) for x in self._cached_value]

	@value.setter
	def value(self,val : T.Union[int,BinaryValue,T.List[int]]):
		self._update_cache()
		if isinstance(val,(int,BinaryValue)) :
			self._cached_value = int_to_vector(int(val),self.dim)
		elif isinstance(val,list) :
			if len(val) > len(self._cached_value) :
				self._log.warning(f"Value overflow. Got a list of {len(val)} values while expecting a maximum of {len(self._cached_value)}.\nResults might be unexpected.")

			for i in range(len(val)):
				if i >= self.dim[0]:
					break
				else:
					self._cached_value[i] = val[i]
		self._write_output(vector_to_int(self._cached_value,self.dim[-1]))

	def _update_cache(self):
		new_time = get_sim_time()
		if new_time != self._last_updated :
			self._cached_value = self._cached_value = int_to_vector(int(self.itf.sig.value),self.dim,self.signed)
			self._last_updated = new_time

	def _write_cache_to_output(self):
		self.value = self._cached_value

	def _write_output(self,value):
		if self.is_active :
			self.itf.sig.value = value

	def __getitem__(self, item : int):
		self._update_cache()
		return BinaryValue(self._cached_value[item])

	def __setitem__(self, item : int,value):
		self._update_cache()

		self._cached_value[item] = int(value)
		self._write_cache_to_output()

	def __iter__(self):
		self._update_cache()
		return self._cached_value.__iter__()

	def __len__(self):
		return self.dim[0]