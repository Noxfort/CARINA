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

# File: src/engine/state_extractor.py
# Author: Gabriel Moraes
# Date: February 19, 2026

import logging
import sys
import os
import numpy as np
import sumolib
from typing import TYPE_CHECKING, Dict, List, Any

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

# Add 'src' directory to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

class StateExtractor:
    """
    The "Translator" of the HFT environment.
    Converts raw Synapse data into tensors for the AI,
    using the static topology extracted from the .net.xml map.
    """

    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        self.locale_manager = locale_manager
        self.lm = locale_manager
        
        self.tl_incoming_edges: Dict[str, List[str]] = {}
        self.tl_green_phases: Dict[str, List[int]] = {}
        
        # Maps ID_SEMAFORO -> { ID_FASE: STRING_ESTADO }
        self.tl_phase_codes: Dict[str, Dict[int, str]] = {}
        
        # NEW: Maps ID_SEMAFORO -> List of Lane Lists by Index
        # Ex: 'C1' -> [ ['edge1_0', 'edge1_1'], ['edge2_0'] ]
        # Where the index of the external list matches the character in the state string.
        self.tl_controlled_lanes_map: Dict[str, List[List[str]]] = {}
        
        self.topology_loaded = False
        
        logging.info(self.lm.get_string("state_extractor.init.sensor_created", fallback="StateExtractor (HFT) inicializado."))

    def load_topology(self, net_file_path: str):
        """
        Reads the .net.xml file and maps connections.
        """
        logging.info(f"Carregando topologia do mapa: {net_file_path}")
        try:
            net = sumolib.net.readNet(net_file_path, withInternal=False)
            
            self.tl_incoming_edges.clear()
            self.tl_green_phases.clear()
            self.tl_phase_codes.clear()
            self.tl_controlled_lanes_map.clear()
            
            for tls in net.getTrafficLights():
                tl_id = tls.getID()
                incoming_edges = set()
                controlled_lanes_by_index = []
                
                try:
                    # tls.getConnections() returns a list of connection lists.
                    # The order of this external list exactly matches the indices of the state string (ryg).
                    connections_list = tls.getConnections()
                    
                    for link_index, link_connections in enumerate(connections_list):
                        lanes_for_this_index = []
                        
                        for item in link_connections:
                            lane_obj = None
                            # Robust Lane/Edge Extraction
                            if hasattr(item, 'getFromLane'): # modern sumolib
                                lane_obj = item.getFromLane()
                            elif hasattr(item, 'getEdge'): # old sumolib or direct Lane object
                                lane_obj = item
                            
                            if lane_obj:
                                # Save Lane ID for Map View UI
                                lanes_for_this_index.append(lane_obj.getID())
                                
                                # Guard Edge ID for AI State Vector
                                if hasattr(lane_obj, 'getEdge'):
                                    edge = lane_obj.getEdge()
                                    if edge:
                                        incoming_edges.add(edge.getID())
                        
                        controlled_lanes_by_index.append(lanes_for_this_index)

                except Exception as e_conn:
                    logging.warning(f"Erro ao extrair conexões para TLS {tl_id}: {e_conn}")

                self.tl_incoming_edges[tl_id] = sorted(list(incoming_edges))
                self.tl_controlled_lanes_map[tl_id] = controlled_lanes_by_index
                
                # Program Extraction (Phases and Colors)
                programs = tls.getPrograms()
                self.tl_phase_codes[tl_id] = {}
                
                if programs:
                    logic = next(iter(programs.values())) 
                    green_phases = []
                    
                    for i, phase in enumerate(logic.getPhases()):
                        state = phase.state
                        self.tl_phase_codes[tl_id][i] = state
                        
                        lower_state = state.lower()
                        if 'g' in lower_state and 'y' not in lower_state:
                            green_phases.append(i)
                            
                    self.tl_green_phases[tl_id] = green_phases
                else:
                    self.tl_green_phases[tl_id] = [0, 2]

            self.topology_loaded = True
            logging.info(f"Topologia carregada. {len(self.tl_incoming_edges)} semáforos mapeados.")
            
        except Exception as e:
            logging.error(f"Erro fatal ao ler topologia com sumolib: {e}", exc_info=True)
            self.topology_loaded = False

    def extract_state(self, traffic_frame: Dict[str, Any], tl_id: str, current_phase_idx: int) -> np.ndarray:
        """
        Extracts the state using HFT-vectorized comprehension arrays, avoiding slow python .extend() loops.
        """
        if not self.topology_loaded:
            return np.array([], dtype=np.float32)

        incoming_edges = self.tl_incoming_edges.get(tl_id, [])
        if not incoming_edges:
            return np.array([], dtype=np.float32)

        edges_data = traffic_frame.get('edges', {})
        default_edge = {'occupancy': 0.0, 'mean_speed': 0.0, 'queue_length': 0}
        
        # O(1) Vectorized tuple expansion via C-backend list comprehension
        sensor_data = [
            val 
            for edge_id in incoming_edges
            for state in (edges_data.get(edge_id, default_edge),)
            for val in (state['occupancy'], min(state['mean_speed'] / 13.89, 1.0), min(state['queue_length'] / 20.0, 1.0))
        ]

        valid_green_phases = self.tl_green_phases.get(tl_id, [])
        num_green_phases = max(len(valid_green_phases), 1)

        phase_one_hot = [0.0] * num_green_phases
        if current_phase_idx in valid_green_phases:
            try:
                phase_one_hot[valid_green_phases.index(current_phase_idx)] = 1.0
            except ValueError: pass
        
        # Pedestrian Call status (from hardware telemetry)
        ped_calls = 0.0
        if 'tls_telemetry' in traffic_frame:
            telemetry = traffic_frame['tls_telemetry'].get(tl_id, {})
            ped_calls = 1.0 if telemetry.get('active_ped_calls', 0) > 0 else 0.0
            
        return np.array(sensor_data + phase_one_hot + [ped_calls], dtype=np.float32)

    def get_observation_space_size(self, tl_id: str) -> int:
        if not self.topology_loaded: return 0
        num_edges = len(self.tl_incoming_edges.get(tl_id, []))
        num_phases = len(self.tl_green_phases.get(tl_id, []))
        if num_phases == 0: num_phases = 1
        return (num_edges * 3) + num_phases + 1 # +1 for pedestrian calls

    def get_phase_lane_states(self, tl_id: str, phase_index: int) -> Dict[str, str]:
        """
        Returns a dictionary { lane_id: 'G'|'r'|'y' } for the UI.
        Converts the raw state string using the topology map.
        """
        if not self.topology_loaded: return {}
        
        state_string = self.tl_phase_codes.get(tl_id, {}).get(phase_index, "")
        lanes_map = self.tl_controlled_lanes_map.get(tl_id, [])
        
        result = {}
        
        # Iterates over the string (ex: "GrGr")
        # The character at index 'i' applies to all lanes in lanes_map[i]
        for i, char_state in enumerate(state_string):
            if i < len(lanes_map):
                target_lanes = lanes_map[i]
                for lane_id in target_lanes:
                    result[lane_id] = char_state
                    
        return result