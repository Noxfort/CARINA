# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/sas/analyzer_data_processor.py
# Author: Gabriel Moraes
# Date: July 18, 2026

from typing import Tuple
from utils.network_topology_parser import NetworkTopologyParser
from sas.sas_historical_data_processor import SASHistoricalDataProcessor
from sas.sas_accumulated_data_processor import SASAccumulatedDataProcessor


class AnalyzerDataProcessor:
    """
    Facade and Orchestrator class for processing raw simulation and database historical data
    for the AnalyzerEngine. Delegates execution to SASHistoricalDataProcessor and SASAccumulatedDataProcessor.
    """

    def __init__(self, locale_manager, topology_parser=None):
        self.locale_manager = locale_manager
        self.historical_processor = SASHistoricalDataProcessor(self.locale_manager)
        self.accumulated_processor = SASAccumulatedDataProcessor(self.locale_manager)
        self.topology_parser = topology_parser or NetworkTopologyParser(self.locale_manager)

    @property
    def topology_parser(self):
        return self._topology_parser

    @topology_parser.setter
    def topology_parser(self, value):
        self._topology_parser = value
        if hasattr(self, 'historical_processor'):
            self.historical_processor.topology_parser = value
        if hasattr(self, 'accumulated_processor'):
            self.accumulated_processor.topology_parser = value

    def process_historical_data(self, db_manager, net_file_path: str, limit_seconds: int = None) -> Tuple[dict, list]:
        """Processes historical database traffic records."""
        return self.historical_processor.process(db_manager, net_file_path, limit_seconds=limit_seconds)

    def process_accumulated_data(self, accumulated_data: dict, sim_duration: float, net_file_path: str) -> Tuple[dict, list]:
        """Processes accumulated simulation metrics from SUMO memory."""
        return self.accumulated_processor.process(accumulated_data, sim_duration, net_file_path)
