from dataclasses import dataclass
from cocotb.handle import ModifiableObject
from cocotb.triggers import *
from vipy.structure import GenericDriver, GlobalEnv, drive_method


class SignalDriver(GenericDriver):

	@dataclass
	class Interface:
		sig : ModifiableObject

	def __init__(self,net : ModifiableObject, reset_state = 0):
		super().__init__()

		self.reset_state = reset_state

		self.itf = SignalDriver.Interface(net)

		self.register_itf_as_driven()

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