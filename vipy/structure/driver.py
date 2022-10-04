from .component import Component
from .globalenv import GlobalEnv
from abc import ABC, abstractmethod
from cocotb.handle import ModifiableObject

import functools
from dataclasses import *
from fnmatch import fnmatch

def drive_method(func):
	@functools.wraps(func)
	async def wrap(self: "GenericDriver", *args, **kwargs):
		if not self.is_active:
			pass
		else:
			return await func(self, *args, **kwargs)
	return wrap


class GenericDriver(Component,ABC):
	def __init__(self):
		super().__init__()
		self._driven_signals = set()
		self.active = False

	@abstractmethod
	async def reset(self):
		raise NotImplementedError()

	@property
	def is_driver(self):
		return True

	@property
	def driven_signals(self) :
		ret= list(self._driven_signals)
		for d in self.drivers :
			ret.extend(d.driven_signals)
		return ret

	def build(self):
		if self.itf is not None :
			self.active = GlobalEnv().register_driver(self)
		super().build()

	def register_signal_as_driven(self,signal : ModifiableObject):
		self._driven_signals.add(signal)

	def register_itf_as_driven(self,pattern = None):
		for signal in [getattr(self.itf, field.name) for field in fields(self.itf) if pattern is None or fnmatch(field.name,pattern)] :
			self.register_signal_as_driven(signal)

	def register_remaining_signals_as_driven(self,pattern = None):
		driven_signals = list()
		drv : "GenericDriver"
		for drv in self.drivers :
			driven_signals.extend(drv.driven_signals)
		for signal in [getattr(self.itf, field.name) for field in fields(self.itf) if pattern is None or fnmatch(field.name,pattern)] :
			if signal in driven_signals :
				continue
			self.register_signal_as_driven(signal)

	def unregister_signal_as_driven(self,signal : ModifiableObject):
		self._driven_signals.remove(signal)
