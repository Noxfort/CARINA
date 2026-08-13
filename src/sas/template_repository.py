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

# File: src/sas/template_repository.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import os
import json
import logging
from typing import Dict, Any

class TemplateRepository:
    """
    Responsibility (SRP & DIP): Handles file I/O operations for reading report templates 
    from config/report_templates.json and managing memory caching.
    Follows SOLID principles.
    """
    _templates_cache: Dict[str, Any] = None

    @classmethod
    def load_templates(cls) -> dict:
        """
        Loads and merges modular template JSON files into memory cache if not already cached.

        :return: Dictionary containing parsed JSON template configurations
        """
        if cls._templates_cache is not None:
            return cls._templates_cache

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_dir = os.path.join(base_dir, "config")

        modular_files = [
            "sas_report_sections.json",
            "sas_intersection_templates.json",
            "sas_recommendation_labels.json",
            "sas_summary_directives.json",
            "report_templates.json"  # Optional legacy fallback
        ]

        merged_cache = {}
        loaded_count = 0

        for filename in modular_files:
            json_path = os.path.join(config_dir, filename)
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        merged_cache.update(data)
                        loaded_count += 1
                        logging.info(f"[TEMPLATE_REPOSITORY] Loaded modular template config: {filename}")
                except Exception as e:
                    logging.warning(f"[TEMPLATE_REPOSITORY] Failed to load JSON '{json_path}': {e}")

        cls._templates_cache = merged_cache
        if loaded_count > 0:
            logging.info(f"[TEMPLATE_REPOSITORY] Successfully unified {loaded_count} modular template files in cache.")
        else:
            logging.error("[TEMPLATE_REPOSITORY] No template configuration files could be loaded.")

        return cls._templates_cache

    @classmethod
    def get_template_value(cls, key: str, language: str, default: str = "") -> str:
        """
        Retrieves a bilingual text value from template storage using target language fallback keys.

        :param key: Configuration key name in template JSON
        :param language: Target language code (e.g., pt_br, en)
        :param default: Fallback default string if key is not found
        :return: Retrieved text string
        """
        templates = cls.load_templates()
        lang = (language or "pt_br").lower()

        item = templates.get(key, {})
        if isinstance(item, dict):
            return item.get(lang, item.get("pt_br", default))
        return default

    @classmethod
    def get_layout_translations(cls, language: str) -> dict:
        """
        Retrieves layout translation dictionary for UI elements.

        :param language: Target language code
        :return: Layout translations dictionary
        """
        templates = cls.load_templates()
        translations = templates.get("translations", {})
        lang_key = (language or "pt_br").lower()
        return translations.get(lang_key, translations.get("pt_br", {}))

    @classmethod
    def get_cluster_prefix(cls, language: str = "pt_br") -> str:
        """
        Retrieves localized cluster prefix string.

        :param language: Target language code
        :return: Cluster prefix string
        """
        translations = cls.get_layout_translations(language)
        return translations.get("cluster_prefix", "Agrupamento" if (language or "pt_br").lower() == "pt_br" else "Cluster")
