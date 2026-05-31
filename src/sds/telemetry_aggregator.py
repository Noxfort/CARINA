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
        # Initialize the periodic data collector with Waze/Maps-like update frequency
        self.periodic_collector = PeriodicDataCollector(update_interval=update_interval)
        
        # Keep legacy buffer for backward compatibility
        self.heatmap_buffer: Dict[str, Dict[str, float]] = {}
        self.last_update_time = 0.0
        self.update_interval = update_interval
        
        # Visualization settings
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
        # Send data to periodic collector for Waze/Maps-style aggregation
        edge_data = {}
        for edge_id, state in frame.edges.items():
            edge_data[edge_id] = {
                'occupancy': state.occupancy,
                'speed': state.mean_speed,
                'queue': state.queue_length
            }
        
        self.periodic_collector.add_sample(frame.timestamp, edge_data)
        
        # Maintain legacy buffer for backward compatibility
        if self.last_update_time == 0.0:
            self.last_update_time = frame.timestamp

        for edge_id, state in frame.edges.items():
            if edge_id not in self.heatmap_buffer:
                self.heatmap_buffer[edge_id] = {'occ': 0.0, 'spd': 0.0, 'q': 0.0, 'count': 0}
            
            buf = self.heatmap_buffer[edge_id]
            buf['occ'] += state.occupancy
            buf['spd'] += state.mean_speed
            buf['q'] += state.queue_length
            buf['count'] += 1

    def should_update(self, current_time: float) -> bool:
        """
        Checks if enough time has passed to trigger a dashboard update.
        """
        return (current_time - self.last_update_time) >= self.update_interval

    def compute_rich_payload(self, current_time: float, maturity_cache: Dict[str, str]) -> Dict[str, Any]:
        """
        Generates the 'rich' payload containing averaged metrics and maturity states
        for the UI using the new periodic collector. Falls back to legacy method if needed.

        Args:
            current_time (float): The current simulation/system time.
            maturity_cache (Dict): Current maturity state of agents (e.g. {'tls_1': 'ADULT'}).

        Returns:
            Dict: The payload ready to be sent to the SDS queue.
        """
        # Try to get data from the new periodic collector first
        periodic_payload = self.periodic_collector.compute_aggregated_payload(current_time, maturity_cache)
        if periodic_payload:
            logging.debug(f"[TelemetryAggregator] Using periodic collector data with {len(periodic_payload['edges'])} edges")
            return periodic_payload
            
        # Fallback to legacy method if periodic collector didn't produce data
        rich_payload = {
            'timestamp': current_time,
            'edges': {},
            'maturity': maturity_cache
        }
        
        # Group by fundamental street ID (strip leading '-' and trailing '#...')
        # to unify bidirectional and multi-segment roads into a single visual entity
        grouped_stats = {}
        for edge_id, buf in self.heatmap_buffer.items():
            count = buf['count']
            if count > 0:
                # 1. Strip directional polarity
                base_id = edge_id[1:] if edge_id.startswith('-') else edge_id
                # 2. Strip segment indices (e.g., "123#0" becomes "123")
                if '#' in base_id:
                    base_id = base_id.split('#')[0]
                
                if base_id not in grouped_stats:
                    grouped_stats[base_id] = {'occ': [], 'spd': [], 'q': [], 'original_edges': []}
                    
                # Store individual values for more accurate statistics
                grouped_stats[base_id]['occ'].append(buf['occ'] / count)
                grouped_stats[base_id]['spd'].append(buf['spd'] / count)
                grouped_stats[base_id]['q'].append(buf['q'] / count)
                grouped_stats[base_id]['original_edges'].append(edge_id)
                
        # Process each street group with improved algorithm
        for base_id, buf in grouped_stats.items():
            occ_values = buf['occ']
            spd_values = buf['spd']
            q_values = buf['q']
            
            if not occ_values:
                continue
                
            # Compute more robust statistics
            avg_occ = statistics.mean(occ_values)
            median_occ = statistics.median(occ_values)
            
            avg_spd = statistics.mean(spd_values) if spd_values else 0.0
            median_spd = statistics.median(spd_values) if spd_values else 0.0
            
            avg_q = statistics.mean(q_values) if q_values else 0.0
            median_q = statistics.median(q_values) if q_values else 0.0
            
            # Improved Professional Heatmap Logic
            # More realistic free flow speeds based on road types
            free_flow_speed = 13.89  # 50 km/h baseline for urban roads
            
            # Adjust free flow speed based on occupancy (lower occupancy might indicate higher speed limits)
            if avg_occ < 0.1:
                free_flow_speed = 16.67  # 60 km/h for low occupancy roads
            elif avg_occ > 0.7:
                free_flow_speed = 11.11  # 40 km/h for high occupancy roads
                
            # Calculate speed ratio using median for robustness
            if median_spd > 0:
                speed_ratio = min(median_spd / free_flow_speed, 1.0)
            else:
                speed_ratio = 0.0
                
            # Base congestion on velocity loss (using median for robustness)
            velocity_congestion = 1.0 - speed_ratio
            
            # Improved queue saturation calculation
            # Use 90th percentile queue length to account for peaks
            q_90th = 0.0
            if q_values:
                q_90th = statistics.quantiles(q_values, n=10)[8] if len(q_values) > 10 else max(q_values)
            
            # Dynamic queue threshold based on road occupancy
            queue_threshold = 15.0
            if avg_occ < 0.3:
                queue_threshold = 20.0  # Higher threshold for less occupied roads
            elif avg_occ > 0.7:
                queue_threshold = 10.0  # Lower threshold for highly occupied roads
                
            q_ratio = min(q_90th / queue_threshold, 1.0) if q_90th >= 0 else 0.0
            
            # Final congestion score: 0 to 100%
            # Weight velocity and queue factors differently
            congestion_percent = (0.7 * velocity_congestion + 0.3 * q_ratio) * 100.0
            
            # Enhanced ghost jam filtering
            # Consider both occupancy and queue length, plus speed
            if (avg_occ < 0.02 and avg_q < 1) or (median_spd < 0.1 and avg_q < 0.5):
                congestion_percent = 0.0
                
            # Additional filtering for very low congestion
            if congestion_percent < 5.0:
                congestion_percent = 0.0
            
            # Apply unified score to all original SUMO edges of this street
            for original_edge in buf['original_edges']:
                rich_payload['edges'][original_edge] = {
                    'congestion': congestion_percent,
                    'speed': median_spd * 3.6, # Convert m/s to km/h using median
                    'vehicles': int(median_q),   # Use median queue length
                    'flow': 0 # Flow is calculated differently, usually kept 0 here for HFT
                }
        
        # Reset state for next cycle
        self.heatmap_buffer.clear()
        self.last_update_time = current_time
        
        return rich_payload
    
    def reset(self) -> None:
        """Manually clears the buffer."""
        self.heatmap_buffer.clear()
        self.last_update_time = 0.0
        self.periodic_collector.reset()