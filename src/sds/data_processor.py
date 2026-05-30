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

# File: src/sds/data_processor.py
# Author: Gabriel Moraes
# Date: February 21, 2026

import logging
import os
import sys
import configparser
from collections import defaultdict
from typing import TYPE_CHECKING, Union

# Adds the 'src' directory to the path to allow absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from utils.map_generator import generate_map_data_files
from utils.map_data_parser import parse_map_data
from utils.network_parser import build_lane_to_edge_map

from sds.tls_state_formatter import TlsStateFormatter
from sds.weights_manager import WeightsManager
from sds.street_metrics_calculator import StreetMetricsCalculator

class DataProcessor:
    """
    Orchestrator component that processes raw simulation data
    and formats it for the UI (Dashboard) using specialized delegates.
    """

    def __init__(self, settings: configparser.ConfigParser, locale_manager: 'LocaleManagerBackend'):
        self.locale_manager = locale_manager
        
        # Instantiate specialists
        self.weights_manager = WeightsManager(settings, project_root)
        self.metrics_calculator = StreetMetricsCalculator()
        
        # Read heatmap update interval from settings
        self.heatmap_update_interval = 5.0  # Default value
        try:
            if settings.has_section('HEATMAP_UPDATES'):
                self.heatmap_update_interval = settings.getfloat('HEATMAP_UPDATES', 'update_interval_seconds', fallback=5.0)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            logging.warning("[DataProcessor] Could not read heatmap update interval from settings, using default 5.0s")
        
        self.map_data = None
        self.lane_to_edge_map = None
        self.geometry_sent = False
        self.edge_to_lanes_map = defaultdict(list)
        
        logging.info(self.locale_manager.get_string("sds_processor.init.processor_created"))

    def process_for_ui(self, raw_data: Union[dict, tuple]) -> dict | None:
        """
        Processes incoming data (HFT Tuple or Legacy Dict) and returns the UI packet.
        """
        self.weights_manager.check_for_live_updates()

        # --- HFT COMMAND HANDLING (High Frequency / Tuples) ---
        if isinstance(raw_data, tuple):
            msg_type, payload = raw_data
            
            if msg_type == "initial_map_geometry":
                self.geometry_sent = True
                return { "type": "initial_map_geometry", "payload": {} }
            
            elif msg_type == "update_heatmap":
                return { "type": "congestion_update", "payload": payload.get("edges", {}) }
            
            elif msg_type == "hft_rich_update":
                edges_data = payload.get("edges", {})
                
                congestion_map = {}
                street_info_map = {}
                
                for edge_id, data in edges_data.items():
                    congestion_map[edge_id] = data.get('congestion', 0.0)
                    street_info_map[edge_id] = data 
                
                maturity_data = payload.get("maturity", {})
                
                # Delegate to the specialized formatter (clean call)
                panel_data = TlsStateFormatter.prepare_panel_data(raw_data=payload)
                
                return {
                    "type": "congestion_update", 
                    "payload": congestion_map,
                    "street_data": street_info_map,     
                    "panel_data": panel_data,           
                    "maturity_phases": maturity_data    
                }
            
            return None

        # --- LEGACY DATA HANDLING (Standard SUMO Dicts) ---
        if not self.map_data:
            net_file = raw_data.get("net_file")
            scenario = raw_data.get("scenario_name")
            if net_file:
                self._lazy_load_map_data(net_file_path=net_file, scenario_name=scenario)
        
        if not raw_data or not self.map_data or not self.lane_to_edge_map:
            return None
        
        # Delegate street calculations
        street_data_payload = self.metrics_calculator.calculate_street_data(
            raw_data=raw_data,
            lane_to_edge_map=self.lane_to_edge_map,
            edge_to_lanes_map=self.edge_to_lanes_map,
            heatmap_weights=self.weights_manager.get_weights(),
            aggregation_strategy=self.weights_manager.get_aggregation_strategy()
        )
        
        congestion_for_heatmap = { street_id: data.get('congestion', 0.0) for street_id, data in street_data_payload.items() }
        
        # Delegate TLS state formatting (clean call)
        panel_data = TlsStateFormatter.prepare_panel_data(raw_data=raw_data)
        
        maturity_phases_data = raw_data.get("maturity_phases", {})
        
        if not self.geometry_sent:
            nodes, edges, _ = self.map_data
            self.geometry_sent = True
            return {
                "type": "initial_map_geometry", "geometry": {"nodes": nodes, "edges": edges},
                "congestion_update": congestion_for_heatmap, "panel_data": panel_data,
                "street_data": street_data_payload, "maturity_phases": maturity_phases_data
            }
        else:
            return {
                "type": "congestion_update", "payload": congestion_for_heatmap,
                "panel_data": panel_data, "street_data": street_data_payload,
                "maturity_phases": maturity_phases_data
            }

    def _lazy_load_map_data(self, net_file_path: str, scenario_name: str):
        if self.map_data and self.lane_to_edge_map: return
        lm = self.locale_manager
        try:
            from src.utils.paths import get_base_output_dir
            results_dir = os.path.join(get_base_output_dir(), "results", scenario_name)
            map_data_prefix = os.path.join(results_dir, "maps", f"{scenario_name}_map")
            
            if not os.path.exists(map_data_prefix + ".nod.xml"):
                 if net_file_path and os.path.exists(net_file_path):
                    generate_map_data_files(net_file_path=net_file_path, output_dir=results_dir, lm=self.locale_manager)
            
            if os.path.exists(map_data_prefix + ".nod.xml"):
                self.map_data = parse_map_data(map_data_prefix)
                
            if net_file_path and os.path.exists(net_file_path):
                self.lane_to_edge_map = build_lane_to_edge_map(net_file_path, self.locale_manager)
                if self.lane_to_edge_map:
                    for lane_id, edge_id in self.lane_to_edge_map.items(): 
                        self.edge_to_lanes_map[edge_id].append(lane_id)
        except Exception as e:
            logging.error(lm.get_string("sds_processor.load_map.error", error=e), exc_info=True)