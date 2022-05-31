from dataclasses import dataclass
import typing as T
import cocotb
from cocotb import RunningTask
from cocotb.triggers import Event, First, Timer, _Event
from fractions import Fraction

from cocotb.utils import get_sim_steps


class EncoderBase:

	@dataclass
	class EncoderEvents:
		pos_changed: Event = Event("enc_pos_changed")
		spd_changed: Event = Event("enc_spd_changed")

	def __init__(self, resolution = 360, position = 0):
		self.resolution = resolution
		self._position = 0

		self.direction = 1
		self.evt = EncoderBase.EncoderEvents()
		self._update_period : T.Tuple[int,str] = None

		self._monitored_events = [
			self.evt.pos_changed.wait(),
			self.evt.spd_changed.wait()
		]

		self._update_position : RunningTask = None
		self.position = position

	@property
	def position(self):
		return self._position

	@position.setter
	def position(self,value):
		self._position = value % self.resolution
		self.evt.pos_changed.set()

	@cocotb.coroutine
	async def _clear_toogled_events(self):
		while True :
			evt : _Event = await First(*self._monitored_events)
			evt.parent.clear()

	@property
	def speed_tr_per_sec(self):
		return 1/self._update_period[0] if self._update_period is not None else 0

	@speed_tr_per_sec.setter
	def speed_tr_per_sec(self, value):
		cocotb.log.info("Update speed")
		self._update_period =  (get_sim_steps(Fraction(1,self.resolution * value),"sec",round_mode="round"),"step")

	async def run_update_position(self):
		if self._update_period is None :
			await self.evt.spd_changed.wait()
		while True:
			await Timer(*self._update_period)
			self.position += 1 if self.direction > 0 else -1

	async def start(self):
		self._update_position = await cocotb.start(self.run_update_position())
