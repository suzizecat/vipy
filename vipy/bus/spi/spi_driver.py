import typing as T
from copy import copy

import cocotb
from cocotb import RunningTask
from cocotb.binary import BinaryValue
from cocotb.clock import Clock

from  cocotb.handle import ModifiableObject
from cocotb.utils import get_time_from_sim_steps
from cocotb.triggers import FallingEdge, Timer, NextTimeStep

from vipy.bus.base.serial import BaseSerial, SerialMode
from .spi_base import SPIBase
import enum

from ..base.word import DataWord
from ...utils.queue import QueueEvt


class SPIDriver(SPIBase):
	def __init__(self, mode : SerialMode, itf : SPIBase.SPIInterface, clk_period : T.Tuple[int,str] = (1,"us")):
		super().__init__(mode)
		self.itf = itf
		self.to_send : QueueEvt[DataWord] = QueueEvt()
		self.csn_pulse_per_word = False
		self.csn_pulse_duration = clk_period
		self._current_data = DataWord(0)
		self._current_data.content.clear()

		self.clk_driver : Clock = Clock(self.itf.clk,*clk_period)
		self._clk_driver_process : RunningTask = None
		self._drive_process : RunningTask = None
		self.start_csn_evt_handling()

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

	async def drive_clock(self, period : T.Tuple[int,str] = None):
		if self._clk_driver_process is not None:
			self.itf.clk._log.warning("Driving an already driven clock")
			await self.stop_clock()
			if period is not None and get_time_from_sim_steps(*period) != self.clk_driver.period :
				self.clk_driver = Clock(self.itf.clk,*period)
		self._clk_driver_process = cocotb.fork(self.clk_driver.start(start_high=self._pol))
		await NextTimeStep()

	async def stop_clock(self):
		if self._clk_driver_process is not None :
			self._clk_driver_process.kill()
			self._clk_driver_process = None

		await self.drive_clk_idle()

	async def drive_clk_idle(self):
		self.itf.clk.value = 0 if self._pol else 1
		await NextTimeStep()

	async def reset(self):
		await self.stop_clock()
		await self.drive_csn(True)

	@cocotb.coroutine
	async def enable_sending(self):
		while True:
			if len(self._current_data) == 0 :
				if self.to_send.empty() and self.csn_pulse_per_word:
					await self.drive_csn(True)
				self._current_data = await self.to_send.get()
				self.tx_pin._log.info(f"Sending word {str(self._current_data)}")
				await self.drive_csn(False)

			for bit in self._current_data :
				await self.active_edge
				self.tx_pin.value = bit

			await self.inactive_edge
			if self.csn_pulse_per_word :
				await self.stop_clock()
				await self.drive_csn(True)
				await Timer(*self.csn_pulse_duration)

			await NextTimeStep()
			self.evt.word_done.set()
			await NextTimeStep()






