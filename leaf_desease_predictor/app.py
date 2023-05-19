#!/usr/bin/python3

import os
import yaml
from typing import Dict
from pathlib import Path
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.flux_table import TableList


logger = logging.getLogger("leaf-wetness-bridge")
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)
logger.setLevel('DEBUG')


@dataclass
class RecordStruct():
    time: datetime 
    field: str
    value: float
    def __repr__(self):
        kws = [f"{key}={value!r}" for key, value in self.__dict__.items()]
        return "{}({})".format(type(self).__name__, ", ".join(kws))

class datetime_isclose():
    """Implements 'datetime' comparing, inspired by 'math.isclose(s)'."""

    __permitted_dimensions__ = ['seconds', 'milliseconds', 'seconds', 'minutes', 'hours', 'days', 'weeks']
    
    @classmethod
    def is_close(cls, a: datetime, b: datetime, tol: int = 0, tol_dim: str = 'seconds') -> bool:
        f"""Compare two datetime objects according to tolerance.

        Args:
            a (datetime): first datetime
            b (datetime): second datetime
            tol (int, optional): tolerance. Defaults to 0.
            tol_dim (str, optional): tolerance dimension. Possible values: ['seconds', 'milliseconds', 'seconds', 'minutes', 'hours', 'days', 'weeks'].
        Returns:
            result (bool)
        """
        assert tol_dim in cls.__permitted_dimensions__, f"Wrong tolerance dimension {tol_dim}, available ones: {cls.__permitted_dimensions__}"
        return (b - a) <= timedelta(**{tol_dim: tol})


class LeafDeseasePredictor():
    
    DEFAULT_CONFIG_FILE = os.path.join(os.curdir, 'config.yaml')
    
    def __init__(self, config_file: Path = Path(DEFAULT_CONFIG_FILE)) -> None:
        self.config = self.load_config(config_file=config_file)
        self.client = influxdb_client.InfluxDBClient(
            url=self.config['server']['url'],
            token=os.environ['INFLUXDB_TOKEN'],
            org=self.config['server']['org'])
    
    def load_config(self, config_file: Path) -> Dict:
        """Load configuration

        Args:
            config_file (Path): path to config file

        Returns:
            Dict: config dict
        """
        logger.info(f"Using configuration file: {config_file}")
        return yaml.safe_load(open(config_file).read())

    def get_record_from_db(self, field: str, topic: str, params: Dict = {}) -> RecordStruct:
        tables = self._get_tables_by_query(field, params=params)
        record = self._get_record_from_tables(tables, topic)
        if not record:
            raise Exception("Cannot get record from database")
        logger.info(f"Got '{field}' from '{self.config['server']['bucket']}': {record}")
        return record

    def _get_tables_by_query(self, field: str, params: Dict = {}) -> TableList:
        if not self.client.ping():
            raise Exception("Cannot ping influxdb server")
        query_api = self.client.query_api()
        return query_api.query(
            f'''from(bucket: "{self.config['server']['bucket']}")
                |> range(start: -2m)
                |> filter(fn: (r) => r["_measurement"] == "{self.config['server']['measurement']}")
                |> filter(fn: (r) => r["_field"] == "{field}")
                |> last()
            ''', params=params)

    def _get_record_from_tables(self, tables: TableList, topic: str) -> RecordStruct|None:
        for table in tables:
            for _record in table.records:
                if _record['topic'] == topic:
                    return RecordStruct(time = _record["_time"], field = _record["_field"], value = _record['_value'])
        return None

    def write_severity(self, value: float, location: str):
        """Write severitu to DB.

        Args:
            value (float): severity value
            location (str): location of station
        """
        field = 'LeafDiseaseSeverity'
        write_api = self.client.write_api(write_options=SYNCHRONOUS)
        point = influxdb_client.Point("mqtt").tag("location", location).field(field, value)
        write_api.write(bucket=self.config['server']['bucket'], org=self.config['server']['org'], record=point)
        logger.info(f"Written to {self.config['server']['bucket']}: {point}")

    def calculate_severity(self, temperature: float, wetness: float) -> float:
        """Calculate severity.

        Args:
            temperature (int): temperatue
            wetness (int): wetness duration

        Returns:
            float: disease severity
        """
        asymptote = -0.5506 + (0.1221 * temperature) + (-0.0025 * (temperature**2))
        rate = (8.1517/temperature) * math.exp(-0.5 * ((math.log(temperature/28.5159)/0.6577)**2))
        severity = asymptote * (1 - math.exp(-rate * wetness))**(-1/(1-1.0553)) 
        logger.info(f"Calculated severity for t={temperature}, w={wetness}: {severity}")
        return severity

    def run(self):
        for mapping in self.config['mappings']:            
            temperature = self.get_record_from_db("LeafTemperature", mapping['topic'])
            wetness = self.get_record_from_db("LeafWetness", mapping['topic'])

            if datetime_isclose.is_close(temperature.time, wetness.time, tol=1, tol_dim='minutes'):
                severity = self.calculate_severity(temperature.value, wetness.value)
                self.write_severity(severity, location=mapping['location'])
        

def main():
    predictor = LeafDeseasePredictor()
    predictor.run()

if __name__ == '__main__':
    main()
