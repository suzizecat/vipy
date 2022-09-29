import cocotb
from cocotb.triggers import *

from .globalenv import GlobalEnv
from .globalenv import GlobalEnv

import typing as T

class Component:
	def __init__(self):
		self._name = None
		self.itf = None
		self.active = True

		self._log = cocotb.log

	@property
	def name(self):
		return self._name if self._name is not None else type(self).__name__

	@name.setter
	def name(self,value):
		self._name = value
		GlobalEnv()._namelen = max(GlobalEnv()._namelen,len(self._name))
		self._refresh_sub_names()

	@property
	def subcomponents(self):
		return [x for x in vars(self).values() if isinstance(x,Component)]

	@property
	def is_driver(self):
		return False

	def build(self,is_top = False):
		if GlobalEnv().top is None :
			GlobalEnv().top = self
			self._log.info(f"")
			self._log.info(f"{' BUILD ENV START ':#^80s}")
		elif GlobalEnv().top is self :
				self._log.info(f"{self._name} - Avoid rebuilding component {self._name}")
				return

		if self._name is None :
			self._name = type(self).__name__
		self._refresh_sub_names()
		for comp in self.subcomponents :
			comp.build()
		self._log.info(f"Built component {self._name}")
		if GlobalEnv().top is self :
			self._log.info(f"{' BUILD ENV CONPLETE ':#^80s}")
			self._log.info(f"")

	def _refresh_sub_names(self):
		for n, var in vars(self).items():
			if isinstance(var, Component):
				var.name = f"{self.name}.{n}"

	@property
	def drivers(self) -> T.List["GenericDrivers"]:
		return [x for x in vars(self).values() if isinstance(x,Component) and x.is_driver]

	@property
	def is_active(self):
		return self.active

	async def reset_drivers(self):
		rst_process_list = list()

		for d in self.drivers :
			if d.is_active :
				self._log.debug(f"Reseting driver {d._name}")
				rst_process_list.append(cocotb.start_soon(d.reset()).join())
		if len(rst_process_list) > 0 :
			await Combine(*rst_process_list)
		
