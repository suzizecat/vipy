import enum
from abc import ABC
from abc import abstractmethod


class SerialMode(enum.Enum):
	SLAVE = enum.auto()
	MASTER = enum.auto()


class BaseSerial(ABC):
	def __init__(self):
		pass

	@property
	@abstractmethod
	def mode(self) -> SerialMode:
		raise NotImplementedError()