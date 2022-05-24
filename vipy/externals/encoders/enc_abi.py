from dataclasses import dataclass

import cocotb
from cocotb import RunningTask
from cocotb.handle import ModifiableObject
from cocotb.triggers import NextTimeStep
from .enc_base import EncoderBase


class EncoderABI(EncoderBase):
	@dataclass
	class ABIInterface:
		a: ModifiableObject = None
		b: ModifiableObject = None
		i: ModifiableObject = None

	def __init__(self, resolution = 360, position = 0, itf : ABIInterface = ABIInterface()):
		super().__init__(resolution*4,position)
		self.itf = itf

		self.drive_process : RunningTask = None

	def abi_from_position(self):
		a_value = (self.position % 4) in [1,2]
		b_value = (self.position % 4) in [2,3]
		i_value = self.position == 0

		return (a_value,b_value,i_value)

	async def update_abi(self):
		while True:
			await self.evt.pos_changed.wait()
			(self.itf.a.value,self.itf.b.value,self.itf.i.value) = self.abi_from_position()
			await NextTimeStep()

	async def start(self):
		self.drive_process = await cocotb.start(self.update_abi())
		await super().start()


