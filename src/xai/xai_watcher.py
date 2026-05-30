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

# File: src/xai/xai_watcher.py
# Author: Gabriel Moraes
# Date: December 16, 2025

import logging
import os
import json
import threading
import time
from xai.captum_analyzer import CaptumAnalyzer
from engine.environment import SumoEnvironment
from core.population_manager import PopulationManager
from core.lifecycle_manager import LifecycleManager
from core.strategic_coordinator import StrategicCoordinator

class XaiWatcher:
    """
    Watches a folder for XAI request files, triggers the analyzer, and creates
    a response file. Acts as a bridge between the UI/External requests and the internal logic.
    """
    def __init__(self, population_manager: PopulationManager, lifecycle_manager: LifecycleManager, 
                 env: SumoEnvironment, strategic_coordinator: StrategicCoordinator):
        self.population_manager = population_manager
        self.lifecycle_manager = lifecycle_manager
        self.env = env
        self.strategic_coordinator = strategic_coordinator
        self.watcher_thread = None
        self.watcher_running = False

    def start(self):
        """Starts the watcher thread."""
        self.watcher_running = True
        self.watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self.watcher_thread.start()

    def stop(self):
        """Stops the watcher thread."""
        self.watcher_running = False

    def _watcher_loop(self):
        """
        Main loop that monitors the 'captum/requests' directory.
        """
        logging.info("[XAI_WATCHER] XAI analysis watcher started.")
        while self.watcher_running:
            try:
                # Wait until the scenario directory is available
                if not self.lifecycle_manager or not self.lifecycle_manager.scenario_checkpoint_dir:
                    time.sleep(5)
                    continue
                
                scenario_results_dir = os.path.dirname(self.lifecycle_manager.scenario_checkpoint_dir)
                base_dir = os.path.join(scenario_results_dir, "captum")
                requests_dir = os.path.join(base_dir, "requests")
                responses_dir = os.path.join(base_dir, "responses")
                os.makedirs(requests_dir, exist_ok=True)
                os.makedirs(responses_dir, exist_ok=True)
                
                # Check for .request files
                for request_filename in os.listdir(requests_dir):
                    if not request_filename.endswith(".request"): continue

                    request_path = os.path.join(requests_dir, request_filename)
                    response_filename = request_filename.replace(".request", ".response")
                    response_path = os.path.join(responses_dir, response_filename)
                    response_tmp_path = response_path + ".tmp"
                    response_data = {}

                    try:
                        logging.info(f"[XAI_WATCHER] Request '{request_filename}' detected. Processing...")
                        
                        # Read request
                        with open(request_path, "r", encoding="utf-8") as f:
                            request_data = json.load(f)
                        
                        agent_id = request_data.get("agent_id")
                        agent = self.population_manager.agents.get(agent_id)

                        if agent and self.env.state_extractor and self.strategic_coordinator:
                            # 1. Build the glossary for the specific agent
                            full_glossary = self.env.state_extractor.get_local_feature_glossary(agent_id)
                            
                            # 2. Add padding explanations (if applicable based on architecture)
                            max_local_dim = self.strategic_coordinator.max_state_dim
                            padding_needed = max_local_dim - len(full_glossary)
                            for i in range(padding_needed):
                                full_glossary.append({
                                    "feature_name": f"Padding (Idx {i})",
                                    "description": "Padding to normalize input size. Not a real sensor."
                                })
                            
                            # 3. Add GAT (Strategic) explanations
                            gat_dim = self.strategic_coordinator.output_dim
                            for i in range(gat_dim):
                                full_glossary.append({
                                    "feature_name": f"Strategic Vector (Comp. {i+1})",
                                    "description": f"Strategic orientation component #{i+1}, summarizing neighbor traffic state."
                                })
                            
                            # 4. Instantiate Analyzer with the glossary
                            analyzer = CaptumAnalyzer(
                                agent=agent, 
                                scenario_results_dir=scenario_results_dir,
                                feature_glossary=full_glossary # Injecting glossary here
                            )
                            
                            # 5. Generate Analysis
                            analysis_result = analyzer.generate_analysis()
                            
                            if analysis_result:
                                response_data = {
                                    "status": "complete", 
                                    "image_path": analysis_result.get("image_path"),
                                    "text_path": analysis_result.get("text_path")
                                }
                            else:
                                response_data = {
                                    "status": "error", 
                                    "message": "Failed to generate analysis files. Check backend logs."
                                }
                        else:
                            response_data = {
                                "status": "error", 
                                "message": f"Agent '{agent_id}' or essential components not found."
                            }
                    except Exception as e:
                        logging.error(f"[XAI_WATCHER] Error processing request: {e}", exc_info=True)
                        response_data = {"status": "error", "message": str(e)}
                    
                    finally:
                        # Write response atomically
                        try:
                            with open(response_tmp_path, "w", encoding="utf-8") as f:
                                json.dump(response_data, f, indent=4)
                            os.rename(response_tmp_path, response_path)
                        except Exception as e:
                            logging.error(f"[XAI_WATCHER] Critical failure writing response file: {e}")
                        
                        # Clean up request file
                        if os.path.exists(request_path):
                            os.remove(request_path)
                        
                        logging.info(f"[XAI_WATCHER] Response for '{response_filename}' sent.")

                time.sleep(2)
            except Exception as e:
                logging.error(f"[XAI_WATCHER] Critical error in watcher loop: {e}", exc_info=True)
                time.sleep(10)
        
        logging.info("[XAI_WATCHER] XAI analysis watcher finished.")