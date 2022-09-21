import os
import logging
import csv
from ..structure import *

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

			self.current_rb = RegisterBank(content[1][2], int(content[3][2]))
			Register.DEFAULT_SIZE = int(content[2][2])
			
			for line in content[5:] :
				try :
					self._process_csv_line(line)
				except KeyError as e :
					log.fatal(f"A key error occured on line {line}")
					log.fatal(f": {e!s}")
					raise e

			self._validate_register()

	def _process_csv_line(self, line : list[str]):
		nline = ["" for i in range(CSVReader.COMMENT +1)]

		for i in range(len(line)) :
			nline[i] = line[i].strip()

		if nline[CSVReader.REGNAME] != "" :
			self._add_reg_from_line(nline)

		if nline[CSVReader.FNAME] != "" :
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
		self.current_reg.add_field(f)





