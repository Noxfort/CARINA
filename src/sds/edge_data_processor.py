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

# File: src/sds/edge_data_processor.py
# Author: Gabriel Moraes
# Date: April 25, 2026

import logging
from typing import Dict, Any, List
import statistics


class EdgeDataProcessor:
    """
    Processes edge data for heatmap visualization, including grouping and congestion calculations.
    
    This class handles the transformation of raw edge data into aggregated metrics
    suitable for heatmap visualization.
    """

    def __init__(self):
        """
        Initializes the EdgeDataProcessor.
        """
        logging.info("[EdgeDataProcessor] Initialized")

    def group_edge_data(self, buffer_data: Dict[str, Dict[str, list]]) -> Dict[str, Dict]:
        """
        Groups edge data by fundamental street ID to unify bidirectional roads.
        
        Args:
            buffer_data (Dict): Raw buffer data with edge IDs as keys
            
        Returns:
            Dict: Grouped statistics
        """
        grouped_stats = {}
        
        for edge_id in buffer_data.keys():
            # Strip directional polarity and segment indices
            base_id = self._normalize_edge_id(edge_id)
            
            if base_id not in grouped_stats:
                grouped_stats[base_id] = {
                    'occ': [], 
                    'spd': [], 
                    'q': [], 
                    'original_edges': []
                }
            
            # Aggregate data from all segments
            buf = buffer_data[edge_id]
            grouped_stats[base_id]['occ'].extend(buf['occ'])
            grouped_stats[base_id]['spd'].extend(buf['spd'])
            grouped_stats[base_id]['q'].extend(buf['q'])
            grouped_stats[base_id]['original_edges'].append(edge_id)
            
        return grouped_stats

    def _normalize_edge_id(self, edge_id: str) -> str:
        """
        Normalizes edge ID by stripping directional and segment markers.
        
        Args:
            edge_id (str): Original edge ID
            
        Returns:
            str: Normalized base ID
        """
        # Strip directional polarity
        base_id = edge_id[1:] if edge_id.startswith('-') else edge_id
        # Strip segment indices
        if '#' in base_id:
            base_id = base_id.split('#')[0]
        return base_id

    def compute_congestion_metrics(self, buffer_data: Dict[str, list]) -> Dict[str, Any]:
        """
        Computes precise congestion metrics using improved professional algorithms.
        
        Args:
            buffer_data (Dict): Buffered data for a street group
            
        Returns:
            Dict: Computed metrics
        """
        occ_values = buffer_data['occ']
        spd_values = buffer_data['spd']
        q_values = buffer_data['q']
        
        if not occ_values:
            return {
                'congestion': 0.0,
                'speed': 0.0,
                'vehicles': 0,
                'flow': 0
            }
        
        # Compute more robust statistics
        avg_occ = statistics.mean(occ_values)
        median_occ = statistics.median(occ_values)
        
        # Safely compute harmonic mean for space-mean speed
        if spd_values:
            # Epsilon prevents division by zero for stopped vehicles
            epsilon = 0.1
            sum_inv = sum(1.0 / max(v, epsilon) for v in spd_values)
            harmonic_spd = len(spd_values) / sum_inv
        else:
            harmonic_spd = 0.0
        
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
            
        # Calculate speed ratio using harmonic mean (space-mean speed) for robustness
        # Handle potential edge cases where simulators might send km/h instead of m/s
        if harmonic_spd > 35.0: # 35 m/s = 126 km/h, very likely it's already in km/h
            harmonic_spd = harmonic_spd / 3.6
            
        if harmonic_spd > 0:
            speed_ratio = min(harmonic_spd / free_flow_speed, 1.0)
        else:
            speed_ratio = 0.0
            
        # Base congestion on velocity loss (using harmonic mean for space-mean precision)
        # Se a velocidade cai para menos de 30% do limite (ex: 15km/h numa via de 50km/h), é 100% congestionado.
        if speed_ratio < 0.3:
            velocity_congestion = 1.0
        else:
            # Escala suavemente de 0.3 até 1.0
            velocity_congestion = (1.0 - speed_ratio) / 0.7
        
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
        
        # Log to debug mock data inputs vs computed congestion
        logging.debug(f"[EdgeDataProcessor] Computed Congestion: {congestion_percent:.2f}% | Spd: {harmonic_spd:.2f} | Occ: {avg_occ:.2f} | Q: {q_90th:.2f}")
        
        # Additional filtering for very low congestion (reduced threshold)
        if congestion_percent < 1.0:
            congestion_percent = 0.0
        # Mathematical Flow Calculation (Flow - vehicles per hour)
        # From the fundamental equation of traffic flow: q = k * v (Flow = Density * Speed)
        # We estimate Density (vehicles/km) using the occupancy ratio.
        # Assuming maximum capacity of an average urban road as ~200 vehicles/km at full congestion (occupancy=1.0)
        estimated_density = avg_occ * 200.0 
        speed_kmh = harmonic_spd * 3.6
        calculated_flow = int(estimated_density * speed_kmh)
            
        return {
            'congestion': congestion_percent,
            'speed': speed_kmh,  # Convert m/s to km/h using harmonic mean
            'vehicles': int(median_q),   # Use median queue length
            'flow': calculated_flow
        }