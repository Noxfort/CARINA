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

# File: ui/handlers/settings_handler.py
# Author: Gabriel Moraes
# Date: 2026-06-09

"""
Defines the SettingsHandler.

In this version, the responsibility of saving the .ini file has been removed.
The 'save_settings' method now only collects and validates UI data,
returning a dictionary ready to be sent to the backend via SettingsClient.
"""

import logging
from typing import Dict, Any
import configparser
import os

class SettingsHandler:
    """
    Manages the logic to load and validate UI settings.
    """
    # The map of keys to sections is still useful for initial reading
    _KEY_TO_SECTION_MAP = {
        'language': 'UI', 'theme_dark': 'UI',
        'min_green_time': 'TRAFFIC_RULES', 'yellow_time_seconds': 'TRAFFIC_RULES',
        'heatmap_strategy': 'HEATMAP_SCALING', 'heatmap_saturation': 'HEATMAP_SCALING',
        'performance_margin': 'MATURITY', 'child_phase_episodes': 'MATURITY',
        'teen_phase_min_episodes': 'MATURITY', 'child_promotion_max_entropy': 'MATURITY',
        'performance_check_window': 'MATURITY',
        'calibration_window_size': 'CALIBRATION',
        'ppo_gamma': 'AI_TRAINING', 'ppo_k_epochs': 'AI_TRAINING', 'ppo_eps_clip': 'AI_TRAINING',
        'dqn_epsilon_decay': 'GUARDIAN_AGENT', 'dqn_batch_size': 'GUARDIAN_AGENT',
        'pbt_frequency': 'PBT', 'pbt_exploitation': 'PBT',
        'watchdog_grace': 'WATCHDOG',
        'analysis_interval_value': 'ANALYSIS_SCHEDULE', 'analysis_interval_unit': 'ANALYSIS_SCHEDULE',
        'weight_waiting_time': 'REWARD_WEIGHTS', 'weight_flow': 'REWARD_WEIGHTS',
        'monitor_enabled': 'EXTERNAL_MONITOR', 'monitor_mqtt_host': 'EXTERNAL_MONITOR',
        'db_type': 'DATABASE', 'db_host': 'DATABASE', 'db_port': 'DATABASE',
        'db_user': 'DATABASE', 'db_password': 'DATABASE', 'db_name': 'DATABASE', 'db_connected': 'DATABASE',
        'tensorboard_enabled': 'TENSORBOARD', 'tensorboard_log_dir': 'TENSORBOARD'
    }

    def __init__(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.config_path = os.path.join(project_root, "config", "settings.ini")
        self.config = configparser.ConfigParser()
        self._defaults = self._get_default_settings_map()
        self._current_settings = self.load_settings()
        logging.info("[SettingsHandler] Settings Handler initialized and settings loaded.")

    def load_settings(self) -> Dict[str, Any]:
        """Reads the .ini file and returns a dictionary with the settings."""
        try:
            if not os.path.exists(self.config_path):
                logging.warning(f"[SettingsHandler] File {self.config_path} not found. Using defaults.")
                return self.get_default_settings()

            self.config.read(self.config_path, encoding='utf-8')
            loaded_settings = {}
            for key, section in self._KEY_TO_SECTION_MAP.items():
                if self.config.has_option(section, key):
                    value = self.config.get(section, key)
                    if value.lower() in ['true', 'false']:
                        loaded_settings[key] = self.config.getboolean(section, key)
                    elif '.' in value:
                        try: loaded_settings[key] = self.config.getfloat(section, key)
                        except ValueError: loaded_settings[key] = value
                    else:
                        try: loaded_settings[key] = self.config.getint(section, key)
                        except ValueError: loaded_settings[key] = value
                else:
                    loaded_settings[key] = self._defaults.get(key)
            
            for key, value in self._defaults.items():
                if key not in loaded_settings:
                    loaded_settings[key] = value

            return loaded_settings
        except Exception as e:
            logging.error(f"[SettingsHandler] Error loading settings: {e}. Using defaults.")
            return self.get_default_settings()

    # --- MAIN CHANGE HERE ---
    # This method no longer writes to the file. It just prepares the data.
    def prepare_settings_for_save(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates and prepares the new settings to be sent to the backend.
        For now, validation is simple (just collection), but can be expanded here.
        """
        # Updates current settings in UI memory
        self._current_settings.update(new_settings)
        logging.info("[SettingsHandler] New settings prepared for sending to the backend.")
        # Returns the complete payload, ready to be sent
        return new_settings

    def get_current_settings(self) -> Dict[str, Any]:
        return self._current_settings.copy()

    def get_default_settings(self) -> Dict[str, Any]:
        return self._defaults.copy()

    def _get_default_settings_map(self) -> Dict[str, Any]:
        """Returns the default settings dictionary."""
        return {
            'theme_dark': True, 'language': 'pt_br', 'min_green_time': '10',
            'yellow_time_seconds': '3', 'heatmap_strategy': 'max', 'heatmap_saturation': '100.0',
            'performance_margin': '-100.0', 'child_phase_episodes': '1',
            'teen_phase_min_episodes': '1', 'child_promotion_max_entropy': '2.0',
            'performance_check_window': '1', 'calibration_window_size': '10',
            'ppo_gamma': '0.99', 'ppo_k_epochs': '4', 'ppo_eps_clip': '0.2',
            'dqn_epsilon_decay': '30000', 'dqn_batch_size': '128',
            'pbt_frequency': '10', 'pbt_exploitation': '25',
            'watchdog_grace': '30',
            'analysis_interval_value': '7', 'analysis_interval_unit': 'days',
            'weight_waiting_time': '-2.0', 'weight_flow': '2.0',
            'monitor_enabled': 'False', 'monitor_mqtt_host': 'localhost',
            'db_type': 'sqlite', 'db_host': 'localhost', 'db_port': '5432',
            'db_user': 'admin', 'db_password': 'admin', 'db_name': 'carina_data', 'db_connected': 'False',
            'tensorboard_enabled': 'False', 'tensorboard_log_dir': 'results/tensorboard'
        }