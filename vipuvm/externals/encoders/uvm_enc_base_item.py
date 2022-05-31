import random

import pyuvm
from pyuvm import *


class ItemEncoderSetSpeed(uvm_sequence_item):
	def __init__(self,name,speed_tr_per_sec):
		super().__init__(name)
		self.speed = abs(speed_tr_per_sec)
		self.direction = speed_tr_per_sec >= 0

	def randomize(self):
		rand_max =  ConfigDB().get(None,"","enc.rand_max_value") if ConfigDB().exists(None,"","enc.rand_max_value") else 1000
		self.speed = random.randint(1,rand_max)
		self.direction = random.randint(0,1)

	def __str__(self):
		return f"Encoder Speed setting : direction {'DIR' if self.direction else 'REV'} - {self.speed}"

	def __eq__(self, other):
		return self.speed == other.speed and self.direction == other.direction