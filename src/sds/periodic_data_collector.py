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

# File: src/sds/periodic_data_collector.py
# Author: Gabriel Moraes
# Date: April 25, 2026

import logging
from typing import Dict, Any, Optional

# Use relative imports to avoid circular dependencies
from .data_buffer_manager import DataBufferManager
from .edge_data_processor import EdgeDataProcessor
from .update_scheduler import UpdateScheduler


class PeriodicDataCollector:
    """
    Responsible for collecting traffic data at periodic intervals similar to 
    Waze and Google Maps update frequency, then applying precise color mathematics
    to generate accurate heatmap visualizations.
    
    This class acts as an orchestrator that delegates responsibilities to specialized components:
    - DataBufferManager: Handles data buffering
    - EdgeDataProcessor: Processes edge data for visualization
    - UpdateScheduler: Manages update timing
    """

    def __init__(self, update_interval: float = 5.0):
        """
        Args:
            update_interval (float): Seconds between visual updates (similar to Waze/Maps: 5-30 seconds).
        """
        self.update_scheduler = UpdateScheduler(update_interval)
        self.data_buffer_manager = DataBufferManager()
        self.edge_data_processor = EdgeDataProcessor()
        
        logging.info(f"[PeriodicDataCollector] Initialized with {update_interval}s update interval")

    def add_sample(self, timestamp: float, edge_data: Dict[str, Dict[str, float]]) -> None:
        """
        Adds a new sample to the collection buffer.
        
        Args:
            timestamp (float): The timestamp of the sample
            edge_data (Dict): Dictionary with edge_id as key and dict with 'occupancy', 'speed', 'queue' as values
        """
        # Set first sample time if not set
        self.update_scheduler.set_first_sample_time(timestamp)
        
        # Add data to buffer
        self.data_buffer_manager.add_sample(timestamp, edge_data)

    def should_update(self, current_time: float) -> bool:
        """
        Checks if enough time has passed to trigger a dashboard update.
        
        Args:
            current_time (float): The current timestamp
            
        Returns:
            bool: True if update is due
        """
        return self.update_scheduler.should_update(current_time)

    def compute_aggregated_payload(self, current_time: float, maturity_cache: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Computes aggregated metrics from buffered data for visualization.
        Resets the buffer after computation.
        
        Args:
            current_time (float): The current timestamp
            maturity_cache (Dict): Current maturity state of agents
            
        Returns:
            Dict or None: Aggregated payload ready for visualization, or None if no update is due
        """
        if not self.should_update(current_time):
            return None
            
        # Get buffer data
        buffer_data = self.data_buffer_manager.get_buffer_data()
        
        if not buffer_data:
            return None
                
        # Compute aggregated metrics
        aggregated_payload = {
            'timestamp': current_time,
            'edges': {},
            'maturity': maturity_cache
        }
        
        # Group by fundamental street ID to unify bidirectional roads
        grouped_stats = self.edge_data_processor.group_edge_data(buffer_data)
        
        # Compute congestion metrics for each street group
        for base_id, buf in grouped_stats.items():
            congestion_data = self.edge_data_processor.compute_congestion_metrics(buf)
            
            # Apply to all original edges of this street
            for original_edge in buf['original_edges']:
                aggregated_payload['edges'][original_edge] = congestion_data
        
        # Trim old data from buffer (60s sliding window) and update timestamp
        self.data_buffer_manager.trim_old_data(current_time, window=60.0)
        self.update_scheduler.update_last_update_time(current_time)
        
        logging.debug(f"[PeriodicDataCollector] Sent update with {len(aggregated_payload['edges'])} edges")
        return aggregated_payload

    def get_stats(self) -> Dict[str, int]:
        """
        Returns collector statistics.
        
        Returns:
            Dict: Statistics
        """
        buffer_stats = self.data_buffer_manager.get_stats()
        return {
            'samples_collected': buffer_stats['samples_collected'],
            'buffer_overflows': buffer_stats['buffer_overflows'],
            'updates_sent': 0  # This would need to be tracked separately
        }

    def reset(self) -> None:
        """
        Resets the collector state.
        """
        self.update_scheduler.reset()
        self.data_buffer_manager.reset()