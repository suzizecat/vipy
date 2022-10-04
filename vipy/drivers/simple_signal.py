from dataclasses import dataclass
from cocotb.handle import ModifiableObject
from cocotb.triggers import *
from vipy.structure import GenericDriver, GlobalEnv, drive_method


class SignalDriver(GenericDriver):

	@dataclass
	class Interface:
		sig : ModifiableObject

	def __init__(self,net : ModifiableObject, active_state = 1):
		super().__init__()

		self.active_state = active_state

		self.itf = SignalDriver.Interface(net)

		self.register_itf_as_driven()

	@drive_method
	async def reset(self):
		self._log.llow(f"Reset command")
		self.itf.sig.value = self.active_state

	@drive_method
	async def set(self,value):
		self.itf.sig.value = value