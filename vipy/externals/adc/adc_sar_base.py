from dataclasses import dataclass
from secrets import randbits

from cocotb import Task
from cocotb.handle import ModifiableObject
from cocotb.clock import get_sim_steps
from cocotb.triggers import *
from vipy.structure import *


class AdcSarBase(GenericDriver):
	@dataclass
	class Interface:
		clk : ModifiableObject
		i_start : ModifiableObject
		i_en : ModifiableObject
		i_chan : ModifiableObject
		o_eoc : ModifiableObject
		o_data : ModifiableObject

	def __init__(self,itf : "AdcSarBase.Interface"):
		super().__init__()
		self.itf = itf

		self.resolution = self.itf.o_data.value.n_bits
		self.req_enable_len = get_sim_steps(100,"ns")
		self.req_start_time = get_sim_steps(10, "ns")
		self.req_clk_cycles_conversion = self.resolution

		self.evt_pu_done = Event("adc_pu_done")
		self.evt_start_done = Event("adc_start_done")
		self.evt_acq_done = Event("adc_acq_done")
		self.evt_pd = Event("adc_power_down")

		self.register_itf_as_driven("o_*")

		self._power_process : Task = None
		self._adc_process : Task = None

	def fit_timings(self,clk_period,cycles_pu,cycles_start,cycles_conversion) :
		base_time = clk_period
		self.req_enable_len = cycles_pu * base_time
		self.req_start_time = cycles_start * base_time
		self.req_clk_cycles_conversion = cycles_conversion

	def post_build(self):
		self._log.llow(f"ADC SAR Timing parameters are:")
		self._log.llow(f"  POWER-UP    : {get_time_from_sim_steps(self.req_enable_len,'ns')} ns")
		self._log.llow(f"  START PULSE : {get_time_from_sim_steps(self.req_start_time,'ns')} ns")
		self._log.llow(f"  CONV. CYCLEs: {self.req_clk_cycles_conversion} cycles")
	

	@drive_method
	async def reset(self):
		self._log.llow(f"Reset requested")
		if self._adc_process is not None :
			self._log.debug(f"Kill ADC process")
			self._adc_process.kill()		
			self._adc_process = None	
		if self._power_process is not None :
			self._log.debug(f"Kill main process")
			self._power_process.kill()
			self._power_process = None
		self._log.debug(f"Reset drivers")
		await self.reset_drivers()
		self.itf.o_eoc.value = 0
		self.itf.o_data.value = 0
		self._log.debug(f"Restart power process")
		self._power_process = cocotb.start_soon(self.handle_enable())

	async def handle_enable(self):
		self._log.debug(f"Start power handler")
		pd_evt = FallingEdge(self.itf.i_en)
		self._log.llow(f"ADC SAR : Enable detected")
		while True :
			if self._adc_process is not None :
				self._log.debug(f"Kill a running ADC process")
				self._adc_process.kill()
				self._adc_process = None
				self.itf.o_eoc.value = 0
				self.itf.o_data.value = 0
			await RisingEdge(self.itf.i_en)
			self.evt_pd.clear()
			trigger = await First(pd_evt,Timer(self.req_enable_len))
			if trigger is pd_evt :
				continue
			self.evt_pu_done.set()
			self._adc_process = await cocotb.start(self.adc_process())
			await pd_evt
			self._log.llow("Power down event detected")
			self.evt_pu_done.clear()
			self.evt_pd.set()

	def provide_value(self):
		return randbits(self.resolution)

	@drive_method
	async def adc_process(self):
		start_len_ok = Timer(self.req_start_time)
		rising_start = RisingEdge(self.itf.i_start)
		while True:
			if self.itf.i_start.value == 0:
				await rising_start
			if self.itf.o_eoc.value == 1 :
				self.itf.o_eoc.value = 0
				self.itf.o_data.value = 0
			trigger = await First(start_len_ok,FallingEdge(self.itf.i_start))
			if trigger is not start_len_ok :
				self._log.warning(f"START pulse duration was too short and therefore ignored.")
				continue
			self.evt_start_done.set()
			trigger = await First(ClockCycles(self.itf.clk,self.req_clk_cycles_conversion),rising_start)
			if trigger is rising_start :
				self._log.warning(f"START rose before the acquisition was done. The acquisition is ignored.")
				continue
			self.itf.o_eoc.value = 1
			self.itf.o_data.value = self.provide_value()









