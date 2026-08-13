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

# File: src/mfd/mfd_network_parser.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import os
import gzip
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Set, Tuple


class MFDNetworkParser:
    """
    Parses SUMO static network XML files (.net.xml / .net.xml.gz) to map
    edge lengths and junction-to-traffic-light connections.
    """

    def __init__(self, scenario_results_dir: str):
        self.scenario_results_dir = scenario_results_dir

    def find_network_file(self) -> str:
        """Locates the static SUMO network file in maps or results directory."""
        net_file = None
        maps_dir = os.path.join(self.scenario_results_dir, "maps")
        if os.path.exists(maps_dir):
            for f in os.listdir(maps_dir):
                if f.endswith(".net.xml") or f.endswith(".net.xml.gz"):
                    return os.path.join(maps_dir, f)

        try:
            from utils.paths import get_base_output_dir
            results_dir = os.path.join(get_base_output_dir(), "results")
            if os.path.exists(results_dir):
                for root, dirs, files in os.walk(results_dir):
                    for f in files:
                        if f.endswith(".net.xml") or f.endswith(".net.xml.gz"):
                            return os.path.join(root, f)
        except Exception:
            pass

        return None

    def parse_network(self) -> Tuple[Dict[str, float], Dict[str, str]]:
        """
        Parses the network XML to extract edge lengths and edge-to-traffic-light mappings.
        Returns (edge_lengths, edge_to_tl).
        """
        net_file = self.find_network_file()
        edge_lengths = {}
        edge_to_tl = {}
        tls_junctions = set()

        if not net_file:
            return edge_lengths, edge_to_tl

        try:
            opener = gzip.open if net_file.endswith('.gz') else open
            with opener(net_file, 'rb') as f:
                tree = ET.parse(f)
            root = tree.getroot()

            # Pass 1: Extract ONLY junctions with type='traffic_light'
            for junction in root.findall("junction"):
                j_type = junction.get("type")
                j_id = junction.get("id")
                if j_type == "traffic_light" and j_id:
                    tls_junctions.add(j_id)

            # Pass 2: Map incoming edges ONLY if the target junction is a traffic_light
            for edge in root.findall("edge"):
                edge_id = edge.get("id")
                to_junction = edge.get("to")
                func = edge.get("function", "")
                if func == "internal" or (edge_id and edge_id.startswith(":")):
                    continue

                length = 0.0
                for lane in edge.findall("lane"):
                    l_len = lane.get("length")
                    if l_len:
                        length = float(l_len)
                        break
                if length <= 0.0:
                    l_len = edge.get("length")
                    if l_len:
                        length = float(l_len)

                if edge_id:
                    if length > 0:
                        edge_lengths[edge_id] = length
                    if to_junction and to_junction in tls_junctions:
                        edge_to_tl[edge_id] = to_junction
        except Exception as e:
            logging.error(f"[MFDNetworkParser] Error parsing static network file {net_file}: {e}")

        return edge_lengths, edge_to_tl
