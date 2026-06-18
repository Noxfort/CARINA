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

# File: ui/handlers/locale_manager.py
# Author: Gabriel Moraes
# Date: December 16, 2025

"""
Defines the LocaleManager, the "brain" of the UI translation system.
In this version, the get_string method was updated to accept the 'default'
argument (formerly 'fallback') for compatibility with the Views.
"""

import os
import json
import logging
from typing import Dict, Any, List

from ui.handlers.settings_handler import SettingsHandler

class LocaleManager:
    """
    Manages loading and accessing the UI translation strings.
    """
    def __init__(self):
        """
        Initializes the translation manager by reading the saved
        language configuration.
        """
        self.locales_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "locales"))
        self.fallback_lang_code = "en_us"
        
        self.current_lang_data: Dict[str, Any] = {}
        self.fallback_lang_data: Dict[str, Any] = {}

        settings_handler = SettingsHandler()
        current_settings = settings_handler.get_current_settings()
        initial_lang_code = current_settings.get('language', 'pt_br')
        
        logging.info(f"[LocaleManager] Initial language set to '{initial_lang_code}' from settings.")
        self.load_language(initial_lang_code)

    def _load_file(self, lang_code: str) -> Dict[str, Any]:
        """
        Reads and processes a single JSON translation file.
        """
        file_path = os.path.join(self.locales_dir, f"{lang_code}.json")
        if not os.path.exists(file_path):
            logging.error(f"[LocaleManager] Translation file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"[LocaleManager] Failed to load or process file '{file_path}': {e}")
            return {}

    def load_language(self, lang_code: str):
        """
        Loads a new language as the primary one and ensures that the fallback language (English)
        is always loaded as a backup.
        """
        logging.info(f"[LocaleManager] Loading language: '{lang_code}'...")
        
        self.fallback_lang_data = self._load_file(self.fallback_lang_code)
        if not self.fallback_lang_data:
            logging.critical("[LocaleManager] CRITICAL FAILURE: Could not load the fallback language (en_us).")

        if lang_code == self.fallback_lang_code:
            self.current_lang_data = self.fallback_lang_data
        else:
            self.current_lang_data = self._load_file(lang_code)
        
        logging.info(f"'{lang_code}' loaded successfully.")

    def _get_nested_value(self, data: Dict, keys: List[str]) -> str | None:
        """
        Navigates a nested dictionary using a list of keys.
        """
        temp_dict = data
        for key in keys:
            if isinstance(temp_dict, dict) and key in temp_dict:
                temp_dict = temp_dict[key]
            else:
                return None
        return str(temp_dict) if isinstance(temp_dict, (str, int, float, bool)) else None

    def get_string(self, key: str, default: str = None, **kwargs) -> str:
        """
        Gets a translation string using a nested key (e.g. "main_ui.app_title").
        Implements fallback logic to English and to a default value.
        Formats the resulting string with any provided kwargs.
        """
        keys = key.split('.')
        
        # 1. Try the translation in the current language
        translation = self._get_nested_value(self.current_lang_data, keys)
        if translation is not None:
            return translation.format(**kwargs) if kwargs else translation
            
        # 2. If it fails, try the translation in the fallback language (English)
        # logging.warning(f"[LocaleManager] Key '{key}' not found in current language. Trying to fallback to English...")
        fallback_translation = self._get_nested_value(self.fallback_lang_data, keys)
        if fallback_translation is not None:
            return fallback_translation.format(**kwargs) if kwargs else fallback_translation
            
        # 3. If it fails again, use the default value provided in the call
        if default is not None:
            # logging.warning(f"[LocaleManager] Key '{key}' not found in English. Using default value.")
            return default.format(**kwargs) if kwargs else default

        # 4. As a last resort, return the key itself
        logging.error(f"[LocaleManager] Key '{key}' not found in any translation file and no default provided.")
        return key