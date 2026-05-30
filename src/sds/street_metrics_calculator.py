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

# File: src/sds/street_metrics_calculator.py
# Author: Gabriel Moraes
# Date: February 21, 2026

from collections import defaultdict
from typing import Dict, Any

class StreetMetricsCalculator:
    """
    Specialist class responsible for calculating traffic metrics
    (flow, occupancy, speed, congestion index) for each street (edge).
    """

    def __init__(self):
        # Keeps track of vehicles from the previous simulation step to calculate flow
        self._last_step_vehicles_per_lane = {}

    def calculate_street_data(
        self,
        raw_data: dict,
        lane_to_edge_map: Dict[str, str],
        edge_to_lanes_map: Dict[str, list],
        heatmap_weights: Dict[str, float],
        aggregation_strategy: str
    ) -> dict:
        """
        Processes raw simulation step data to generate aggregated metrics for each street.
        """
        edge_data = defaultdict(lambda: {'occupancy': [], 'waiting_time': 0, 'flow_per_step': 0})
        step_length = raw_data.get('sim_step_length', 1.0)
        edge_speeds_ms = raw_data.get('edge_mean_speeds', {})
        current_vehicles_per_lane = raw_data.get('lane_vehicle_ids', {})
        
        # Factor to extrapolate step flow to flow per minute
        flow_conversion_factor = (60 / step_length) if step_length > 0 else 60
        
        for lane_id, occupancy in raw_data.get('lane_occupancies', {}).items():
            edge_id = lane_to_edge_map.get(lane_id)
            if edge_id: 
                edge_data[edge_id]['occupancy'].append(occupancy)
            
        for lane_id, waiting_time in raw_data.get('lane_waiting_time', {}).items():
            edge_id = lane_to_edge_map.get(lane_id)
            if edge_id: 
                edge_data[edge_id]['waiting_time'] += waiting_time
            
        # Calculate flow based on departed vehicles since last step
        if self._last_step_vehicles_per_lane:
            for lane_id, vehicles_before in self._last_step_vehicles_per_lane.items():
                edge_id = lane_to_edge_map.get(lane_id)
                if edge_id:
                    vehicles_after = set(current_vehicles_per_lane.get(lane_id, []))
                    departed_count = len(set(vehicles_before) - vehicles_after)
                    edge_data[edge_id]['flow_per_step'] += departed_count
                    
        self._last_step_vehicles_per_lane = current_vehicles_per_lane
        
        street_payload = {}
        for edge_id, data in edge_data.items():
            aggregated_occupancy = 0
            if data['occupancy']:
                if aggregation_strategy == 'max': 
                    aggregated_occupancy = max(data['occupancy'])
                else: 
                    aggregated_occupancy = sum(data['occupancy']) / len(data['occupancy'])
            
            flow_per_minute = data['flow_per_step'] * flow_conversion_factor
            
            congestion_index = (
                (aggregated_occupancy * 100 * heatmap_weights.get('weight_occupancy', 1.0)) + 
                (data['waiting_time'] * heatmap_weights.get('weight_waiting_time', 1.5)) + 
                (data['flow_per_step'] * heatmap_weights.get('weight_flow', -0.5))
            )

            lanes_for_this_edge = edge_to_lanes_map.get(edge_id, [])
            num_vehicles = sum(len(current_vehicles_per_lane.get(lane, [])) for lane in lanes_for_this_edge)
            speed_ms = edge_speeds_ms.get(edge_id, 0.0)
            speed_kmh = speed_ms * 3.6
            
            street_payload[edge_id] = { 
                "congestion": congestion_index, 
                "flow": int(round(flow_per_minute)), 
                "vehicles": num_vehicles, 
                "speed": round(speed_kmh, 1) 
            }
            
        return street_payload