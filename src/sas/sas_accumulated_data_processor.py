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

# File: src/sas/sas_accumulated_data_processor.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import logging
from typing import Tuple
from utils.network_topology_parser import NetworkTopologyParser
from sas.sas_helpers import EdgeClassifier, TrafficMetricsCalculator, SyntheticSampleGenerator


class SASAccumulatedDataProcessor:
    """
    Processes in-memory accumulated simulation metrics (departures, waiting times) for the AnalyzerEngine.
    """

    def __init__(self, locale_manager, topology_parser=None):
        self.locale_manager = locale_manager
        self.topology_parser = topology_parser or NetworkTopologyParser(self.locale_manager)

    def process(self, accumulated_data: dict, sim_duration: float, net_file_path: str) -> Tuple[dict, list]:
        """Processes accumulated simulation metrics into junction grouped data structures."""
        lm = self.locale_manager
        logging.info(lm.get_string("sas_engine.run.processing_data"))

        junction_types, junction_incoming_edges = self.topology_parser.build(net_file_path)

        if not junction_types or not junction_incoming_edges:
            logging.error(lm.get_string("sas_engine.topology.cannot_continue_error"))
            return {}, []

        true_traffic_light_ids = [j_id for j_id, j_type in junction_types.items() if j_type == 'traffic_light']

        processed_data = {}
        sim_duration_hours = sim_duration / 3600.0 if sim_duration > 0 else 1.0

        for j_id, incoming_edges in junction_incoming_edges.items():
            if not incoming_edges:
                continue

            # Calculate average volume for each incoming edge to use in classification
            edge_volumes = {}
            for edge_id, edge_data in incoming_edges.items():
                vehicles = sum(accumulated_data.get('total_vehicles_departed_per_lane', {}).get(lane, 0) for lane in edge_data['lanes'])
                edge_volumes[edge_id] = vehicles / sim_duration_hours

            sorted_edges, has_different_lanes, max_lanes, primary_ids = EdgeClassifier.classify(incoming_edges, edge_volumes)

            primary_edges = {}
            secondary_edges = {}
            primary_lanes = []
            secondary_lanes = []

            for edge_id, edge_data in sorted_edges:
                is_primary = (edge_data['num_lanes'] == max_lanes) if has_different_lanes else (edge_id in primary_ids)
                if is_primary:
                    primary_lanes.extend(edge_data['lanes'])
                else:
                    secondary_lanes.extend(edge_data['lanes'])

                vehicles = sum(accumulated_data.get('total_vehicles_departed_per_lane', {}).get(lane, 0) for lane in edge_data['lanes'])
                waiting_time = sum(accumulated_data.get('total_waiting_time_per_lane', {}).get(lane, 0) for lane in edge_data['lanes'])

                avg_volume = vehicles / sim_duration_hours
                avg_delay = waiting_time / vehicles if vehicles > 0 else 0.0

                edge_len = edge_data.get('length', 0.0)
                spd_lim = edge_data.get('speed_limit', 13.89)
                adjusted_speed_ms = TrafficMetricsCalculator.compute_adjusted_speed(edge_len, avg_delay, spd_lim)
                density = avg_volume / (adjusted_speed_ms * 3.6) if adjusted_speed_ms > 0.1 else 0.0

                rep_samples = SyntheticSampleGenerator.generate_accumulated(
                    edge_id=edge_id,
                    density=density,
                    adjusted_speed_ms=adjusted_speed_ms,
                    edge_len=edge_len,
                    num_lanes=edge_data.get('num_lanes', 1),
                    speed_limit=spd_lim
                )

                if is_primary:
                    primary_edges[edge_id] = rep_samples
                else:
                    secondary_edges[edge_id] = rep_samples

            primary_vehicles = sum(accumulated_data.get('total_vehicles_departed_per_lane', {}).get(lane, 0) for lane in primary_lanes)
            secondary_vehicles = sum(accumulated_data.get('total_vehicles_departed_per_lane', {}).get(lane, 0) for lane in secondary_lanes)
            secondary_wait_time = sum(accumulated_data.get('total_waiting_time_per_lane', {}).get(lane, 0) for lane in secondary_lanes)

            vol_primary = int(primary_vehicles / sim_duration_hours)
            vol_secondary = int(secondary_vehicles / sim_duration_hours)
            avg_delay_secondary = (secondary_wait_time / secondary_vehicles) if secondary_vehicles > 0 else 0

            # Wrap legacy data into the V2 format for compatibility
            processed_data[j_id] = {
                'primary_edges': primary_edges,
                'secondary_edges': secondary_edges,
                'conflict_events': accumulated_data.get('conflict_events_per_junction', {}).get(j_id, 0),
                'type': junction_types.get(j_id, 'unknown'),
                # Legacy fields (for backward compatibility with reports)
                "volume": vol_primary,
                "vol_secondary": vol_secondary,
                "avg_delay": avg_delay_secondary,
            }

        logging.info(lm.get_string("sas_engine.run.data_processed", count=len(processed_data)))
        return processed_data, true_traffic_light_ids
