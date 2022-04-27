import typing
from copy import copy

import cocotb
from cocotb import RunningTask
from cocotb.binary import BinaryValue
from cocotb.clock import Clock

from  cocotb.handle import ModifiableObject

from cocotb.triggers import FallingEdge, Timer, NextTimeStep

from vipy.bus.base.serial import BaseSerial, SerialMode
from .spi_base import SPIBase
import enum

from ..base.word import DataWord
from ...utils.queue import QueueEvt


class SPIDriver(SPIBase):
	def __init__(self, mode : SerialMode, itf : SPIBase.SPIInterface, clk_period : typing.Tuple[int,str] = (1,"us")):
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

	def drive_csn(self, state : bool):
		expected_state = 1 if state else 0
		if self.itf.csn.value.integer != expected_state :
			self.itf.csn.value = expected_state

		else :
			return

	def drive_clock(self):
		if self._clk_driver_process is not None:
			self.stop_clock()
		self._clk_driver_process = cocotb.fork(self.clk_driver.start())

	def stop_clock(self):
		if self._clk_driver_process is not None :
			self._clk_driver_process.kill()
			self._clk_driver_process = None

	def drive_tx_idle(self):
		self.tx_pin.value.integer = 1 if self._pol else 0

	def reset(self):
		self.stop_clock()
		self.drive_tx_idle()
		self.drive_csn(True)

	def start(self):
		self.stop()
		self._drive_process = cocotb.start_soon(self.drive())

	def stop(self):
		if self._drive_process is not None:
			self._drive_process.kill()
			self._drive_process = None
			self.stop_clock()
			self.drive_csn(True)


	@cocotb.coroutine
	async def drive(self):
		self.stop_clock()
		self.drive_tx_idle()
		self.drive_csn(True)

		while True:
			if len(self._current_data) == 0 :
				if self.to_send.empty() :
					self.drive_csn(True)
				self._current_data = await self.to_send.get()
				self.tx_pin._log.info(f"Sending word {str(self._current_data)}")
				self.drive_csn(False)
				if self._clk_driver_process is None :
					await Timer(self.clk_driver.period)
					self.drive_clock()

			for bit in self._current_data :
				await self.active_edge
				self.tx_pin.value = bit

			await self.inactive_edge
			if self.csn_pulse_per_word :
				self.drive_tx_idle()
				self.stop_clock()
				self.drive_csn(True)
				await Timer(*self.csn_pulse_duration)

			await NextTimeStep()
			self.evt.word_done.set()
			await NextTimeStep()






