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

	async def reset(self):
		self.start()

	async def _run(self):
		while True:
			self._trigger_event = await First(*self._sensitivity_list)
			await ReadOnly()
			self.monitor()

	async def _autoreset_events_handler(self):
		if len(self._autoreset_events) > 0 :
			_trigger_events = [e.wait() for e in self._autoreset_events]
			evt_trigger  : _Event = None
			while True :
				evt_trigger = await First(*_trigger_events)
				evt_trigger.parent.clear()

	def build(self,is_top = False):
		super(Monitor, self).build(is_top)
		self._autoreset_process = cocotb.start_soon(self._autoreset_events_handler())

	def start(self):
		if self._run_process is not None :
			self.stop()
		self._run_process = cocotb.start_soon(self._run())

	def stop(self):
		if self._run_process is not None:
			self._run_process.kill()
		self._run_process = None

	def add_evt_to_sensitivity(self,evt : Trigger):
		if evt not in self._sensitivity_list :
			trg = evt.wait() if isinstance(evt,Event) else evt
			self._sensitivity_list.append(trg)

	def add_edge_to_sensitivity(self,evt_type,nets : T.List[ModifiableObject]):
		for n in nets :
			self.add_evt_to_sensitivity(evt_type(n))

	def add_itf_to_sensitivity(self, pattern):
		for signal in [getattr(self.itf, field.name) for field in fields(self.itf) if pattern is None or fnmatch(field.name,pattern)] :
			self.add_evt_to_sensitivity(Edge(signal))

	def add_evt_to_autoreset(self, evt : Event):
		if evt not in self._autoreset_events :
			self._autoreset_events.append(evt)