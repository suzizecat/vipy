import cocotb
from cocotb.triggers import *

from .globalenv import GlobalEnv, VipyLogAdapter
from dataclasses import  *
import typing as T

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
		GlobalEnv()._namelen = max(GlobalEnv()._namelen,len(self._name))
		self._refresh_sub_names()

	@property
	def subcomponents(self):
		return [x for x in vars(self).values() if isinstance(x,Component)]

	@property
	def is_driver(self):
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
		GlobalEnv()._log.lhigh(f"Built component {self._name:{GlobalEnv()._namelen}s} : {active_state} {type(self).__name__}")
		if GlobalEnv().top is self :
			GlobalEnv()._log.lhigh(f"{' BUILD ENV COMPLETE ':#^80s}")
			GlobalEnv()._log.lhigh(f"")

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
		self._log.debug(f"Reseting drivers for {self.name}")
		for d in self.drivers :
			rst_process_list.append(cocotb.start_soon(d.reset()).join())

		if len(rst_process_list) > 0 :
			await Combine(*rst_process_list)

	def bind_itf(self,device):
		for name in [getattr(self.itf, field.name) for field in fields(self.itf)] :
			try :
				setattr(self.itf,name,device._id(name,extended=False))
			except AttributeError as e :
				pass


		
