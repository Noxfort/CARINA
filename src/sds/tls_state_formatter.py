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

# File: src/sds/tls_state_formatter.py
# Author: Gabriel Moraes
# Date: 2026-02-24

"""
Description:
Specialist class responsible for formatting raw traffic light states
into structured dictionaries for the UI. 
It determines the exact number of physical traffic lights by counting
the number of incoming edges (approaching streets) to the junction
and delegates the state acquisition to the TlsStateProvider, passing 
the real telemetry phase.
"""

import os
import sys
import gzip
import xml.etree.ElementTree as ET
import logging

# Ensures the root directory and src are in the path to import utilities
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from sds.tls_state_provider import TlsStateProvider
from sds.tls_map_extractor import TlsMapExtractor

class TlsStateFormatter:
    """
    Specialist class responsible for formatting raw traffic light states
    into structured dictionaries for the UI.
    """

    _tl_incoming_edges = {}
    _map_loaded = False

    @classmethod
    def load_network_topology(cls, net_file_path: str):
        """
        Extracts the exact incoming edges (streets) for each traffic light junction.
        Initializes the Map Extractor to learn phase strings.
        """
        if cls._map_loaded or not net_file_path: 
            return
            
        cls._map_loaded = True
        try:
            if not os.path.exists(net_file_path): 
                logging.warning(f"[TlsStateFormatter] Arquivo .net.xml não encontrado: {net_file_path}")
                cls._map_loaded = False
                return

            # INJECTION OF THE KNOWLEDGE EXTRACTOR
            TlsMapExtractor.load_network(net_file_path)

            logging.info(f"[TlsStateFormatter] Lendo vias de aproximação do mapa estático: {net_file_path}")
            opener = gzip.open if net_file_path.endswith('.gz') else open
            with opener(net_file_path, 'rb') as f:
                tree = ET.parse(f)
                
            root = tree.getroot()
            count = 0
            
            # Find all edges and map them to their destination junction
            for edge in root.findall("edge"):
                to_junction = edge.get("to")
                edge_id = edge.get("id")
                func = edge.get("function", "")
                
                # Ignore internal intersection logic routes
                if func == "internal" or (edge_id and edge_id.startswith(":")):
                    continue
                
                if to_junction and edge_id:
                    if to_junction not in cls._tl_incoming_edges:
                        cls._tl_incoming_edges[to_junction] = []
                    
                    if edge_id not in cls._tl_incoming_edges[to_junction]:
                        cls._tl_incoming_edges[to_junction].append(edge_id)
                        count += 1
            
            logging.info(f"[TlsStateFormatter] Topologia carregada: {count} vias de aproximação mapeadas para os semáforos.")
                    
        except Exception as e:
            logging.error(f"[TlsStateFormatter] Erro crítico ao ler mapa estático: {e}", exc_info=True)

    @staticmethod
    def prepare_panel_data(raw_data: dict) -> dict:
        """
        Generates the visual state dictionary for Semaphores (Phase + Colors).
        Retrieves the state dynamically from the TlsStateProvider using the real telemetry phase.
        """
        tls_phases = raw_data.get('tls_phases', {})
        panel_data = {}
        
        hw_info_map = raw_data.get('hardware_status', {})
        
        for tl_id, phase in tls_phases.items():
            str_tl_id = str(tl_id)
            incoming_edges = TlsStateFormatter._tl_incoming_edges.get(str_tl_id, [])
            
            # Now passing tl_id and phase explicitly to the Provider
            junction_state = TlsStateProvider.get_live_states_for_junction(incoming_edges, str_tl_id, phase)

            # Retrieve brand & model if available in hardware status or query active ConnectionManager
            tl_hw = hw_info_map.get(str_tl_id, {}) or hw_info_map.get(tl_id, {})
            brand = tl_hw.get("brand")
            model = tl_hw.get("model")

            if not brand or brand in ["Não informado", "Desconectado"]:
                try:
                    from src.controller.connection_manager import HardwareConnectionManager
                    conn_hw = HardwareConnectionManager.get_global_hardware_info(str_tl_id)
                    if conn_hw:
                        brand = conn_hw.get("brand", "Desconectado")
                        model = conn_hw.get("model", "Desconectado")
                except Exception:
                    pass

            brand = brand if brand else "Desconectado"
            model = model if model else "Desconectado"
                
            panel_data[str_tl_id] = { 
                "phase": phase, 
                "lanes_state": junction_state.get("lanes_state", {}),
                "display_state": junction_state.get("display_state", "RED"),
                "brand": brand,
                "model": model
            }
            
        return panel_data