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

# File: src/sds/tls_map_extractor.py
# Author: Gabriel Moraes
# Date: 2026-02-24

"""
Description:
Parses SUMO network files (.net.xml or .net.xml.gz) to extract physical 
traffic light definitions. It maps phase strings (e.g., 'GGggrrrr') to 
specific incoming edges, serving as the ground truth for UI color rendering.
Applies traffic engineering logic to collapse multiple simulated movements 
into a single realistic physical traffic light color per approach, prioritizing 
straight movements.
"""

import xml.etree.ElementTree as ET
import gzip
import logging
import os

class TlsMapExtractor:
    """
    Knowledge extractor for network topologies.
    Reads the physical map to understand which edge receives which color 
    during a specific traffic light phase, filtering out micro-simulation noise.
    """

    # Stores phase strings for each traffic light
    # Key: tl_id (str), Value: dict of {phase_idx (int): state_string (str)}
    _tl_phases = {}

    # Maps linkIndex in the state string to the incoming edge ID and movement direction
    # Key: tl_id (str), Value: dict of {linkIndex (int): {'edge': from_edge (str), 'dir': direction (str)}}
    _tl_connections = {}

    @classmethod
    def load_network(cls, file_path: str):
        """
        Reads the .net.xml.gz map and populates the internal knowledge base.
        
        Args:
            file_path (str): The absolute or relative path to the map file.
        """
        if not os.path.exists(file_path):
            logging.error(f"[TlsMapExtractor] Map file not found: {file_path}")
            return

        try:
            if file_path.endswith('.gz'):
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    tree = ET.parse(f)
            else:
                tree = ET.parse(file_path)
            
            root = tree.getroot()

            # 1. Parse Traffic Light Logic (Phases)
            for tl_logic in root.findall('tlLogic'):
                tl_id = tl_logic.get('id')
                if tl_id not in cls._tl_phases:
                    cls._tl_phases[tl_id] = {}
                
                for idx, phase in enumerate(tl_logic.findall('phase')):
                    cls._tl_phases[tl_id][idx] = phase.get('state', '')

            # 2. Parse Connections (Mapping linkIndex to Incoming Edges & Directions)
            for conn in root.findall('connection'):
                tl_id = conn.get('tl')
                if tl_id:
                    link_index = conn.get('linkIndex')
                    from_edge = conn.get('from')
                    dir_attr = conn.get('dir', 's') # Defaults to straight ('s') if unknown
                    
                    if link_index is not None and from_edge is not None:
                        if tl_id not in cls._tl_connections:
                            cls._tl_connections[tl_id] = {}
                        cls._tl_connections[tl_id][int(link_index)] = {
                            'edge': from_edge,
                            'dir': dir_attr.lower()
                        }

            logging.info(f"[TlsMapExtractor] Successfully loaded phases for {len(cls._tl_phases)} traffic lights.")

        except Exception as e:
            logging.error(f"[TlsMapExtractor] Error parsing map: {e}")

    @classmethod
    def get_edge_colors_for_phase(cls, tl_id: str, phase_idx: int) -> dict:
        """
        Resolves the color of each incoming edge for a specific phase,
        using traffic engineering priorities (Straight > Left > Right).
        
        Args:
            tl_id (str): Traffic light ID.
            phase_idx (int): The current active phase index.
            
        Returns:
            dict: Mapping of edge_id to its respective color character ('G', 'y', 'r').
        """
        edge_colors = {}
        
        if tl_id not in cls._tl_phases or tl_id not in cls._tl_connections:
            return edge_colors
            
        phases = cls._tl_phases[tl_id]
        
        if phase_idx not in phases:
            if not phases:
                return edge_colors
            phase_idx = list(phases.keys())[0]
            
        state_str = phases[phase_idx]
        connections = cls._tl_connections[tl_id]
        
        for link_idx, data in connections.items():
            if link_idx < len(state_str):
                edge_id = data['edge']
                direction = data['dir'].upper()
                color = state_str[link_idx]
                
                focal_group = f"{edge_id} ({direction})"
                
                # Normalize color
                if color.lower() == 'g':
                    norm_color = 'G'
                elif color.lower() == 'y':
                    norm_color = 'y'
                else:
                    norm_color = 'r'
                    
                # Prioritize Green > Yellow > Red for the same focal group
                if focal_group not in edge_colors:
                    edge_colors[focal_group] = norm_color
                else:
                    if norm_color == 'G':
                        edge_colors[focal_group] = 'G'
                    elif norm_color == 'y' and edge_colors[focal_group] == 'r':
                        edge_colors[focal_group] = 'y'

        return edge_colors
        
    @classmethod
    def get_all_focal_groups_for_tl(cls, tl_id: str) -> list:
        if tl_id not in cls._tl_connections:
            return []
        
        groups = set()
        for data in cls._tl_connections[tl_id].values():
            groups.add(f"{data['edge']} ({data['dir'].upper()})")
        return list(groups)