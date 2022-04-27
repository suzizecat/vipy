import typing as T


class DataWordOverflowError(RuntimeError):
	pass

class DataWord:
	word_size = 8
	msbfirst= True
	def __init__(self, value : int, wsize = None, msbf = None):
		self._msbf = msbf if msbf is not None else DataWord.msbfirst
		self.wsize = wsize if wsize is not None else DataWord.word_size
		self.content : T.List[int] = list()
		self._from_int(value)

	def clear(self):
		self.content.clear()

	@property
	def msbf(self):
		return self._msbf

	@msbf.setter
	def msbf(self,val):
		if val != self._msbf :
			self._msbf = val
			self.content.reverse()

	@property
	def value(self):
		return int("".join([str(x) for x in self.content]),2)

	@property
	def is_full(self):
		return len(self.content) >= self.wsize

	def _from_int(self,val):
		self.content.clear()
		self.content = [int(x) for x in f"{val:0{self.wsize}b}"]
		if not self.msbf :
			self.content.reverse()
		if len(self.content) > self.wsize :
			self.content = self.content[:self.wsize]

	def append(self,val : int):
		if self.is_full :
			raise DataWordOverflowError

		val = 1 if val else 0
		if self.msbf :
			self.content.append(val)
		else:
			self.content.insert(0,val)

	def __iter__(self):
		return self

	def __next__(self):
		if len(self.content) > 0 :
			return self.content.pop(0)
		else :
			raise StopIteration

	def __len__(self):
		return len(self.content)

	def __str__(self):
		return f"{self.wsize:2d} : {''.join([str(x) for x in self.content])}"
