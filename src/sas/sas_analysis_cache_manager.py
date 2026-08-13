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

# File: src/sas/sas_analysis_cache_manager.py
# Author: Gabriel Moraes
# Date: August 12, 2026

import os
import json
import logging
from typing import Tuple, Optional


class SASAnalysisCacheManager:
    """
    Handles loading and saving of previous SAS analysis cache snapshots
    for change detection across analysis runs (DB primary + file backup).
    """

    def load_cache(self, db_manager, scenario_name: str, scenario_dir: Optional[str]) -> Tuple[dict, bool]:
        """Loads previous analysis cache snapshot from DB or JSON file fallback."""
        last_analysis_path = os.path.join(scenario_dir, "sas_last_analysis.json") if scenario_dir else None
        last_analysis_cache = {}
        has_previous_report = False

        if db_manager is not None:
            try:
                last_analysis_cache = db_manager.get_sas_analysis_cache(scenario_name)
                if last_analysis_cache:
                    has_previous_report = True
            except Exception as e:
                logging.warning(f"[SAS_CACHE_MANAGER] Failed to load cache from database: {e}")

        # Fallback to local JSON file if cache was not loaded from DB
        if not last_analysis_cache and last_analysis_path and os.path.exists(last_analysis_path):
            try:
                with open(last_analysis_path, "r", encoding="utf-8") as f:
                    last_analysis_cache = json.load(f)
                has_previous_report = True
            except Exception as e:
                logging.warning(f"[SAS_CACHE_MANAGER] Failed to load cache from file: {e}")

        return last_analysis_cache, has_previous_report

    def save_cache(self, db_manager, scenario_name: str, scenario_dir: Optional[str], new_cache_data: dict):
        """Saves current analysis cache snapshot into DB and JSON file backup."""
        if not new_cache_data:
            return

        if db_manager is not None:
            try:
                db_manager.save_sas_analysis_cache(scenario_name, new_cache_data)
            except Exception as e:
                logging.error(f"[SAS_CACHE_MANAGER] Failed to save cache into database: {e}")

        if scenario_dir:
            last_analysis_path = os.path.join(scenario_dir, "sas_last_analysis.json")
            try:
                with open(last_analysis_path, "w", encoding="utf-8") as f:
                    json.dump(new_cache_data, f, indent=4)
            except Exception as e:
                logging.error(f"[SAS_CACHE_MANAGER] Failed to save cache into file: {e}")
