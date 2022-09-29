from dataclasses import dataclass
from cocotb.handle import ModifiableObject
from cocotb.triggers import *
from cocotb.clock import *
from cocotb import *
from vipy.structure import GenericDriver, GlobalEnv


class ClockDriver(GenericDriver):
	@dataclass
	class Interface:
		clock: ModifiableObject

	def __init__(self, clock_net: ModifiableObject):
		super().__init__()

		self.itf = ClockDriver.Interface(clock_net)

		self._clk_process : Task = None
		self.register_itf_as_driven()

	@GenericDriver.drive_method
	async def stop(self, gracefully=True):
		if self._clk_process is None :
			return

		self._log.info(f"{self.name} - Stopping clock")
		if gracefully :
			await FallingEdge(self.itf.clock)
		self._clk_process.kill()
		self.itf.clock.value = 0

	@GenericDriver.drive_method
	async def start(self, period : int = 1,unit: str = "ns"):
		self._log.info(f"{self.name} - Starting clock")
		await self.stop(gracefully=False)
		self._clk_process = await cocotb.start(Clock(self.itf.clock,period,unit).start())
		self._log.info(f"{self.name} - Clock started")

	@GenericDriver.drive_method
	async def reset(self):
		self._log.info(f"{self.name} - Reset command")
		await self.stop(gracefully=False)
		self.itf.clock.value = 0
		self._log.info(f"{self.name} - Reset done")

