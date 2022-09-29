from dataclasses import dataclass
import typing as T
import cocotb

from  cocotb.handle import ModifiableObject
from cocotb.triggers import Event, RisingEdge, FallingEdge, Edge, First, NextTimeStep

from vipy.bus.base import DataWord
from vipy.bus.base.serial import BaseSerial, SerialMode

import enum


@dataclass
class SPIInterface:
	mosi: ModifiableObject = None
	miso: ModifiableObject = None
	clk: ModifiableObject = None
	csn: ModifiableObject = None

class SPIBase(BaseSerial):

	@dataclass
	class SPIEvents:
		config_changed: Event = Event("spi_config_changed")
		selected: Event = Event("is_selected")
		deselected: Event = Event("is_deselected")
		word_done : Event = Event("word_done")

	def __init__(self, mode : SerialMode):
		super().__init__()
		self._serial_mode = mode
		self._pha : bool = False
		self._pol : bool = False
		self.evt : SPIBase.SPIEvents = SPIBase.SPIEvents()
		self.itf : SPIInterface = SPIInterface()

		self._monitored_events = [
			self.evt.config_changed.wait(),
			self.evt.word_done.wait()
		]

		self.word_size : int = DataWord.word_size

		cocotb.start_soon(self._clear_toogled_events())

	def start_csn_evt_handling(self):
		cocotb.start_soon(self._csn_evt_handler())

	@cocotb.coroutine
	async def _csn_evt_handler(self) :
		if not self.is_selected:
			self.evt.deselected.set()
		else :
			self.evt.selected.set()

		while True :
			if not self.is_selected:
				await FallingEdge(self.itf.csn)
				self.evt.deselected.clear()
				self.evt.selected.set()
			else :
				await RisingEdge(self.itf.csn)
				self.evt.selected.clear()
				self.evt.deselected.set()
			await NextTimeStep()

	@property
	def tx_pin(self) -> ModifiableObject :
		return self.itf.mosi if self.mode == SerialMode.MASTER else self.itf.miso

	@property
	def rx_pin(self) -> ModifiableObject :
		return self.itf.mosi if self.mode == SerialMode.SLAVE else self.itf.miso

	@property
	def is_selected(self) -> bool:
		return self.itf.csn.value.integer == 0

	@property
	def mode(self) -> SerialMode:
		return self._serial_mode

	@property
	def spi_mode(self) -> int:
		output = 0
		output += 1 if self._pha else 0
		output += 2 if self._pol else 0
		return output

	@cocotb.coroutine
	async def _clear_toogled_events(self):
		while True :
			evt : Event = await First(*self._monitored_events)
			evt.parent.clear()

	@spi_mode.setter
	def spi_mode(self,val : int):
		val = val & 0b11
		if not val != self.spi_mode :
			return
		self._pha = (val & 0b01) != 0
		self._pol = (val & 0b10) != 0

		self.evt.config_changed.set(self.spi_mode)
		self.evt.config_changed.clear()

	@property
	def capture_edge(self) -> T.Union[RisingEdge, FallingEdge]:
		rising = self._pha == self._pol
		return RisingEdge(self.itf.clk) if rising else FallingEdge(self.itf.clk)

	@property
	def drive_edge(self) -> T.Union[RisingEdge, FallingEdge]:
		rising = self._pha != self._pol
		return RisingEdge(self.itf.clk) if rising else FallingEdge(self.itf.clk)