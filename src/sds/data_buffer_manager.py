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
            # Add data to buffer
            for edge_id, metrics in edge_data.items():
                self.data_buffer[edge_id]['occ'].append(metrics.get('occupancy', 0.0))
                self.data_buffer[edge_id]['spd'].append(metrics.get('speed', 0.0))
                self.data_buffer[edge_id]['q'].append(metrics.get('queue', 0.0))
            
            self.stats['samples_collected'] += 1
            
            # Prevent buffer from growing too large
            if self.stats['samples_collected'] % 1000 == 0:
                self._trim_buffer()

    def get_buffer_data(self) -> Dict[str, Dict[str, list]]:
        """
        Gets a copy of the current buffer data.
        
        Returns:
            Dict: Current buffer data
        """
        with self.buffer_lock:
            # Return a deep copy of the buffer data
            buffer_copy = {}
            for edge_id, metrics in self.data_buffer.items():
                buffer_copy[edge_id] = {
                    'occ': metrics['occ'].copy(),
                    'spd': metrics['spd'].copy(),
                    'q': metrics['q'].copy()
                }
            return buffer_copy

    def clear_buffer(self) -> None:
        """
        Clears the buffer data.
        """
        with self.buffer_lock:
            self.data_buffer.clear()

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