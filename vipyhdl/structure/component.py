import cocotb
from cocotb.triggers import *

from .globalenv import GlobalEnv, VipyLogAdapter
from dataclasses import  *
import typing as T

class Component(object):
	def __init__(self):
		"""
		This class defines a basic verification component that might be used to represent an environment.
		It is used as a common basis for all subcomponent.
		"""
		super().__init__()

		"""Hold the name of the component, typically changed by the build function"""
		self._name = None

		"""Hold the interface. Typically a dataclass containing multiple cocotb.ModifiableObject"""
		self.itf  = None

		"""Provide a logger. By default, cocotb logger is used. Is updated by the build step"""
		self._log : VipyLogAdapter = cocotb.log

		"""Active flags"""
		self._user_active = True
		self._build_active = True

	@property
	def name(self) -> str:
		"""
		:return: The component name or the type name instead
		"""
		return self._name if self._name is not None else type(self).__name__

	@name.setter
	def name(self,value):
		"""
		Set the current component name.
		Automatically refresh subcomponent names
		"""
		self._name = value
		if value is not None :
			GlobalEnv()._namelen = max(GlobalEnv()._namelen,len(self._name))
			self._refresh_sub_names()

	@property
	def subcomponents(self) -> T.Iterable["Component"]:
		"""
		:return: List of all member which are components
		"""
		return [x for name, x in vars(self).items() if not name.startswith("_") and isinstance(x,Component)]

	@property
	def is_driver(self) -> bool:
		"""
		:return: True if current component is a driver
		"""
		return False

	@property
	def is_checker(self) -> bool:
		"""
		:return: True if current component is a checker
		"""
		return False

	@property
	def is_monitor(self) -> bool:
		"""
		:return: True if current component is a monitor
		"""
		return False

	def post_build(self):
		"""
		Post build step.
		Called for custom actions *after* the build is done.
		"""
		pass

	def build(self):
		"""
		Perform the bench build and elaboration.
		This function will recursively call the build function of all subcomponent, thus setting up:
		  - the hierarchical naming
		  - the appropriate logger
		  - the active state, depending on driver net availability.
		There should be only one component as testbench top.
		If the current component is already built as a top, the build should not be re-done.
		Otherwise, the first component to be built will be considered as a top and will be saved in the GlobalEnv.

		Post-build step is done after all subcomponent build.
		Therefore, the post-build of all subcomponent will be performed *before* the parent post-build.
		"""
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
		self._log.debug(f"Set vipyhdl logger for component {self.name}")

		self._refresh_sub_names()
		for comp in self.subcomponents :
			comp.build()

		self.post_build()

		# Report the build process
		active_state = "  ACTIVE" if self.is_active else "INACTIVE"
		log_line = f"Built component {self._name:{GlobalEnv()._namelen}s} : {active_state} {type(self).__name__}"
		GlobalEnv()._log.lhigh(log_line) if self.is_active else GlobalEnv()._log.llow(log_line)

		if GlobalEnv().top is self :
			GlobalEnv()._log.lhigh(f"{' BUILD ENV COMPLETE ':#^80s}")
			GlobalEnv()._log.lhigh(f"")

	def _refresh_sub_names(self):
		"""
		Set the name of all subcomponent to <current component name>.<component instance name>
		In example :

			class Foo(Component):
				def __init__(self):
					super().__init__()

					self.sub = Component()

			top = Foo()
			top.name = "top"
			top._refresh_sub_names()
			print(top.sub.name)
			# "top.sub"

		Subcomponents with a leading _ (private members) will not be automatically renamed.
		"""

		for n, var in vars(self).items():
			if not n.startswith("_") and isinstance(var, Component):
				var.name = f"{self.name}.{n}"

	async def reset(self):
		"""
		Should be overriden, implement the reset action of the component
		Reset all subcomponent by default.
		"""

		await self.reset_all()

	@property
	def drivers(self) -> T.Iterable["GenericDrivers"]:
		"""
		:return: List of all subcomponents which are drivers
		"""
		return [x for x in self.subcomponents if x.is_driver]

	@property
	def checkers(self) :
		"""
		:return: List of all subcomponents which are checkers
		"""
		return [x for x in self.subcomponents if x.is_checker]

	@property
	def monitors(self) :
		"""
		:return: List of all subcomponents which are monitors
		"""
		return [x for x in self.subcomponents if x.is_monitor]

	@property
	def simplecomponents(self) :
		"""
		:return: List of all subcomponents which are neither a driver, nor a checker, nor a monitor
		"""
		return [x for x in self.subcomponents if not (x.is_monitor or x.is_checker or x.is_driver)]

	@property
	def is_active(self):
		"""
		:return: True if the component is deemed active.
		The component can be disabled either by the build step (see GenericDriver) or by the user.
		"""
		return self._user_active and self._build_active

	@is_active.setter
	def is_active(self,value):
		"""
		User interface to enable/disable an otherwise active component.
		:param value: Desired state of the "is_active" flag.
		Only impact the user action, the build step can still disable the component.
		"""
		self._user_active = bool(value)

	async def reset_drivers(self):
		"""
		Parallel reset and await for the end of the reset of all drivers
		"""
		rst_process_list = list()
		self._log.debug(f"Reseting drivers for {self.name}")
		for d in self.drivers :
			rst_process_list.append(cocotb.start_soon(d.reset()).join())

		if len(rst_process_list) > 0 :
			await Combine(*rst_process_list)

	async def reset_monitor(self):
		"""
		Parallel reset and await for the end of the reset of all monitors
		"""
		rst_process_list = list()
		self._log.debug(f"Reseting monitors for {self.name}")
		for d in self.monitors :
			rst_process_list.append(cocotb.start_soon(d.reset()).join())

		if len(rst_process_list) > 0 :
			await Combine(*rst_process_list)

	async def reset_checkers(self):
		"""
		Parallel reset and await for the end of the reset of all checkers
		"""
		rst_process_list = list()
		self._log.debug(f"Reseting checkers for {self.name}")
		for d in self.checkers :
			rst_process_list.append(cocotb.start_soon(d.reset()).join())

		if len(rst_process_list) > 0 :
			await Combine(*rst_process_list)

	async def reset_components(self):
		"""
		Parallel reset and await for the end of the reset of all simple components
		"""
		rst_process_list = list()
		self._log.debug(f"Reseting simples components for {self.name}")
		for d in self.simplecomponents :
			rst_process_list.append(cocotb.start_soon(d.reset()).join())

		if len(rst_process_list) > 0 :
			await Combine(*rst_process_list)

	async def reset_all(self):
		"""
		Parallel reset and await for the end of the reset of all subcomponents
		"""
		rst_process_list = list()
		rst_process_list.append(cocotb.start_soon(self.reset_drivers()).join())
		rst_process_list.append(cocotb.start_soon(self.reset_monitor()).join())
		rst_process_list.append(cocotb.start_soon(self.reset_checkers()).join())
		rst_process_list.append(cocotb.start_soon(self.reset_components()).join())
		await Combine(*rst_process_list)
