from cocotb.queue import Queue
from cocotb.triggers import Event


class QueueEvt(Queue):
	def __init__(self, maxsize = 0):
		super().__init__(maxsize)
		self.is_full = Event()
		self.is_empty = Event()

		self.is_empty.set()

	def _put(self,item):
		super()._put(item)
		self.is_empty.clear()
		if self.full() :
			self.is_full.set()

	def _get(self):
		ret = super()._get()
		self.is_full.clear()
		if self.empty() :
			self.is_empty.set()
		return ret
