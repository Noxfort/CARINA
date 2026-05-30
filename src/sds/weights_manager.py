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

# File: src/sds/weights_manager.py
# Author: Gabriel Moraes
# Date: February 21, 2026

import os
import json
import time
import logging
import configparser
from typing import Dict

class WeightsManager:
    """
    Specialist class responsible for managing and updating heatmap weights.
    It handles reading initial weights from settings and polling for live updates
    from the file system.
    """

    def __init__(self, settings: configparser.ConfigParser, project_root: str):
        self.project_root = project_root
        self.heatmap_weights = {}
        self.aggregation_strategy = 'max'
        
        self.live_weights_path = None
        self.last_weights_check_time = 0
        
        self._load_initial_settings(settings)

    def _load_initial_settings(self, settings: configparser.ConfigParser):
        """Loads the initial configuration from the main settings file."""
        try:
            cfg = settings['HEATMAP_SCALING']
            self.heatmap_weights = {
                'weight_occupancy': cfg.getfloat('weight_occupancy', 1.0),
                'weight_waiting_time': cfg.getfloat('weight_waiting_time', 1.5),
                'weight_flow': cfg.getfloat('weight_flow', -0.5)
            }
            self.aggregation_strategy = cfg.get('lane_aggregation_strategy', 'max')
        except (KeyError, configparser.NoSectionError):
            self.heatmap_weights = {
                'weight_occupancy': 1.0, 
                'weight_waiting_time': 1.5, 
                'weight_flow': -0.5
            }
            self.aggregation_strategy = 'max'
        
        logging.info(f"[WEIGHTS_MANAGER] Initial Heatmap Weights: {self.heatmap_weights}")

    def check_for_live_updates(self):
        """
        Checks if there is a new heatmap weights configuration file generated live
        in the latest simulation results directory and updates the internal state.
        """
        current_time = time.time()
        
        # Only check file system every 5 seconds to prevent I/O bottleneck
        if (current_time - self.last_weights_check_time) < 5: 
            return

        self.last_weights_check_time = current_time

        if not self.live_weights_path: 
            from src.utils.paths import get_base_output_dir
            results_dir = os.path.join(get_base_output_dir(), "results")
            if not os.path.isdir(results_dir): 
                return
            
            all_scenarios = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))]
            if not all_scenarios: 
                return

            latest_scenario_dir = max(all_scenarios, key=lambda d: os.path.getmtime(os.path.join(results_dir, d)))
            self.live_weights_path = os.path.join(results_dir, latest_scenario_dir, "heatmap_weights_live.json")

        if self.live_weights_path and os.path.exists(self.live_weights_path):
            try:
                with open(self.live_weights_path, "r", encoding="utf-8") as f:
                    new_weights = json.load(f)
                
                if new_weights != self.heatmap_weights:
                    self.heatmap_weights = new_weights
                    logging.info(f"[WEIGHTS_MANAGER] Heatmap weights updated live: {self.heatmap_weights}")

            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"[WEIGHTS_MANAGER] Error reading live weights file: {e}")
                
    def get_weights(self) -> Dict[str, float]:
        """Returns the current heatmap weights."""
        return self.heatmap_weights
        
    def get_aggregation_strategy(self) -> str:
        """Returns the configured lane aggregation strategy (e.g., 'max', 'avg')."""
        return self.aggregation_strategy