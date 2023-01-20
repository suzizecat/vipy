import typing as T

import logging


import cocotb
import functools
from dataclasses import *
from fnmatch import fnmatch

from cocotb.triggers import _Event

from . import  Component
from abc import ABC, abstractmethod

from cocotb.triggers import *
from cocotb.handle import *
from cocotb import Task


class Monitor(Component, ABC) :
	def __init__(self):
		super(Monitor, self).__init__()
		self._sensitivity_list : T.List[Trigger] = list()
		self._autoreset_events : T.List[Event] = list()

		self._run_process : Task = None
		self._autoreset_process = None
		self.evt = None
		self._trigger_event = None

	@abstractmethod
	def monitor(self):
		raise NotImplementedError

	@property
	def is_monitor(self):
		return True

	@property
	def events(self) -> T.List[Event]:
		return [getattr(self.evt, field.name) for field in fields(self.evt)]

	def clear_all_events(self):
		for e in self.events :
			e.clear()

	async def reset(self):
		self._log.debug(f"Reset command")

		self.start()
		await self.reset_all()

	async def _run(self):
		while True:
			self._trigger_event = await First(*self._sensitivity_list)
			await ReadOnly()
			self.monitor()

	async def _autoreset_events_handler(self):
		self._log.debug(f"Start autoclear event handler")
		if len(self._autoreset_events) > 0 :
			_trigger_events = [e.wait() for e in self._autoreset_events]
			evt_trigger  : _Event = None
			while True :
				evt_trigger = await First(*_trigger_events)
				#self._log.debug(f"Clear event {evt_trigger!r}")
				evt_trigger.parent.clear()

	def build(self):
		super(Monitor, self).build()
		self._autoreset_process = cocotb.start_soon(self._autoreset_events_handler())

	def post_build(self):
		super().post_build()
		evt : Event
		for evt in [getattr(self.evt, field.name) for field in fields(self.evt)]:
			evt.name = self.evt_name(evt.name)

	def start(self):
		if self._run_process is not None :
			self.stop()
		self._run_process = cocotb.start_soon(self._run())

	def stop(self):
		if self._run_process is not None:
			self._run_process.kill()
		self.clear_all_events() # No issue in clearing anyway
		self._run_process = None

	def add_evt_to_sensitivity(self,evt : T.Union[T.Iterable[Trigger],Trigger]):
		if hasattr(evt,"__iter__") :
			for e in evt :
				self.add_evt_to_sensitivity(e)
		else:
			if evt not in self._sensitivity_list :
				trg = evt.wait() if isinstance(evt,Event) else evt
				self._sensitivity_list.append(trg)

	def add_edge_to_sensitivity(self,evt_type,nets : T.List[ModifiableObject]):
		for n in nets :
			self.add_evt_to_sensitivity(evt_type(n))

	def add_itf_to_sensitivity(self, pattern = None):
		signals = [getattr(self.itf, field.name) for field in fields(self.itf) if pattern is None or fnmatch(field.name,pattern)]
		if len(signals) == 0 :
			self._log.warning(f"Sensitivity lookup found no matching signals in {self.name}.itf for pattern {pattern!s}")
		for signal in signals :
			self.add_evt_to_sensitivity(Edge(signal))

	def add_evt_to_autoreset(self, evt : T.Union[T.Iterable[Event],Event]):
		if hasattr(evt,"__iter__") :
			for e in evt :
				self.add_evt_to_autoreset(e)
		else:
			if evt not in self._autoreset_events :
				self._autoreset_events.append(evt)

	def evt_name(self,name : str):
		return  f"{self.name}@{name}"

	def trigger_name(self,evt_name : str):
		return  f"{self.evt_name(evt_name)}.wait()"