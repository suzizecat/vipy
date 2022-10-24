import logging

from vipy.utils.meta import Singleton
import typing as T
from cocotb.handle import ModifiableObject
import cocotb
from cocotb.log import SimBaseLog
from logging import LoggerAdapter, Filter
import os
from inspect import getmodule


class VipyLogAdapter(LoggerAdapter):
	LOW = logging.INFO+1
	MEDIUM = LOW +1
	HIGH = MEDIUM+1
	DEFAULT = logging.INFO
	def __init__(self,ref,level = None):
		self.ref = ref
		logger_name = "vipy"
		if ref.name is not None :
			logger_name += f".{ref.name}"
		logger = logging.getLogger().getChild(logger_name)
		super().__init__(logger,dict())

		envlevel = os.environ["VIPY_LOG"] if "VIPY_LOG" in os.environ else None

		if level is not None :
			self.setLevel(level)
		elif envlevel is not None :
			try:
				self.setLevel(envlevel)
			except TypeError as e :
				self.error(f"Error when using VIPY_LOG level '{envlevel}' : {e!s}")
				self.setLevel(VipyLogAdapter.DEFAULT)
			except ValueError as e :
				self.error(f"Error when using VIPY_LOG level '{envlevel}' : {e!s}")
				self.setLevel(VipyLogAdapter.DEFAULT)
		else :
			self.setLevel(VipyLogAdapter.DEFAULT)


	def indent(self,addlevel = 1):
		GlobalEnv()._indent += addlevel

	def deindent(self,sublevel = 1):
		if GlobalEnv()._indent > 0 :
			GlobalEnv()._indent -= sublevel


	def lhigh( self, msg: object, *args,stacklevel : int=1, **kwargs) -> None:
		self.log(self.HIGH,msg,*args,stacklevel=stacklevel+2,**kwargs)

	def lmed( self, msg: object,*args: object,stacklevel : int=1, **kwargs: object ) -> None:
		self.log(self.MEDIUM, msg, *args,stacklevel=stacklevel+2, **kwargs)

	def llow( self, msg: object,*args: object,stacklevel : int=1,**kwargs: object ) -> None:
		self.log(self.LOW, msg, *args,stacklevel=stacklevel+2,**kwargs)

	def process(self, msg, kwargs):
		#return (f"{self.ref.name:{GlobalEnv()._namelen}s} - {msg}", kwargs)

		return (f" - {msg}", kwargs)

class GlobalEnv(metaclass=Singleton):
	def __init__(self):
		logging.addLevelName(logging.INFO, " ")
		logging.addLevelName(VipyLogAdapter.LOW,"LOW")
		logging.addLevelName(VipyLogAdapter.MEDIUM, "MEDIUM")
		logging.addLevelName(VipyLogAdapter.HIGH, "HIGH")

		self.name = "global"
		self._log = VipyLogAdapter(self)


		self.signals_to_driver = dict()
		self._namelen = 1
		self.built = False
		self.top = None

		self._ident_level = 0

		mod = getmodule(SimBaseLog)
		mod._FILENAME_CHARS = 40

	def is_driven(self,net : T.Union[ModifiableObject,str]):
		name = None
		if isinstance(net,ModifiableObject) :
			name = net._path
		else :
			name = net
		return name in self.signals_to_driver

	def register_driver(self,driver):
		self._log.debug(f"Registering driver {driver.name}.")
		net : ModifiableObject
		for net in driver._driven_signals :
			if net is None :
				self._log.debug(f"    Net set to None, considered as not present.")
				return False
			driver._log.debug(f"    Checking driven net {net._path}")
			if self.is_driven(net) :
				self._log.debug(f"       Net {net._path} is already driven by {self.signals_to_driver[net._path].name}")
				return False

		for net in driver._driven_signals :
			self.signals_to_driver[net._path] = driver
		return True

	def get_top(self,top_type,*args,topname="top",force=False,build=True,**kwargs):
		if force or self.top is None :
			ret = top_type(*args, **kwargs)
			if build :
				ret.name = topname
				ret.build()
			return ret
		else :
			return self.top