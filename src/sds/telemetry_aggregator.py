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

# File: src/sds/telemetry_aggregator.py
# Author: Gabriel Moraes - Noxfort Systems
# Date: 12/24/2025

import logging
import time
import statistics
from typing import Dict, Any, Optional

# Use relative import to avoid circular dependency
from .periodic_data_collector import PeriodicDataCollector

class TelemetryAggregator:
    """
    Responsible for aggregating high-frequency traffic data into periodic
    updates for the Smart Dashboard Service (SDS).
    
    This class isolates the visualization logic (heatmap weights, normalization)
    from the core control logic.
    """

    def __init__(self, update_interval: float = 5.0) -> None:
        """
        Args:
            update_interval (float): Minimum seconds between visual updates (Waze/Maps style: 5-30 seconds).
        """
        self.periodic_collector = PeriodicDataCollector(update_interval=update_interval)
        self.last_update_time = 0.0
        self.update_interval = update_interval
        
        self.heatmap_weights = {
            'occupancy': 1.0,
            'queue': 0.8,
            'speed': -0.5
        }
        
        logging.info(f"[TelemetryAggregator] Initialized with {update_interval}s update interval")

    def process_frame(self, frame: Any) -> None:
        """
        Accumulates data from a single traffic frame into the aggregation buffer.
        """
        edge_data = {}
        for edge_id, state in frame.edges.items():
            edge_data[edge_id] = {
                'occupancy': state.occupancy,
                'speed': state.mean_speed,
                'queue': state.queue_length
            }
        
        self.periodic_collector.add_sample(frame.timestamp, edge_data)
        if self.last_update_time == 0.0:
            self.last_update_time = frame.timestamp

    def should_update(self, current_time: float) -> bool:
        """
        Checks if enough time has passed to trigger a dashboard update.
        """
        return (current_time - self.last_update_time) >= self.update_interval

    def compute_rich_payload(self, current_time: float, maturity_cache: Dict[str, str]) -> Dict[str, Any]:
        """
        Generates the 'rich' payload containing averaged metrics and maturity states
        for the UI using the periodic collector.

        Args:
            current_time (float): The current simulation/system time.
            maturity_cache (Dict): Current maturity state of agents (e.g. {'tls_1': 'ADULT'}).

        Returns:
            Dict: The payload ready to be sent to the SDS queue.
        """
        periodic_payload = self.periodic_collector.compute_aggregated_payload(current_time, maturity_cache)
        if periodic_payload:
            self.last_update_time = current_time
            return periodic_payload
            
        return {
            'timestamp': current_time,
            'edges': {},
            'maturity': maturity_cache
        }
    
    def reset(self) -> None:
        """Manually clears the buffer."""
        self.last_update_time = 0.0
        self.periodic_collector.reset()