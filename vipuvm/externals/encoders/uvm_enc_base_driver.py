import pyuvm
from pyuvm import *
from .uvm_enc_base_item import ItemEncoderSetSpeed
from vipy.externals.encoders import EncoderABI


class DriverEncoderABI(uvm_driver):
	def __init__(self,name,parent):
		super().__init__(name,parent)
		self.bridge : EncoderABI = None

	def start_of_simulation_phase(self):
		super().start_of_simulation_phase()
		resolution = ConfigDB().get(self,"","res")
		itf = ConfigDB().get(self,"","itf")
		self.bridge = EncoderABI(resolution=resolution,itf=itf)
		if ConfigDB().exists(self,"","init_pos") :
			self.bridge.position = ConfigDB().get(self,"","init_pos")

	async def run_phase(self):
		await self.bridge.start()
		while True:
			item = await self.seq_item_port.get_next_item()
			if isinstance(item,ItemEncoderSetSpeed) :
				self.bridge.speed_tr_per_sec = item.speed
				self.bridge.direction = item.direction
			else :
				raise TypeError(f"Got invalid item type{str(type(item))}")
			self.seq_item_port.item_done()

