import typing as T

class Access:
	def __init__(self,name : str, itf_wr = True, itf_rd = True,des_wr = False, des_rd = True, attributes : T.Dict[str,str] = None, is_shadow : bool = False):
		self.name = name
		self.attributes = dict().update(attributes) if attributes is not None else dict()
		self.is_writable_by_itf = itf_wr
		self.is_readable_by_itf = itf_rd
		self.is_writable_by_design = des_wr
		self.is_readable_by_design = des_rd
		self.is_shadow = is_shadow

	def __hash__(self):
		"""Only the name is a guarantee that two access are equals, as their behaviour will depend on implementation"""
		return hash(self.name)

access_mapping = {
	"RW" : Access("RW",itf_wr = True, itf_rd=True, des_wr=False, des_rd = True),
	"RO" : Access("RO",itf_wr = False, itf_rd=True, des_wr=True, des_rd = False),
	"Rsh": Access("Rsh",itf_wr = False, itf_rd=True, des_wr=True, des_rd = False,is_shadow=True),
	"RWsh": Access("RWsh",itf_wr = True, itf_rd=True, des_wr=False, des_rd = True,is_shadow=True),
	"RESERVED" : Access("RESERVED",itf_wr = False, itf_rd=False, des_wr=False, des_rd = False)
}
