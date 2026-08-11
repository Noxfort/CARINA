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

# File: src/utils/network_topology_parser.py (NEW FILE)
# Author: Gabriel Moraes
# Date: October 13, 2025

import logging
import xml.etree.ElementTree as ET
import gzip
from collections import defaultdict
from typing import TYPE_CHECKING, Tuple, Dict

if TYPE_CHECKING:
    from .locale_manager_backend import LocaleManagerBackend

class NetworkTopologyParser:
    """
    A specialist in reading a SUMO .net.xml file and extracting
    its network topology.
    """
    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        """
        Initializes the topology parser.
        """
        self.locale_manager = locale_manager

    def build(self, net_file_path: str) -> Tuple[Dict, Dict]:
        """
        Reads a .net.xml file and builds the network topology.

        Args:
            net_file_path (str): The path to the .net.xml file.

        Returns:
            A tuple containing (junction_types, incoming_edges_by_junction).
        """
        lm = self.locale_manager
        junction_types = {}
        junction_incoming_edges = defaultdict(dict)

        try:
            opener = gzip.open if net_file_path.endswith('.gz') else open
            with opener(net_file_path, 'rb') as f:
                tree = ET.parse(f)
            
            root = tree.getroot()

            # Extracts the type of each junction (e.g. 'traffic_light')
            for junction in root.findall('junction'):
                j_id = junction.get('id')
                j_type = junction.get('type')
                if j_id and j_type:
                    junction_types[j_id] = j_type

            # Maps the streets (edges) that reach each junction
            # Also extracts length and speed_limit from lane attributes
            edge_connections = {}
            for edge in root.findall('edge'):
                j_id = edge.get('to')
                edge_id = edge.get('id')
                from_node = edge.get('from')
                
                if edge_id and from_node and j_id and not edge_id.startswith(':'):
                    edge_connections[edge_id] = (from_node, j_id)

                if j_id and edge_id:
                    lanes = []
                    max_length = 0.0
                    max_speed = 0.0
                    for lane in edge.findall('lane'):
                        lane_id = lane.get('id')
                        if lane_id:
                            lanes.append(lane_id)
                        try:
                            lane_len = float(lane.get('length', 0))
                            if lane_len > max_length:
                                max_length = lane_len
                        except (ValueError, TypeError):
                            pass
                        try:
                            lane_speed = float(lane.get('speed', 0))
                            if lane_speed > max_speed:
                                max_speed = lane_speed
                        except (ValueError, TypeError):
                            pass
                    junction_incoming_edges[j_id][edge_id] = {
                        'lanes': lanes,
                        'num_lanes': len(lanes),
                        'length': max_length,
                        'speed_limit': max_speed,
                    }

            # Calculate unique neighbors for each junction to filter out dead-ends and non-intersections
            junction_neighbors = defaultdict(set)
            for edge_id, (from_n, to_n) in edge_connections.items():
                junction_neighbors[from_n].add(to_n)
                junction_neighbors[to_n].add(from_n)

            # Filter junction_types to keep only traffic lights or junctions with >= 3 distinct neighbors
            ignored_types = {'dead_end', 'internal', 'rail_crossing', 'rail_signal'}
            filtered_junction_types = {}
            for j_id, j_type in junction_types.items():
                if j_type == 'traffic_light':
                    filtered_junction_types[j_id] = j_type
                elif len(junction_neighbors[j_id]) >= 3 and j_type not in ignored_types:
                    filtered_junction_types[j_id] = j_type
            
            junction_types = filtered_junction_types

            # Filter junction_incoming_edges based on the filtered junctions
            filtered_incoming = defaultdict(dict)
            for j_id, edges in junction_incoming_edges.items():
                if j_id in junction_types:
                    filtered_incoming[j_id] = edges
            junction_incoming_edges = filtered_incoming
        
        except FileNotFoundError:
             logging.error(f"[TopologyParser] Network file not found at: {net_file_path}")
             return {}, defaultdict(dict)
        except Exception as e:
            # Translation key already exists in backend.json
            logging.error(lm.get_string("sas_engine.topology.critical_error", error=e), exc_info=True)
            return {}, defaultdict(dict)
        
        return junction_types, junction_incoming_edges