import typing as T

import cocotb
from cocotb import RunningTask
from cocotb.handle import ModifiableObject
from cocotb.utils import *
from cocotb.triggers import *

class ServoDriver:

	def __init__(self, net : ModifiableObject, period : T.Tuple[int,str] = (20,'ms'), min : T.Tuple[int,str] = (1,'ms'), max : T.Tuple[int,str] = (2,'ms')):
		self.net = net
		self._period = period
		self._min = get_sim_steps(*min)
		self._max = get_sim_steps(*max)
		self.value = 0
		self._driver_process : RunningTask = None

	def reset(self):
		self.net.value = 0

	def start(self):
		if self._driver_process is not None :
			self.stop()

		self._driver_process = cocotb.start_soon(self._running_process())

	def stop(self):
		if self._driver_process is not None :
			self._driver_process.kill()
			self._driver_process = None

	async def _running_process(self):
		while True:
			active_steps = self._min + round((self._max - self._min) * self._set_value)
			wait_steps = get_sim_steps(*self._period) - active_steps
			active_steps = max(active_steps,0)
			wait_steps = max(wait_steps, 0)
			self.net.value = 1
			await Timer(active_steps)
			self.net.value = 0
			await Timer(wait_steps)
