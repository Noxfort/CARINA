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
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: src/sas/topology_recorder_bridge.py
# Author: Gabriel Moraes
# Date: 2026-06-09

import logging

class TopologyRecorderBridge:
    """
    Extracts edge topology (length, lanes, max_speed) from the SUMO net file
    and pushes it to the TrafficDataRecorder for sample enrichment.
    """
    def __init__(self, traffic_data_recorder, locale_manager):
        self.traffic_data_recorder = traffic_data_recorder
        self.locale_manager = locale_manager

    def update_recorder_topology(self, net_file_path: str):
        if not self.traffic_data_recorder or not net_file_path:
            return
        try:
            from utils.network_topology_parser import NetworkTopologyParser
            parser = NetworkTopologyParser(self.locale_manager)
            _, junction_incoming_edges = parser.build(net_file_path)
            
            # Flatten all edges into a single dict of {edge_id: {length, lanes, max_speed}}
            topology_edges = {}
            for j_id, edges in junction_incoming_edges.items():
                for edge_id, edge_data in edges.items():
                    topology_edges[edge_id] = {
                        'length': edge_data.get('length', 0),
                        'lanes': edge_data.get('num_lanes', 1),
                        'max_speed': edge_data.get('speed_limit', 13.89),
                    }
            self.traffic_data_recorder.set_topology(topology_edges)
        except Exception as e:
            logging.warning(f"[TopologyRecorderBridge] Failed to update recorder topology: {e}")
