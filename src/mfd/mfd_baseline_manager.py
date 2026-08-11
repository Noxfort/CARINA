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

# File: src/xai/mfd_baseline_manager.py
# Author: Gabriel Moraes
# Date: July 03, 2026

import os
import json
import logging

class MFDReportBaselineManager:
    """Manages saving and loading of baseline MFD analysis files (raw, unformatted values)."""

    @staticmethod
    def load_baselines(scenario_results_dir: str = None, scenario_name: str = None, db_manager=None) -> tuple[dict, dict]:
        last_data = {}
        first_data = {}

        if not scenario_name and scenario_results_dir:
            scenario_name = os.path.basename(os.path.normpath(scenario_results_dir))

        if db_manager is not None and scenario_name:
            try:
                db_last, db_first = db_manager.get_mfd_analysis_baselines(scenario_name)
                if db_last:
                    last_data = db_last
                if db_first:
                    first_data = db_first
            except Exception as e:
                logging.warning(f"[MFD_BASELINE_MANAGER] Failed to load baselines from database: {e}")

        # Fallback to local files if not fully loaded from database
        if scenario_results_dir:
            last_analysis_path = os.path.join(scenario_results_dir, "mfd_last_analysis.json")
            first_analysis_path = os.path.join(scenario_results_dir, "mfd_first_analysis.json")

            if not last_data and os.path.exists(last_analysis_path):
                try:
                    with open(last_analysis_path, "r", encoding="utf-8") as f:
                        last_data = json.load(f)
                except Exception as e:
                    logging.warning(f"[MFD_BASELINE_MANAGER] Failed to load previous analysis: {e}")

            if not first_data and os.path.exists(first_analysis_path):
                try:
                    with open(first_analysis_path, "r", encoding="utf-8") as f:
                        first_data = json.load(f)
                except Exception as e:
                    logging.warning(f"[MFD_BASELINE_MANAGER] Failed to load first analysis baseline: {e}")

        return last_data, first_data

    @staticmethod
    def save_baselines(scenario_results_dir: str = None, current_analysis_snapshot: dict = None, scenario_name: str = None, db_manager=None) -> None:
        if not current_analysis_snapshot:
            return

        if not scenario_name and scenario_results_dir:
            scenario_name = os.path.basename(os.path.normpath(scenario_results_dir))

        # Save to Database as primary storage
        if db_manager is not None and scenario_name:
            try:
                db_manager.save_mfd_analysis_baselines(scenario_name, current_analysis_snapshot)
            except Exception as e:
                logging.error(f"[MFD_BASELINE_MANAGER] Failed to save baselines in database: {e}")

        # Save local JSON file backups
        if scenario_results_dir:
            last_analysis_path = os.path.join(scenario_results_dir, "mfd_last_analysis.json")
            first_analysis_path = os.path.join(scenario_results_dir, "mfd_first_analysis.json")

            # Overwrite mfd_last_analysis.json
            try:
                with open(last_analysis_path, "w", encoding="utf-8") as f:
                    json.dump(current_analysis_snapshot, f, indent=4)
            except Exception as e:
                logging.error(f"[MFD_BASELINE_MANAGER] Failed to save current analysis: {e}")

            # Save first analysis ONLY if it does not exist locally
            if not os.path.exists(first_analysis_path):
                try:
                    with open(first_analysis_path, "w", encoding="utf-8") as f:
                        json.dump(current_analysis_snapshot, f, indent=4)
                    logging.info("[MFD_BASELINE_MANAGER] First analysis baseline saved.")
                except Exception as e:
                    logging.error(f"[MFD_BASELINE_MANAGER] Failed to save first analysis baseline: {e}")
