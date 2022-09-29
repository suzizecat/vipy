from vipy.utils.meta import Singleton
import typing as T
from cocotb.handle import ModifiableObject


class GlobalEnv(metaclass=Singleton):
	def __init__(self):
		self.signals_to_driver = dict()
		self._namelen = 1
		self.built = False
		self.top = None

	def is_driven(self,net : T.Union[ModifiableObject,str]):
		name = None
		if isinstance(net,ModifiableObject) :
			name = net._path
		else :
			name = net
		return name in self.signals_to_driver

	def register_driver(self,driver):
		driver._log.debug(f"Registering driver {driver.name}.")
		net : ModifiableObject
		for net in driver._driven_signals :
			driver._log.debug(f"    Checking driven net {net._path}")
			if self.is_driven(net) :
				driver._log.debug(f"       Net {net._path} is already driven")
				return False

		for net in driver._driven_signals :
			self.signals_to_driver[net._path] = driver
		return True