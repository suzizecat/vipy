
class Access:
	def __init__(self, itf_wr = True, itf_rd = True,des_wr = False, des_rd = True):
		self.is_writable_by_itf = itf_wr
		self.is_readable_by_itf = itf_rd
		self.is_writable_by_design = des_wr
		self.is_readable_by_design = des_rd


access_mapping = {
	"RW" : Access(itf_wr = True, itf_rd=True, des_wr=False, des_rd = True),
	"RO" : Access(itf_wr = False, itf_rd=True, des_wr=True, des_rd = True)
}
