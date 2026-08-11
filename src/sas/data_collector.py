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

# File: src/sas/data_collector.py (FIXED FOR PERFORMANCE)
# Author: Gabriel Moraes
# Date: October 13, 2025

import logging
from collections import defaultdict, deque
import math
import sys
import os
from typing import TYPE_CHECKING

# Add 'src' directory to path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class DataCollector:
    """Accumulates performance and safety data of a simulation."""

    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        """Initializes the data accumulators."""
        self.locale_manager = locale_manager
        self.total_waiting_time_per_lane = defaultdict(float)
        self.total_vehicles_departed_per_lane = defaultdict(int)
        self.conflict_events_per_junction = defaultdict(int)
        self._last_step_vehicles_per_lane = {}
        # MEMORY FIX: Bounded buffer prevents indefinite growth in long-running sessions.
        # 10,000 entries ≈ ~4 MB max, covers sufficient history for heatmap calibration.
        self.calibration_data_points = deque(maxlen=10000)
        self._collect_step_counter = 0

        # --- PERFORMANCE FIX (Part 1): Cache Attributes ---
        self.lane_to_edge_map = None
        self.edge_to_lanes_map = None
        # --- END OF CORRECTION ---
        
        logging.info(self.locale_manager.get_string("sas_collector.init.collector_created"))

    def reset(self):
        """Clears all accumulated data for a new analysis cycle."""
        self.total_waiting_time_per_lane.clear()
        self.total_vehicles_departed_per_lane.clear()
        self.conflict_events_per_junction.clear()
        self._last_step_vehicles_per_lane.clear()
        self.calibration_data_points.clear()
        self._collect_step_counter = 0

        # Resets caches so they are reloaded on the next run
        self.lane_to_edge_map = None
        self.edge_to_lanes_map = None
        
        logging.info(self.locale_manager.get_string("sas_collector.reset.data_reset"))
    
    def _find_nearest_junction(self, event_pos: tuple, junction_positions: dict) -> str | None:
        if not junction_positions: return None
        nearest_junction_id = None
        min_dist_sq = float('inf')
        for j_id, j_pos in junction_positions.items():
            dist_sq = (event_pos[0] - j_pos[0])**2 + (event_pos[1] - j_pos[1])**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest_junction_id = j_id
        if math.sqrt(min_dist_sq) < 200:
            return nearest_junction_id
        return None

    def collect(self, raw_data: dict):
        if not raw_data: return
        self._collect_step_counter += 1

        # --- PERFORMANCE FIX (Part 2): Lazy Map Loading ---
        # It only reads the XML file the first time.
        if self.lane_to_edge_map is None:
            net_file = raw_data.get('net_file')
            if net_file:
                from utils.network_parser import build_lane_to_edge_map
                self.lane_to_edge_map = build_lane_to_edge_map(net_file, self.locale_manager)
                self.edge_to_lanes_map = defaultdict(list)
                if self.lane_to_edge_map:
                    for lane, edge in self.lane_to_edge_map.items():
                        self.edge_to_lanes_map[edge].append(lane)
        # --- END OF CORRECTION ---

        # Collection logic for infrastructure analysis (unchanged)
        lane_waiting_times = raw_data.get('lane_waiting_time', {})
        for lane_id, time in lane_waiting_times.items():
            self.total_waiting_time_per_lane[lane_id] += time
            
        current_vehicles_per_lane = raw_data.get('lane_vehicle_ids', {})
        if self._last_step_vehicles_per_lane:
            for lane_id, vehicles_before in self._last_step_vehicles_per_lane.items():
                vehicles_after = set(current_vehicles_per_lane.get(lane_id, []))
                departed_count = len(set(vehicles_before) - vehicles_after)
                self.total_vehicles_departed_per_lane[lane_id] += departed_count
        
        junction_positions = raw_data.get('junction_positions', {})
        emergency_positions = raw_data.get('sim_emergency_stop_positions', [])
        if emergency_positions and junction_positions:
            for event_pos in emergency_positions:
                nearest_junction = self._find_nearest_junction(event_pos, junction_positions)
                if nearest_junction:
                    self.conflict_events_per_junction[nearest_junction] += 1
        
        # Collection logic for heatmap calibration
        total_bad_events = len(emergency_positions) + raw_data.get('sim_starting_teleports_len', 0)

        # Create a snapshot for each street in this step
        if self.edge_to_lanes_map: # Only runs if the street map has been loaded
            for edge_id, lanes in self.edge_to_lanes_map.items():
                occupancies = [raw_data.get('lane_occupancies', {}).get(lane, 0.0) for lane in lanes]
                waiting_times = [raw_data.get('lane_waiting_time', {}).get(lane, 0.0) for lane in lanes]
                
                flow = 0
                if self._last_step_vehicles_per_lane:
                    for lane_id in lanes:
                        vehicles_before = set(self._last_step_vehicles_per_lane.get(lane_id, []))
                        vehicles_after = set(current_vehicles_per_lane.get(lane_id, []))
                        flow += len(vehicles_before - vehicles_after)

                self.calibration_data_points.append({
                    'occupancy': max(occupancies) if occupancies else 0.0,
                    'waiting_time': sum(waiting_times),
                    'flow': flow,
                    'bad_events': total_bad_events 
                })

        # MEMORY FIX: Shallow-copy only the lane IDs we need, breaking the reference
        # to the full raw_sim_data dict so the GC can free it promptly.
        self._last_step_vehicles_per_lane = {
            lane_id: list(veh_ids) for lane_id, veh_ids in current_vehicles_per_lane.items()
        }

    def get_accumulated_data(self) -> dict:
        processed_data = {
            "total_waiting_time_per_lane": dict(self.total_waiting_time_per_lane),
            "total_vehicles_departed_per_lane": dict(self.total_vehicles_departed_per_lane),
            "conflict_events_per_junction": dict(self.conflict_events_per_junction)
        }
        logging.info(self.locale_manager.get_string("sas_collector.get_data.data_processed"))
        return processed_data

    def get_calibration_data(self) -> list:
        return self.calibration_data_points