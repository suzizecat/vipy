import os
import logging
import csv
from ..structure import *
import typing as T
log = logging.getLogger(__name__)


class CSVReader:
	REGNAME = 1
	OFFSET = 2
	RESET = 3
	BITS = 4
	FNAME = 5
	ACCESS = 6
	COMMENT = 7

	def __init__(self):
		self.current_rb : RegisterBank = None
		self.current_reg: Register = None
		self.ignore_invalid = True

		self.process_reg = False
		self.process_field = False

		self._last_shadow = "DEFAULT"
		pass

	def read_csv(self,path : str):
		log.info(f"REGBANK : Read register bank CSV file {path}")
		required_path = os.path.abspath(path)
		if not os.path.exists(required_path) :
			log.error(f"Path {required_path} does not exists.")
			return

		with open(required_path,newline='') as csvfile :
			reader = csv.reader(csvfile)
			content = [line for line in reader]

			self.current_rb = RegisterBank(content[1][2].strip().strip("_"), int(content[3][2]), int(content[2][2]))
			Register.DEFAULT_SIZE = int(content[2][2])
			
			for line in content[5:] :
				try :
					self._process_csv_line(line)
				except KeyError as e :
					if self.ignore_invalid :
						log.error(f"Skipped invalid line {','.join(line)}")
						if self.process_reg :
							self.current_reg = None
							self.process_reg = False
							self.process_field = False
					else :
						log.fatal(f"A key error occured on line {line}")
						log.fatal(f": {e!s}")
						raise e

			self._validate_register()
			self._finalize_shadow_groups()

	def _process_csv_line(self, line : T.List[str]):
		nline = ["" for i in range(CSVReader.COMMENT +1)]
		self.process_reg = False
		self.process_field = False
		for i in range(len(line)) :
			nline[i] = line[i].strip()

		if nline[CSVReader.REGNAME] != "" :
			self.process_reg = True
			self._add_reg_from_line(nline)

		if nline[CSVReader.FNAME] != "" :
			if self.current_reg is not None :
				self.process_field = True
				self._add_field_from_line(nline)

	def _add_reg_from_line(self, line):
		self._validate_register()

		self.current_reg = Register(
			line[CSVReader.REGNAME],
			int(line[CSVReader.OFFSET],0),
			reset_value=int(line[CSVReader.RESET],0)
		)

	def _validate_register(self):
		if self.current_reg is not None:
			self.current_rb.add_register(self.current_reg)

	def _add_field_from_line(self, line):
		f = Field(line[CSVReader.FNAME],FieldSize.from_specifier(line[CSVReader.BITS]),line[CSVReader.ACCESS])
		if f.access.is_shadow:
			if "shadow" in f.access_attributes :
				self._last_shadow = f.access_attributes["shadow"]
			else :
				f.access_attributes["shadow"] = self._last_shadow
			self.current_rb.add_shadow_group(self._last_shadow).add_register(self.current_reg)
		self.current_reg.add_field(f)

	def _finalize_shadow_groups(self):
		for group in self.current_rb.shadow_groups.values() :
			access_names = [a.name for a in group.included_accesses]

			if "Wsh" in access_names or "RWsh" in access_names :
				group.trigger_position = ShadowGroup.TRIGGER_LAST




