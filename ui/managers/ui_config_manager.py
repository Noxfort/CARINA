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

# File: ui/managers/ui_config_manager.py
# Author: Gabriel Moraes
# Date: June 17, 2026

"""
Defines the UIConfigManager.
Loads visual/layout configuration parameters from a JSON configuration file.
"""

import json
import os
import logging
from src.utils.paths import resource_path

class UIConfigManager:
    """
    Manager responsible for loading and resolving UI configuration parameters from JSON.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UIConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.filepath = resource_path(os.path.join("config", "ui_config.json"))
        self.config = {}
        self.load()
        self._initialized = True

    def load(self):
        default_config = {
            "live_map": {
                "chrome_width_offset": 420,
                "chrome_height_offset": 160,
                "bgcolor": "#F7F7F7",
                "border_radius": 10,
                "initial_canvas_width": 1280,
                "initial_canvas_height": 720,
                "double_click_time_threshold": 0.3
            }
        }
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                logging.error(f"[UIConfigManager] Erro ao carregar ui_config.json: {e}")
                self.config = default_config
        else:
            self.config = default_config

    def get_section(self, section_name: str) -> dict:
        return self.config.get(section_name, {})

# Global singleton instance
ui_config = UIConfigManager()
