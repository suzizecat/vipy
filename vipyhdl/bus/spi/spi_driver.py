import typing as T

import cocotb
from cocotb import Task
from cocotb.clock import Clock

from cocotb.utils import get_time_from_sim_steps
from cocotb.triggers import *

from vipy.bus.base.serial import BaseSerial, SerialMode
from .spi_base import SPIBase, SPIInterface
import enum

from ..base.word import DataWord
from ...utils.queue import QueueEvt

from vipy.structure import *
from vipy.drivers import *

class SPIDriver(SPIBase, GenericDriver):
	def __init__(self, mode : SerialMode, itf : SPIInterface, clk_period : T.Tuple[int,str] = (1,"us")):
		SPIBase.__init__(self,mode)
		GenericDriver.__init__(self)
		self.itf = itf
		self.to_send : QueueEvt[DataWord] = QueueEvt()
		self.clk_period = clk_period
		self.csn_pulse_per_word = True
		self.csn_pulse_duration = clk_period
		self._current_data = DataWord(0)
		self._current_data.content.clear()

		self.clock = ClockDriver(self.itf.clk,idle=self.clk_idle)

		self._drive_process : Task = None
		self.start_csn_evt_handling()

		self.is_idle = Event()
		self.is_idle.set()

		self.register_remaining_signals_as_driven()
		self.unregister_signal_as_driven(self.itf.miso)

	@drive_method
	async def drive_csn(self, state : bool, pulse_period : T.Tuple[int,str] = None):
		expected_state = 1 if state else 0
		if self.itf.csn.value.integer != expected_state :
			self.itf.csn.value = expected_state
			if pulse_period is not None :
				await Timer(*pulse_period)
				self.itf.csn.value = 1-expected_state
			await NextTimeStep()
		else :
			await NextTimeStep()

	@drive_method
	async def reset(self):
		await self.reset_drivers()
		if self._drive_process is not None :
			self._drive_process.kill()
		self._drive_process = cocotb.start_soon(self.enable_sending())
		await self.drive_csn(True)

	@cocotb.coroutine
	async def enable_sending(self):
		need_clk_resume = False
		first_frame_bit = False
		while True:
			if len(self._current_data) == 0 :
				if self.to_send.empty():
					await self.clock.stop(gracefully=True)
					await Timer(self.clock.period)
					await self.drive_csn(True)
					need_clk_resume = True
					self.is_idle.set()
				self._current_data = await self.to_send.get()
				self.is_idle.clear()

				if need_clk_resume :
					await self.drive_csn(False)
					await self.clock.start(self.clk_period)
					need_clk_resume = False
					first_frame_bit = True

			for bit in self._current_data :
				if self._pha == 1 or not first_frame_bit :
					await self.drive_edge
				else :
					first_frame_bit = False
				self.tx_pin.value = bit

			await self.capture_edge

			if self.csn_pulse_per_word :
				await self.clock.stop(gracefully=True)
				await self.drive_csn(True)
				await Timer(*self.csn_pulse_duration)
				await self.drive_csn(False)
				await self.clock.start(*self.clk_period)

			self.evt.word_done.set()
			await NextTimeStep()






