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

# File: ui/clients/xai_client.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import os
import json
import threading
import time
import logging
from typing import Callable, List, Optional

class XaiClient:
    """
    Manages communication to initiate XAI analyses and load the agent list.
    Handles file-based IPC between the UI and the XaiWorker backend.
    """
    def __init__(self, on_analysis_complete_callback: Callable[[dict], None]):
        """
        Initializes the client.

        Args:
            on_analysis_complete_callback: Function to be called when the XAI analysis is complete.
        """
        self.on_analysis_complete = on_analysis_complete_callback
        # Assuming file structure: project_root/ui/clients/xai_client.py
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def _find_latest_scenario_path(self) -> Optional[str]:
        """Finds the absolute path to the most recent scenario folder in 'results'."""
        try:
            from src.utils.paths import get_base_output_dir
            results_dir = os.path.join(get_base_output_dir(), "results")
            if os.path.exists(results_dir):
                ignored_dirs = {"database"}
                all_scenarios = [
                    d for d in os.listdir(results_dir) 
                    if os.path.isdir(os.path.join(results_dir, d)) and d not in ignored_dirs
                ]
                if all_scenarios:
                    latest_scenario_name = max(all_scenarios, key=lambda d: os.path.getmtime(os.path.join(results_dir, d)))
                    return os.path.join(results_dir, latest_scenario_name)
        except Exception as e:
            logging.error(f"[XaiClient] Error finding latest scenario: {e}")
            return None
        return None

    def _get_agent_list_sync(self) -> List[str]:
        """
        Reads status.json from the most recent scenario and returns the list of agent IDs.
        Private method intended to be run in a thread.
        """
        latest_scenario_path = self._find_latest_scenario_path()
        if not latest_scenario_path:
            return []
        try:
            status_file_path = os.path.join(latest_scenario_path, "status.json")
            if os.path.exists(status_file_path):
                with open(status_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("agent_ids", [])
        except Exception as e:
            logging.error(f"[XaiClient] Error loading agent list: {e}")
            return []
        return []
        
    def _fetch_agent_list_thread_target(self, on_list_loaded_callback: Callable[[List[str]], None]):
        """
        Background target: fetches the agent list and invokes the callback.
        """
        agent_ids = self._get_agent_list_sync()
        if on_list_loaded_callback:
            on_list_loaded_callback(agent_ids)

    def start_fetching_agent_list(self, on_list_loaded_callback: Callable[[List[str]], None]):
        """
        Starts fetching the agent list in a new thread to avoid blocking the UI.
        """
        logging.info("[XaiClient] Starting asynchronous agent list fetch...")
        thread = threading.Thread(
            target=self._fetch_agent_list_thread_target,
            args=(on_list_loaded_callback,),
            daemon=True
        )
        thread.start()

    def start_analysis(self, agent_id: str):
        """
        Starts the XAI analysis in a new thread. Returns immediately.
        The result will be delivered via the callback provided in __init__.
        """
        thread = threading.Thread(
            target=self._analysis_worker_thread_target,
            args=(agent_id,),
            daemon=True
        )
        thread.start()

    def _analysis_worker_thread_target(self, agent_id: str, timeout_seconds: int = 300):
        """
        Main worker loop for the analysis request.
        Writes a .request file and polls for a .response file.
        """
        scenario_path = self._find_latest_scenario_path()
        if not scenario_path:
            if self.on_analysis_complete:
                self.on_analysis_complete({"status": "error", "message": "Scenario directory 'results' not found."})
            return

        try:
            # Ensure paths match the backend structure
            captum_base_dir = os.path.join(scenario_path, "captum")
            requests_dir = os.path.join(captum_base_dir, "requests")
            responses_dir = os.path.join(captum_base_dir, "responses")
            os.makedirs(requests_dir, exist_ok=True)
            os.makedirs(responses_dir, exist_ok=True)

            request_path = os.path.join(requests_dir, f"{agent_id}.request")
            response_path = os.path.join(responses_dir, f"{agent_id}.response")

            # Clean up old files to avoid false positives
            if os.path.exists(response_path): 
                os.remove(response_path)
            if os.path.exists(request_path): 
                os.remove(request_path)

            # Write request
            with open(request_path, "w", encoding="utf-8") as f:
                json.dump({"agent_id": agent_id}, f)
            
            logging.info(f"[XaiClient] Request sent for Agent {agent_id}")
        
        except Exception as e:
            logging.error(f"[XaiClient] Failed to create request file: {e}")
            if self.on_analysis_complete:
                self.on_analysis_complete({"status": "error", "message": f"Failed to create request file: {e}"})
            return

        # Poll for response
        start_time = time.time()
        response_data = None
        
        while time.time() - start_time < timeout_seconds:
            if os.path.exists(response_path):
                try:
                    # Small delay to ensure file write is complete
                    time.sleep(0.2) 
                    with open(response_path, "r", encoding="utf-8") as f:
                        response_data = json.load(f)
                    
                    # Cleanup response file after reading
                    os.remove(response_path)
                    break 
                except Exception as e:
                    logging.error(f"[XaiClient] Error reading response: {e}")
                    response_data = {"status": "error", "message": f"Failed to read response file: {e}"}
                    break
            time.sleep(2)

        if response_data is None: 
            response_data = {"status": "error", "message": "Timeout. The XAI backend did not respond in time."}
        
        # Delivery result
        if self.on_analysis_complete:
            self.on_analysis_complete(response_data)