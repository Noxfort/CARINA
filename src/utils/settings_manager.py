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

# File: src/utils/settings_manager.py (ONLY resource_path ADDED)
# Author: Gabriel Moraes
# Date: October 22, 2025 # <-- DATE UPDATED

"""
Defines the SettingsManager, a backend class responsible for reading and
writing system configurations in the settings.ini file.
"""

import configparser
import os
import logging
from typing import Dict, Any

# Dotenv for 12-Factor App Secrets Management
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# --- CHANGE 1: Import resource_path ---
import sys
# Ensures that 'src' is in the path for relative import to work
project_root_sm = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path_sm = os.path.join(project_root_sm, 'src')
if src_path_sm not in sys.path:
    sys.path.insert(0, src_path_sm)
from src.utils.paths import resource_path # Import the function
# --- END OF CHANGE 1 ---

class SettingsManager:
    """
    Manages reading and writing to the 'settings.ini' configuration file.
    """
    _KEY_TO_SECTION_MAP = {
        'theme_dark': 'UI', 'language': 'UI',
        'green_time': 'TRAFFIC_RULES', 'yellow_time': 'TRAFFIC_RULES', # Note: Originally it had yellow_time_seconds, but the ui/handlers/settings_handler file uses yellow_time. Keeping yellow_time.
        'heatmap_strategy': 'HEATMAP_SCALING', 'heatmap_saturation': 'HEATMAP_SCALING',
        'log_progress': 'LOGGING', # Note: Original key can be log_step_progress
        'watchdog_grace': 'WATCHDOG', # Note: Originally it had initial_grace_period_seconds / heartbeat_timeout_seconds
        'analysis_interval_value': 'ANALYSIS_SCHEDULE', 'analysis_interval_unit': 'ANALYSIS_SCHEDULE',
        'performance_margin': 'MATURITY', # Note: Originally had performance_margin_percent
        'ppo_gamma': 'AI_TRAINING', 'ppo_k_epochs': 'AI_TRAINING', 'ppo_eps_clip': 'AI_TRAINING',
        'dqn_epsilon_decay': 'GUARDIAN_AGENT', 'dqn_batch_size': 'GUARDIAN_AGENT',
        'pbt_frequency': 'PBT', 'pbt_exploitation': 'PBT',
        # --- Add other keys/sections that need to be saved if they exist ---
        'weight_waiting_time': 'REWARD_WEIGHTS', 'weight_flow': 'REWARD_WEIGHTS',
        'update_frequency_seconds': 'GAT_STRATEGIST', # Added GAT
        # --- CARINA Monitor Integration ---
        'monitor_enabled': 'EXTERNAL_MONITOR',
        'monitor_mqtt_host': 'EXTERNAL_MONITOR',
        'monitor_mqtt_port': 'EXTERNAL_MONITOR',
        'monitor_mqtt_topic_heartbeat': 'EXTERNAL_MONITOR',
        'monitor_mqtt_topic_incident': 'EXTERNAL_MONITOR',
        
        # --- CARINA Database Settings ---
        'db_type': 'DATABASE', 'db_host': 'DATABASE', 'db_port': 'DATABASE',
        'db_user': 'DATABASE', 'db_password': 'DATABASE', 'db_name': 'DATABASE',
        'db_connected': 'DATABASE',
        
        'tensorboard_enabled': 'TENSORBOARD', 'tensorboard_log_dir': 'TENSORBOARD',
        
        # --- CARINA Universal Report Formatting Settings ---
        'decimal_separator': 'REPORT_FORMATTING',
        'report_logo_path': 'REPORT_FORMATTING',
        'report_city': 'REPORT_FORMATTING',
        'report_state_uf': 'REPORT_FORMATTING',
        'report_secretary_name': 'REPORT_FORMATTING',
        'report_secretary_title': 'REPORT_FORMATTING',
        'report_agency_name': 'REPORT_FORMATTING',
        'report_department_name': 'REPORT_FORMATTING',
        'report_title': 'REPORT_FORMATTING',
        'report_block_order': 'REPORT_FORMATTING',
        'report_font_name': 'REPORT_FORMATTING',
        'report_font_size': 'REPORT_FORMATTING',
        'report_margin_top': 'REPORT_FORMATTING',
        'report_margin_bottom': 'REPORT_FORMATTING',
        'report_margin_left': 'REPORT_FORMATTING',
        'report_margin_right': 'REPORT_FORMATTING',
        'report_line_spacing': 'REPORT_FORMATTING',
        'report_alignment': 'REPORT_FORMATTING',
        'report_speed_unit': 'REPORT_FORMATTING',
        'report_ordinance_enabled': 'REPORT_FORMATTING',
        'report_ordinance_number': 'REPORT_FORMATTING',
        'report_slm_device': 'REPORT_FORMATTING',
        'report_slm_gpu_layers': 'REPORT_FORMATTING',

        # Legacy XAI key aliases mapped to REPORT_FORMATTING section
        'xai_logo_path': 'REPORT_FORMATTING',
        'xai_secretary_name': 'REPORT_FORMATTING',
        'xai_secretary_title': 'REPORT_FORMATTING',
        'xai_agency_name': 'REPORT_FORMATTING',
        'xai_department_name': 'REPORT_FORMATTING',
        'xai_report_title': 'REPORT_FORMATTING',
        'xai_block_order': 'REPORT_FORMATTING',
        'xai_font_name': 'REPORT_FORMATTING',
        'xai_font_size': 'REPORT_FORMATTING',
        'xai_margin_top': 'REPORT_FORMATTING',
        'xai_margin_bottom': 'REPORT_FORMATTING',
        'xai_margin_left': 'REPORT_FORMATTING',
        'xai_margin_right': 'REPORT_FORMATTING',
        'xai_line_spacing': 'REPORT_FORMATTING',
        'xai_alignment': 'REPORT_FORMATTING',
        'xai_speed_unit': 'REPORT_FORMATTING',
        'xai_slm_device': 'REPORT_FORMATTING',
        'xai_slm_gpu_layers': 'REPORT_FORMATTING'
    }

    def __init__(self, locale_manager=None):
        """
        Initializes the manager, locating the settings.ini file using resource_path.
        """
        self.locale_manager = locale_manager
        self.config_path = resource_path(os.path.join("config", "settings.ini"))
        log_msg = self._get_string("settings_manager.init", default="[SettingsManager] Settings manager pointing to: {path}", path=self.config_path)
        logging.debug(log_msg)

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, 'get_string'):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def load_config(self) -> configparser.ConfigParser:
        """
        Reads and returns the configparser.ConfigParser instance for the settings.ini file.
        """
        config = configparser.ConfigParser()
        if not os.path.exists(self.config_path):
            logging.error(self._get_string("settings_manager.not_found", default="Configuration file not found at {path}", path=self.config_path))
            raise FileNotFoundError(f"Settings file not found at {self.config_path}")
        config.read(self.config_path, encoding='utf-8')
        return config

    def load_settings(self) -> Dict[str, Any]:
        """
        Reads the .ini file and converts it into a flat dictionary.
        (Original logic kept)
        """
        config = configparser.ConfigParser()
        if not os.path.exists(self.config_path):
            logging.error(self._get_string("settings_manager.not_found", default="Configuration file not found at {path}", path=self.config_path))
            return {}

        config.read(self.config_path, encoding='utf-8')

        settings_dict = {}
        # Mapping may need fine-tuning based on the actual contents of settings.ini and what the UI sends
        for key, section in self._KEY_TO_SECTION_MAP.items():
            if config.has_section(section) and config.has_option(section, key):
                settings_dict[key] = config.get(section, key)

        # Add boolean keys if necessary (example kept from original)
        if config.has_section('LOGGING') and config.has_option('LOGGING', 'log_step_progress'):
             # Uses original key 'log_step_progress' to read, but saves as 'log_progress' if mapped like this
             settings_dict['log_progress'] = config.getboolean('LOGGING', 'log_step_progress')
        elif config.has_section('UI') and config.has_option('UI', 'theme_dark'): # Add theme_dark
             settings_dict['theme_dark'] = config.getboolean('UI', 'theme_dark')

        # --- 12-FACTOR APP: OVERRIDE SECRETS WITH .ENV VARIABLES ---
        if load_dotenv is not None:
            load_dotenv() # Loads variables from local .env into os.environ

        env_overrides = {
            'CARINA_DB_USER': 'db_user',
            'CARINA_DB_PASSWORD': 'db_password',
            'CARINA_DB_HOST': 'db_host',
            'CARINA_DB_PORT': 'db_port',
            'CARINA_DB_NAME': 'db_name',
            'CARINA_DB_SCHEMA': 'db_schema',
            'CARINA_SNMP_COMMUNITY': 'snmp_community_string', # Not originally in INI, but good for drivers
            'CARINA_MQTT_HOST': 'monitor_mqtt_host',
            'CARINA_MQTT_PORT': 'monitor_mqtt_port',
        }
        
        for env_key, settings_key in env_overrides.items():
            env_val = os.getenv(env_key)
            if env_val and settings_key not in settings_dict:
                settings_dict[settings_key] = env_val

        # --- UNIFIED REPORT FORMATTING ALIASES (XAI, MFD, PLANNING) ---
        for k, v in list(settings_dict.items()):
            if k.startswith("xai_"):
                report_alias = "report_" + k[4:]
                if report_alias not in settings_dict:
                    settings_dict[report_alias] = v
            elif k.startswith("report_"):
                xai_alias = "xai_" + k[7:]
                if xai_alias not in settings_dict:
                    settings_dict[xai_alias] = v

        return settings_dict

    def save_settings(self, new_settings: Dict[str, Any]):
        """
        Updates and saves the .ini file with the new values.
        (Original logic kept, uses self.config_path which is now calculated with resource_path)
        """
        config = configparser.ConfigParser()
        if not os.path.exists(self.config_path):
            logging.error(self._get_string("settings_manager.save_not_found", default="Configuration file not found. Unable to save."))
            return

        config.read(self.config_path, encoding='utf-8')

        for key, value in new_settings.items():
            if key in self._KEY_TO_SECTION_MAP:
                section = self._KEY_TO_SECTION_MAP[key]
                if not config.has_section(section):
                    config.add_section(section)

                # Ensures boolean values ​​are saved as 'True'/'False' strings
                if isinstance(value, bool):
                     config.set(section, key, str(value))
                else:
                     config.set(section, key, str(value)) # Convert everything to string to save

        try:
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            logging.info(self._get_string("settings_manager.save_success", default="Settings saved successfully at {path}", path=self.config_path))
        except IOError as e:
            logging.error(self._get_string("settings_manager.save_error", default="Failed to write configuration file: {error}", error=e))