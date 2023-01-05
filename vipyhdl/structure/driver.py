from .component import Component
from .globalenv import GlobalEnv

from cocotb.handle import ModifiableObject
import typing as T
import functools
from dataclasses import *
from fnmatch import fnmatch

from overrides import override
def drive_method(func):
	"""
	This decorator should be used on any function that actually drive the design.
	The decorated function will not be ran if the Driver is not active.
	This allows the separation between active functions and passive functions, thus allowing a correct object state
	even if the design is not actually driven.
	"""
	@functools.wraps(func)
	async def wrap(self: "GenericDriver", *args, **kwargs):
		if not self.is_active:
			pass
		else:
			return await func(self, *args, **kwargs)
	return wrap


class GenericDriver(Component):
	def __init__(self):
		"""
		This class implement the base of any Vipy driver.
		"""
		super().__init__()
		self._driven_signals = set()


	@property
	def is_driver(self) -> bool:
		"""Returns true as this object is the base for a driver"""
		return True

	@property
	def driven_signals(self) -> T.List[ModifiableObject]:
		"""
		:return: All signals registered as driven
		"""
		ret= list(self._driven_signals)
		for d in self.drivers :
			ret.extend(d.driven_signals)
		return ret

	def build(self):
		"""
		Build the component.
		The component is deemed as a "valid driver" if all of its registered nets are actually driven by itself.
		The component tries to register itself *before* any subcomponent, thus automatically disabling any subdriver
		that is superseded by the current component.
		"""
		if self.itf is not None :
			self._build_active = GlobalEnv().register_driver(self)
		super().build()

	def register_signal_as_driven(self,signal : ModifiableObject):
		"""
		Register a signal as being driven by the current driver.

		This signal *must* not be already driven for the Driver to be active after build.

		:param signal: Signal to register
		"""
		self._driven_signals.add(signal)

	def register_itf_as_driven(self,pattern : T.Optional[str] = None):
		"""
		Assuming self.itf to be a dataclass representing the interface of the component, register all nets in this
		interface which matches the provided pattern, if any.

		If no pattern is provided, all nets will be registered.

		:param pattern: Unix-style pattern, supporting wildcards. Example : "i_*"
		"""
		for signal in [getattr(self.itf, field.name) for field in fields(self.itf) if pattern is None or fnmatch(field.name,pattern)] :
			self.register_signal_as_driven(signal)

	def register_remaining_signals_as_driven(self,pattern = None):
		"""
		Assuming self.itf to be a dataclass representing the interface of the component,
		register all nets in this interface that are not already registered
		and which matches the provided pattern, if any.

		If no pattern is provided, all nets will be registered.

		:param pattern: Unix-style pattern, supporting wildcards. Example : "i_*"
		"""
		driven_signals = list()
		drv : "GenericDriver"
		for drv in self.drivers :
			driven_signals.extend(drv.driven_signals)
		for signal in [getattr(self.itf, field.name) for field in fields(self.itf) if pattern is None or fnmatch(field.name,pattern)] :
			if signal in driven_signals :
				continue
			self.register_signal_as_driven(signal)

	def unregister_signal_as_driven(self,signal : ModifiableObject):
		"""
		Removes a signal from the list of registered signals.
		:param signal: Handle for the signal to remove.
		"""
		self._driven_signals.remove(signal)
