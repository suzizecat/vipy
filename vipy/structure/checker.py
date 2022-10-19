import typing as T

import logging


import cocotb
import functools
from dataclasses import *
from fnmatch import fnmatch
from . import  Component
from abc import ABC, abstractmethod

from cocotb.triggers import *
from cocotb.handle import *
from cocotb import Task


class Checker(Component, ABC) :
	def __init__(self):
		super(Checker, self).__init__()
		self._sensitivity_list : T.List[Trigger] = list()

		self._run_process : Task = None

	@property
	def is_checker(self):
		return True

	@abstractmethod
	def check(self):
		raise NotImplementedError

	async def reset(self):
		self.start()

	async def _run(self):
		while True:
			await First(*self._sensitivity_list)
			await ReadOnly()
			self.check()

	def start(self):
		if not self.is_active :
			return
		if self._run_process is not None :
			self.stop()
		self._run_process = cocotb.start_soon(self._run())

	def stop(self):
		if self._run_process is not None:
			self._run_process.kill()
		self._run_process = None

	def add_evt_to_sensitivity(self,evt : Trigger):
		if evt not in self._sensitivity_list :
			self._sensitivity_list.append(evt)

	def add_edge_to_sensitivity(self,evt_type,nets : T.List[ModifiableObject]):
		for n in nets :
			self.add_evt_to_sensitivity(evt_type(n))

	def add_itf_to_sensitivity(self, pattern):
		for signal in [getattr(self.itf, field.name) for field in fields(self.itf) if pattern is None or fnmatch(field.name,pattern)] :
			self.add_evt_to_sensitivity(Edge(signal))