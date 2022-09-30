from dataclasses import dataclass
from cocotb.handle import ModifiableObject
from cocotb.triggers import *
from vipy.structure import GenericDriver, GlobalEnv, drive_method


class ResetDriver(GenericDriver):

	@dataclass
	class Interface:
		reset : ModifiableObject

	def __init__(self,reset_net : ModifiableObject, active_state = 0):
		super().__init__()

		self.active_state = active_state

		self.itf = ResetDriver.Interface(reset_net)

		self.register_itf_as_driven()

	@drive_method
	async def reset(self):
		self._log.info(f"{self.name} - Reset command")
		self.itf.reset.value = self.active_state
		await Timer(10,"ns")
		self.itf.reset.value = 1-self.active_state
