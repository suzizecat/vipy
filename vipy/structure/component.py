import cocotb
from cocotb.triggers import *

from .globalenv import GlobalEnv, VipyLogAdapter
from dataclasses import  *
import typing as T

def bind_itf(itf,device):
	for name in [getattr(itf, field.name) for field in fields(itf)] :
		try :
			GlobalEnv()._log.debug(f"Trying to bind net name {name!s}")
			if name is None :
				continue
			setattr(itf,name,device._id(name,extended=False))
		except AttributeError as e :
			GlobalEnv()._log.debug(f"Failed to bind net {name}")
			pass
	return itf


class Component(object):
	def __init__(self):
		super().__init__()
		self._name = None
		self.itf  = None
		self.active = True

		self._log : VipyLogAdapter = cocotb.log

	@property
	def name(self):
		return self._name if self._name is not None else type(self).__name__

	@name.setter
	def name(self,value):
		self._name = value
		if value is not None :
			GlobalEnv()._namelen = max(GlobalEnv()._namelen,len(self._name))
			self._refresh_sub_names()

	@property
	def subcomponents(self):
		return [x for x in vars(self).values() if isinstance(x,Component)]

	@property
	def is_driver(self):
		return False

	@property
	def is_checker(self):
		return False

	@property
	def is_monitor(self):
		return False

	def end_of_build(self):
		pass

	def build(self,is_top = False):
		if GlobalEnv().top is None :
			GlobalEnv().top = self
			GlobalEnv()._log.lhigh(f"")
			GlobalEnv()._log.lhigh(f"{' BUILD ENV START ':#^80s}")
		elif GlobalEnv().top is self :
				GlobalEnv()._log.lhigh(f"Avoid rebuilding component {self._name}")
				return

		if self._name is None :
			self._name = type(self).__name__

		self._log = VipyLogAdapter(self)
		self._log.debug(f"Set vipy logger for component {self.name}")

		self._refresh_sub_names()
		for comp in self.subcomponents :
			comp.build()

		self.end_of_build()
		active_state = "  ACTIVE" if self.is_active else "INACTIVE"
		if self.is_active :
			GlobalEnv()._log.lhigh(f"Built component {self._name:{GlobalEnv()._namelen}s} : {active_state} {type(self).__name__}")
		else:
			GlobalEnv()._log.llow(f"Built component {self._name:{GlobalEnv()._namelen}s} : {active_state} {type(self).__name__}")

		if GlobalEnv().top is self :
			GlobalEnv()._log.lhigh(f"{' BUILD ENV COMPLETE ':#^80s}")
			GlobalEnv()._log.lhigh(f"")

	def _refresh_sub_names(self):
		for n, var in vars(self).items():
			if isinstance(var, Component):
				var.name = f"{self.name}.{n}"

	async def reset(self):
		pass

	@property
	def drivers(self) -> T.List["GenericDrivers"]:
		return [x for x in vars(self).values() if isinstance(x,Component) and x.is_driver]

	@property
	def checkers(self) :
		return [x for x in vars(self).values() if isinstance(x,Component) and x.is_checker]

	@property
	def monitors(self) :
		return [x for x in vars(self).values() if isinstance(x,Component) and x.is_monitor]

	@property
	def simplecomponents(self) :
		return [x for x in vars(self).values() if isinstance(x,Component) and not  (x.is_monitor or x.is_checker or x.is_driver)]

	@property
	def is_active(self):
		return self.active

	async def reset_drivers(self):
		rst_process_list = list()
		self._log.debug(f"Reseting drivers for {self.name}")
		for d in self.drivers :
			rst_process_list.append(cocotb.start_soon(d.reset()).join())

		if len(rst_process_list) > 0 :
			await Combine(*rst_process_list)

	async def reset_monitor(self):
		rst_process_list = list()
		self._log.debug(f"Reseting monitors for {self.name}")
		for d in self.monitors :
			rst_process_list.append(cocotb.start_soon(d.reset()).join())

		if len(rst_process_list) > 0 :
			await Combine(*rst_process_list)

	async def reset_checkers(self):
		rst_process_list = list()
		self._log.debug(f"Reseting checkers for {self.name}")
		for d in self.checkers :
			rst_process_list.append(cocotb.start_soon(d.reset()).join())

		if len(rst_process_list) > 0 :
			await Combine(*rst_process_list)

	async def reset_components(self):
		rst_process_list = list()
		self._log.debug(f"Reseting simples components for {self.name}")
		for d in self.simplecomponents :
			rst_process_list.append(cocotb.start_soon(d.reset()).join())

		if len(rst_process_list) > 0 :
			await Combine(*rst_process_list)

	async def reset_all(self):
		rst_process_list = list()
		rst_process_list.append(cocotb.start_soon(self.reset_drivers()).join())
		rst_process_list.append(cocotb.start_soon(self.reset_monitor()).join())
		rst_process_list.append(cocotb.start_soon(self.reset_checkers()).join())
		rst_process_list.append(cocotb.start_soon(self.reset_components()).join())
		await Combine(*rst_process_list)

	def bind_itf(self,device):
		self.itf = bind_itf(self.itf,device)

		
