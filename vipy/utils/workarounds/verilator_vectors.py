import typing as T
from math import prod
from copy import  copy

def int_to_vector(v: T.Union[int, T.List[T.Any]], vdim: T.Tuple[int]) -> T.List[int]:
	if len(vdim) == 0:
		return v
	if isinstance(v, int):
		nv = [c for c in f"{v:0{prod(vdim)}b}"]
		nv.reverse()
		return int_to_vector(nv, vdim)

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

				nv.append(int(curr_word[::-1], 2))
				curr_word = ""
			else:
				nv.append(copy(curr_word))
				curr_word.clear()

	return int_to_vector(nv, vdim[:-1])


def vector_to_int(v, wsize):
	ret = list()
	if hasattr(v[0], '__iter__'):
		for e in v:
			ret.extend(e)
		return vector_to_int(ret)
	else:
		return int("".join(reversed([(f"{x:0{wsize}b}" if isinstance(x, int) else x) for x in v])), 2)