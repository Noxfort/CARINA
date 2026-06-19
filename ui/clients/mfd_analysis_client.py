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

# File: ui/clients/mfd_analysis_client.py
# Author: Gabriel Moraes
# Date: June 19, 2026

import os
import json
import threading
import time
import logging
from typing import Callable, Optional

class MfdAnalysisClient:
    """
    Manages communication to trigger MFD optimization analysis report generation.
    Handles file-based IPC between the UI and the XaiWorker backend.
    """
    def __init__(self, on_analysis_complete_callback: Callable[[dict], None], results_dir: Optional[str] = None):
        """
        Initializes the client.

        Args:
            on_analysis_complete_callback: Function to be called when the MFD report is ready.
            results_dir: Optional directory path of the active scenario results.
        """
        self.on_analysis_complete = on_analysis_complete_callback
        self.results_dir = results_dir
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def _get_active_scenario_path(self) -> Optional[str]:
        """Returns self.results_dir if set, otherwise finds the latest scenario path."""
        if self.results_dir and os.path.exists(self.results_dir):
            return self.results_dir
        return self._find_latest_scenario_path()

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
            logging.error(f"[MfdAnalysisClient] Error finding latest scenario: {e}")
            return None
        return None

    def start_analysis(self):
        """
        Starts the MFD optimization analysis in a new thread. Returns immediately.
        The result will be delivered via the callback.
        """
        thread = threading.Thread(
            target=self._analysis_worker_thread_target,
            args=("mfd",),
            daemon=True
        )
        thread.start()

    def _analysis_worker_thread_target(self, req_id: str = "mfd", timeout_seconds: int = 300):
        """
        Main worker loop for the MFD analysis request.
        Writes a .request file and polls for a .response file.
        """
        scenario_path = self._get_active_scenario_path()
        if not scenario_path:
            if self.on_analysis_complete:
                self.on_analysis_complete({"status": "error", "message": "Scenario directory 'results' not found."})
            return

        try:
            mfd_base_dir = os.path.join(scenario_path, "mfd_analysis")
            requests_dir = os.path.join(mfd_base_dir, "requests")
            responses_dir = os.path.join(mfd_base_dir, "responses")
            os.makedirs(requests_dir, exist_ok=True)
            os.makedirs(responses_dir, exist_ok=True)

            request_path = os.path.join(requests_dir, f"{req_id}.request")
            response_path = os.path.join(responses_dir, f"{req_id}.response")

            # Clean up old files
            if os.path.exists(response_path): 
                os.remove(response_path)
            if os.path.exists(request_path): 
                os.remove(request_path)

            # Write request
            with open(request_path, "w", encoding="utf-8") as f:
                json.dump({"request_id": req_id, "timestamp": time.time()}, f)
            
            logging.info(f"[MfdAnalysisClient] Request sent for MFD analysis.")
        
        except Exception as e:
            logging.error(f"[MfdAnalysisClient] Failed to create request file: {e}")
            if self.on_analysis_complete:
                self.on_analysis_complete({"status": "error", "message": f"Failed to create request file: {e}"})
            return

        # Poll for response
        start_time = time.time()
        response_data = None
        
        while time.time() - start_time < timeout_seconds:
            if os.path.exists(response_path):
                try:
                    time.sleep(0.2) 
                    with open(response_path, "r", encoding="utf-8") as f:
                        response_data = json.load(f)
                    os.remove(response_path)
                    break 
                except Exception as e:
                    logging.error(f"[MfdAnalysisClient] Error reading response: {e}")
                    response_data = {"status": "error", "message": f"Failed to read response file: {e}"}
                    break
            time.sleep(2)

        if response_data is None: 
            response_data = {"status": "error", "message": "Timeout. The analysis backend did not respond in time."}
        
        if self.on_analysis_complete:
            self.on_analysis_complete(response_data)
