from dataclasses import dataclass
from cocotb.handle import ModifiableObject
from cocotb.triggers import *
from cocotb.clock import *
from cocotb import *
from vipyhdl.structure import GenericDriver, GlobalEnv, drive_method

import typing as T

class ClockDriver(GenericDriver):
	@dataclass
	class Interface:
		clock: ModifiableObject

	def __init__(self, clock_net: ModifiableObject, idle = 0, period : T.Tuple[int,str] = (1,"ns")):
		super().__init__()

		self.itf = ClockDriver.Interface(clock_net)
		self.idle_state = idle
		self._clk_process : Task = None
		self.register_itf_as_driven()
		self.period = get_sim_steps(*period)

	@drive_method
	async def stop(self, gracefully=True):
		if self._clk_process is None :
			return

		self._log.llow(f"Stopping clock")
		if gracefully :
			await FallingEdge(self.itf.clock) if self.idle_state == 0 else RisingEdge(self.itf.clock)
			await Timer(self.period // 2)
		self._clk_process.kill()
		self.itf.clock.value = 0

	@drive_method
	async def start(self, period : T.Tuple[int,str] = None):
		self._log.llow(f"Starting clock")
		await self.stop(gracefully=False)
		if period is not None :
			self.period = get_sim_steps(*period)
		self._clk_process = await cocotb.start(Clock(self.itf.clock,self.period).start())
		self._log.llow(f"Clock started")

	@drive_method
	async def reset(self):
		self._log.llow(f"Reset command")
		await self.stop(gracefully=False)
		self.itf.clock.value = 0
		self._log.llow(f"Reset done")

	

