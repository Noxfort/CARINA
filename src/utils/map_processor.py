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

# File: src/utils/map_processor.py
# Author: Gabriel Moraes - Noxfort Systems
# Date: 12/24/2025

import logging
import json
import time
import os
import sumolib  # type: ignore
from typing import Dict, Any

class MapProcessor:
    """
    Responsible for parsing SUMO network files (.net.xml) and extracting 
    topology data for the UI and system configuration.
    """

    @staticmethod
    def extract_topology_to_json(net_file: str, output_json: str) -> Dict[str, str]:
        """
        Reads .net.xml file and generates a JSON containing ALL junctions.
        Returns a dictionary mapping Traffic Light IDs to their initial maturity state (default 'CHILD').
        """
        logging.info(f"[MAP_GEN] Extracting vector data to: {output_json}")
        
        maturity_cache = {}
        
        try:
            net = sumolib.net.readNet(net_file, withInternal=False)
            
            bbox = net.getBBoxXY() 
            bounds = {
                "min_x": bbox[0][0], "min_y": bbox[0][1], 
                "max_x": bbox[1][0], "max_y": bbox[1][1]
            }
            
            edges_list = []
            for edge in net.getEdges():
                edges_list.append({
                    "id": edge.getID(),
                    "shape": list(edge.getShape())
                })
                
            nodes_list = []
            traffic_lights_count = 0
            junctions_count = 0
            
            ignored_types = {'dead_end', 'internal', 'rail_crossing', 'rail_signal'}

            for node in net.getNodes():
                n_type = node.getType()
                if n_type in ignored_types: continue
                
                if n_type == "traffic_light":
                    traffic_lights_count += 1
                    # Initialize default maturity
                    maturity_cache[node.getID()] = "CHILD" 
                else:
                    junctions_count += 1

                nx, ny = node.getCoord()
                node_data = { "id": node.getID(), "x": nx, "y": ny, "type": n_type }
                nodes_list.append(node_data)
                    
            topology_data = {
                "bounds": bounds, "edges": edges_list, "nodes": nodes_list,
                "metadata": {
                    "generated_at": time.time(), "total_tls": traffic_lights_count,
                    "total_junctions": junctions_count
                }
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_json), exist_ok=True)
            
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(topology_data, f)
                
            logging.info(f"[MAP_GEN] JSON generated. TLS: {traffic_lights_count}, Junctions: {junctions_count}")
            
            return maturity_cache

        except Exception as e:
            logging.error(f"[MAP_GEN] Critical error parsing map: {e}", exc_info=True)
            raise e