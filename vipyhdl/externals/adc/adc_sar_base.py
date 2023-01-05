from dataclasses import dataclass
from secrets import randbits

from cocotb import Task
from cocotb.handle import ModifiableObject
from cocotb.clock import get_sim_steps
from cocotb.triggers import *
from vipy.structure import *
from vipy.drivers import *
import typing as T

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

		self.drv_eoc = SignalDriver(self.itf.o_eoc)
		self.drv_data = SignalDriver(self.itf.o_data)

		self.register_remaining_signals_as_driven("o_*")

		self._power_process : Task = None
		self._adc_process : Task = None

		self.queued_values : T.Dict[int, T.List[int]] = {i:list() for i in range(2 ** self.itf.i_chan.value.n_bits)}

	def fit_timings(self,clk_period,cycles_pu,cycles_start,cycles_conversion) :
		base_time = clk_period
		self.req_enable_len = cycles_pu * base_time
		self.req_start_time = cycles_start * base_time
		self.req_clk_cycles_conversion = cycles_conversion

	def post_build(self):
		self._log.llow(f"ADC SAR Timing parameters are:\n"
					   f"  POWER-UP    : {get_time_from_sim_steps(self.req_enable_len,'ns')} ns"
					   f"  START PULSE : {get_time_from_sim_steps(self.req_start_time,'ns')} ns"
					   f"  CONV. CYCLEs: {self.req_clk_cycles_conversion} cycles")


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
		await self.reset_all()
		self.clear_queued_values()
		self._log.debug(f"Restart power process")
		self._power_process = cocotb.start_soon(self.handle_enable())

	async def handle_enable(self):
		self._log.debug(f"Start power handler")
		pd_evt = FallingEdge(self.itf.i_en)
		
		while True :
			if self._adc_process is not None :
				self._log.debug(f"Kill a running ADC process")
				self._adc_process.kill()
				self._adc_process = None
				self.itf.o_eoc.value = 0
				self.itf.o_data.value = 0
			await RisingEdge(self.itf.i_en)
			self._log.llow(f"ADC SAR : Enable detected")
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
		chan = self.itf.i_chan.value.integer
		if len(self.queued_values[chan]) :
			return self.queued_values[chan].pop(0)
		else :
			return randbits(self.resolution)

	def clear_queued_values(self):
		for q in self.queued_values.values():
			q.clear()

	@drive_method
	async def adc_process(self):
		start_len_ok = Timer(self.req_start_time)
		rising_start = RisingEdge(self.itf.i_start)
		self._log.debug("ADC Process started")
		while True:
			if self.itf.i_start.value == 0:
				self._log.llow(f"Await start")
				await rising_start
				self._log.llow(f"Start detected")
			if self.itf.o_eoc.value == 1 :
				self.itf.o_eoc.value = 0
				self.itf.o_data.value = 0
			trigger = await First(start_len_ok,FallingEdge(self.itf.i_start))
			if trigger is not start_len_ok :
				self._log.warning(f"START pulse duration was too short and therefore ignored.")
				continue
			self.evt_start_done.set()
			self._log.debug("Await conversion")
			trigger = await First(ClockCycles(self.itf.clk,self.req_clk_cycles_conversion),rising_start)
			self._log.debug("End of conversion")
			if trigger is rising_start :
				self._log.warning(f"START rose before the acquisition was done. The acquisition is ignored.")
				continue
			await self.drv_data.set(self.provide_value())
			#await self.drv_eoc.pulse(1,1,"ns")
			self.itf.o_eoc.value = 1


class AdcSarBaseMonitor(Monitor) :
	@dataclass
	class Eventlist:
		start : Event
		eoc : Event
	def __init__(self, itf = AdcSarBase.Interface):
		super().__init__()
		self.itf = itf

		self.evt = AdcSarBaseMonitor.Eventlist(start=Event("start"),eoc=Event("eoc"))

		self.add_edge_to_sensitivity(RisingEdge,[self.itf.o_eoc,self.itf.i_start])
		self.add_evt_to_autoreset([self.evt.eoc,self.evt.start])

		self.started_channel = None

	def monitor(self):
		self._log.debug(f"Triggered by {self._trigger_event!r}")
		if self.itf.i_start.value :
			self.started_channel = self.itf.i_chan.value.integer
			self._log.llow(f"ADC Conversion started on channel {self.started_channel}")
			self.evt.start.set(self.started_channel)
		if self.itf.o_eoc.value :
			value = self.itf.o_data.value.integer
			self._log.llow(f"ADC Conversion done for channel {self.started_channel}, value is {value} ")
			self.evt.eoc.set((self.started_channel,value))
			self.started_channel = None










