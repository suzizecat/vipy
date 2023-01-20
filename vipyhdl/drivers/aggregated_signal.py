import typing as T
from cocotb.handle import ModifiableObject
from cocotb.triggers import *
from .simple_signal import SignalDriver
from vipyhdl.structure import drive_method

from vipyhdl.regbank.structure import Register, Field


class AggregatedSignalDriver(SignalDriver):
	def __init__(self, nets : T.List[ModifiableObject], reset_value = 0):
		"""
		This class allows aggregating several net and handle them as though they are a single net.
		:param nets: List of nets to handle, LSB is at list index 0
		:param reset_value: Reset value of the aggregated signal
		"""
		# There is no proper interface
		# TODO introduce a proper SignalDriverBase class
		super().__init__(None)
		self.itf = None

		"""List of nets used, the order will be retained by the _value_interface"""
		self._nets = {n._name : n for n in nets}


		"""As the expected behavior is similar to a Register, we just use this as a base"""
		self._value_interface = Register("",0,sum([f.value.n_bits for f in nets]),reset_value)

		# The value interface shall be built while we have the list of fields as an (ordered) list
		foffset = 0
		for signal in nets :
			name = signal._name
			f = Field(name,f"{foffset}:{foffset-1+signal.value.n_bits}")
			self._value_interface.add_field(f)
			foffset = f.size.next

		"""Raw "int" value, used to avoir some recomputation when syncing cache"""
		self._cached_raw_value = reset_value

		"""All provided signals will be driven"""
		for signal in self._nets.values() :
			self.register_signal_as_driven(signal)

	async def reset(self):
		self._value_interface.reset()
		await self._push_cached_values()

	def __len__(self) -> int:
		""":return: The number of bits of the aggregated signal"""
		return sum([n.value.n_bits for n in self._nets.values()])

	@drive_method
	async def _push_cached_values(self):
		"""
		Push each cached value to its actual net
		"""
		self._log.debug(f"Require pushing value {self._value_interface.value} to design")
		if self._value_interface.value != self._cached_raw_value:
			self._cached_raw_value = self._value_interface.value
			for field in self._value_interface:
				self._log.debug(f"Setting field {field.name} to value {field.value}")
				self._nets[field.name].value = field.value

	def _pull_cached_values(self):
		"""
		Read the design and update the cache from it.
		"""
		for field in self._value_interface:
			field.value = self._nets[field.name].value.integer
		self._cached_raw_value = self._value_interface.value

	async def set(self,value):
		"""
		Assign a value to the aggregated signal and push the values to the design
		:param value: Value to set the aggregated signal to
		"""
		self._log.debug(f"Set to value {value}")
		self._value_interface.value = value
		await self._push_cached_values()

	@property
	def value(self) -> int:
		"""
		:return: Pull and return the integer value of the aggregated signal
		"""
		self._pull_cached_values()
		return self._value_interface.value

	async def pulse(self,value, time = 1, unit = "step"):
		prev_val = self.value
		await self.set(value)
		await Timer(time,unit)
		await self.set(prev_val)

	async def pulse_evt(self,value,evt):
		prev_val = self.value
		await evt
		await self.set(value)
		await evt
		await self.set(prev_val)



