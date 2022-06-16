import typing as T

import cocotb
from cocotb import RunningTask
from cocotb.triggers import *

from vipy.bus.base.serial import BaseSerial, SerialMode
from .spi_base import SPIBase, SPIInterface
import enum

from ..base.word import DataWord
from ...utils.queue import QueueEvt


class SPIMonitor(SPIBase):
	def __init__(self, mode: SerialMode, itf: SPIInterface):
		super().__init__(mode)
		self.itf = itf
		self.to_handle : QueueEvt[DataWord] = QueueEvt()
		self.current_word = DataWord(0,wsize=self.word_size,msbf=True,limit=True)
		self.current_word.clear()

		self._processes  : T.List[RunningTask] = list()

	@cocotb.coroutine
	async def _monitor_task(self):

		if self.is_selected :
			await RisingEdge(self.itf.csn)
		if self._pha == 1 :
			await self.capture_edge
		while True :
			await Combine(self.evt.selected.wait(), self.capture_edge)

			self.current_word.append(self.rx_pin.value.integer)
			if self.current_word.is_full :
				self.to_handle.put_nowait(DataWord(self.current_word.value,wsize=self.word_size,msbf=True))
				self.current_word.clear()

	@cocotb.coroutine
	async def _auto_clear_word(self):
		while True :
			await self.evt.deselected.wait()
			self.current_word.clear()
			await self.evt.selected.wait()

	def start(self):
		cocotb.log.info(f"Starting SPI Monitor in mode {self.spi_mode}")
		self.stop()
		self._processes.append(cocotb.start_soon(self._monitor_task()))
		self._processes.append(cocotb.start_soon(self._auto_clear_word()))

	def stop(self):
		for task in self._processes :
			task.kill()
		self._processes.clear()
