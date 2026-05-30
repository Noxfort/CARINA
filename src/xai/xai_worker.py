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

# File: src/xai/xai_worker.py
# Author: Gabriel Moraes
# Date: December 17, 2025

import logging
import os
import json
import time
import sys
import re
import subprocess
import configparser
import torch

from typing import Dict, Any

from xai.request_scanner import RequestScanner
from xai.agent_reconstructor import AgentReconstructor
from xai.report_pipeline import ReportPipeline

class XAIOrchestrator:
    """
    Responsibility: Coordinate the Explanable AI pipeline by delegating 
    tasks to the Scanner (File I/O), Reconstructor (Memory), and Pipeline (Math/NLP).
    """
    def __init__(self, scenario_results_dir: str):
        self.scenario_results_dir = scenario_results_dir
        
        captum_base_dir = os.path.join(scenario_results_dir, "captum")
        requests_dir = os.path.join(captum_base_dir, "requests")
        responses_dir = os.path.join(captum_base_dir, "responses")
        reports_dir = os.path.join(captum_base_dir, "reports")
        checkpoints_dir = os.path.join(scenario_results_dir, "checkpoints")
        
        os.makedirs(reports_dir, exist_ok=True)
        
        # Inject Dependencies
        self.scanner = RequestScanner(requests_dir, responses_dir)
        self.reconstructor = AgentReconstructor(checkpoints_dir)
        self.pipeline = ReportPipeline(scenario_results_dir, reports_dir)

    def process_job(self, agent_id: str):
        """Executes a single end-to-end Explainability job."""
        logging.info(f"[XAI_ORCHESTRATOR] Processing request for Agent: {agent_id}")
        
        response_data = {"status": "error", "message": "Unknown error"}
        
        try:
            # 1. Reconstruct Blind Agent
            agent = self.reconstructor.reconstruct_agent(agent_id)
            
            # 2. Run Math & Transducer
            response_data = self.pipeline.generate_full_report(agent, agent_id)
            
        except Exception as e:
            logging.error(f"[XAI_ORCHESTRATOR] Pipeline error for {agent_id}: {e}", exc_info=True)
            response_data = {"status": "error", "message": str(e)}
        finally:
            # 3. Clean up and respond
            self.scanner.write_response(agent_id, response_data)
            self.scanner.clear_request(agent_id)
            logging.info(f"[XAI_ORCHESTRATOR] Job finished for {agent_id}.")

    def run_forever(self):
        """Blocking event loop."""
        logging.info(f"[XAI_ORCHESTRATOR] Service started. Watching: {self.scanner.requests_dir}")
        while True:
            try:
                pending_jobs = self.scanner.get_pending_requests()
                
                if not pending_jobs:
                    time.sleep(2)
                    continue
                    
                for agent_id in pending_jobs:
                    self.process_job(agent_id)
                    
                time.sleep(1)
                
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e:
                logging.error(f"[XAI_ORCHESTRATOR] Critical Loop Error: {e}", exc_info=True)
                time.sleep(5)
                
        logging.info("[XAI_ORCHESTRATOR] Shutdown.")


def run_xai_worker(settings: configparser.ConfigParser, scenario_results_dir: str):
    """Entry point for multiprocessing."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from utils.logging_setup import setup_logging
    
    from src.utils.paths import get_base_output_dir
    log_dir = os.path.join(get_base_output_dir(), "logs", "xai_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    orchestrator = XAIOrchestrator(scenario_results_dir)
    orchestrator.run_forever()