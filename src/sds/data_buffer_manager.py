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

# File: src/sds/data_buffer_manager.py
# Author: Gabriel Moraes
# Date: April 25, 2026

import logging
import threading
from collections import defaultdict
from typing import Dict, List


class DataBufferManager:
    """
    Manages the buffering of traffic data for periodic collection and aggregation.
    
    This class handles the storage and management of high-frequency traffic data
    before it's processed for visualization.
    """

    def __init__(self):
        """
        Initializes the DataBufferManager.
        """
        # Buffer structure: {edge_id: {'occ': list, 'spd': list, 'q': list}}
        self.data_buffer: Dict[str, Dict[str, list]] = defaultdict(lambda: {'occ': [], 'spd': [], 'q': []})
        
        # Lock for thread safety
        self.buffer_lock = threading.Lock()
        
        # Statistics for tracking data quality
        self.stats = {
            'samples_collected': 0,
            'buffer_overflows': 0
        }
        
        logging.info("[DataBufferManager] Initialized")

    def add_sample(self, timestamp: float, edge_data: Dict[str, Dict[str, float]]) -> None:
        """
        Adds a new sample to the collection buffer.
        
        Args:
            timestamp (float): The timestamp of the sample
            edge_data (Dict): Dictionary with edge_id as key and dict with 'occupancy', 'speed', 'queue' as values
        """
        with self.buffer_lock:
            # Add data to buffer as (timestamp, value) tuples
            for edge_id, metrics in edge_data.items():
                self.data_buffer[edge_id]['occ'].append((timestamp, metrics.get('occupancy', 0.0)))
                self.data_buffer[edge_id]['spd'].append((timestamp, metrics.get('speed', 0.0)))
                self.data_buffer[edge_id]['q'].append((timestamp, metrics.get('queue', 0.0)))
            
            self.stats['samples_collected'] += 1
            
            # Prevent buffer from growing too large
            if self.stats['samples_collected'] % 1000 == 0:
                self._trim_buffer()

    def get_buffer_data(self) -> Dict[str, Dict[str, list]]:
        """
        Gets a copy of the current buffer data, stripping the timestamps.
        
        Returns:
            Dict: Current buffer data as lists of floats
        """
        with self.buffer_lock:
            # Return a deep copy of the buffer data (stripping timestamps)
            buffer_copy = {}
            for edge_id, metrics in self.data_buffer.items():
                buffer_copy[edge_id] = {
                    'occ': [v for t, v in metrics['occ']],
                    'spd': [v for t, v in metrics['spd']],
                    'q': [v for t, v in metrics['q']]
                }
            return buffer_copy

    def clear_buffer(self) -> None:
        """
        Clears the buffer data entirely (legacy support).
        """
        with self.buffer_lock:
            self.data_buffer.clear()

    def trim_old_data(self, current_time: float, window: float = 60.0) -> None:
        """
        Removes data points older than the specified time window.
        
        Args:
            current_time (float): The current simulation timestamp
            window (float): The sliding window duration in seconds
        """
        cutoff_time = current_time - window
        with self.buffer_lock:
            empty_edges = []
            for edge_id, metrics in self.data_buffer.items():
                metrics['occ'] = [(t, v) for t, v in metrics['occ'] if t >= cutoff_time]
                metrics['spd'] = [(t, v) for t, v in metrics['spd'] if t >= cutoff_time]
                metrics['q']   = [(t, v) for t, v in metrics['q'] if t >= cutoff_time]
                
                if not metrics['occ'] and not metrics['spd'] and not metrics['q']:
                    empty_edges.append(edge_id)
            
            for edge_id in empty_edges:
                del self.data_buffer[edge_id]

    def _trim_buffer(self) -> None:
        """
        Trims buffer to prevent excessive memory usage.
        """
        max_samples_per_edge = 1000
        trimmed = 0
        
        for edge_id, buf in self.data_buffer.items():
            for metric in ['occ', 'spd', 'q']:
                if len(buf[metric]) > max_samples_per_edge:
                    # Keep the most recent samples
                    buf[metric] = buf[metric][-max_samples_per_edge:]
                    trimmed += 1
                    
        if trimmed > 0:
            self.stats['buffer_overflows'] += trimmed
            logging.warning(f"[DataBufferManager] Trimmed {trimmed} buffers to prevent overflow")

    def get_stats(self) -> Dict[str, int]:
        """
        Returns buffer manager statistics.
        
        Returns:
            Dict: Statistics
        """
        return self.stats.copy()

    def reset(self) -> None:
        """
        Resets the buffer manager state.
        """
        with self.buffer_lock:
            self.data_buffer.clear()
            self.stats = {
                'samples_collected': 0,
                'buffer_overflows': 0
            }