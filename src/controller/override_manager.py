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

# File: src/controller/override_manager.py (Refactored with robust TraCIException import)
# Author: Gabriel Moraes
# Date: October 26, 2025

import logging
import os
import sys # Import sys for path manipulation
import json
from typing import Dict, Tuple, TYPE_CHECKING

# Add 'src' directory to path (kept)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    # Assume LocaleManagerBackend is in src/utils
    from utils.locale_manager_backend import LocaleManagerBackend

class EnvironmentConnectionException(Exception):
    pass

class OverrideManager:
    """
    A specialist that manages the state and execution of manual overrides
    on traffic lights, persisting their state to disk.
    """
    def __init__(self, locale_manager: 'LocaleManagerBackend'): # Fixed type hint
        self.locale_manager = locale_manager
        self.active_overrides: Dict[str, str] = {}
        self.state_file_path: str | None = None
        logging.info("Manual Overrides Manager created.")

    def init_persistence(self, scenario_name: str):
        """
        Defines the state file path and loads the previous state.
        """
        if not scenario_name:
            logging.error("[OverrideManager] Scenario name not provided. Override persistence is disabled.")
            return

        # Recalculate project_root here too to ensure
        from src.utils.paths import get_base_output_dir
        scenario_dir = os.path.join(get_base_output_dir(), "results", scenario_name)
        os.makedirs(scenario_dir, exist_ok=True)
        self.state_file_path = os.path.join(scenario_dir, "override_state.json")
        self._load_state_from_disk()

    def _load_state_from_disk(self):
        """Reads the state JSON file, if it exists."""
        if self.state_file_path and os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    self.active_overrides = json.load(f)
                logging.info(f"Override state loaded from {self.state_file_path}. {len(self.active_overrides)} traffic lights in manual mode.")
            except (IOError, json.JSONDecodeError) as e:
                logging.error(f"Error loading override state: {e}")

    def _save_state_to_disk(self):
        """Saves the active overrides dictionary to the JSON file."""
        if not self.state_file_path:
            logging.warning("[OverrideManager] Attempted to save override state before full initialization. Ignoring.")
            return
        try:
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(self.active_overrides, f, indent=4)
        except IOError as e:
            logging.error(f"Error saving override state: {e}")

    def restore_sumo_state(self, sumo_conn):
        """
        Applies the loaded override states to the SUMO simulation.
        """
        if not self.active_overrides or not sumo_conn: # Add sumo_conn check
            return

        logging.info("Restoring manual override states in SUMO simulation...")
        for semaphore_id, state in self.active_overrides.items():
            payload = {"semaphore_id": semaphore_id, "state": state}
            # Calls handle_ui_command which already has the try/except TraCIException
            self.handle_ui_command(payload, sumo_conn, is_restoring=True)

    def handle_ui_command(self, payload: Dict, sumo_conn, is_restoring: bool = False):
        """
        Processes an override command from UI and applies it to SUMO.
        """
        semaphore_id = payload.get("semaphore_id")
        state = payload.get("state")

        if not semaphore_id or not state or not sumo_conn: # Add sumo_conn check
            logging.warning(f"[OverrideManager] Invalid UI command or missing SUMO connection. Payload: {payload}")
            return

        try:
            # Checks if the traffic light exists in the simulation before trying to control it
            # (May be useful if the state is loaded from a different scenario)
            all_tls_ids = sumo_conn.trafficlight.getIDList()
            if semaphore_id not in all_tls_ids:
                 logging.warning(f"[OverrideManager] Override attempt on traffic light '{semaphore_id}' which does not exist in current simulation. Ignoring.")
                 # Removes from active state if no longer exists
                 if semaphore_id in self.active_overrides:
                     del self.active_overrides[semaphore_id]
                     if not is_restoring: self._save_state_to_disk()
                 return

            if state == "ALERT":
                self.active_overrides[semaphore_id] = state
                if not is_restoring: logging.info(f"[Agnostic] Traffic light '{semaphore_id}' commanded to Alert state.")

            elif state == "OFF":
                self.active_overrides[semaphore_id] = state
                if not is_restoring: logging.info(f"[Agnostic] Traffic light '{semaphore_id}' commanded to Disabled state.")

            elif state == "NORMAL":
                if semaphore_id in self.active_overrides:
                    del self.active_overrides[semaphore_id]
                if not is_restoring: logging.info(f"[Agnostic] Traffic light '{semaphore_id}' returned to automatic control.")

            if not is_restoring:
                self._save_state_to_disk()

        except Exception as e_general: 
             logging.error(f"Unexpected error applying override for '{semaphore_id}': {e_general}", exc_info=True)


    def is_ai_command_blocked(self, request: Tuple) -> bool:
        """Checks if a command from the AI should be blocked due to an override."""
        # The internal logic remains the same
        try:
            module_name, func_name, args, _ = request
            # Only blocks 'setPhase' commands from AI for traffic lights with active override
            if module_name == 'trafficlight' and func_name == 'setPhase' and args:
                tl_id = args[0]
                if tl_id in self.active_overrides:
                    # Skipped action log is handled in request_processor
                    return True
        except (IndexError, TypeError, ValueError) as e:
             # Error unpacking the request - logs in and considers it not blocked for security
             logging.warning(f"[OverrideManager] Error parsing AI request for blocking: {e}. Request: {request}")
        return False