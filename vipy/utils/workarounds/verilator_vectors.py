import typing as T
from math import prod
from copy import  copy
import os


def is_verilator() -> bool :
	return os.environ["SIM"] == "verilator"

def sign_bin_to_int(val : int,wsize = 8) :
	mask = (2**wsize) - 1
	if val & (1 << (wsize-1)):
		nval = -(((val ^ mask) & mask) +1)
	else :
		nval = val & mask

	return nval

def int_to_sign_bin(val : int,wsize = 8) :
	mask = (2**wsize) - 1
	if val < 0 :
		nval = ((abs(val) ^ mask) +1) & mask
	else :
		nval = val & mask
	return nval
	

def int_to_vector(v: T.Union[int, T.List[T.Any]], vdim: T.List[int],signed=False) -> T.List[int]:
	"""
	Convert a binary value into a list of integer
	"""
	if len(vdim) == 0:
		return v
	if isinstance(v, int):
		nv = [c for c in f"{v:0{prod(vdim)}b}"]
		nv.reverse()
		return int_to_vector(nv, vdim,signed)

	word_group_size = vdim[-1]
	if isinstance(v[0], str):
		curr_word = str()
	else:
		curr_word = list()
	nv = list()

	if len(vdim) == 1:
		return v

	for c in v:
		curr_word += c
		if len(curr_word) == word_group_size:
			if isinstance(curr_word, str):
				new_value = int(curr_word[::-1], 2)
				if signed :
					new_value = sign_bin_to_int(new_value,len(curr_word))
				nv.append(new_value)
				curr_word = ""
			else:
				nv.append(copy(curr_word))
				curr_word.clear()

	return int_to_vector(nv, vdim[:-1],signed)


def vector_to_int(v, wsize):
	"""
	Convert a list of integer into a concatenated integer.
	"""
	ret = list()
	if hasattr(v[0], '__iter__'):
		for e in v:
			ret.extend(e)
		return vector_to_int(ret)
	else:
		new_v = list()
		for x in v :
			if isinstance(x,int) and x < 0 :
				x = int_to_sign_bin(x,wsize)
			new_v.append(x)
		return int("".join(reversed([(f"{x:0{wsize}b}" if isinstance(x, int) else x) for x in new_v])), 2)