import typing as T
from .queue import QueueEvt


class DataPort():
	def __init__(self):
		self.queues : T.Dict[object,QueueEvt] = dict()

	def connect(self,child) -> QueueEvt:
		if child not in self.queues :
			self.queues[child] = QueueEvt()
		return self.queues[child]

	def put(self,item):
		for q in self.queues.values():
			q.put(item)

