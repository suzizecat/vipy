from dataclasses import dataclass
from cocotb.handle import ModifiableObject
from cocotb.triggers import *
from vipy.structure import GenericDriver, GlobalEnv, drive_method
from vipy.utils.workarounds import *
import typing as T


class VectorDriver(GenericDriver):

	@dataclass
	class Interface:
		sig : ModifiableObject

	def __init__(self,net : ModifiableObject,dim : T.List[int], reset_state : T.List[int] = None):
		super().__init__()

		if reset_state is None :
			reset_state = list()
		self.reset_state = [reset_state[t] if t < len(reset_state) else 0 for t in range(dim[0])]

		self.itf = VectorDriver.Interface(net)
		self._is_cocotb_handled = hasattr(self.itf.sig,"__iter__")
		self.register_itf_as_driven()

		self._cached_value = list()


	@drive_method
	async def reset(self):
		self._log.llow(f"Reset command")
		self.itf.sig.value = self.reset_state

	@drive_method
	async def set(self,value):
		self.itf.sig.value = value

	@drive_method
	async def pulse(self,value, time = 1, unit = "step"):
		self.itf.sig.value = value
		await Timer(time,unit)
		self.itf.sig.value = self.reset_state